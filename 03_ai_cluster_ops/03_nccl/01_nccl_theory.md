# NCCL 技術理論深度解析

> 覆蓋 AllReduce 算法原理、RDMA 通訊機制、性能建模、記憶體管理、容錯與監控等理論主題。

---

## 1. AllReduce 算法原理

AllReduce 是分散式訓練中最核心的集合通訊原語——將 N 個 GPU 上的資料進行歸約運算（求和、最大值等），再將結果廣播到所有 GPU。梯度同步、參數聚合都依賴它。

NCCL 根據資料量和 GPU 數量自動選擇演算法：

| 資料量       | 算法               | 延遲特徵              | A100 8-GPU 實測 bus_bw  |
| ------------ | ------------------ | --------------------- | ----------------------- |
| < 32 KB      | Tree               | O(log₂N) 步，延遲最優 | ~5 GB/s                 |
| 32 KB - 2 MB | Double Binary Tree | 平衡延遲和頻寬        | ~50-150 GB/s            |
| > 2 MB       | Ring               | O(N) 步但頻寬高       | **225 GB/s** (NVSwitch) |
| 大消息       | NVLS               | NVSwitch Gen3 組播在網歸約，單遍完成 | —（A100 無 Gen3 Switch，不啟用；NVSwitch Gen3 + NCCL 2.17+，即 Hopper 世代起的大訊息首選） |

> 注：< 32 KB / 32 KB-2 MB / > 2 MB 三檔閾值為 NCCL 2.29.x + A100 8-GPU 環境的實測經驗值，不是官方數字。NCCL 按拓撲與訊息大小自動選擇，版本間會調整。

### 1.1 Ring AllReduce

N 個 GPU 構成邏輯環，每個 GPU 只與左右鄰居通訊。分兩階段：

1. **Reduce-Scatter**：沿環傳遞 N-1 輪，每輪每個 GPU 发送 1/N 資料並歸約接收到的資料。完成後每個 GPU 持有 1/N 完整歸約結果。
2. **AllGather**：再沿環傳遞 N-1 輪，每輪傳送自己的歸約結果。完成后所有 GPU 擁有完整結果。

**理論傳輸量**：每 GPU 單向傳送 `2 × (N-1)/N × data_size`，8 GPU 時約為 1.75× data_size。頻寬效率高，但延遲隨 N 線性增長。

### 1.2 Tree AllReduce (含 NVSwitch)

GPU 構成二叉樹（或經 NVSwitch），歸約沿樹向上、廣播沿樹向下。只需 O(log₂N) 步：

- 8 GPU：3 步完成（vs Ring 的 14 步）
- 延遲遠低於 Ring，尤其適合小資料
- NVSwitch 硬體做歸約（SHARP）：資料在流經 Switch 時被截獲歸約，僅返回最終結果。注意代際：SHARP/NVLS 需要 NVSwitch Gen3（Hopper 世代起），A100 的 Gen2 Switch 不支持

A100 + NVSwitch 環境下，NCCL 在 > 2 MB 時仍選 Ring，因為 Ring 在 NVSwitch 全連線下也能高效運作。實測 7 GPU bus_bw 達 225 GB/s，與 P2P 單向 239 GB/s 僅差 6%。詳見 [NCCL 基準測試方法論](04_nccl_benchmark.md)。

### 1.3 與 AllGather / ReduceScatter 的關係

| 操作          | 方向                      | 典型場景         | 與 AllReduce 的關係              |
| ------------- | ------------------------- | ---------------- | -------------------------------- |
| ReduceScatter | 歸約 + 分發結果到各自 GPU | ZeRO 梯度分发    | AllReduce 的 Reduce-Scatter 階段 |
| AllGather     | 收集並廣播                | ZeRO 參數收集    | AllReduce 的 AllGather 階段      |
| AllReduce     | 歸約 + 廣播完整結果       | 資料並行梯度同步 | ReduceScatter + AllGather        |

---

## 2. GPUDirect RDMA 技術原理

GPUDirect 是 NVIDIA 為消除 PCIe 瓶頸提出的裝置直連技術棧。在分散式訓練中，它的核心價值是**讓網路介面卡直接訪問 GPU 顯存，完全繞過 CPU 和系統記憶體**。

### 2.1 資料路徑對比

**傳統路徑（無 GPUDirect）**：

```text
GPU VRAM → CPU DRAM (via PCIe/DMA) → CPU → NIC → 網路
```

涉及兩次 PCIe 傳輸（GPU→CPU、CPU→NIC）和一次 CPU 記憶體複製。

