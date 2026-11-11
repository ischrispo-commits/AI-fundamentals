# GPU 排程為什麼比 CPU 排程難——碎片化、拓撲、Gang Scheduling

Kubernetes 預設排程器把 GPU 當成標量資源（`nvidia.com/gpu: 1`），和 CPU 的 `cpu: 4` 沒什麼區別。這個模型對於單 GPU 作業基本夠用，但對於 AI 叢集的真實負載有三個致命盲區：GPU 碎片化、拓撲不感知、Gang Scheduling 缺失。

本文從這三個問題出發，解釋為什麼 AI 叢集需要 GPU 感知的排程策略。後文展開具體的解決方案：Gang Scheduling（§02）、拓撲感知（§03）、GPU 共享排程（§04）。

---

## 一、盲區 1：GPU 碎片化——4 張空閒 GPU ≠ 可以跑 4-GPU 的訓練任務

K8s 預設排程器做的是「裝箱」：把每個 Pod 放到一個滿足資源請求的節點上。假設叢集有 2 個 8-GPU 節點，節點 A 已經被 4 個單 GPU 作業各佔了一張 GPU（GPU 0/2/4/6），剩余 4 張 GPU 空閒。此時一個請求 4 張 GPU 的訓練 Pod 提交，預設排程器看到節點 A 有 4 張空閒 GPU，會把它排程上去。

然后 Pod 啟動失敗。

為什麼？看剩余的卡落在哪。GPU 0/2/4/6 被佔滿後，剩下的是 GPU 1/3/5/7。如果這 4 張卡跨了 NVLink 域或 NUMA 邊界（分散在不同 PCIe switch 下、不同 NUMA node 上），TP=4 訓練的 NCCL 通信就要在 PCIe 和 NUMA 之間來回跳躍，頻寬會從 NVLink 的數百 GB/s 掉到 PCIe 的几十 GB/s（PCIe Gen4 x16 單向約 32 GB/s、Gen5 單向約 64 GB/s，跨 socket 再疊加 UPI 一跳約 28 GB/s，均為數量級估計）；如果它們仍在同一個 NVLink 域內，訓練就不受影響。預設排程器分辨不出這兩種情況。

**真實案例：一台 8×H100 的 NVSwitch 全互聯拓撲**（`nvidia-smi topo -m` 實測）：

```text
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18
...（所有 8 張 GPU 兩兩之間均為 NV18，同一個 NVSwitch 域）
```

所有 GPU 共享一個 NVSwitch 域，任意 pair 都有完整的 450 GB/s 單向頻寬。現在假設 4 個單 GPU 推理 Pod 分別佔用了 GPU 0、2、4、6：

```text
節點 A (8×H100, NVSwitch 全互聯)
┌─┬─┬─┬─┬─┬─┬─┬─┐
│■│ │■│ │■│ │■│ │  ← 4 個推理 Pod 各佔一張 GPU
└─┴─┴─┴─┴─┴─┴─┴─┘
 0 1 2 3 4 5 6 7

剩餘空閒: GPU 1,3,5,7 (4 張)
NVLink 實測頻寬: 任意 pair ~316 GB/s (all_reduce bus_bw)
```

此時提交一個 TP=4 的訓練作業，請求 4 張 GPU。K8s 預設排程器看到 `Allocatable: 4, Requested: 4 → OK`，排程成功。NVLink 實測也正常：這台 H100 的 8 張 GPU 全部在同一個 NVSwitch 域內，GPU 1/3/5/7 之間同樣是 NVLink 全速互聯，訓練不受影響。

但如果把同樣的場景放到一台 **無 NVSwitch、按 4 張一組 NVLink bridge 分組的 A100 伺服器**（常見的 8 卡 A100 機型）上：

```text
節點 B (8×A100, 無 NVSwitch, NVLink bridge 分組)
組 1 (GPU 0-3):  兩兩 NVLink ~600 GB/s 雙向 (bridge 互聯)
組 2 (GPU 4-7):  兩兩 NVLink ~600 GB/s 雙向 (bridge 互聯)
跨組 (GPU 0↔4):  PCIe P2P ~32 GB/s (Gen4 x16 單向, 數量級估計)  ← 只有 NVLink 的 1/10-1/5
```

此時 GPU 0/2/4/6 被占用后，剩余的 GPU 1/3/5/7 分屬兩個 bridge 組。TP=4 作業被排程到 GPU 1,3（組 1）和 GPU 5,7（組 2），跨組通訊只能走 PCIe，訓練吞吐從 90% 利用率跌到 30%。

預設排程器在兩個場景下看到的完全一樣：`Allocatable: 4, Requested: 4 → OK`。但實際結果天差地別，前者正常訓練，后者慢 3 倍。`nvidia.com/gpu` 表達不了 NVLink 域的拓撲邊界。

解決方案方向：拓撲感知排程 + 碎片整理（重排程/deschedule 低優先順序單 GPU 作業）。

---

