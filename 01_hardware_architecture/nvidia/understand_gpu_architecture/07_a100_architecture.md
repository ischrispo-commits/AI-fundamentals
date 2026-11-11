# GPU 架構實例：NVIDIA A100 (Ampere)

> 基於 A100-SXM4-80GB (CC 8.0) 伺服器實測。A100 是 NVIDIA 資料中心 GPU 從 Volta 到 Hopper 的關鍵轉折點：TF32 精度、結構稀疏性（Sparsity）、MIG 分割槽這些至今仍是 AI 訓練推理基座的能力都從這一代開始。本文從架構規格到實測驗證完整覆蓋，規格數字為 NVIDIA A100 資料表口徑（2020 年发布）。

---

## 1. Ampere GA100 概覽

A100 基於 Ampere 架構的 **GA100** 芯片，SM 數量從 V100 的 80 個提升到 108 個。與 V100 的對比：

| 規格 | V100 (Volta) | A100 (Ampere) | 變化 |
|------|-------------|--------------|------|
| SM 數量 | 80 | **108** | +35% |
| CUDA Cores/SM | 64 FP32 | 64 FP32 + 64 INT32 → 可全部用於 FP32 | 翻倍 |
| CUDA Cores 總數 | 5120 | **6912** | +35% |
| Tensor Cores/SM | 8 (Gen1) | 4 (Gen3) | 減半但單核效能翻倍+ |
| Tensor Core 精度 | FP16 | **TF32, FP16, BF16, INT8, INT4, INT1** | 精度矩陣完整 |
| L2 Cache | 6 MB | **40 MB** | +6.7× |
| 顯存 | 32/16 GB HBM2 | **80/40 GB HBM2e** | +2.5× |
| 顯存頻寬 | 900 GB/s | **2039 GB/s** (80GB) | +2.3× |
| NVLink | 6 links × 25 GB/s = 300 GB/s | **12 links × 25 GB/s = 600 GB/s** | +2× |
| PCIe | Gen 3 x16 | **Gen 4 x16** | +2× |
| 制程 | TSMC 12nm | **TSMC 7nm** | 密度提升 |
| MIG | 不支持 | **支持** (最多 7 實例) | 新能力 |
| Sparsity | 不支持 | **支持** (2:4 結構化稀疏) | 新能力 |

> 注：A100 80GB 版本使用 HBM2e，顯存時鐘 1593 MHz；40GB 版本使用 HBM2，顯存時鐘 1215 MHz。本文資料基於 80GB 版本。

---

## 2. GA100 SM 內部結構

每個 GA100 SM 包含 4 個處理分割槽（Partitions），每個分割槽有獨立的 L0 指令快取、Warp Scheduler 和 Dispatch Unit：

```text
GA100 SM (108 個在 A100 中)
├── 4 × 處理分割槽 (Processing Partition)
│   ├── 1 × Warp Scheduler (32 threads/warp)
│   ├── 16 × FP32 CUDA Core ──┐
│   ├── 16 × INT32 CUDA Core ─┤ 在同一資料路徑上
│   ├── 1 × Tensor Core (Gen3) │ → 每 SM 共 4 個 Tensor Core
│   ├── 4 × LD/ST Unit          │
│   └── 1 × SFU                 │
├── 128 KB L1 Data Cache / Shared Memory (可配置)
├── 讀取-Only Data Cache
└── 寄存器文件: 65536 × 32-bit
```

**關鍵改進**：V100 中 FP32 和 INT32 資料路徑分離，不能同時使用。A100 將兩者合併到同一條資料路徑上：當不需要 INT32 運算時，INT32 資料路徑也可執行 FP32 指令，使每 SM 的 FP32 吞吐實際上可達 V100 的 2 倍。

---

## 3. 第三代 Tensor Core

A100 的 Tensor Core 是第三代，帶來兩個關鍵新能力：

### 3.1 TF32：訓練精度的"甜點"

