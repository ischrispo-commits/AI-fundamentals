# MIG 配置與實操

> 基於 A100-SXM4-80GB (GPU 7, MIG Enabled) 的現場查詢資料。MIG (Multi-Instance GPU) 將一張物理 A100 切分為最多 7 個獨立 GPU 實例，每個實例有專用 SM、顯存、L2 Cache 和記憶體頻寬切片。本文覆蓋查詢、啟用/禁用、建立實例的全流程，基於 `nvidia-smi mig` 命令集，不執行任何變更操作。

---

## 1. 什麼是 MIG，為什麼需要它

在共享 GPU 叢集中，多個使用者的 workload 跑在同一張 GPU 上時面臨三個問題：

| 問題     | 傳統方案           | 方案缺陷                      |
| -------- | ------------------ | ----------------------------- |
| 顯存隔離 | 無（大家共享顯存） | OOM 互相影響                  |
| 算力隔離 | GPU 時間片 (MPS)   | 無故障隔離，kernel 可能被阻塞 |
| QoS 保證 | 靠排程器優先順序     | 無法保證延遲 SLO              |

**MIG 的解決方案**：在硬體層將一張 GPU 物理分割槽，每個實例獲得專用的 SM 集合、L2 Cache 分片、顯存容量與頻寬切片和顯存控制器（頻寬切片不等於獨立實體記憶體通道）。

```text
                    A100-80GB (MIG Disabled)
                    ┌───────────────────────┐
                    │    1 × 完整 GPU        │
                    │    108 SM, 80 GB      │
                    │    可被多個行程共享      │
                    └───────────────────────┘

                    A100-80GB (MIG Enabled)
                    ┌───────┬───────┬───────┐
                    │ 1g.10 │ 1g.10 │ 2g.20 │
                    │ 14 SM │ 14 SM │ 28 SM │
                    │ 9.5GB │ 9.5GB │19.5GB │
                    │隔離    │隔離    │隔離   │
                    └───────┴───────┴───────┘
```

**適用場景**：多租戶推理服務、CI/CD 資源隔離、小模型併發推理。不適合大規模訓練（需要整卡 SM 和顯存）。

---

## 2. 查詢 MIG 狀態

### 2.1 確認 MIG 模式

```bash
nvidia-smi -i 7 --query-gpu=mig.mode.current,mig.mode.pending --format=csv
```

GPU 7 當前狀態：

```text
mig.mode.current, mig.mode.pending
Enabled, Enabled
```

`Pending` 與 `Current` 一致說明 MIG 模式已穩定（無待處理的狀態變更）。

### 2.2 列出可用的 GPU Instance Profile

```bash
nvidia-smi mig -i 7 --list-gpu-instance-profiles
```

GPU 7 的所有 profile（A100-80GB）：

```text
+-------------------------------------------------------------------------------+
| GPU instance profiles:                                                        |
| GPU   Name               ID    Instances   Memory     P2P    SM    DEC   ENC  |
|                                Free/Total   GiB              CE    JPEG  OFA  |
|===============================================================================|
|   7  MIG 1g.10gb         19     7/7        9.50       No     14     0     0   |
|                                                               1     0     0   |
|   7  MIG 1g.10gb+me      20     1/1        9.50       No     14     1     0   |
|                                                               1     1     1   |
|   7  MIG 1g.20gb         15     4/4        19.50      No     14     1     0   |
|                                                               1     0     0   |
|   7  MIG 2g.20gb         14     3/3        19.50      No     28     2     0   |
|                                                               2     0     0   |
|   7  MIG 3g.40gb          9     2/2        39.25      No     42     3     0   |
|                                                               3     0     0   |
|   7  MIG 4g.40gb          5     1/1        39.25      No     56     4     0   |
|                                                               4     0     0   |
|   7  MIG 7g.80gb          0     1/1        79.00      No     98     5     0   |
|                                                               7     1     1   |
+-------------------------------------------------------------------------------+
```

**欄位解讀**：

| 字段                   | 含義                                                          |
| ---------------------- | ------------------------------------------------------------- |
| `Name`                 | Profile 名稱：N g.M GB — N 個 GPU 實例中的 SM 比例，M GB 顯存 |
| `Instances Free/Total` | 還可以建立幾個該 profile 的實例 / 最多幾個                    |
| `P2P`                  | MIG 實例間不支援 P2P（全部為 No）                             |
| `SM`                   | 分配給該實例的 SM 數量（A100 總共 108 SM，MIG 可用 98）       |
| `CE`                   | Copy Engine 數量（1×H2D, 1×D2H）                              |

### 2.3 MIG 對 CUDA 裝置列舉的影響

關鍵對比：

```bash
# 編譯同一個 CUDA 查詢程式
nvcc -arch=sm_80 -o check_device check_device.cu

# GPU 3 (MIG Disabled) → 正常
CUDA_VISIBLE_DEVICES=3 ./check_device
# 輸出: CUDA device count: 1
#        Device 0: NVIDIA A100-SXM4-80GB (CC 8.0, SM 108, Mem 79 GB)

# GPU 7 (MIG Enabled, 無實例) → 錯誤！
CUDA_VISIBLE_DEVICES=7 ./check_device
# 輸出: CUDA device count: <錯誤碼>
```

**解讀**：MIG Enabled 但沒有任何 GI（GPU Instance）被建立時，該 GPU 對 CUDA 應用**完全不可見**。這是 MIG 與普通模式的本質區別：必須建立至少一個 GI，CUDA 才能"看到"這個 GPU。

---

