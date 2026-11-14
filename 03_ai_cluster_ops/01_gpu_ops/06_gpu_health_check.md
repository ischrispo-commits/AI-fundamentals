# GPU 叢集健康檢查

> 基於 A100-SXM4-80GB (8 GPU) 現場資料（採集於 2026-11 之前，驅動 535.183.01 + DCGM v3.3.9）。將日常運維中零散的檢查項整合為系統化的健康檢查流程：從溫度/功耗的快速掃一眼，到 NVLink 鏈路、ECC 錯誤、MIG 狀態等深入診斷。GPU 7（NVLink 故障 + MIG Enabled）作為貫穿全文的真實異常案例。

---

## 1. 檢查分層

健康檢查按深度分為三層：

| 層級               | 耗時   | 內容                                       | 頻率           |
| ------------------ | ------ | ------------------------------------------ | -------------- |
| **L1: 快速掃一眼** | < 10s  | 溫度、功耗、顯存使用、GPU-Util（僅參考）   | 日常登入時     |
| **L2: 結構檢查**   | < 1min | NVLink 鏈路、ECC 錯誤、MIG 模式、PCIe 狀態 | 部署前、故障后 |
| **L3: 壓力驗證**   | > 5min | DCGM diag、NCCL bandwidth、P2P test        | 硬體變更後     |

---

## 2. L1: 快速掃一眼

**一行體檢**（登入後第一件事）：

```bash
nvidia-smi --query-gpu=index,temperature.gpu,power.draw,memory.used,utilization.gpu \
  --format=csv,noheader
```

### 2.1 溫度與功耗

```bash
nvidia-smi --query-gpu=index,name,temperature.gpu,power.draw,power.limit --format=csv
```

本節點輸出：

```text
0, NVIDIA A100-SXM4-80GB, 28, 63.28 W, 400 W
1, NVIDIA A100-SXM4-80GB, 27, 62.80 W, 400 W
...
7, NVIDIA A100-SXM4-80GB, 26, 48.75 W, 400 W
```

**判斷標準**：

| 指標     | 正常範圍        | 預警                    | 危險               |
| -------- | --------------- | ----------------------- | ------------------ |
| 空閒溫度 | 25-40°C         | > 60°C（散熱不足）      | > 80°C（觸發降頻） |
| 空閒功耗 | 45-70W (A100)   | > 100W（有殘留行程）    | —                  |
| 滿載功耗 | 250-400W (A100) | < 250W（降頻/功率限制） | —                  |

> 本節點全部 8 GPU 溫度在 25-29°C，功耗 48-64W——空閒狀態健康。

### 2.2 顯存使用

```bash
nvidia-smi --query-gpu=index,memory.used,memory.total,memory.free --format=csv
```

發現顯存殘留（`memory.used > 500 MB` 且無行程）→ 殭屍行程未釋放顯存：`fuser -v /dev/nvidia*` 排查。

---

## 3. L2: 結構檢查

### 3.1 NVLink 鏈路拓撲

```bash
nvidia-smi topo -m
```

```text
        GPU0  GPU1  GPU2  GPU3  GPU4  GPU5  GPU6  GPU7
GPU0     X    NV12  NV12  NV12  NV12  NV12  NV12  NV12
...                                                       ← 中間行（GPU1/GPU2/GPU4/GPU5/GPU6）省略
GPU3    NV12  NV12  NV12   X    NV12  NV12  NV12  NV12
GPU7    SYS   SYS   SYS   SYS   NODE  NODE  PXB    X
```

**檢查點**：

- [ ] 除對角線外，所有 GPU 對是否都是 `NV12`？（如果有 `SYS`/`NODE` → 該 GPU NVLink 故障）
- [ ] 是否存在 `PIX`（PCIe P2P 可用但非 NVLink）？（單機多卡訓練不應出現）
- [ ] 同一 NUMA node 的 GPU 是否形成連續 NV12 組？

> 本節點：GPU 0-6 全部 NV12 ↔ OK。GPU 7 全部 SYS/NODE/PXB ↔ **NVLink 故障**。

### 3.2 NVLink 鏈路詳情

```bash
nvidia-smi nvlink --status        # 每條 link 速率
dcgmi nvlink -s                   # DCGM 緊湊輸出（適合指令碼）
```

```text
gpuId 0-6: U U U U U U U U U U U U   ← 12 links, all Up
gpuId 7:   _ _ _ _ _ _ _ _ _ _ _ _   ← 0 links, all Not Supported
```

**判斷**：gpuId 0-6 的 12 條 link 全部 `U`（Up），速率 25 GB/s → NVLink 3.0 健康。gpuId 7 全部 `_` → 物理層故障。

### 3.3 ECC 錯誤與 Retired Pages

ECC 是資料中心 GPU 的標配——A100 上預設啟用，覆蓋 HBM 顯存和內部 SRAM。

#### ECC 模式確認

```bash
nvidia-smi --query-gpu=index,ecc.mode.current --format=csv
```

本節點全部 8 GPU 均為 `Enabled`——資料中心 GPU 預設狀態。