**GPUDirect RDMA 路徑**：

```text
GPU VRAM → NIC (via PCIe, direct DMA) → 網路
```

一次 DMA 直通。延遲降低 40-60%，CPU 使用率降低 80%+，頻寬利用率提升 20-30%。

### 2.2 前置條件

- GPU 支持 GPUDirect RDMA（資料中心 GPU: V100/A100/H100）
- 網卡支援 PCIe P2P（需與 GPU 在同一 PCIe 根匯流排段下）
- `nvidia-smi topo -m` 確認 P2P 能力
- `NCCL_NET_GDR_LEVEL`：限制 GDR 使用的 GPU-NIC 距離上限（GDR 預設已啟用，該變數只調上限）；整數僅為相容保留（`2` = `PXB`），推薦用字串 `PXB`，即 GPU 與網卡之間最多跨兩級 PCIe switch

> 深度閱讀：[GPUDirect RDMA 與 Storage 技術詳解](../../01_hardware_architecture/gpudirect/01_gpudirect_technology.md) | [GPUDirect P2P 技術詳解](../../01_hardware_architecture/gpudirect/02_gpudirect_p2p.md)

### 2.3 GPUDirect 與 NVLink 的關係

GPUDirect P2P 是 CUDA 層的 API（`cudaDeviceEnablePeerAccess`），NVLink 是物理層的高速鏈路。當一個 GPU 透過 GPUDirect P2P 訪問另一個 GPU 時：

- **有 NVLink 時**：走 NVLink（600 GB/s 雙向），CUDA 自動優選
- **無 NVLink 時**：走 PCIe P2P（~32 GB/s Gen4），需在同一 PCIe 根匯流排段下
- **跨 NUMA node**：P2P 不可用，回退到 CPU 中轉

> 實測資料：A100 NVLink P2P 單向 239 GB/s，PCIe H2D 約 28 GB/s，差距 8.5 倍。詳見 [GPU P2P 頻寬實測](../../02_gpu_programming/04_profiling/08_p2p_bandwidth.md)。

---

## 3. NCCL 自動拓撲檢測

NCCL 啟動時透過 NVML 與 `/sys` 讀取匯流排與 NVLink 拓撲，`nvidia-smi topo -m` 是同一份資訊的人工檢視；NCCL 據此構建通訊拓撲圖，為每對 GPU 選擇最優路徑。

### 3.1 單節點檢測優先順序

```text
NVLink (NV12) > PCIe P2P (PIX) > PCIe via CPU (NODE) > 跨 socket (SYS)
```

| 拓撲標識 | 含義                                | NCCL 路徑      | 頻寬 (A100)   |
| -------- | ----------------------------------- | -------------- | ------------- |
| **NV12** | NVLink 3.0, 12 links 全通           | NVLink 直連    | 600 GB/s 雙向 |
| **PIX**  | 同一 PCIe switch 下                 | PCIe P2P       | ~32 GB/s      |
| **NODE** | 同一 NUMA node, 經 PCIe Host Bridge | CPU 中轉       | ~28 GB/s      |
| **SYS**  | 跨 NUMA node, 經 QPI/UPI            | CPU 中轉 + SMP | 更低          |

### 3.2 多節點檢測

跨節點時 NCCL 優先 InfiniBand (RDMA)，其次 RoCE (RDMA over Ethernet)，最后 TCP Socket。檢測透過 `ibv_devinfo` 和網卡能力協商實現。

### 3.3 拓撲異常案例

GPU 7 在我們的測試環境中顯示全 SYS/NODE/PXB 連線（無 NVLink）。NCCL 檢測到後會回退到 CPU 中轉路徑，AllReduce 頻寬從 225 GB/s 跌至 ~28 GB/s。詳見 [NVLink 診斷與實操](../../01_hardware_architecture/nvlink/nvlink_diagnostics.md) 和 [GPU 叢集健康檢查](../01_gpu_ops/06_gpu_health_check.md)。

---

## 4. 效能建模與預測

### 4.1 Hockney 通信模型

基礎模型：`T_comm = α + β × message_size`，其中 α 為啟動延遲（startup latency），β 為每位元組傳輸時間（1/bandwidth）。

**Ring AllReduce 總時間**：

```text
T_ring = 2(P-1) × α + 2(P-1)/P × message_size × β
```

**Tree AllReduce 總時間**：

```text
T_tree = 2log₂(P) × α + 2 × message_size × β
```

**決策邊界**：當 `message_size < α/β × log₂(P)/(P-1)` 時 Tree 更快（延遲主導），否則 Ring 更快（頻寬主導）。A100 上實測拐點約在 2 MB。