```text
TF32 = FP32 的 8-bit 指數 + FP16 的 10-bit 尾數 = 19 bits
```

TF32 的數值範圍與 FP32 相同（不會溢位），但尾數精度截斷到 10 bits。對於深度學習訓練，這種精度截斷在實踐中不影響收斂，Tensor Core 吞吐為 FP16 的一半（TF32 156 TFLOPS，FP16 312 TFLOPS）；不需要修改任何訓練程式碼，只需將輸入保持為 FP32。

```c
// cuBLAS 的預設 math mode（CUBLAS_DEFAULT_MATH）官方語義是
// "Tensor Cores will be used whenever possible"——CC ≥ 8.0 上的 FP32 GEMM
// 預設就會走 TF32；顯式設定 CUBLAS_TF32_TENSOR_OP_MATH 是把這一點寫死，
// 不依賴預設行為隨版本漂移。
// cuDNN 的預設 math mode 不做 FP32 下轉換，需要顯式開關；
// PyTorch、TensorFlow 等框架則由框架自己的開關控制 TF32
cublasSetMathMode(handle, CUBLAS_TF32_TENSOR_OP_MATH);
```

### 3.2 精度矩陣

按 A100-SXM4-80GB 資料表口徑折算（FP32 19.5 TFLOPS 為 1×；帶 2:4 稀疏時各 Tensor Core 精度再翻倍）：

| 精度 | 吞吐 (相對 FP32) | 主要用途 |
|------|-----------------|---------|
| TF32 | 8× | 訓練（無程式碼改動） |
| FP16 | 16× | 訓練 + 推理 |
| BF16 | 16× | 訓練（與 TPU 兼容） |
| INT8 | 32× | 推理量化 |
| INT4 | 64× | 輕量推理 |
| FP64 | 0.5× | HPC（A100 的 FP64 是 FP32 的一半，V100 也是這一比例） |

---

## 4. HBM2e 顯存與 L2 Cache

A100 80GB 版本配備 5 個 HBM2e 堆疊，每個提供 1024-bit 接口：

```text
顯存位寬: 5 stacks × 1024 bits = 5120 bits
顯存時鐘: 1593 MHz
理論頻寬: 2 × 1.593 GHz × 5120 / 8 = 2039 GB/s
```

**L2 Cache** 從 V100 的 6 MB 增加到 **40 MB**。40 MB 的 L2 意味著多數中等大小矩陣的中間結果可以被完整快取，大幅減少 HBM 訪問。

> 實測驗證：在 A100 上執行 `transpose` (4 MB 矩陣)，optimized copy 達到 ~1188 GB/s (~58% 理論峰值)。另一組跨代參考資料：64 MB 矩陣在 RTX 5090 (96 MB L2，理論頻寬 1792 GB/s) 上實測約 1341 GB/s，不是其理論峰值。A100 的 40 MB L2 對於 4 MB 矩陣同樣提供了可觀的加速。

---

## 5. A100 實測驗證

以下資料來自一台 8 × A100-SXM4-80GB (NVSwitch Gen2) 伺服器實測：

```bash
# deviceQuery 關鍵輸出
nvidia-smi --query-gpu=index,name,memory.total,clocks.current.sm,clocks.current.memory --format=csv
# 3, NVIDIA A100-SXM4-80GB, 81920 MiB, 1410 MHz, 1593 MHz
```

| 屬性 | deviceQuery 值 | 說明 |
|------|---------------|------|
| Compute Capability | 8.0 | Ampere |
| SMs | 108 | × 64 CUDA Cores/SM = 6912 |
| Max Threads/SM | 2048 | V100 也是 2048 |
| Max Blocks/SM | 32 | 比 RTX 5090 的 24 更多 |
| Shared Memory/SM | 167936 bytes | 可配置為 164 KB |
| Registers/SM | 65536 | |
| Async Copy Engines | 3 | RTX 5090 只有 2 |
| Warp Size | 32 | 所有 NVIDIA GPU 一樣 |
| ECC | Enabled | 資料中心級 |
| NVLink | 12 links × 25 GB/s | 總雙向 600 GB/s |
| PCIe | Gen 4 × 16 | max: 5 (RTX 5090) / 4 (A100) |