#### Volatile vs Aggregate

```bash
nvidia-smi --query-gpu=index,ecc.errors.corrected.volatile.total,ecc.errors.uncorrected.volatile.total,ecc.errors.corrected.aggregate.total,ecc.errors.uncorrected.aggregate.total --format=csv
```

當前輸出（全部 `0`，僅 GPU 2 有 1 個 aggregate corrected 歷史記錄）：

| 類型          | 含義                                  | 重置方式                  |
| ------------- | ------------------------------------- | ------------------------- |
| **Volatile**  | 自上次驅動載入/GPU 重置以來的錯誤計數 | 重啟驅動或 GPU 重置后清零 |
| **Aggregate** | GPU 整個生命週期內的累計錯誤          | 不可清零（硬體記錄）      |

> **關鍵區分**：Volatile = 0 但 Aggregate > 0 → GPU 過去曾遇到錯誤但當前正常，無需處理。**Volatile 持續增長**才是需要關注的訊號——說明自上次重啟以來 HBM 仍在產生新的單位元錯誤。

#### 可接受的錯誤頻率

| 錯誤類型               | 正常           | 需關注                | 需立即處理 |
| ---------------------- | -------------- | --------------------- | ---------- |
| Corrected / Volatile   | 0-10/day       | > 100/day             | > 1000/day |
| Uncorrected / Volatile | **必須為 0**   | 任何非零值            | > 0        |
| Corrected / Aggregate  | 任何值（历史） | Volatile 與之同步增長 | —          |

#### SRAM vs DRAM 錯誤

```bash
nvidia-smi -i <ID> -q | grep -A8 'ECC Errors'
```

輸出區分兩類錯誤的來源：

```text
Volatile
    SRAM Correctable           : 0     ← GPU 內部 SRAM (寄存器文件、L1、共享記憶體)
    SRAM Uncorrectable         : 0
    DRAM Correctable           : 0     ← HBM 顯存
    DRAM Uncorrectable         : 0
```

- **SRAM 錯誤**：影響計算單元內部快取。少量 correctable 可接受，uncorrectable 可能導致靜默資料損壞
- **DRAM 錯誤**：影響 HBM 顯存。單位元自動糾正，雙位元不可糾正——如果 DRAM Uncorrectable > 0，立即停用該 GPU

#### Retired Pages 與 Remapped Rows

當 HBM 某個記憶體頁反覆出現單位元錯誤，GPU 韌體會將其標記為 "retired"（退役），用備用記憶體行替換：

```bash
nvidia-smi -i <ID> -q | grep -A20 'Retired'
```

```text
Retired Pages
    Single Bit ECC            : N/A    ← A100 上此字段不再使用
    Double Bit ECC            : N/A
    Pending Page Blacklist    : N/A
Remapped Rows
    Correctable Error         : 0      ← 因單位元錯誤被重對映的行數
    Uncorrectable Error       : 0      ← 因雙位元錯誤被重對映的行數
    Pending                   : No     ← 有待處理的重對映？
    Remapping Failure Occurred: No     ← 重對映失敗？（備用行耗盡）
```

| 字段                         | 含義                        | 危險訊號             |
| ---------------------------- | --------------------------- | -------------------- |
| `Correctable Error`          | 已被 remap 的單位元錯誤行數 | > 100 說明 HBM 老化  |
| `Uncorrectable Error`        | 已被 remap 的雙位元錯誤行數 | **> 0 立即停用**     |
| `Remapping Failure Occurred` | 備用行耗盡，無法再 remap    | **Yes = GPU 需更換** |

> 本節點 GPU 3 的 Remapped Rows 全部為 0，無重對映記錄——HBM 健康。

### 3.4 MIG 模式一致性

```bash
nvidia-smi --query-gpu=index,mig.mode.current --format=csv
```

```text
0-6: Disabled
7:   Enabled
```

**不一致 → 影響**：DCGM diag 無法執行；CUDA 裝置列舉行為不同（MIG Enabled 無 GI 時 GPU 不可見）。

**建議**：在訓練叢集中保持所有 GPU 的 MIG 模式一致。推理叢集可按需配置。

### 3.5 PCIe 鏈路狀態

```bash
nvidia-smi --query-gpu=index,pcie.link.gen.current,pcie.link.width.current --format=csv
```

A100 期望：`4, 16`（PCIe Gen 4 x16）。如果看到 `1, 16` → ASPM 空閒降級，正常。如果 max 也低 → 插槽問題。

---

## 4. L3: 壓力驗證

### 4.1 DCGM 診斷（Level 1 快速模式）

```bash
dcgmi diag -r 1 -i <GPU_ID>
```

