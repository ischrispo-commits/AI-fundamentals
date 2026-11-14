# AI 基礎設施延遲金字塔

本文旨在為 AI 工程師提供一份直觀的系統延遲參考指南。透過建立 **"延遲金字塔" (Latency Pyramid)** 模型，將從晶片內部到跨資料中心的各級延遲資料視覺化，幫助開發者建立對系統效能數量級的第一性認知。

> **基準說明**：資料基於 NVIDIA H100/A100 + NVLink/NVSwitch + IB NDR 網路環境下的典型熱路徑估算。

---

## 1. 延遲金字塔總覽

為了更直觀地理解資料移動的代價，我們將時間延遲對映為"人類距離尺度" (Human Distance Scale)。

> **核心隱喻**：
> 在 AI 基礎設施中，我們將基準定義為 **1 GPU 周期 (~0.5 ns)**。
> 假設 **1 GPU 周期 (0.5 ns)** 相當於 **邁出 1 步 (0.5 米)**。
>
> **速算口訣**: `1 ns ≈ 1 米`

```text
# -----------------------------------------------------------------------------
# Level 1 — 晶片內部 (Chip Internal)
# -----------------------------------------------------------------------------
事件 (Event)                        延遲 (Latency)        人類距離尺度 (Distance Scale)
-----------------------------------------------------------------------------
Register Access                 ~0.5 ns               0.5 m   (伸手拿紙)
L1 Cache                        15-30 ns              15-30 m (穿過大辦公室)
Shared Memory (Bank Conflicts)  20-30 ns              20-30 m (去隔壁會議室)
GPU L2 Cache                    100-120 ns            100-120 m (下樓去便利店)

# -----------------------------------------------------------------------------
# Level 2 — 顯存與互聯 (Memory & Interconnect)
# -----------------------------------------------------------------------------
NVLink hop (Direct)             80-120 ns             80-120 m (去隔壁樓棟)
HBM3 Access                     250-350 ns            250-350 m (繞小區半圈)
NVSwitch traversal              150-250 ns            150-250 m (去小區門口)
PCIe Gen5 Transaction           400-600 ns            400-600 m (步行去地鐵站)

# -----------------------------------------------------------------------------
# Level 3 — 通訊與網路 (Communication & Network)
# -----------------------------------------------------------------------------
RDMA 1KB (One-way)              1.5-2 us              1.5-2 km (共享單車去地鐵站)
Host-Device RTT (PCIe)          1-3 us                1-3 km   (跑步去鄰村)
Kernel Launch (CPU->GPU)        5-15 us               5-15 km  (10公里長跑)
NCCL AllReduce (NVLink)         20-200 us             20-200 km (開車跨城上班)
TCP RTT (Intra/Cross Rack)      20-150 us             20-150 km (北京到天津)
NCCL AllReduce (Cross Node)     200 us - 5 ms         200 km+   (高鐵跨省)

# -----------------------------------------------------------------------------
# Level 4 — 儲存與 I/O (Storage & I/O)
# -----------------------------------------------------------------------------
NVMe Random Read (4KB)          ~100 us               100 km   (北京到保定)
NVMe Seq Read (1MB)             100-300 us            100-300 km (北京到石家莊)
HDD Seek                        ~10 ms                10,000 km (坐飛機去美國)
Object Storage First Byte       30-100 ms             30,000-100,000 km (繞地球約 0.75-2.5 圈)
Region-to-Region RTT            80-150 ms             80,000-150,000 km (地月距離的 1/4)
```

![AI Latency Pyramid Guide Overview](./img/ai_latency_pyramid_overview.png)

---

## 2. 核心層級詳解

### 2.1 Level 1: 計算核心層

這是 AI 計算的微觀世界，效能單位為 **納秒 (ns)**。

- **Register (~0.5 ns)**: 資料的最終目的地，計算發生的場所。
- **L1 / Shared Memory (15-30 ns)**:
  - **L1 Cache (15-30 ns)**: 約 30-60 個 GPU 周期，遠高於 CPU L1 的 4-5 個週期。
  - **Shared Memory (20-30 ns)**: 開發者可控的暫存區，若发生 Bank Conflict，延遲會顯著增加。
- **L2 Cache (100-120 ns)**: 所有 SM 共享的片上快取 (50MB)。相比 A100 (40MB)，H100 的 L2 更大，延遲約 200+ 周期。

> **關鍵認知**: 即使是訪問 L2 Cache (100ns+)，相比寄存器 (0.5ns) 也慢了 200 倍。

### 2.2 Level 2: 顯存與互聯層

這是 "Memory Wall" (記憶體牆) 的发生地，效能單位為 **百納秒 (100s ns)**。

- **HBM3 (250-350 ns)**: 高頻寬記憶體。雖然頻寬極大 (3TB/s)，但延遲並未顯著降低 (400-600+ 周期)。
- **NVLink**:
  - **Direct Hop (80-120 ns)**: 點對點直連延遲。
  - **NVSwitch Path (150-250 ns)**: 跨 NVSwitch 的通訊延遲。
