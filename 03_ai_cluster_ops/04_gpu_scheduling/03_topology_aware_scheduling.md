# 拓撲感知排程——讓排程器知道 NVLink 和 NUMA

預設 K8s 排程器處理 `nvidia.com/gpu: 4` 時，只要能找到 4 張空閒 GPU 就視為滿足。它不管這 4 張 GPU 之間走 NVLink 還是 PCIe、在同一個 NUMA node 上還是跨 socket。結果是：訓練 Pod 雖然啟動成功了，但 NCCL 通訊頻寬可能比最優路徑差一個數量級。

本文解釋拓撲感知排程的三層：GPU 親和性、NUMA 親和性、跨節點親和性。

---

## 一、GPU 親和性——NVLink 域內 vs 跨 NVSwitch

同一個節點上 8 張 A100/H100 透過 NVSwitch 全互聯（DGX/HGX 機型）。任意兩張 GPU 都能達到 NVLink 最高頻寬（H100: ~450 GB/s 理論單向頻寬，NCCL all_reduce 實測 bus_bw ~316 GB/s；A100: ~600 GB/s 雙向）。但並非所有 8 卡機型都有 NVSwitch：無 NVSwitch 的 A100 伺服器按 4 張一組用 NVLink bridge 互聯，如果 4 張 GPU 分別來自兩個 bridge 組，跨組通訊需要經過 PCIe 中轉：

```text
bridge 組 1 (GPU 0-3):          bridge 組 2 (GPU 4-7):
  GPU 0 ←→ GPU 3: NVLink          GPU 4 ←→ GPU 7: NVLink
  GPU 0 ←→ GPU 4: PCIe P2P        ← 跨組，走 PCIe
                                    （頻寬約 NVLink 的 1/10-1/5，數量級估計）
```

排程器的任務是：為 TP=4 的作業分配 4 張 GPU 時，優先選擇**全部在同一個 NVLink 域內**的 GPU 組。

### 1.1 實現方式（概念模型）

拓撲感知排程在 Filter 和 Score 階段做兩件事：

- **Filter**：剔除不滿足拓撲約束的候選。比如 TP=4 的作業，如果某個候選節點找不出同一個 NVLink 域內的 4 張卡，就把它排除。
- **Score**：在透過 Filter 的候選裡，給拓撲更優的節點更高分。同 NVLink 域 > 同 PCIe switch > 同 NUMA node。

這套概念模型是通用的，但落到具體產品，配置入口各不相同，並不存在 `nvidia.com/gpu.topo.nvswitch`、`schedulerName: nvidia-topology-aware-scheduler` 這類統一欄位。

### 1.2 現狀：專案已換代（截至 2026-10）

NVIDIA 早年開源過一個 topology-aware scheduler（基於 Volcano 的 PodGroup/minMember 機制構建），但其文件頁和 GitHub 倉庫都已下線，圍繞它的各種配置寫法隨之失效。NVIDIA 現行的方案是：

- **KAI-Scheduler**：源自 Run:AI 排程器，NVIDIA 捐給 CNCF 的 sandbox 專案（2025 年受理），內建 gang 排程與拓撲感知放置（topology 維度）。
- **Topograph**：NVIDIA 開源的拓撲匯出層，把 NVLink/PCIe/IB 拓撲整理成節點標籤，供 KAI-Scheduler 等排程器消費。

生態裡的其他選擇：Volcano 的 network-topology-aware 排程（HyperNode 層級）、HAMi 的 GPU 池化與親和排程。

### 1.3 代價

強制執行拓撲約束會降低 GPU 利用率：如果在某個節點上同 NVLink 域的 4 張 GPU 被占用，即使有其他 4 張空閒 GPU 分佈在兩個 NVLink 域中，這個 Pod 也不會被排程。對於訓練任務這是正確的取捨（慢 10 倍的訓練 ≈ 浪費），但對於推理任務（單 GPU，無跨 GPU 通信），拓撲約束沒有意義。

---

## 二、NUMA 親和性——GPU 離哪個 CPU 更近

GPU 透過 PCIe 連線到特定的 NUMA node。H2D 傳輸時，如果 CPU 執行緒和 GPU 不在同一個 NUMA node，資料需要跨 QPI/UPI 傳輸，延遲翻倍：

```text
2-socket 伺服器 (Intel Xeon):
  socket 0 ──QPI── socket 1
    │               │
  NUMA 0         NUMA 1
    │               │
  GPU 0-3         GPU 4-7     ← GPU 物理上繫結到特定的 NUMA node
  CPU 0-23        CPU 24-47   ← CPU core 也繫結到 NUMA node

錯誤: GPU 0 (NUMA 0) + CPU 24 (NUMA 1) → H2D 跨 QPI，~2 倍延遲
正確: GPU 0 (NUMA 0) + CPU 0  (NUMA 0) → H2D 本地，最優延遲
```

排程器應在 Score 階段為 CPU 和 GPU 在同一個 NUMA node 的分配賦予更高分。

### 2.1 實現方式

