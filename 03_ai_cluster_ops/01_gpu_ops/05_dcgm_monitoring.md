# DCGM 監控實操

> 基於 A100-SXM4-80GB (8 GPU) + DCGM v3.3.9 實測（資料採集於 2026-11 之前）。DCGM (Data Center GPU Manager) 是 NVIDIA 官方推薦的 GPU 叢集監控方案，它提供了 `nvidia-smi` 不具備的能力：SM Active 等 profiling 指標、顯存頻寬利用率、長時間趨勢採集、以及與 Prometheus/Grafana 的原生集成。本文覆蓋 `dcgmi` 命令列的診斷、監控、健康檢查三大功能。

---

## 1. DCGM 與 nvidia-smi 的區別

`nvidia-smi` 的 `GPU-Util` 只告訴你"某段時間有 kernel 在跑"——1 個執行緒在跑也是 100%，全部 SM 滿載也是 100%，無法區分。DCGM 在 `nvidia-smi` 的指標之上，補充了**真正反映硬體利用率的指標**：

| 指標            | nvidia-smi          | DCGM                             | 說明                                   |
| --------------- | ------------------- | -------------------------------- | -------------------------------------- |
| GPU 利用率      | GPU-Util (誤導性)   | **SM Active** / **SM Occupancy** | DCGM 區分"有 kernel 在跑"和"SM 被用滿" |
| 顯存頻寬利用率  | ❌ 無               | **DRAM Active** / **PCIe TX/RX** | 判斷是否是 memory bound                |
| 功耗            | `power.draw`        | **Power Usage**                  | 兩者都有，DCGM 可做趨勢                |
| NVLink 狀態     | `nvidia-smi nvlink` | **NVLink 鏈路 Up/Down**          | DCGM 輸出更緊湊，適合指令碼解析          |
| 歷史資料        | ❌ 無               | DCGM 只負責輸出指標，時間序列儲存在 Prometheus 側 | 回溯分析的關鍵       |
| Prometheus 集成 | ❌ 無               | ✅ 原生 exporter                 | 叢集級監控的基礎                       |

> 前置閱讀：[GPU 利用率是一個誤導性指標](02_gpu_utilization_myth.md)

---

## 2. 安裝與基礎發現

### 2.1 安裝

```bash
# Ubuntu/Debian
apt-get install datacenter-gpu-manager

# 驗證
dcgmi --version
# dcgmi  version: 3.3.9
```

### 2.2 GPU 發現

```bash
dcgmi discovery -l
```

```text
8 GPUs found.
+--------+--------------------------------------------+
| GPU ID | Device Information                         |
+--------+--------------------------------------------+
| 0      | Name: NVIDIA A100-SXM4-80GB                |
|        | PCI Bus ID: 00000000:07:00.0               |
+--------+--------------------------------------------+
... (8 GPUs listed)
0 NvSwitches found.
```

> 注意：`dcgmi discovery` 顯示 0 NvSwitch——這並不意味著 NVSwitch 不存在，而是 DCGM v3.3.9 的 NVSwitch 發現依賴特定驅動介面。NVSwitch 的實際狀態透過 NVLink 鏈路狀態間接反映。

### 2.3 建立 GPU 組

DCGM 操作基於"組"（Group）模型。先建立組，再將 GPU 加入：

```bash
# 建立包含所有支援 GPU 的組
dcgmi group -c allgpus --default

# 檢視所有組
dcgmi group -l
```

```text
3 groups found.
  0: DCGM_ALL_SUPPORTED_GPUS       → GPU 0-7 (系統預設)
  1: DCGM_ALL_SUPPORTED_NVSWITCHES → None (無 NVSwitch 被檢測)
  2: allgpus                       → GPU 0-7 (使用者建立)
```

---

## 3. 實時監控：`dcgmi dmon`

`dcgmi dmon` 是 DCGM 的實時監控命令——以固定間隔取樣 GPU 指標。

### 3.1 關鍵 Field ID 速查

下表按 DCGM v3.3.9 的 `dcgm_fields.h` 核對。注意：203 是 `DCGM_FI_DEV_GPU_UTIL`，與 nvidia-smi 的 GPU-Util 同口徑（取樣週期內有 kernel 執行的時間佔比）；真正反映 SM 活躍度的是 profiling 指標 1002。

