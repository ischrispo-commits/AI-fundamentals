# HBM 顯存技術演進：從 HBM2 到 HBM3e

> HBM (High Bandwidth Memory) 是 AI 算力的"燃料管道"：GPU 算力每年翻倍，顯存頻寬跟不上，Tensor Core 就只能空轉。本文覆蓋 HBM 各代的技術參數、關鍵創新及 A100 (HBM2e) 與 RTX 5090 (GDDR7) 的實測對比（規格資料 2026-11 核對）。

---

## 1. 為什麼 HBM 對 AI 至關重要

GPU 的計算吞吐和顯存頻寬必須匹配。以 A100 為例：

```text
A100 Tensor Core (BF16): 312 TFLOPS (稀疏口徑，白皮書標稱；稠密 156 TFLOPS)
A100 HBM2e 頻寬:        2039 GB/s
頻寬/算力比:            2039 GB/s ÷ 312 TFLOPS ≈ 6.5 bytes/千 FLOP
```

對算術強度高的算子（如大矩陣乘），每千 FLOP 需要的資料量遠低於 6.5 位元組，頻寬不是瓶頸。但 Attention 機制每次計算都要讀取整個 KV Cache。按序列長度 32K、hidden size 8192、單層、FP16 存放 K+V 估算，KV Cache 約 1.07 GB，在 A100 上讀一遍需要 ~0.5 ms；模型有幾十層，這個時間隨層數線性放大。顯存頻寬是 LLM 推理的真正瓶頸。

---

## 2. HBM vs GDDR：兩種顯存路線

|          | HBM (High Bandwidth Memory)       | GDDR (Graphics Double Data Rate) |
| -------- | --------------------------------- | -------------------------------- |
| 設計理念 | **位寬優先**：1024-bit 起，堆疊式 | **頻率優先**：32-bit 接口，高頻  |
| 位寬     | 1024-8192 bits (多堆疊)           | 32-512 bits (多芯片)             |
| 頻率     | 1.2-3.2 GHz                       | 14-28 GHz                        |
| 頻寬     | 410 GB/s → 8.0 TB/s (HBM3e)       | 1792 GB/s (RTX 5090 GDDR7)       |
| 功耗效率 | 高 (~3.5 pJ/bit)                  | 較低 (~7 pJ/bit)                 |
| 封裝     | 3D 堆疊 + Si Interposer           | PCB 上平面排布                   |
| 成本     | 極高                              | 低                               |
| 典型產品 | A100, H100, B200                  | RTX 4090, RTX 5090               |

> 消費級 GPU 使用 GDDR 是因為成本敏感。資料中心 GPU 使用 HBM 是因為頻寬需求壓倒成本考量。

---

## 3. HBM 代際演進

| 代際      | 頻寬/堆疊    | 堆疊數 | 總位寬       | 總頻寬        | 代表 GPU         |
| --------- | ------------ | ------ | ------------ | ------------- | ---------------- |
| HBM2      | 307 GB/s     | 4      | 4096-bit     | 900 GB/s      | V100 (32 GB)     |
| **HBM2e** | **410 GB/s** | **5**  | **5120-bit** | **2039 GB/s** | **A100 (80 GB)** |
| HBM3      | 665 GB/s     | 6      | 6144-bit     | 3.35 TB/s     | H100 (80 GB)     |
| HBM3e     | 1.15 TB/s    | 8      | 8192-bit     | 4.8 TB/s      | H200 (141 GB)    |
| HBM3e     | 1.0 TB/s     | 8      | 8192-bit     | 8.0 TB/s      | B200 (192 GB)    |

> 表中堆疊數/位寬/頻寬是各代代表 GPU 的實際配置，不是 JEDEC 上限（HBM2e 標準支援到 8 堆疊 / 8192-bit，HBM3 每 pin 資料率上限 6.4 Gbps/pin）。

**公式**：`總頻寬 = 堆疊數 × 每堆疊頻寬`（每 pin 資料率 ×2 的 DDR 折算已含在每堆疊頻寬裡，不要重複乘）

以 A100 為例：

```text
5 stacks × 1024 bits × 1.593 GHz × 2 (DDR) ÷ 8 = 2039 GB/s
```

### 3.1 HBM2e：A100 的位寬設計

A100 的 NVLink 3.0 設計邏輯與 HBM2e 一脈相承：**減少每條鏈路的訊號線數量，翻倍增加鏈路數**。

|            | V100 HBM2 | A100 HBM2e    | 變化  |
| ---------- | --------- | ------------- | ----- |
| 堆疊數     | 4         | **5**         | +25%  |
| 每堆疊位寬 | 1024-bit  | 1024-bit      | 不變  |
| 總位寬     | 4096-bit  | **5120-bit**  | +25%  |
| 資料率     | 1.76 Gbps/pin | **3.19 Gbps/pin** | +81% |
| 總頻寬     | 900 GB/s  | **2039 GB/s** | +2.3× |

位寬增加 25%，每 pin 資料率提升近一倍，兩者相乘得到 2.3 倍頻寬（資料率按 Gbps/pin 計，代回公式可復算出 900 / 2039 GB/s）。更寬的位寬同時意味著可以處理更多併發記憶體請求，減少排隊延遲。

