# Gang Scheduling——分散式訓練的 All-or-Nothing 排程

PyTorch DDP 初始化時，所有 rank 需要同時執行 `init_process_group`。如果 8 GPU 的訓練任務只有 6 個 Pod 被排程，已有的 6 個 Pod 會阻塞在初始化上——占着 GPU、不計算、等待超時。這就是預設排程器逐個 Pod 決策的結構性問題：排程器不知道哪些 Pod 屬於同一個訓練作業。

本文解釋 Gang Scheduling 的兩種主流實現方式：Volcano Coscheduling 和 Kubernetes SchedulingGates。

---

## 一、問題：部分排程的三重浪費

一個典型場景：

```text
叢集: 2 節點 × 8 GPU，節點 A 還剩 6 GPU，節點 B 還剩 4 GPU
作業: TP=8 訓練，需要 8 GPU

K8s 預設排程器逐個處理 8 個 Pod:
  Pod 0-5: 排程到節點 A（佔滿剩餘 6 GPU）
  Pod 6-7: Pending（沒有足夠 GPU 了）

結果:
  Pod 0-5 啟動 → init_process_group → 等 Pod 6-7 → 阻塞
  節點 A 的 6 GPU 被佔但零計算
  節點 B 的 4 GPU 空閒但 Pod 6-7 不夠分配
  整個作業卡死
```

**三重浪費**：（1）已排程的 GPU 被無效佔用；（2）其他作業因為節點 A "GPU 已滿"得不到排程；（3）訓練作業自身因超時而整體失敗，GPU 釋放後一切從頭再來。

---

## 二、方案 A：Volcano Coscheduling

Volcano 是 CNCF 的批次計算排程器（截至 2026-10 最新版本 v1.16.0），在原生 K8s 排程能力之上增加了 Gang Scheduling、Fair-share、Queue 等特性。其 Coscheduling 的實現思路是：

```text
1. PodGroup 建立 → 宣告 "這個作業需要 8 個 Pod"
2. 排程器不是逐個排程 Pod，而是為整個 PodGroup 做決策
3. 只有當 8 個 Pod 的資源需求都能滿足時，才一次提交排程
4. 如果資源不夠 → 整個 PodGroup 排隊等待，不占任何 GPU
```

核心配置：

```yaml
apiVersion: scheduling.volcano.sh/v1beta1
kind: PodGroup
metadata:
  name: training-job-tp8
spec:
  minMember: 8 # 至少 8 個 Pod 全部就緒才啟動
  minResources: # 整組最低資源總量（組級，非按 Pod）
    nvidia.com/gpu: "8"
  queue: ai-training # 所屬佇列
---
# 每個訓練 Pod 中指定所屬的 PodGroup
apiVersion: v1
kind: Pod
metadata:
  annotations:
    scheduling.k8s.io/group-name: training-job-tp8 # 關聯到 PodGroup（Volcano 官方註記）
spec:
  schedulerName: volcano # 使用 Volcano 排程器
  containers:
    - resources:
        limits:
          nvidia.com/gpu: 1
```

Pod 與 PodGroup 的關聯靠的是 Pod 上的 `scheduling.k8s.io/group-name` 註記（Volcano 官方文件與原始碼口徑；不少老資料寫作 `scheduling.volcano.sh/podgroup` 的 label，這個 key 並不存在）。與預設排程器的關鍵區別：Volcano 在看到 8 個 Pod 時不會逐個提交——它先檢查叢集中是否存在能同時容納 8 個 Pod 的節點/節點組。如果存在，一次性全調；如果不存在，PodGroup 進入 `Inqueue` 狀態等待。

---

## 三、方案 B：Kubernetes SchedulingGates（1.26+）

K8s 1.26 引入了 SchedulingGates，允許外部控制器在 Pod 上設定「柵欄」，被柵住的 Pod 不會被排程器處理。K8s 社群也在把 Gang Scheduling 收進原生能力：KEP-4671 以 Scheduling Gates 為基礎構建，1.35 進入 alpha、1.37 進入 beta（引入 Workload API），落地後可以不再依賴外部控制器。配合一個 Gang Scheduling Controller，可以在不替換排程器的前提下實現 All-or-Nothing：

```text
1. Job Controller 建立 8 個 Pod，每個 Pod 帶一個 scheduling gate
2. Gang Controller 檢測到 8 個 Pod 的 PodGroup 已就緒
3. Gang Controller 移除所有 8 個 Pod 的 scheduling gate
4. 排程器同時處理 8 個 Pod → 逐個排程但不是逐個搶佔
```

核心配置：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: training-worker-0
spec:
  schedulingGates: # K8s 1.26+
    - name: gang-scheduling # 有 gate 時排程器不處理此 Pod
  containers:
    - resources:
        limits:
          nvidia.com/gpu: 1
```

SchedulingGates 的優勢是不需要替換排程器，但劣勢也很明顯：移除 gate 後排程器仍然是逐個 Pod 決策，可能出現「部分 Pod 排程成功、部分仍 Pending」——只是把「先到先得」變成了「同時開始」。要徹底解決部分排程問題，仍需要在排程器層做 All-or-Nothing 決策，即 Volcano 的 Coscheduling 模型。

---

## 四、選型建議

| 場景                                    | 推薦方案                         | 原因                                                 |
| --------------------------------------- | -------------------------------- | ---------------------------------------------------- |
| 純訓練叢集，作業以多 GPU 分散式訓練為主 | Volcano Coscheduling             | 保證 All-or-Nothing，配合 queue 實現優先順序和公平排程 |
| 混合負載叢集，訓練 + 推理共存           | K8s SchedulingGates + 輕量控制器 | 不改排程器，漸進式引入 Gang Scheduling               |
| 已有 K8s 叢集，不想引入額外排程器       | SchedulingGates                  | 最小改動，但效果不如 Volcano 徹底                    |
| 多租戶 + 多佇列 + 優先順序                | Volcano                          | Queue + Fair-share 開箱即用                          |

---

## 五、相關資源

- [Volcano 官方文件](https://volcano.sh/en/docs/) — PodGroup / Queue / Coscheduling
- [K8s SchedulingGates KEP](https://github.com/kubernetes/enhancements/tree/master/keps/sig-scheduling/3521-pod-scheduling-readiness)
- [GPU 排程問題總覽](01_gpu_scheduling_problem.md) — 碎片化、拓撲、Gang Scheduling 三個盲區
- [拓撲感知排程](03_topology_aware_scheduling.md) — Gang Scheduling 解決「夠不夠」的問題，拓撲感知解決「快不快」的問題
