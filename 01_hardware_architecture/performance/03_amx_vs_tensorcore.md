# CPU AMX vs GPU Tensor Core：混合計算場景分析

> 基於 Intel Xeon Platinum 8470Q (Sapphire Rapids, 支持 AMX) + NVIDIA RTX 5090 (Blackwell Tensor Core) 實際環境。

---

## 1. 什麼是 AMX

**AMX (Advanced Matrix Extensions)** 是 Intel 從 Sapphire Rapids (第 4 代 Xeon) 起引入的矩陣運算擴展指令集，對標 NVIDIA Tensor Core。

### 1.1 核心元件

| 元件                     | 說明                                    |
| ------------------------ | --------------------------------------- |
| **Tile Register**        | 8 個 2D 寄存器 (1KB each)，儲存矩陣資料 |
| `tdpbf16ps`              | BF16 矩陣乘 + FP32 累加                 |
| `tdpbusd`                | INT8 矩陣乘 + INT32 累加                |
| `tdpbuud`                | UINT8 矩陣乘 + UINT32 累加              |
| `tileload` / `tilestore` | Tile 暫存器與記憶體之間的資料搬運         |

### 1.2 本環境確認

```bash
lscpu | grep -E "amx_bf16|amx_tile|amx_int8"
# Flags: ... amx_bf16 amx_tile amx_int8 ...
```

三個 AMX 相關 flag 全部存在，確認 Sapphire Rapids 完整支持 AMX。

---

## 2. AMX vs Tensor Core 對比

### 2.1 硬體規格

| 維度      | Intel AMX (SPR)                 | NVIDIA Tensor Core (RTX 5090)    |
| --------- | ------------------------------- | -------------------------------- |
| 架構      | Sapphire Rapids                 | Blackwell                        |
| FP32 核心 | AVX-512 (2×512b FMA)            | CUDA Cores (170 SM × 128)        |
| 矩陣加速  | AMX tile (8×1KB)                | 5th Gen Tensor Core              |
| BF16 算力 | ~106-130 TFLOPS/socket (估算*)  | ~209.5 TFLOPS dense (官方規格頁) |
| INT8 算力 | ~200+ TOPS/socket (估算*)       | 數百 TOPS                        |
| 記憶體      | DDR5, ~307 GB/s (8 通道)        | GDDR7, 1792 GB/s                 |
| 功耗      | 350W/socket                     | 575W                             |
| 延遲      | 極低 (無 PCIe 開銷)             | 需經 PCIe 傳輸資料               |

\* AMX 算力按每核峰值模型估算：每核 1024 BF16 FLOP/cycle（Intel 官方口徑，約 16× AVX-512 FP32），8470Q 52 核 × 2.0-2.4 GHz 得 ~106-130 TFLOPS/socket，INT8 翻倍約 200+ TOPS。未找到 8470Q 的直接實測資料。DDR5 側 8 通道 DDR5-4800 理論頻寬約 307 GB/s/socket；~480 GB/s 需 12 通道，是 Granite Rapids 級別。

### 2.2 適用場景

| 場景                    | 推薦              | 原因                      |
| ----------------------- | ----------------- | ------------------------- |
| 大規模矩陣乘 (GEMM)     | GPU Tensor Core   | BF16 dense 算力約 2-4 倍，同一數量級 |
| 小 batch 推理 (< 4)     | CPU AMX           | 避免 PCIe 往返延遲        |
| 實時性要求高            | CPU AMX           | 確定性延遲，無 PCIe       |
| 訓練大批次              | GPU Tensor Core   | 高吞吐                    |
| 混合管道 (預處理→推理)  | AMX + Tensor Core | CPU 預處理 + GPU 核心計算 |
| 已有 CPU 管線，GPU 離線 | CPU AMX           | 減少架構改動成本          |

---

## 3. AMX 程式設計模型

### 3.1 透過 Intel AMX Intrinsics (C)

```c
#include <immintrin.h>

void amx_matmul_bf16() {
    // 1. 配置 tile 寄存器
    _tile_loadconfig(&config);

    // 2. 載入矩陣到 tile 寄存器
    _tile_loadd(0, buf_a, stride_a);  // A → tile 0
    _tile_loadd(1, buf_b, stride_b);  // B → tile 1
    _tile_loadd(2, buf_c, stride_c);  // C → tile 2

    // 3. 矩陣乘: tile[2] += tile[0] × tile[1]
    _tile_dpbf16ps(2, 0, 1);

    // 4. 儲存結果
    _tile_stored(2, buf_c, stride_c);

    // 5. 釋放 tile 寄存器
    _tile_release();
}
```

### 3.2 透過 PyTorch (高層封裝)

```python
import torch

# CPU 上使用 AMX（PyTorch 2.0+ 自動利用）
x = torch.randn(1024, 1024, dtype=torch.bfloat16)
w = torch.randn(1024, 1024, dtype=torch.bfloat16)

# PyTorch 在 SPR 上自動排程到 AMX
y = torch.matmul(x, w)
```

### 3.3 編譯要求

```bash
# C 程式碼編譯 (需 GCC 12+ 或 Intel Compiler)
gcc -march=sapphirerapids -mamx-bf16 -mamx-tile -mamx-int8 \
    -o amx_test amx_test.c
```

---

## 4. 混合場景：CPU AMX + GPU Tensor Core 協同

### 4.1 典型 Pipeline

```text
資料輸入 → CPU AMX 預處理 (tokenize/embed) → GPU Core (attention/FFN) → CPU 後處理
```

### 4.2 非同步流水線虛擬碼

```c
// 階段 1: CPU AMX 做 embedding 查表 + 投影
// (在 CPU pinned memory 中完成)
compute_embedding_amx(input, cpu_buffer);

// 階段 2: 非同步 H2D
cudaMemcpyAsync(gpu_buffer, cpu_buffer, size,
                cudaMemcpyHostToDevice, stream);

// 階段 3: GPU Tensor Core 做 attention
launch_attention_kernel(gpu_buffer, stream);
```

### 4.3 NUMA 注意事項

CPU AMX 在哪個 socket 上執行，應與 GPU 的 NUMA 位置對齊。本環境中 GPU 位於 NUMA node 1，AMX kernel 執行緒應繫結到 node 1 的核（CPU 52-103, 156-207）。

```bash
taskset -c 52-103,156-207 ./hybrid_amx_cuda_program
```

---

## 5. 何時使用 AMX，何時用 GPU

```text
        小 batch → CPU AMX
        ↓
推理    大 batch → GPU Tensor Core
        ↓
        實時 < 1ms → CPU AMX
        ↓
訓練    微調 → GPU Tensor Core
        ↓
        預訓練 → GPU Tensor Core (唯一選擇)
```

核心決策因素：

1. **batch size**：AMX 優勢體現在小 batch，大 batch 時 GPU 的吞吐明顯更高
2. **實時性**：AMX 的延遲可預測（~μs 級），GPU 需經 PCIe + kernel launch（~10-50μs）
3. **現有架構**：如果管線已經在 CPU 上完成 tokenize/prefill，加 AMX 推理比引入 GPU 改動小

---

## 6. 延伸閱讀

AMX 的詳細程式設計和最佳化超出本文範圍（本文側重 GPU 基礎設施），推薦資源：

- [Intel AMX Programming Guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html)
- [PyTorch CPU 效能調優](https://pytorch.org/tutorials/recipes/recipes/tuning_guide.html)
- [Intel Extension for PyTorch](https://github.com/intel/intel-extension-for-pytorch)