K8s 1.18+（beta）的 Topology Manager 配合 CPU Manager + Memory Manager 可以做 NUMA 對齊（功能在 1.16 以 alpha 引入）。GPU 的 NUMA 親和性需要 Device Plugin 在 `Allocate()` 時上報拓撲資訊：

```yaml
# Kubelet Topology Manager 策略
# /var/lib/kubelet/config.yaml
topologyManagerPolicy: single-numa-node # 所有資源在同一 NUMA node
# 可選: best-effort, restricted, single-numa-node
```

`single-numa-node` 策略會導致 Pod 被限制在一個 NUMA node 內：如果 GPU 在 NUMA 0 但所需的 CPU 核心不夠，Pod 不會排程。這是最嚴格的策略，只在延遲極其敏感的場景（如 HPC 訓練）中使用。

### 2.2 建議

| 場景                                | NUMA 策略                        |
| ----------------------------------- | -------------------------------- |
| 單 GPU 推理、H2D 只发生一次         | 不需要 NUMA 對齊                 |
| 多 GPU 訓練，DataLoader 放在 CPU 端 | `best-effort` — 儘量對齊但不強制 |
| HPC 訓練、GPU-direct RDMA 頻繁傳輸  | `single-numa-node` — 強制執行    |

---

## 三、跨節點親和性——什麼時候才需要關心

Gang Scheduling（§02）解決了「跨節點 GPU 數量足夠」的問題，但不解決「跨節點通訊有多快」的問題。TP=8 如果跨了 2 個節點，NCCL 通訊就要從 NVLink（μs 級）換成 IB（10-20 μs 級），延遲上升一個數量級（數量級估計）。

對於 TP（Tensor Parallelism），跨節點必須避免：TP 的通訊頻率極高，延遲的放大直接反映為訓練吞吐的下降。排程器應優先將 TP 組內的 GPU 放在同一節點上。

對於 DP（Data Parallelism），跨節點不可避免，梯度同步本來就是節點間的操作，IB 頻寬可接受。DP 的訓練作業不需要拓撲約束。

```text
訓練作業: 2 節點 × 4 GPU = 8 GPU 總量
  TP=4: 每個節點 4 GPU，節點內 NVLink 通信 → 拓撲約束: 同節點
  DP=2: 節點間 IB 梯度同步 → 拓撲約束: 無特殊要求
```

大多數深度學習框架（PyTorch DDP、DeepSpeed）在啟動時允許使用者指定 TP size 和節點的對映關係，排程器只需要確保 TP 組內的 GPU 在同一個節點上即可，不再需要更細粒度的 NVSwitch 域感知。

---

## 四、實測案例：NVLink 和 PCIe 到底差多少

以下資料來自同一台 8×H100 NVSwitch 伺服器（詳見 [NCCL 通訊路徑逐層壓測](../03_nccl/06_nccl_path_benchmark.md)）：

| 通訊路徑                                 | 512MB all_reduce bus_bw | 排程含義                         |
| ---------------------------------------- | ----------------------- | -------------------------------- |
| NVLink GPU0↔GPU1（同 NVSwitch 域）       | **315.8 GB/s**          | 最優，TP 組內 GPU 的期望值       |
| NVLink GPU0↔GPU4（跨 NUMA，同 NVSwitch） | **316.3 GB/s**          | 同 NVSwitch 域內，NUMA 無影響    |
| P2P 禁用 GPU0↔GPU1（走 PCIe fallback）   | **23.8 GB/s**           | 比 NVLink 慢 13 倍，訓練不可接受 |

關鍵發現：同 NVSwitch 域內跨 NUMA 不影響頻寬（316.3 ≈ 315.8 GB/s），排程器不需要擔心 NUMA 對 GPU-GPU 通訊的影響。真正要避免的是跨 NVLink 域（走 PCIe P2P）或禁用 P2P（CPU fallback）的路徑，它們比 NVLink 慢一個數量級。

---

## 五、三層拓撲感知總結

| 層級         | 排程器需要知道什麼                      | 約束強度                 | 典型場景                  |
| ------------ | --------------------------------------- | ------------------------ | ------------------------- |
| GPU 親和性   | 哪些 GPU 在同一個 NVSwitch 域內         | 強（TP 組必須同域）      | TP=4/8 訓練               |
| NUMA 親和性  | 哪些 CPU core 和 GPU 在同一個 NUMA node | 中（Score 偏好，不強制） | DataLoader 效能敏感的訓練 |
| 跨節點親和性 | TP 組不跨節點                           | 強（TP 組必須同節點）    | 任何 TP > 1 的訓練        |

---

## 相關資源

- [KAI-Scheduler（CNCF sandbox）](https://github.com/kai-scheduler/KAI-Scheduler)
- [NVIDIA Topograph](https://docs.nvidia.com/topograph/) — 拓撲匯出層
- [K8s Topology Manager](https://kubernetes.io/docs/tasks/administer-cluster/topology-manager/)
- [GPU 排程問題總覽](01_gpu_scheduling_problem.md)
- [NCCL 通訊路徑逐層壓測](../03_nccl/06_nccl_path_benchmark.md) — NVLink 和 PCIe 實測差距