### 3.2 A100 vs RTX 5090：HBM2e vs GDDR7 實測

| 指標              | A100 HBM2e           | RTX 5090 GDDR7   | 說明                                |
| ----------------- | -------------------- | ---------------- | ----------------------------------- |
| 位寬              | **5120-bit**         | 512-bit          | A100 寬 10 倍                       |
| 頻率              | 1593 MHz             | **14001 MHz**    | RTX 5090 高 8.8 倍                  |
| 理論頻寬          | **2039 GB/s**        | 1792 GB/s        | A100 高 14%                         |
| 實測 Copy Engine (1GB)  | ~818 GB/s (40%) | —          | cudaMemcpy D2D 走 DMA Copy Engine |
| 實測 Kernel R+W (1GB)   | **~1453 GB/s** (71%) | —      | SM 驅動 read+write，接近 HBM 全頻寬 |

> 資料來源：[`03_hbm_bandwidth_bench.cu`](../../02_gpu_programming/04_profiling/code/03_hbm_bandwidth_bench.cu) — 配套 benchmark，同時對比 Copy Engine vs Kernel 兩種測法。Copy Engine（cudaMemcpy）只能到 ~40% 峰值，要用 SM 驅動的 kernel 才能測得真正的 HBM 頻寬。

---

## 4. HBM 的 3D 封裝技術

HBM 的效能來自於獨特的物理結構：

```text
          HBM 堆疊 (側檢視)
          ┌──────────┐
          │ DRAM Die │ ← 第 8 層
          │ DRAM Die │ ← 第 7 層
          │ DRAM Die │ ← 第 6 層
          │ DRAM Die │ ← 第 5 層
          │ DRAM Die │ ← 第 4 層
          │ DRAM Die │ ← 第 3 層
          │ DRAM Die │ ← 第 2 層
          │ DRAM Die │ ← 第 1 層 (頂層)
          │ Logic Die│ ← 控制器 + PHY
    ┌─────┴──────────┴─────┐
    │   Silicon Interposer │ ← 矽中介層
    │   (連線 GPU 與 HBM)   │
    └──────────────────────┘
    ┌──────────────────────┐
    │    GPU Die (GA100)   │
    └──────────────────────┘
```

- **3D 堆疊**：DRAM die 垂直堆疊，透過 **TSV (Through-Silicon Via)** 連線
- **Silicon Interposer**：微凸點（micro-bump）連線的矽中介層，GPU 和 HBM 堆疊共享
- **物理距離**：GPU 到 HBM 的訊號路徑只有 ~1 mm，而 GDDR 走 PCB 需要 ~20-30 mm，這是 HBM 能用更低頻率實現更高頻寬的物理原因

---

## 5. L2 Cache：HBM 的最後一級加速器

從 A100 開始，NVIDIA 大幅增加了 L2 Cache：

| GPU      | L2 Cache  | HBM 頻寬  | L2/HBM 比 |
| -------- | --------- | --------- | --------- |
| V100     | 6 MB      | 900 GB/s  | 1:150     |
| A100     | **40 MB** | 2039 GB/s | 1:51      |
| H100     | 50 MB     | 3350 GB/s | 1:67      |
| B200     | 96 MB*    | 8000 GB/s | 1:83      |
| RTX 5090 | **96 MB** | 1792 GB/s | 1:19      |

\* B200 的 L2 容量為第三方微基準口徑（非官方），NVIDIA 未在官方規格中公佈。

L2 越大，越能掩蓋 HBM 延遲。40 MB L2 在 A100 上足以容納 4M 元素的 fp32 矩陣，中等大小的矩陣操作可以完全在 cache 內完成，頻寬利用率可達 58% 以上。

---

## 6. 程式設計啟示

- **儘量把資料留在顯存**：A100 HBM2e 內部頻寬 (2039 GB/s) vs PCIe Gen4 (~28 GB/s) = **73倍**
- **利用 L2 cache**：中等矩陣 (≤ 數 MB) 操作受益於 L2 命中，實際頻寬可達到峰值 50% 以上
- **大矩陣操作**：A100 的寬位寬 (5120-bit) 比 RTX 5090 (512-bit) 更適合大資料流
- **GDDR vs HBM**：RTX 5090 的 GDDR7 在 L2 命中時很快（~1341 GB/s），但一旦需要 DRAM 訪問，窄位寬立刻成為瓶頸

## 參考

- [HBM 顯存頻寬測試](../../02_gpu_programming/04_profiling/03_hbm_bandwidth_test.md) — A100 實測對比（含 Copy Engine vs Kernel 兩種方法）
- [HBM 頻寬 Benchmark](../../02_gpu_programming/04_profiling/code/03_hbm_bandwidth_bench.cu) — 可編譯執行的配套程式碼
- [NVIDIA A100 架構詳解](../nvidia/understand_gpu_architecture/07_a100_architecture.md) — HBM2e 在 A100 上的完整規格
- [PCIe & NVLink 頻寬速查表](05_pcie_nvlink_speed_reference.md) — 頻寬全景對比
- [AI 基礎設施延遲金字塔](ai_latency_pyramid.md) — 各級延遲基準
- [JEDEC HBM Specs](https://www.jedec.org/) — HBM 標準制定者