> 前提：所有 GPU MIG 模式一致。當前 GPU 7 為 Enabled、GPU 0-6 為 Disabled，無法執行。參見 [DCGM 監控實操](05_dcgm_monitoring.md#5-診斷測試dcgmi-diag)。

### 4.2 P2P 頻寬驗證

```bash
# 在每對 GPU 上執行 simpleP2P，確認 P2P 可用且頻寬達標
CUDA_VISIBLE_DEVICES=0,1 ./simpleP2P   # 應輸出 ~239 GB/s (NVLink)
CUDA_VISIBLE_DEVICES=3,6 ./simpleP2P   # 應輸出 ~239 GB/s
CUDA_VISIBLE_DEVICES=3,7 ./simpleP2P   # 應失敗（SYS 不支持 P2P）
```

> 詳見 [GPU P2P 頻寬實測](../../02_gpu_programming/04_profiling/08_p2p_bandwidth.md)

### 4.3 NCCL AllReduce 頻寬

```bash
# 編譯 nccl-tests（一次性）
git clone https://github.com/NVIDIA/nccl-tests.git && cd nccl-tests && make MPI=0

# 在所有 NVLink 正常的 GPU 上執行（排除 GPU 7）
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6 ./build/all_reduce_perf -b 1G -e 8G -g 7
```

期望值參考：[NCCL 通訊路徑逐層壓測](../03_nccl/06_nccl_path_benchmark.md) — H100 NVLink ~316 GB/s, P2P Disable ~24 GB/s。

---

## 5. 健康檢查指令碼

將 L1+L2 整合為單次執行：

```bash
#!/bin/bash
# gpu_health_check.sh — GPU 叢集 L1+L2 健康檢查

echo "=== [L1] 溫度與功耗 ==="
nvidia-smi --query-gpu=index,temperature.gpu,power.draw --format=csv,noheader | \
  awk -F',' '{ printf "GPU %s: %s°C  %sW\n", $1, $2, $3 }'

echo ""
echo "=== [L1] 顯存使用 ==="
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader | \
  awk -F',' '{ printf "GPU %s: %.0f / %.0f MiB\n", $1, $2, $3 }'

echo ""
echo "=== [L2] NVLink 拓撲摘要 ==="
# grep -c 統計的是行數；拓撲矩陣對稱，一對連線出現兩次，用 grep -o 統計出現次數。
# 先刪掉 Legend 之後的圖例（圖例文字里也有 SYS/NODE 等字樣，會汙染計數）
topo_matrix=$(nvidia-smi topo -m 2>/dev/null | sed '/^Legend/,$d')
nv_count=$(echo "$topo_matrix" | grep -o "NV12" | wc -l | tr -d ' ')
non_nv_count=$(echo "$topo_matrix" | grep -oE "\b(SYS|NODE|PXB|PIX)\b" | wc -l | tr -d ' ')
echo "NV12 連線數: $nv_count  非 NVLink 連線數: $non_nv_count"

echo ""
echo "=== [L2] ECC 錯誤 ==="
nvidia-smi --query-gpu=index,ecc.errors.corrected.volatile.total,ecc.errors.uncorrected.volatile.total --format=csv,noheader

echo ""
echo "=== [L2] PCIe 鏈路 ==="
nvidia-smi --query-gpu=index,pcie.link.gen.current,pcie.link.width.current --format=csv,noheader | \
  awk -F',' '{ printf "GPU %s: Gen %s x%s\n", $1, $2, $3 }'

echo ""
echo "=== [L2] MIG 模式 ==="
nvidia-smi --query-gpu=index,mig.mode.current --format=csv,noheader
```

### 5.1 異常輸出示例：GPU 7

本節點執行該指令碼時，GPU 7 相關的異常訊號：

```text
GPU 7: 26°C  48.75W              ← 溫度/功耗正常
GPU 7: 0 / 81920 MiB              ← 顯存完全空閒
NV12 連線數: 42  非 NVLink 連線數: 14   ← GPU 0-6 兩兩 NV12 共 21 對 ×2；GPU 7 無 NVLink，7 對連線 ×2（SYS×8、NODE×4、PXB×2）
GPU 7, 0, 0                       ← ECC 無錯誤
GPU 7: Gen 4 x16                  ← PCIe 鏈路正常
MIG Mode: GPU 7 = Enabled         ← 與 GPU 0-6 不一致
```

**診斷結論**：GPU 7 的 NVLink 硬件故障 + MIG Enabled（可能是故障排查后的配置）。不適合放入訓練 TP 組，可用於獨立推理或 MIG 實驗。

---

## 6. 相關文件

- [`03_nvidia_smi_guide.md`](03_nvidia_smi_guide.md)：本文用到的 nvidia-smi 命令詳解
- [`05_dcgm_monitoring.md`](05_dcgm_monitoring.md)：L3 壓力驗證中 DCGM 診斷的使用
- [NVLink 診斷與實操](../../01_hardware_architecture/nvlink/nvlink_diagnostics.md)：NVLink 鏈路層面的深入排查
- [GPU P2P 頻寬實測](../../02_gpu_programming/04_profiling/08_p2p_bandwidth.md)：P2P 頻寬驗證作為 L3 壓力測試的一部分

---

## 參考

- [NVIDIA DCGM 官方文件](https://docs.nvidia.com/datacenter/dcgm/latest/)
- [NCCL 環境變數](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html)
