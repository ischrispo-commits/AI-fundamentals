# GPU 行程與資源管理

> 基於 8 × A100-SXM4-80GB (NVSwitch Gen2) 生產環境實測。GPU 是共享資源——多使用者、多工同時提交時，如何確保正確的人在正確的卡上執行，如何隔離顯存、如何避免 OOM、如何排查殘留行程。本文從 Compute Mode 到 NUMA 親和性完整覆蓋。

---

## 1. Compute Mode：GPU 的共享策略

GPU 的 Compute Mode 決定多個行程能否同時在該 GPU 上執行計算：

```bash
nvidia-smi --query-gpu=index,name,compute_mode --format=csv
```

當前環境輸出（全部 Default）：

```text
0, NVIDIA A100-SXM4-80GB, Default
3, NVIDIA A100-SXM4-80GB, Default
7, NVIDIA A100-SXM4-80GB, Default
```

| Mode                  | 含義                                                  | 適用場景                     |
| --------------------- | ----------------------------------------------------- | ---------------------------- |
| **Default**           | 多個行程可以在同一 GPU 上同時執行 CUDA 程式碼           | 共享叢集、開發環境           |
| **EXCLUSIVE_PROCESS** | 同一時刻只有一個行程的 CUDA context 能在該 GPU 上存在 | 專機專用訓練、性能 benchmark |
| **PROHIBITED**        | 該 GPU 禁止任何 CUDA 程序使用                         | 預留 GPU（如留給 MIG 實驗）  |
| **EXCLUSIVE_THREAD**  | 已廢棄，同 EXCLUSIVE_PROCESS                          | —                            |

```bash
# 設定 GPU 3 為獨佔模式（需要 root）
nvidia-smi -i 3 -c 1    # 1=EXCLUSIVE_PROCESS

# 恢復預設可共享
nvidia-smi -i 3 -c 0    # 0=Default
```

> **Default 模式的隱患**：兩個訓練任務同時佔用同一 GPU 時不會報錯，各自認為自己擁有全部顯存，直到 OOM。Default 模式適合開發環境，生產訓練建議 EXCLUSIVE_PROCESS。

---

## 2. MPS：多行程共享 GPU 計算資源

MPS（Multi-Process Service）是另一種 GPU 共享機制，與 Compute Mode 互補：

| 方式                               | 顯存               | 計算資源                         | 適用場景                   |
| ---------------------------------- | ------------------ | -------------------------------- | -------------------------- |
| **Default + CUDA_VISIBLE_DEVICES** | 共享（可超額）     | 時間片輪轉                       | 開發環境                   |
| **MPS**                            | 共享               | 真正並行（CUDA kernel 併發執行） | 多個小推理服務共享一張 GPU |
| **MIG**                            | 硬切分（獨立顯存） | 硬切分（獨立 SM）                | 嚴格隔離的生產推理         |
| **EXCLUSIVE_PROCESS**              | 獨佔               | 獨佔                             | 訓練、benchmark            |

MPS 的核心價值：讓多個行程的 CUDA kernel 在 GPU 上**真正並行執行**，而不是 Default 模式下的時間片切換。Volta (SM 7.0) 及以上架構支援。

```bash
# 啟動 MPS 服務（需 root）
nvidia-cuda-mps-control -d

# 驗證
ps aux | grep mps

# 停止
echo quit | nvidia-cuda-mps-control
```

啟動後，所有 CUDA 行程自動透過 MPS 排程，無需修改程式碼。**限制**：MPS 與 MIG 互斥——啟用了 MIG 的 GPU 不能同時使用 MPS；MPS 不提供顯存隔離，一個行程 OOM 仍會影響同 GPU 上的其他行程。

> 典型部署：一張 A100 上同時跑 4 個輕量推理服務 → 開啟 MPS，用 `CUDA_VISIBLE_DEVICES` 圈定行程範圍，MPS 讓計算資源得到充分利用（MPS 不做顯存隔離，顯存超用風險仍在）。

---

## 3. 查看 GPU 上的行程

### 3.1 nvidia-smi 行程列表

```bash
nvidia-smi --query-compute-apps=pid,process_name,used_memory,gpu_name --format=csv
```

當前環境（摘錄）：

```text
pid, process_name, used_gpu_memory [MiB], gpu_name
2159821, sglang::scheduler_TP1, 9752 MiB, NVIDIA A100-SXM4-80GB
2160317, sglang::scheduler_TP0, 9752 MiB, NVIDIA A100-SXM4-80GB
2332308, VLLM::EngineCore, 75172 MiB, NVIDIA A100-SXM4-80GB
1105912, ada_be, 4770 MiB, NVIDIA A100-SXM4-80GB
2095211, VLLM::EngineCore, 75260 MiB, NVIDIA A100-SXM4-80GB
```