- **PCIe Gen5 (400 ns - 3 us)**:
  - **Transaction (400-600 ns)**: 純硬體匯流排傳輸延遲。
  - **Host-Device RTT (1-3 us)**: 包含驅動和 CPU 互動的端到端往返延遲。

> **關鍵認知**: 經 NVLink 訪問鄰居 GPU 顯存的完整路徑是 本地 L2 → NVLink → 遠端 L2 → 遠端 HBM，GPU 之間沒有跨卡的 L2 一致性。這條路徑 (Total ~200-300 ns) 比訪問本地 HBM (250-350 ns) 更快，所以"鄰居快取" (Cooperative Caching) 指的是讀鄰居的顯存，而不是共享它的 L2。

### 2.3 Level 3: 分散式通訊層

這是分散式訓練 Scaling 的關鍵，效能單位為 **微秒 (us)**。

- **RDMA (1.5-2 us)**: NDR InfiniBand 網路的典型單向延遲。
- **Kernel Launch (5-15 us)**: CPU 下发指令到 GPU 開始執行的開銷。使用 CUDA Graphs 可將其降低到 3-5 us。
- **NCCL AllReduce (NVLink)**:
  - **Small Tensor (20-50 us)**: 延遲敏感型的小包通訊。
  - **Typical Payload (50-200 us)**: 正常訓練負載下的通訊耗時。
- **TCP RTT (20-150 us)**: 同機架 (20-50 us) vs 跨機架 (50-150 us)。

> **關鍵認知**: 跨機通訊 (Network) 相比機內通訊 (NVLink) 有 10-100 倍的延遲差距，這是設計分散式演算法時必須考慮的物理約束。

### 2.4 Level 4: 儲存與 I/O 層

這是資料持久化層，效能單位為 **毫秒 (ms)**。

- **NVMe SSD**:
  - **Random Read (80-120 us)**: 4KB 隨機讀取。
  - **Seq Read 1MB (100-300 us)**: 大塊順序讀取效率極高，遠快於 1ms。
- **Object Storage (30-100 ms)**: 首位元組延遲 (TTFB) 波動較大，受網路和雲服務負載影響。

> **關鍵認知**: I/O 延遲是計算延遲的 10,000 倍以上。任何同步 I/O 操作都會導致 GPU 算力的巨大浪費。

---

## 3. 常見操作延遲速查表

| 操作 (Operation)  | 典型延遲   | 數量級 | 備註                          |
| :---------------- | :--------- | :----- | :---------------------------- |
| **Math**          | < 1 ns     | Nano   | FMA, Tensor Core op           |
| **SRAM Access**   | 15-30 ns   | Nano   | L1 (~30 cycles), Shared       |
| **DRAM Access**   | 250-350 ns | Nano   | HBM3 (500 cycles+), DDR5      |
| **GPU-GPU Raw**   | 80-250 ns  | Nano   | NVLink (Direct vs Switch)     |
| **Host-Device**   | 1-3 us     | Micro  | PCIe RTT                      |
| **Net-Device**    | 2-4 us     | Micro  | GPUDirect RDMA                |
| **Kernel Launch** | 5-15 us    | Micro  | CUDA API Overhead             |
| **Small Kernel**  | ~5 us      | Micro  | Element-wise op               |
| **Attention**     | 50-300 us  | Micro  | FlashAttn (seq len dependent) |
| **AllReduce**     | 50 μs - 5 ms | Milli  | Single Node vs Multi Node     |
| **Disk I/O**      | 0.1-10 ms  | Milli  | NVMe vs HDD                   |

---

## 4. 延遲估算公式

在沒有實測資料時，可用以下簡易模型進行估算：

1. **資料傳輸 (Data Transfer)**:
   `Time = Latency + (Size / Bandwidth)`
   - _小資料看 Latency，大資料看 Bandwidth。_

2. **集合通信 (Ring AllReduce)**:
   `Time ≈ 2 * (N-1) / N * (Latency + Size/Bandwidth)`
   - _隨著節點數 N 增加，頻寬利用率趨近恆定，但 Latency 線性增長。_

3. **推理首字 (TTFT)**:
   `TTFT ≈ Launch_Overhead + HBM_Read + KV_Fetch + Network_RTT + Queue_Delay`
   - _除了計算和顯存，KV Cache 獲取和排程排隊往往是長尾延遲的來源。_

---

## 5. 總結

**"延遲金字塔"** 揭示了 AI 系統設計的核心挑戰：

1. **層級跨越代價巨大**: 每跨越一層，延遲增加約 1-2 個數量級。
2. **局部性 (Locality)**: 把計算留在 Level 1/2，避免頻繁跌落到 Level 3/4。
3. **隱藏延遲 (Hiding)**: 高層級的延遲 (Level 3/4) 必須透過非同步流水線被低層級的計算 (Level 1) 掩蓋。

寫程式碼或設計架構時，先確認資料當前在哪一層，再決定要不要移動它。
