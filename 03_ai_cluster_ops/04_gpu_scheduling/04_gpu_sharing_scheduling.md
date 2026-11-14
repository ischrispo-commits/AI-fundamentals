# GPU 共享排程——MIG、MPS、Time-slicing 在 K8s 中的表達

不是所有 GPU 作業都需要獨佔一張卡。推理服務、Jupyter Notebook、小規模實驗，這些場景下，一張 A100 跑 8 個推理實例比 8 張 A100 各跑 1 個經濟得多。問題是在 K8s 中怎麼把「共享」表達為排程器能理解的資源模型。

三種共享方式（MIG 硬切分、MPS 計算共享、Time-slicing 分時多工）對排程器來說是三種完全不同的資源抽象。

---

## 一、MIG：顯存和 SM 的硬切分

MIG 將一張物理 GPU 切分為多個獨立的 GPU 實例，每個實例有專屬的顯存、SM 和頻寬。以 A100-80GB 為例，最多可以切為 7 個 10GB（`1g.10gb`×7）、3 個 20GB（`2g.20gb`×3）或 2 個 40GB（`3g.40gb`×2）。

對 K8s 排程器來說，每個 MIG 實例暴露為獨立的 `nvidia.com/mig-<profile>` 資源，不是 `nvidia.com/gpu`，而是更細粒度的資源類型：

```yaml
# MIG 切分後的資源類型
nvidia.com/mig-1g.10gb      # 1 個 GPU 計算切片 + 10GB 顯存
nvidia.com/mig-2g.20gb      # 2 個 GPU 計算切片 + 20GB 顯存
nvidia.com/mig-3g.40gb      # 3 個 GPU 計算切片 + 40GB 顯存

# Pod 請求一個 MIG 實例
apiVersion: v1
kind: Pod
spec:
  containers:
  - resources:
      limits:
        nvidia.com/mig-1g.10gb: 1    # 一個 10GB MIG 實例
```

**排程器的視角**：MIG 切分后，一張物理 GPU 對排程器來說變成了 7 個可排程單元。每個 MIG 實例的顯存和計算資源被硬隔離，一個實例 OOM 不會影響同一張 GPU 上的其他實例。代價是 MIG 實例間不支援 P2P/IPC；MPS 可以在單個 MIG 實例內使用（每個實例一個 MPS server，每 GPU 上限 48 個 client），但不能跨實例共享。

MIG 配置需要在節點層面預先設定（`nvidia-smi mig -cgi`），排程器無法動態切分——它只能排程到已切好的實例上。因此 MIG 適合推理場景中 GPU 資源規劃相對固定的情況。

---

## 二、MPS：計算資源共享，顯存不隔離

MPS 讓多個行程的 CUDA kernel 在同一張 GPU 上真正並行執行，而不是 Default 模式下的時間片切換。這與 MIG 的關鍵區別：

| 維度         | MIG                                 | MPS                                   |
| ------------ | ----------------------------------- | ------------------------------------- |
| 顯存         | 硬隔離，每個實例有固定顯存上限      | 共享，一個行程 OOM 影響整張 GPU       |
| 計算資源     | 硬隔離，每個實例有固定 SM 配額      | 共享，CUDA kernel 並行執行            |
| P2P          | 不支持                              | 支持（受拓撲限制）                    |
| K8s 資源模型 | 獨立的資源類型 (`nvidia.com/mig-*`) | 不改變資源模型，排程器不知道 MPS 存在 |

對 K8s 排程器來說，MPS 不改變資源模型——Pod 仍然請求 `nvidia.com/gpu: 1`，排程器不知道多個 Pod 被 MPS 排程到同一張 GPU 上。這意味著顯存超分是 MPS 在 K8s 中的核心挑戰：

```text
GPU 有 80GB 顯存
  Pod A 請求 nvidia.com/gpu: 1 → 排程器看到 1/1 GPU，排程成功 → 實際佔用 50GB
  Pod B 請求 nvidia.com/gpu: 1 → 排程器看到 1/1 GPU，已經滿了
  （但 Pod A 宣告瞭 1 GPU，預設排程器認為這張 GPU 已經被佔用了）
```

解決這個矛盾需要 Device Plugin 支持 GPU 共享策略。K8s 並沒有一個官方的 GPU 共享資源名，`nvidia.com/gpu.shared` 這樣的寫法並不存在；業界的做法是在 Device Plugin 層把 `nvidia.com/gpu` 的 replicas 擴容來表達共享，代表性方案有三種：NVIDIA GPU Operator 的 Time-slicing（下一節）、阿里開源的 gpushare（用 `aliyun.com/gpu-mem` 請求顯存額度）、HAMi 的 vGPU 配額（沿用 `nvidia.com/gpu`，顯存/算力配額記在節點註記上）。

---

## 三、Time-slicing：分時多工

NVIDIA GPU Operator（截至 2026-10 最新為 v26.7.x）支持 Time-slicing，在 Device Plugin 層面將一張物理 GPU 虛擬化為多個邏輯 GPU：

```yaml
# GPU Operator 的 time-slicing 配置
# 將一張物理 GPU 暴露為 4 個邏輯 GPU
apiVersion: v1
kind: ConfigMap
metadata:
  name: time-slicing-config
data:
  any: |-
    version: v1
    flags:
      migStrategy: none
    sharing:
      timeSlicing:
        resources:
        - name: nvidia.com/gpu
          replicas: 4          # 每張物理 GPU → 4 個邏輯 GPU
```

配置后，K8s 看到的 GPU 資源從 `8 × nvidia.com/gpu` 變為 `32 × nvidia.com/gpu`，每個 Pod 請求 `nvidia.com/gpu: 1` 時，實際獲得的是 1/4 張 GPU 的時間片。

**代價**：Time-slicing 不提供顯存隔離。4 個 Pod 共享 80GB 顯存，排程器不知道每個 Pod 實際用了多少。一個 Pod 的顯存洩漏可以導致同 GPU 上的其他 Pod OOM。同時，時間片切換引入了排程延遲——推理服務的 P99 latency 會明顯惡化。

---

## 四、三種共享方式的決策矩陣

| 場景                           | 推薦方式           | 原因                                                  |
| ------------------------------ | ------------------ | ----------------------------------------------------- |
| 多租戶推理，需要嚴格 SLA 隔離  | MIG                | 顯存和 SM 硬隔離，互不影響                            |
| 多個輕量推理服務，顯存佔用可控 | MPS + Time-slicing | MPS 提供計算並行，Time-slicing 讓排程器能分配多個 Pod |
| 開發/實驗環境，隔離需求低      | Time-slicing       | 配置最簡單，不需要手動切 GPU                          |
| 訓練作業                       | 不共享，獨佔整卡   | 訓練對顯存和頻寬要求高，共享模式效能損失不可接受      |

---

## 五、相關資源

- [NVIDIA GPU Operator Time-slicing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)
- [GPU 行程與資源管理](../01_gpu_ops/07_gpu_process_management.md) — MPS 和 MIG 的命令行操作
- [GPU 排程問題總覽](01_gpu_scheduling_problem.md)