### 4.2 A100 實測驗證

從 [NCCL 基準測試](04_nccl_benchmark.md) 的 7 GPU 資料：

| 資料量 | bus_bw           | 分析                        |
| ------ | ---------------- | --------------------------- |
| 1 MB   | 16.8 GB/s (8.5%) | α 主導，頻寬遠未飽和        |
| 8 MB   | 89 GB/s (45%)    | 過渡區                      |
| 64 MB  | 170 GB/s (86%)   | 接近 β 主導                 |
| 256 MB | 206 GB/s (91%)   | 接近硬體極限                |
| 1 GB   | **225 GB/s**     | Ring 飽和，效率 ~94% vs P2P |

### 4.3 擴展性分析

- **Strong Scaling**：固定總資料量，增加 GPU 數 P。效率 `E(P) = T(1) / (P × T(P)) × 100%`。通訊開銷隨 P 增長，小資料量時擴展性受限於 α。
- **Weak Scaling**：每 GPU 資料量固定。效率 `E(P) = T(1) / T(P) × 100%`。NVSwitch 架構下 Weak Scaling 接近線性——bus_bw 從 2 GPU (197 GB/s) → 7 GPU (225 GB/s) 反而上升。

---

## 5. 瓶頸分析框架

定位分散式訓練中通訊效能問題的系統化方法：

### 5.1 三層瓶頸分類

| 瓶頸類型 | 指標特徵                                | 排查工具                         | 最佳化方向                |
| -------- | --------------------------------------- | -------------------------------- | ----------------------- |
| 計算瓶頸 | GPU SM Active > 80%，通信 < 10% 總時間  | `ncu --set basic`                | 最佳化 kernel，增大 batch |
| 通訊瓶頸 | 通信 > 30% 總時間，網路頻寬利用率 > 80% | `nsys profile`, `all_reduce_perf` | 換更快網路，減少通訊量  |
| 記憶體瓶頸 | HBM 頻寬利用率 > 85%，頻繁分配/釋放     | `dcgmi dmon -e 204`, `ncu`       | 記憶體池，梯度累計        |

### 5.2 排查流程

```text
發現問題 → nsys 看 timeline（誰在等誰）
          → 若 CPU 等 GPU → ncu 看 kernel（compute/memory bound）
          → 若 GPU 等通信 → all_reduce_perf 測頻寬 → 對照 topo 拓撲
          → 若等網路 IO → ib_write_bw 測 RDMA → 檢查交換機/線纜
```

> 工具鏈參考：[DCGM 監控實操](../01_gpu_ops/05_dcgm_monitoring.md) | [Nsight Compute CLI](../../02_gpu_programming/04_profiling/06_nsight_compute_cli.md) | [Nsight Systems CLI](../../02_gpu_programming/04_profiling/07_nsight_systems_cli.md)

---

## 6. 高階最佳化技術

### 6.1 通訊與計算重疊

利用 CUDA Stream 將反向傳播計算與梯度 AllReduce 重疊執行：

```text
傳統方式：Layer N 反向 → AllReduce 梯度 → Layer N-1 反向
重疊方式：Layer N 反向 ∥ AllReduce 梯度（非同步啟動，不等結果）
```

重疊效率 = `min(T_compute, T_comm) / max(T_compute, T_comm)`。理想情況下 T_total = max(T_compute, T_comm)。注意：PyTorch DDP 的反向/通訊重疊預設來自 bucket 機制（按 bucket 切分梯度、邊算邊傳），`gradient_as_bucket_view` 參數預設為 False，與該重疊機制無關。

### 6.2 梯度壓縮

減少通訊量，以微小精度損失換取頻寬：

| 方法        | 壓縮比     | 精度影響   | 適用場景            |
| ----------- | ---------- | ---------- | ------------------- |
| FP32 → FP16 | 2:1        | 極小       | 混合精度訓練標配    |
| FP32 → INT8 | 4:1        | 需校准     | 推理、大 batch 訓練 |
| Top-K 稀疏  | 10:1-100:1 | 依賴稀疏度 | 通訊瓶頸嚴重的場景  |
| PowerSGD    | 可變       | 收斂略慢   | 低頻寬網路          |

### 6.3 NCCL 環境變數調優

關鍵旋鈕（詳見 [NCCL 基準測試](04_nccl_benchmark.md)）：