| Field ID | 短名  | 含義                                                                        | 什麼時候用                                 |
| -------- | ----- | --------------------------------------------------------------------------- | ------------------------------------------ |
| **203**  | GPUTL | `DCGM_FI_DEV_GPU_UTIL`：有 kernel 執行的時間佔比，即被 [GPU 忙不忙怎麼判斷](09_gpu_busy_check.md) 批評的 GPU-Util 口徑 | 與 nvidia-smi GPU-Util 對齊                |
| **204**  | MCUTL | `DCGM_FI_DEV_MEM_COPY_UTIL`：顯存複製/頻寬利用率                            | > 80% 且 SMACT 低 → memory bound           |
| **1001** | GRACT | `DCGM_FI_PROF_GR_ENGINE_ACTIVE`：圖形引擎活躍週期佔比（比例）               | kernel 執行佔比的比例形式                  |
| **1002** | SMACT | `DCGM_FI_PROF_SM_ACTIVE`：SM 上至少一個 warp 活躍的週期佔比                 | 判斷 SM 真實活躍度，替代 GPU-Util          |
| **1003** | SMOCC | `DCGM_FI_PROF_SM_OCCUPANCY`：SM 占用率（活躍 warp 駐留比例）                | 區分"SM 活躍"與"SM 駐留深度"               |
| **1005** | DRAMA | `DCGM_FI_PROF_DRAM_ACTIVE`：DRAM 活躍週期佔比                               | 顯存頻寬瓶頸定位                           |
| **1010** | PCIRX | `DCGM_FI_PROF_PCIE_RX_BYTES`：PCIe 接收吞吐                                 | 跨機通訊資料量                             |
| **150**  | TMPTR | GPU 溫度 (°C)                                                               | 散熱健康                                   |
| **155**  | PWR   | GPU 功耗 (W)                                                                | 能效評估                                   |

### 3.2 基礎監控示例

```bash
# 每 3 秒取樣，共 5 次。監控 GPU 利用率、顯存利用率、SM Active、溫度
dcgmi dmon -e 203,204,1001,1002,150 -d 3000 -c 5
```

當前節點輸出（8 GPU 全部空閒；列頭短名為示意口徑，按 §3.1 欄位表對應，實機輸出未逐列複核）：

```text
#Entity   GPUTL      MCUTL      GRACT       SMACT       TMPTR
ID                                                (C)
GPU 7     N/A        N/A        0.000       0.000       26
GPU 6     0          0          0.000       0.000       26
GPU 5     0          0          0.000       0.000       25
GPU 4     0          0          0.000       0.000       26
GPU 3     0          0          0.000       0.000       27
GPU 2     0          0          0.000       0.000       27
GPU 1     0          0          0.000       0.000       27
GPU 0     0          0          0.000       0.000       28
```

**解讀**：

- GPU 7 `GPUTL` 和 `MCUTL` 顯示 `N/A`，其他 GPU 顯示 `0`：前者是 MIG Enabled 導致的監控異常（參見 [MIG 配置與實操](../../01_hardware_architecture/nvidia/mig_hands_on.md)），後者是真實空閒
- 所有 GPU 的 GRACT 和 SMACT 為零，無負載
- 溫度 25-29°C，健康空閒溫度範圍

> **對比 nvidia-smi**：同樣的空閒狀態，`nvidia-smi` 的 GPU-Util 也會顯示 0%。但關鍵區別發生在**有負載時**——nvidia-smi 的 GPU-Util 50% 可能意味着 SM Active 只有 20% 或 80%，DCGM 能精確區分。
>
> **取樣注意**：`dcgmi dmon` 的取樣週期（`-d`）是毫秒級。如果 Kernel 執行時間 < 取樣週期，SM Active 可能被低估——高頻率的短 Kernel（如小型推理請求）建議用更短的取樣間隔（`-d 100` = 100ms），或透過 `-c` 增加取樣次數取平均。

---

## 4. NVLink 監控：`dcgmi nvlink`

DCGM 的 NVLink 輸出比 `nvidia-smi nvlink --status` 更緊湊，適合指令碼化採集：

```bash
dcgmi nvlink -s
```

```text
gpuId 0: U U U U U U U U U U U U _ _ _ _ _ _   ← 12 條 NVLink 全 Up
gpuId 1: U U U U U U U U U U U U _ _ _ _ _ _
gpuId 2: U U U U U U U U U U U U _ _ _ _ _ _
gpuId 3: U U U U U U U U U U U U _ _ _ _ _ _
gpuId 4: U U U U U U U U U U U U _ _ _ _ _ _
gpuId 5: U U U U U U U U U U U U _ _ _ _ _ _
gpuId 6: U U U U U U U U U U U U _ _ _ _ _ _
gpuId 7: _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _   ← 全部 Not Supported

Key: Up=U, Down=D, Disabled=X, Not Supported=_
```