## 二、盲區 2：拓撲不感知——最近的 GPU 不一定是挨著編號的

K8s 預設排程器不理解 GPU 之間的通訊路徑。它看到兩張 GPU，不會知道它們之間走 NVLink 還是 PCIe、延遲差幾個數量級。

```text
GPU 0 ← NVLink 450 GB/s       → GPU 1  ← 同一 NVLink 域，最快
GPU 0 ← PCIe ~32-64 GB/s      → GPU 4  ← 跨 NUMA，次快（Gen4/Gen5 單向，數量級估計）
GPU 0 ← UPI ~28 GB/s（經驗值）→ GPU 8  ← 跨 socket（雙路伺服器），最慢
```

（示意圖按雙路伺服器通用畫法：單節點 8 卡通常編號 0-7，跨 socket 的卡只在 16 卡這類更大規格的節點上才會編到 8。）

對於單 GPU 推理任務，拓撲無關緊要。對於 TP=8 的訓練，GPU 之間的通訊路徑決定了吞吐。如果 8 張 GPU 不在同一個 NVLink 域內、甚至跨了節點，訓練吞吐可能從 90% 利用率跌到 30%。

節點內的拓撲資訊來自 `nvidia-smi topo -m`。NVIDIA 早年提供一個 topology-aware scheduler 外掛來消費這些資訊，但該專案已下線（文件頁與 GitHub 倉庫均已 404），現行方案是 KAI-Scheduler（已入 CNCF sandbox）配合 Topograph 拓撲匯出層，詳見[拓撲感知排程](03_topology_aware_scheduling.md)。另外要注意，拓撲感知排程的效果取決於 GPU 資源的實際分配狀態：在高負載混合叢集中，拓撲最優的 GPU 很可能已經被其他作業佔用了。

---

## 三、盲區 3：Gang Scheduling——要麼全排程，要麼全不等

訓練任務是 All-or-Nothing 的：PyTorch DDP 初始化 NCCL communicator 時需要 **全部 rank 同時線上**。如果 8 GPU 的訓練任務只有 6 個 Pod 被排程、另外 2 個還在 Pending，已有的 6 個 Pod 會阻塞在 `init_process_group` 上——**占着 GPU 但不計算**，直到超時。

這種部分排程的後果是多重浪費：

- 已排程的 Pod 占着 GPU 空轉
- 未排程的 Pod 在佇列中卡住
- 其他等待 GPU 的作業因為「GPU 看似被佔滿」而得不到排程

K8s 預設排程器是逐個 Pod 獨立決策的，無法理解「只有全部 Pod 都能排程時，這個作業才有意義」。解決這個問題需要 Gang Scheduling：排程器在確認所有 Pod 的 GPU 需求都能滿足之前，不為任何一個 Pod 做排程決策。Volcano 的 Coscheduling 和 Kubernetes 原生的 SchedulingGates 是實現這一需求的主流方案。詳見 [Gang Scheduling：分散式訓練的 All-or-Nothing 排程](02_gang_scheduling_for_training.md)。

---

## 四、三個盲區的解決路徑

| 盲區               | 現象                                    | 解決方向                          | 詳見                                      |
| ------------------ | --------------------------------------- | --------------------------------- | ----------------------------------------- |
| GPU 碎片化         | 多 GPU 訓練無法找到連續 GPU 組          | 拓撲感知排程 + 碎片整理           | [§03](03_topology_aware_scheduling.md)    |
| 拓撲不感知         | 排程到跨 NUMA/跨 socket 的 GPU，通信慢  | NVLink/NUMA 感知的 Filter + Score | [§03](03_topology_aware_scheduling.md)    |
| 無 Gang Scheduling | 訓練任務部分 Pod 占 GPU 空轉            | Coscheduling / SchedulingGates    | [§02](02_gang_scheduling_for_training.md) |
| GPU 共享的粒度     | MIG/MPS/Timeslicing 如何暴露為 K8s 資源 | Device Plugin 的不同策略          | [§04](04_gpu_sharing_scheduling.md)       |

---

## 相關資源

- [Kubernetes 排程器介紹](https://github.com/ForceInjection/kubernetes-hands-on-course/tree/master/Advanced-Topics/调度/k8s-scheduler-intro-basic.md) — 預設排程器的工作原理
- [GPU 排程器擴展案例](https://github.com/ForceInjection/kubernetes-hands-on-course/tree/master/Advanced-Topics/调度/k8s-scheduler-gpu-case.md) — Device Plugin + 自定義排程器擴展
- [KAI-Scheduler（CNCF sandbox，NVIDIA 捐獻）](https://github.com/kai-scheduler/KAI-Scheduler)
- [NVIDIA Topograph](https://docs.nvidia.com/topograph/) — 拓撲匯出層，把叢集拓撲暴露給排程器
- [NCCL 通訊路徑逐層壓測](../03_nccl/06_nccl_path_benchmark.md) — NVLink 和 PCIe 到底差多少