- sglang 占用 GPU 0/1 各 ~9.5 GB — TP=2 推理
- vllm 占用 GPU 2/6 各 ~75 GB — 大模型推理
- ada_be 占用 GPU 6 的 4.7 GB — 開發環境
- GPU 3/4/5 空閒（僅 4-130 MiB 驅動佔用）

### 3.2 fuser：排查殘留行程

`nvidia-smi` 列出的都是有行程名的活躍行程。但有時行程已退出、顯存卻未釋放：

```bash
fuser -v /dev/nvidia*
```

正常輸出會列出每個 `/dev/nvidia*` 裝置檔案的開啟行程。如果列出的 PID 在 `nvidia-smi` 中看不到 → 殭屍 GPU context（行程退出但 CUDA context 未釋放）。

**清理殘留 context**：

```bash
# 1. 確認行程已退出
ps aux | grep <PID>

# 2. 等待 CUDA context 自動回收（通常 < 30s），大多數情況這樣就夠了

# 3. 如果等待後仍未釋放，且該 GPU 已無其他負載，用 GPU reset 強制清空
nvidia-smi -i <ID> -r
# 需要 root；reset 要求 GPU 上沒有執行中的行程，生產環境不保證總能成功，失敗兜底是重啟機器
```

> **常見場景**：Python 指令碼 `Ctrl+C` 中斷後，PyTorch 的 CUDA context 可能延遲數秒才釋放。`-pm 0/-pm 1` 只切換驅動是否常駐，並不清理殘留 context；清不掉時的標準做法是 GPU reset（`-r`）或重啟。

---

## 4. CUDA_VISIBLE_DEVICES：行程級 GPU 選擇

這是最常用的 GPU 隔離方式——設定環境變數，讓行程只能"看到"指定的 GPU：

```bash
# 只使用 GPU 3
CUDA_VISIBLE_DEVICES=3 python train.py

# 使用 GPU 0,3,5（對映為 device 0,1,2）
CUDA_VISIBLE_DEVICES=0,3,5 python train.py

# 排除 GPU 7
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6 python train.py
```

**對映規則**：

```text
物理 GPU:  0  1  2  3  4  5  6  7
設定:      3,5,7
映射后:    ─  ─  ─  0  ─  1  ─  2  ← 行程內的 device ID
                (不可見)
```

**常見用法**：

| 場景                 | 命令                                                       | 說明                                |
| -------------------- | ---------------------------------------------------------- | ----------------------------------- |
| 每個使用者分配專屬 GPU | `CUDA_VISIBLE_DEVICES=3`                                   | 行程只看得到 GPU 3，對映為 device 0 |
| 訓練避開生產 GPU     | `CUDA_VISIBLE_DEVICES=3,4,5`                               | 用空閒的 GPU 3/4/5                  |
| 多 GPU 分布式        | `CUDA_VISIBLE_DEVICES=0,1,2,3 torchrun --nproc_per_node=4` | 在 4 GPU 上並行                     |
| 排除故障 GPU         | 排除 GPU 7（NVLink 故障）                                  | 避免 NCCL fallback 到 PCIe          |

> **限制**：`CUDA_VISIBLE_DEVICES` 只對單個行程生效，不影響其他使用者。多個使用者仍可透過 `CUDA_VISIBLE_DEVICES=3` 同時使用同一 GPU（除非設定了 EXCLUSIVE_PROCESS）。

---

## 5. GPU-NUMA 親和性繫結

A100 透過 PCIe 連線到特定的 NUMA node。如果 GPU 和 CPU 執行緒不在同一 NUMA node，H2D/D2H 傳輸需要跨 socket 經 QPI/UPI，延遲顯著增加。

### 5.1 查看 GPU 的 NUMA 歸屬

```bash
nvidia-smi topo -m
```

```text
        GPU0  ...  GPU3  GPU4  ...  GPU7  CPU Affinity    NUMA Affinity
GPU3    ...       X    NV12  ...  NV12  0-23,48-71       0
GPU7    ...      SYS    PXB  ...   X    24-47,72-95      1
```

- GPU 0-3 → NUMA node 0, CPUs 0-23, 48-71
- GPU 4-7 → NUMA node 1, CPUs 24-47, 72-95

### 5.2 NUMA 繫結：taskset + numactl

```bash
# 將行程繫結到 GPU 3 所屬的 NUMA node 0 的 CPU
taskset -c 0-23,48-71 CUDA_VISIBLE_DEVICES=3 python train.py

# 或用 numactl
numactl --cpunodebind=0 --membind=0 CUDA_VISIBLE_DEVICES=3 python train.py
```

**為什麼重要**：