**一眼定位故障**：GPU 7 的 18 個 link 位置全部為 `_`（Not Supported）——與 `nvidia-smi topo -m` 中 GPU 7 的 SYS/NODE/PXB 連線相互印證。GPU 0-6 的 12 條 link 全部為 `U`（Up），NVLink 健康。

---

## 5. 診斷測試：`dcgmi diag`

DCGM 內建三級診斷（Level 1-3），從快速冒煙測試到深度壓力測試：

```bash
dcgmi diag -r 1 -i 3   # Level 1: 快速診斷 (GPU 3)
dcgmi diag -r 2 -i 3   # Level 2: 中等壓力
dcgmi diag -r 3 -i 3   # Level 3: 全力壓力測試
```

**本環境限制**：當叢集中同時存在 MIG Enabled (GPU 7) 和 MIG Disabled (GPU 0-6) 的 GPU 時，`dcgmi diag` 會報錯：

```text
Cannot run diagnostic: CUDA does not support enumerating GPUs when one or
more GPUs has MIG mode enabled and one or more GPUs has MIG mode disabled.
```

**解決**：在執行 `dcgmi diag` 前，確保所有 GPU 的 MIG 模式一致（全部 Disabled 或全部 Enabled + 建立 GI/CI）。

---

## 6. Prometheus + Grafana 集成

DCGM 的 `dcgm-exporter` 將 GPU 指標暴露為 Prometheus 格式，配合 Grafana 實現叢集級長期監控。CLI 工具只能看當前時刻的取樣值，指標寫入 Prometheus 之後才能做跨天的趨勢回溯。

```bash
# 啟動 DCGM Exporter（主渠道為 NGC 的 nvcr.io/nvidia/k8s/dcgm-exporter；
# tag 規則：<exporter 版本>-<DCGM 版本>-<OS>，應選用與節點 DCGM 版本配套的 tag，勿用 latest）
docker run -d --gpus all --name dcgm-exporter -p 9400:9400 \
  nvcr.io/nvidia/k8s/dcgm-exporter:3.3.9-3.6.1-ubuntu22.04

# 驗證指標端點
curl http://localhost:9400/metrics | grep -E "DCGM_FI_(DEV_SM_CLOCK|PROF_DRAM_ACTIVE|DEV_POWER_USAGE)"
```

Grafana Dashboard 推薦：**NVIDIA DCGM Exporter Dashboard**（ID: 12239），關鍵面板：SM Active、DRAM Active、NVLink 吞吐、溫度、功耗。

> 本文聚焦 CLI 診斷。DCGM Exporter 的完整部署（systemd 服務、K8s DaemonSet、Prometheus Operator 集成）留給 Prometheus 運維專題。

---

## 7. 監控指令碼示例

將 DCGM 監控嵌入日常運維：

```bash
#!/bin/bash
# quick_gpu_check.sh — 快速 GPU 叢集健康檢查

echo "=== GPU 概覽 ==="
dcgmi discovery -l | grep -E "GPU ID|Name"

echo ""
echo "=== NVLink 鏈路狀態 ==="
dcgmi nvlink -s | grep -c "U U U U U U U U U U U U" | awk '{print $1 " / 8 GPUs have 12 NVLink Up"}'

echo ""
echo "=== 當前溫度 ==="
dcgmi dmon -e 150 -d 1000 -c 1 2>/dev/null | tail -9 | awk '{printf "GPU %s: %s°C\n", $1, $2}'

echo ""
echo "=== SM Active (最近 3 秒) ==="
dcgmi dmon -e 1002 -d 3000 -c 1 2>/dev/null
```

---

## 8. 相關文件

- [`02_gpu_utilization_myth.md`](02_gpu_utilization_myth.md)：解釋了為什麼 DCGM 的 SM Active 才是正確指標
- [`03_nvidia_smi_guide.md`](03_nvidia_smi_guide.md)：nvidia-smi 基本操作，DCGM 是其升級版
- [NVLink 診斷與實操](../../01_hardware_architecture/nvlink/nvlink_diagnostics.md)：nvidia-smi nvlink vs dcgmi nvlink 雙工具對比
- [MIG 配置與實操](../../01_hardware_architecture/nvidia/mig_hands_on.md)：MIG Enabled GPU 對 DCGM 監控的影響

---

## 參考文件

- [NVIDIA DCGM 官方文件](https://docs.nvidia.com/datacenter/dcgm/latest/)
- [DCGM Exporter for Prometheus](https://github.com/NVIDIA/dcgm-exporter)
- [NVIDIA DCGM Grafana Dashboards](https://grafana.com/grafana/dashboards/12239)