| 變數                 | 作用          | A100 建議值            |
| -------------------- | ------------- | ---------------------- |
| `NCCL_P2P_LEVEL`     | 強制 P2P 路徑 | `NVL` (優先 NVLink)    |
| `NCCL_IB_DISABLE`    | 禁用 IB       | `1` (純單機 NVLink 時) |
| `NCCL_ALGO`          | 強制演算法      | 通常讓 NCCL 自動選     |
| `NCCL_MIN_NCHANNELS` | 最小通道數    | `8` (增加並行度)       |
| `NCCL_NTHREADS`      | CUDA 執行緒數   | `256-512`              |

---

## 7. 記憶體與內部機制

### 7.1 NCCL 通訊記憶體模型

NCCL 為每個通訊操作管理三級緩衝：

| 緩衝類型            | 位置     | 用途           | 管理策略                       |
| ------------------- | -------- | -------------- | ------------------------------ |
| Send Buffer         | GPU VRAM | 待傳送資料的源 | 使用者提供，NCCL 直接讀取        |
| Receive Buffer      | GPU VRAM | 接收資料的目標 | 使用者提供，NCCL 直接寫入        |
| Intermediate Buffer | GPU VRAM | 歸約中間結果   | NCCL 內部分配，雙緩衝/環形緩衝 |

A100 的 HBM2e (5120-bit, 2039 GB/s) 為 NCCL 提供了充足的內部緩衝頻寬。詳見 [HBM 顯存技術演進](../../01_hardware_architecture/performance/01_hbm_evolution.md) | [GPU 記憶體層次結構](../../01_hardware_architecture/nvidia/understand_gpu_architecture/02_gpu_memory.md)。

### 7.2 AllReduce 執行流水線

NCCL 將 AllReduce 拆分為非同步流水線：

```text
排隊 → 拓撲分析(首次) → 資源分配(GPU Stream + Buffer)
  → Reduce-Scatter(N-1輪 Ring/Tree)
  → AllGather(N-1輪) → 完成通知 → 釋放資源
```

每輪內部透過 CUDA Stream 實現 kernel 執行與資料傳輸的重疊。

### 7.3 快取與一致性

- 統一 L1/Shared Memory（A100 為 192 KB/SM）和 L2 (A100 40 MB) 被 NCCL 用於緩衝小塊資料
- GPU 使用弱一致性模型，NCCL 在需要時透過 `__threadfence_system()` 確保跨 GPU 可見性
- GPUDirect RDMA 涉及 PCIe 的 DMA 一致性，需 BAR1 對映正確配置

---

## 8. 容錯與監控

### 8.1 錯誤檢測層次

| 層級      | 機制                           | 恢復方式                     |
| --------- | ------------------------------ | ---------------------------- |
| HBM       | ECC 單位元自動糾正，雙位元檢測 | 驅動記錄錯誤計數，超閾值告警 |
| NVLink    | CRC 校驗                       | Replay 重傳，錯誤計數器監控  |
| PCIe      | AER (Advanced Error Reporting) | 驅動層重試或鏈路重訓練       |
| NCCL 軟體 | `ncclResult_t` 錯誤碼          | 上層框架重試或告警           |

### 8.2 NCCL 錯誤碼速查

| 錯誤碼                   | 含義          | 常見原因                 |
| ------------------------ | ------------- | ------------------------ |
| `ncclSuccess`            | 成功          | —                        |
| `ncclUnhandledCudaError` | CUDA 側錯誤   | OOM, kernel launch 失敗  |
| `ncclSystemError`        | 系統資源不足  | 記憶體不足, 檔案描述符耗盡 |
| `ncclInternalError`      | NCCL 內部錯誤 | 通訊鏈路異常, 參數無效   |
| `ncclInvalidArgument`    | 參數錯誤      | count/type/comm 不匹配   |
| `ncclInvalidUsage`       | 用法錯誤      | 重複初始化, 已銷燬 comm  |

### 8.3 容錯策略

- **檢查點機制**：定期儲存模型參數 + 最佳化器狀態 + 通訊拓撲快照，支援從故障恢復
- **彈性訓練**：NCCL 本身不支持 communicator 執行中的動態成員變更（拓撲在初始化時定型）。節點加入/離開靠上層框架（如 TorchElastic）在成員變化時重啟行程、重建 communicator
- **故障隔離**：NCCL 不做單 GPU 降級。初始化階段探測到異常路徑會直接報錯退出，通訊中的鏈路異常會置 communicator 為錯誤態；恢復都需要上層重建 communicator

---

## 參考

- [NCCL 官方文件](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/index.html)
- [GPUDirect RDMA 文件](https://docs.nvidia.com/cuda/gpudirect-rdma/index.html)
- [NCCL 環境變數參考](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html)