**deviceQuery 示例與輸出**：見同目錄 [05_exer_device_query.md](05_exer_device_query.md)。

**NVLink 拓撲**：8 卡透過 NVSwitch Gen2 全互聯 (NV12)，每對 GPU 間 600 GB/s 雙向。詳見 [NVLink 診斷與實操](../../nvlink/nvlink_diagnostics.md)。

---

## 6. MIG：多實例 GPU

A100 是首款支持 **MIG (Multi-Instance GPU)** 的 NVIDIA GPU，它將一張物理 GPU 切分為最多 7 個獨立的 GPU 實例，每個實例有專用的 SM、顯存、L2 Cache 和記憶體頻寬：

```text
A100-80GB MIG 配置示例:
  7 × 1g.10gb  (10 GB, ~14 SMs)    — 最多實例
  3 × 2g.20gb  (20 GB, ~28 SMs)    — 均衡
  1 × 4g.40gb  (40 GB, ~56 SMs)    — 常用大實例
  1 × 7g.80gb  (80 GB, 98 SM, 79 GiB) — MIG 最大單實例
非 MIG 的預設態是完整 GPU（108 SM，80 GB），不建立任何 MIG 實例
```

**適用場景**：多租戶推理服務、小模型訓練、CI/CD 資源隔離。訓練通常不用 MIG（需要整卡算力），推理場景中 MIG 可以避免多個服務競爭同一 GPU。

```bash
# 啟用 MIG 模式
nvidia-smi -i 0 -mig 1

# 列出 MIG 實例
nvidia-smi mig --list-gpu-instances
```

---

## 7. 結構化稀疏 (2:4 Sparsity)

A100 的 Tensor Core 支持 **2:4 結構化稀疏**：在每 4 個連續權重值中，最多 2 個可以為零。硬體直接跳過零值的計算，使有效吞吐翻倍：

```text
權重向量: [w0, 0, w2, 0, w4, w5, 0, w7]
            └──2:4──┘  └──2:4──┘
稀疏後有效計算: 50% 的非零值 → Tensor Core 跳過零 → 2× 加速
```

配合 cuSPARSELt 庫或 PyTorch 的 `torch.sparse` 使用，對推理場景尤其有效。

---

## 8. A100 vs 消費級 GPU

A100 與文件中頻繁對比的 RTX 5090 的關鍵差異：

| 能力 | A100 | RTX 5090 | 影響 |
|------|------|---------|------|
| FP64 性能比 | **2:1** | 64:1 | A100 適合 HPC 雙精度 |
| NVLink | **600 GB/s** | 不支持 | 多卡訓練必須 NVLink |
| MIG | 支持 | 不支持 | 多租戶 GPU 分割槽 |
| ECC | 預設開啟 | 可選 | 資料中心可靠性 |
| Async Engines | 3 | 2 | 併發 D2H/H2D 能力 |
| Max Threads/SM | 2048 | 1536 | A100 SM 容更多執行緒 |
| L2 Cache | 40 MB | 96 MB | RTX 5090 L2 更大（但無 NVLink） |

---

## 參考

- [NVIDIA A100 Tensor Core GPU Architecture](https://images.nvidia.com/aem-dam/en-zz/Solutions/data-center/nvidia-ampere-architecture-whitepaper.pdf) — Ampere 架構白皮書
- [NVIDIA A100 產品規格](https://www.nvidia.com/en-us/data-center/a100/)
- [GPU 架構深入理解](README.md) — 本目錄其他 GPU 型號分析
- [NVLink 技術入門](../../nvlink/nvlink_intro.md) — NVLink 3.0 細節
- [NVLink 診斷與實操](../../nvlink/nvlink_diagnostics.md) — A100 NVLink 實測