| 場景                                          | H2D 路徑            | NUMA 距離 | 影響                   |
| --------------------------------------------- | ------------------- | --------- | ---------------------- |
| GPU 3 (node 0)，CPU 執行緒在 node 1 或被排程到遠端 | 跨 socket 經 UPI    | 32        | 延遲顯著增加，頻寬下降 |
| GPU 3 (node 0)，CPU 執行緒繫結到 node 0         | 本地訪問            | 10        | 最優                   |

```bash
# 查看 NUMA 距離
numactl --hardware
# node 0 → node 1: 32  (跨 socket, 慢)
# node 0 → node 0: 10  (本地, 快)
```

> **經驗法則**：單 GPU 推理對 NUMA 不敏感（H2D 每請求只發生一兩次，繫結收益有限）；多 GPU 分散式訓練建議用 `torchrun` / `mpirun` 的 NUMA 感知啟動器，或手動 `taskset` / `numactl` 繫結。

---

## 6. 顯存管理

### 6.1 檢查顯存使用

```bash
nvidia-smi --query-gpu=index,memory.used,memory.free,memory.total --format=csv
```

GPU 3/4/5 的顯存狀態：

```text
3, 130 MiB, 81790 MiB, 81920 MiB
4, 4 MiB, 81916 MiB, 81920 MiB
5, 4 MiB, 81916 MiB, 81920 MiB
```

- 130 MiB（GPU 3）：之前跑過測試後 CUDA context 可能未完全釋放
- 4 MiB（GPU 4/5）：純空閒，僅驅動開銷

### 6.2 PyTorch 顯存控制

```python
import torch

# 限制 PyTorch 可用的最大顯存比例（多行程共享 GPU 時有用）
torch.cuda.set_per_process_memory_fraction(0.5)  # 只用 50%

# 控制顯存分配器的碎片化行為
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"
```

> `set_per_process_memory_fraction` 在多行程共享同一 GPU 時最有用——限制每個行程不會搶光全部顯存。單行程獨佔 GPU 時不需要設。

### 6.3 清理顯存

```python
# 釋放 PyTorch 快取的顯存（不釋放仍被引用的 tensor）
torch.cuda.empty_cache()
gc.collect()                    # 先回收 Python 側的無效引用
torch.cuda.empty_cache()        # 再釋放 CUDA 側快取
```

> `empty_cache()` 只釋放 PyTorch 分配器快取的空閒塊，不會釋放正在使用的 tensor。訓練中 OOM 的根因通常是 batch size 太大或模型太大——先降 batch，再考慮 gradient checkpointing。排查流程見 [§7 常見問題](#7-常見問題與排查)。

---

## 7. 常見問題與排查

| 問題                   | 現象                                      | 排查                                             | 解決                                                     |
| ---------------------- | ----------------------------------------- | ------------------------------------------------ | -------------------------------------------------------- |
| 顯存洩漏               | `nvidia-smi` 顯示顯存佔用但無行程         | `fuser -v /dev/nvidia*` 找殭屍 PID               | `kill -9 <PID>` 或重啟 persistenced                      |
| 多使用者衝突             | 兩個訓練任務 OOM                          | `nvidia-smi --query-compute-apps` 看是否同一 GPU | 設定 EXCLUSIVE_PROCESS 或用 `CUDA_VISIBLE_DEVICES`       |
| 跨 NUMA 延遲高         | H2D 頻寬遠低於預期 (~15 GB/s vs ~28 GB/s) | `numactl --hardware` 看 GPU 和 CPU 的 NUMA 歸屬  | `taskset` 繫結 CPU 到對應 NUMA node                      |
| CUDA out of memory     | 訓練中途 OOM                              | `nvidia-smi` 看剩餘顯存                          | 減小 batch size / 啟用 gradient checkpointing            |
| GPU 3 (130 MiB) 不是 0 | CUDA context 未完全釋放                   | `nvidia-smi` 無活躍行程但 `memory.used > 0`      | 等待自動回收；未釋放則 `nvidia-smi -i <ID> -r`（需無應用佔用）或重啟 |

---

## 8. 相關文件

- [`03_nvidia_smi_guide.md`](03_nvidia_smi_guide.md)：nvidia-smi 基礎命令詳解
- [`06_gpu_health_check.md`](06_gpu_health_check.md)：行程殘留檢查是 L1 健康檢查的一部分
- [NVLink 診斷與實操](../../01_hardware_architecture/nvlink/nvlink_diagnostics.md)：GPU 7 NVLink 故障 → 建議在分散式訓練中排除
- [GPU P2P 頻寬實測](../../02_gpu_programming/04_profiling/08_p2p_bandwidth.md)：NUMA 親和性直接影響 P2P 頻寬

---

## 參考

- [NVIDIA nvidia-smi 文件](https://docs.nvidia.com/deploy/nvidia-smi/)
- [CUDA Environment Variables](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#env-vars)