## 3. 啟用與禁用 MIG（命令參考，不執行）

> **重要**：啟用/禁用 MIG 需要 GPU reset，會斷開該 GPU 上的所有行程，且需要 root 許可權。以下命令僅供參考，不在本文環境中執行。

### 3.1 啟用 MIG

```bash
# 步驟 1：啟用 MIG 模式（GPU 會重置）
nvidia-smi -i <GPU_ID> -mig 1

# 步驟 2：確認模式切換完成
nvidia-smi -i <GPU_ID> --query-gpu=mig.mode.current,mig.mode.pending --format=csv
# 期望：Enabled, Enabled

# 步驟 3：建立 GPU Instance (GI)
nvidia-smi mig -i <GPU_ID> -cgi 19,19,14  # 建立 2×1g.10gb + 1×2g.20gb
# 這裡 19,14 是 profile ID (從 --list-gpu-instance-profiles 獲取)
# 建立後按順序分配 GI ID：0, 1, 2

# 步驟 4：建立 Compute Instance (CI)
nvidia-smi mig -i <GPU_ID> -cci 0 -gi 0,1,2  # 在 GI 0/1/2 中各建立 1 個 CI（CI profile 0）
```

**完整流程**：Enable MIG → Create GI → Create CI → CUDA 可見。GI 定義資源劃分，CI 是可被 CUDA 程式使用的實例。

### 3.2 禁用 MIG

```bash
# 一次性銷燬所有實例並關閉 MIG 模式
nvidia-smi -i <GPU_ID> -mig 0

# GPU 重置後恢復為完整裝置
```

**MIG 禁用后**：之前建立的 GI/CI 全部被銷燬，CUDA 重新看到完整的單 GPU 裝置。GPU 在此期間需要數秒重置時間。

### 3.3 查詢已建立的 MIG 實例

```bash
# 列出所有 GPU Instance (GI)
nvidia-smi mig -i <GPU_ID> --list-gpu-instances

# 列出所有 Compute Instance (CI)
nvidia-smi mig -i <GPU_ID> --list-compute-instances

# 銷燬特定 CI
nvidia-smi mig -i <GPU_ID> -dci -gi 0 -ci 0  # 銷燬 GI 0 中的 CI 0

# 銷燬特定 GI 及其 CI
nvidia-smi mig -i <GPU_ID> -dgi -gi 0
```

### 3.4 實例組合示例

以 GPU 7 的 profile 表為據，常見組合：

| 組合       | GI Profile                | 實例數 | 總顯存  | 用途                   |
| ---------- | ------------------------- | ------ | ------- | ---------------------- |
| 最大化實例 | 1g.10gb × 7               | 7      | 66.5 GB | 7 個開發者各用一片 GPU |
| 混合       | 1g.10gb × 3 + 2g.20gb × 2 | 5      | 67.5 GB | 小模型 + 中等模型混部  |
| 均衡       | 3g.40gb × 2               | 2      | 78.5 GB | 兩個獨立推理服務       |
| 最大單實例 | 7g.80gb × 1               | 1      | 79 GB   | 接近完整 GPU（98 SM）  |

---

## 4. GPU 7 vs GPU 3 狀態對比

| 屬性              | GPU 3 (正常)              | GPU 7 (MIG Enabled)        |
| ----------------- | ------------------------- | -------------------------- |
| MIG Mode          | Disabled                  | Enabled                    |
| CUDA device count | **1**                     | **0**（無可用的 GI/CI）    |
| 可用 GI Profile   | 存在（需要先 Enable MIG） | 7 個 profile               |
| CUDA 程式可見     | 是                        | 否（需要建立至少 1 個 GI） |
| NVLink            | NV12 全互聯               | 無（走 PCIe SYS）          |
| 當前顯存使用      | 130 MiB                   | 0 MiB                      |

> **GPU 7 同時失去 NVLink，處於 MIG Enabled 但未建立實例的狀態**：在 NCCL 拓撲中被標記為僅 PCIe 可達，且在 CUDA 中不可見。這是實驗室環境中的典型配置：專門留給 MIG 實驗而不影響訓練 GPU。

---

## 5. MIG 與訓練/推理的關係

| 場景               | 推薦配置                      | 原因                               |
| ------------------ | ----------------------------- | ---------------------------------- |
| 大規模訓練 (TP/PP) | MIG Disabled + NVLink         | 需要整卡顯存 + 跨卡高速通信        |
| 小模型推理         | MIG 1g.10gb × N               | 每實例 9.5 GB 足夠 Llama-7B (INT8) |
| 中等模型推理       | MIG 2g.20gb 或 3g.40gb        | Llama-13B/70B 量化版本             |
| 併發推理服務       | MIG 多實例 + CUDA MPS（可選） | 硬體隔離 + 額外時間片共享          |
| 開發者環境         | MIG 1g.10gb × 7               | 多個使用者互不干擾                   |

---

## 6. 相關文件

- [`07_a100_architecture.md`](understand_gpu_architecture/07_a100_architecture.md)：A100 MIG 能力的硬體基礎
- [`nvlink_diagnostics.md`](../nvlink/nvlink_diagnostics.md)：GPU 7 的 NVLink 故障與 MIG 配置的關係

## 參考

- [NVIDIA MIG User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/)
- [nvidia-smi mig 命令參考](https://docs.nvidia.com/deploy/nvidia-smi/index.html#mig)
- [NVIDIA A100 架構白皮書](https://images.nvidia.com/aem-dam/en-zz/Solutions/data-center/nvidia-ampere-architecture-whitepaper.pdf) — MIG 章節
