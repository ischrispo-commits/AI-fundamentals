# nvidia-smi 場景速查

`nvidia-smi` 有 100+ 個選項，但真正遇到問題時你只需要 5-6 個。本文按運維場景組織：從「看一眼」到「改配置」到「指令碼化」，每個場景給出最精簡的命令和輸出解讀。完整選項參考 `nvidia-smi -h`。

---

## 一、快速掃一眼：「有什麼 GPU？狀態怎麼樣？」

```bash
nvidia-smi                          # 概要
nvidia-smi -L                       # 僅型號 + UUID
```

`nvidia-smi` 預設輸出的每一列：

```text
+---------------------------------------------------------------------------------------+
| NVIDIA-SMI 535.183.01             Driver Version: 535.183.01   CUDA Version: 12.2     |
|-----------------------------------------+----------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |         Memory-Usage | GPU-Util  Compute M. |
|                                         |                      |               MIG M. |
|=========================================+======================+======================|
|   0  Tesla T4                       On  | 00000000:81:00.0 Off |                    0 |
| N/A   40C    P8              10W /  70W |      2MiB / 15360MiB |      0%      Default |
|                                         |                      |                  N/A |
+-----------------------------------------+----------------------+----------------------+
```

| 列                     | 含義                             | 關注點                                      |
| ---------------------- | -------------------------------- | ------------------------------------------- |
| `Fan`                  | 風扇轉速百分比，`N/A` = 被動散熱 | —                                           |
| `Temp`                 | GPU 核心溫度 (°C)                | T4 < 75°C，H100 < 70°C（滿載時）            |
| `Perf`                 | P0-P12 效能狀態，P0 = 最高頻率   | 如果一直是 P8，GPU 沒有計算負載             |
| `Pwr:Usage/Cap`        | 當前功耗 / 功耗上限 (W)          | Usage 遠小於 Cap = 沒跑滿                   |
| `Memory-Usage`         | 已用 / 總顯存                    | OOM 前兆：`Used` 接近 `Total`               |
| `GPU-Util`             | GPU 利用率（kernel 執行時間佔比） | ≠ 算力利用率，詳見下文「常見誤區」          |
| `Compute M.`           | 計算模式                         | `Default` = 多行程共享，`E. Process` = 獨佔 |
| `MIG M.`               | MIG 模式                         | A100/H100 支持 GPU 切分，`N/A` = 不支持     |
| `Volatile Uncorr. ECC` | 本次執行中未糾正的 ECC 錯誤      | > 0 立即關注                                |
| `Persistence-M`        | 持久化模式                       | `On` 可避免 GPU 空閒時驅動解除安裝              |

**常見誤區**：`GPU-Util` 只表示取樣週期內有 Kernel 在跑，1 個 SM 在跑顯示 100%，全部 SM 都在跑也顯示 100%。注意 nvidia-smi 裡沒有單獨的「SM 利用率」查詢：`GPU-Util`、`--query-gpu=utilization.gpu`、`dmon` 的 `sm` 列同源於 NVML `nvmlDeviceGetUtilizationRates`，口徑都是 kernel 執行時間佔比。判斷 GPU 是否真的被用滿，用 §三 的 util + 顯存利用率 + 功耗三件套，要量化 SM 佔用則用 DCGM 的 SMACT (1002)。詳見 [GPU 利用率是一個誤導性指標](02_gpu_utilization_myth.md) 和 [GPU 忙不忙怎麼判斷](09_gpu_busy_check.md)。

---

## 二、誰在用什麼？「哪個行程佔了多少顯存？」

```bash
nvidia-smi pmon -i 0                # 行程級實時
nvidia-smi --query-compute-apps=pid,used_memory --format=csv  # 指令碼化
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
```

`pmon` 輸出：

```text
# gpu   pid  type   sm   mem   enc   dec   command
    0  2635     C    0     0     0     0   python
    0  4210     C   45    12     0     0   python3
```

列含義：

| 列        | 含義                                 |
| --------- | ------------------------------------ |
| `type`    | `C` = 計算，`G` = 圖形               |
| `sm`      | 該行程的 kernel 執行時間佔比（口徑同 GPU-Util，行程級） |
| `mem`     | 該行程的顯存頻寬利用率               |
| `enc/dec` | 編碼/解碼引擎利用率                  |

**指令碼化示例**（查詢顯存佔用 TOP 3）：

```bash
nvidia-smi --query-compute-apps=pid,process_name,used_memory \
  --format=csv,noheader | sort -t',' -k3 -rn | head -3
```

---

## 三、跑滿了沒？「GPU 在幹活還是閒著？」

### 3.1 實時滾動

```bash
nvidia-smi dmon -s mucp -d 2        # 顯存用量 + 利用率四列 + 時鐘 + 功耗溫度，每 2 秒
```

`-s` 選項控制顯示哪些列（按 nvidia-smi 手冊）：

| -s 選項 | 列含義                                                  |
| ------- | ------------------------------------------------------- |
| `m`     | 顯存用量：fb（framebuffer）+ bar1                       |
| `u`     | 利用率四列：sm / mem / enc / dec（sm、mem 口徑同 GPU-Util） |
| `c`     | SM 時鐘 + 顯存時鐘 (MHz)                                |
| `p`     | 功耗 + 溫度                                             |
| `v`     | power/thermal violations（限頻事件計數）                |
| `t`     | PCIe 吞吐 (MB/s)；dmon 沒有 NVLink 吞吐列               |

常用組合：`-s mucp`（顯存用量 + 利用率四列 + 時鐘 + 功耗溫度），一行看 GPU 負載全景。

### 3.2 指令碼化單次查詢

```bash
# GPU 利用率 + 顯存利用率
nvidia-smi --query-gpu=utilization.gpu,utilization.memory --format=csv,noheader

# 功耗
nvidia-smi --query-gpu=power.draw,power.limit --format=csv,noheader

# 時鐘
nvidia-smi --query-gpu=clocks.current.sm,clocks.current.memory --format=csv,noheader
```

### 3.3 解讀

判讀靠三件套：`utilization.gpu`（kernel 活躍）+ `utilization.memory`（顯存頻寬）+ 功耗。注意 `utilization.gpu` 高只說明 kernel 執行時間佔比高，不能單獨推出計算飽和。

| 現象                                              | 含義             | 方向                                                       |
| ------------------------------------------------- | ---------------- | ---------------------------------------------------------- |
| util.gpu < 20%，util.memory > 80%                 | Memory-bound 訊號 | 檢查是否未用 pinned memory 或 batch 太小                   |
| util.gpu > 80%，util.memory < 30%，功耗接近 power limit | 在真算，疑似計算重負載 | 確認飽和用 DCGM SMACT (1002)；想更快就換更強的 GPU        |
| util.gpu 低，`Perf` 始終是 P8，功耗貼近空閒值     | GPU 無計算負載   | 行程可能卡在 CPU 端                                       |

---

## 四、健康嗎？「溫度/功耗/ECC/拓撲有沒有異常？」

### 4.1 溫度和功耗

```bash
nvidia-smi -q -d TEMPERATURE,POWER
```

關鍵欄位：`GPU Current Temp`、`GPU Slowdown Temp`（撞此溫度後 GPU 自動降頻）、`Power Limit`、`Power Draw`。

正常範圍：H100 滿載 ~65-72°C、T4 ~70-78°C。功耗應顯著低於 `Power Limit`：如果 `Power Draw` 一直等於 `Power Limit`，GPU 在功耗牆上被限制，換更強的散熱或降低功耗配置。

### 4.2 ECC 錯誤

```bash
nvidia-smi -q -d ECC
```

- **Volatile ECC > 0**：本次驅動載入以來已糾正的錯誤。如果是 DRAM 錯誤且持續增長，GPU 可能有硬體問題
- **Aggregate ECC 緩慢增長**：出廠以來的累計值，單 GPU 累計 < 100 屬正常老化
- **Uncorrectable ECC > 0**：嚴重，資料完整性風險。Ampere 及之後架構優先看 Remapped Rows（row remapping 兜底），如需清計數可 `nvidia-smi -i <ID> --reset-ecc-errors=volatile`，仍在增長則更換 GPU

區分 SRAM 和 DRAM 錯誤：SRAM 錯誤通常來自宇宙射線（單粒子翻轉），單次出現無影響；DRAM 錯誤頻繁出現則表明顯存顆粒老化。

### 4.3 NVLink 和拓撲

```bash
nvidia-smi topo -m                       # 連線矩陣
nvidia-smi nvlink --status               # 每條 link 的狀態 + 頻寬
nvidia-smi nvlink --capabilities         # NVLink 版本和能力
nvidia-smi nvlink --error-counters       # 錯誤計數
```

拓撲標識解讀：

| 標識   | 含義                                | 性能            |
| ------ | ----------------------------------- | --------------- |
| `NV12` | 12 條 NVLink 直連                   | ~600 GB/s 雙向  |
| `PIX`  | 同一 PCIe switch，P2P 可用          | ~32 GB/s (Gen4) |
| `NODE` | 同一 NUMA node，經 PCIe Host Bridge | ~28 GB/s        |
| `SYS`  | 跨 NUMA，經 QPI/UPI                 | 最慢            |

詳見 [GPU 叢集健康檢查](06_gpu_health_check.md) L2 流程和 [NCCL 通訊路徑逐層壓測](../03_nccl/06_nccl_path_benchmark.md) 的實測資料。

### 4.4 PCIe 鏈路

```bash
nvidia-smi -q -d PCIE
```

確保 `Current Link Width` = `Max Link Width`（通常都是 x16）。如果 Gen4 卡執行在 Gen3 或 x16 掉到 x8：檢查主機板 BIOS 設定、PCIe 擴展器、Riser 卡。

---

## 五、出錯了？「XID 錯誤和 GPU 重置」

```bash
dmesg | grep -i "NVRM\|Xid"                      # 核心日誌中的 XID 錯誤
nvidia-smi -i <ID> --reset-ecc-errors=volatile   # 清零 volatile ECC 計數（aggregate 不可清）
nvidia-smi -i 0 --gpu-reset                      # 重置 GPU：需 root，目標 GPU 及 NVLink peer 空閒；Ampere 之前架構的多卡互聯 GPU 須用同一命令一起重置。官方註明生產環境不建議常規使用
```

常見 XID 錯誤速查（含義按 NVIDIA Xid Errors 目錄，Release 620，as-of 2026-11）：

| XID | 官方含義                                                            | 處理                                              |
| --- | ------------------------------------------------------------------- | ------------------------------------------------- |
| 31  | GPU memory page fault（MMU 報告的頁面錯誤，多為應用非法地址訪問）   | 單次出現多為應用層問題，復現則排查應用            |
| 43  | GPU stopped processing（應用觸發軟體故障，GPU 仍健康）              | 多為應用錯誤；復現時定位應用，不是硬體問題        |
| 45  | Preemptive cleanup, due to previous errors（此前錯誤的連帶清理）    | 伴隨其他 XID 時先處理根因；單獨出現重啟行程/GPU   |
| 48  | Double Bit ECC Error（雙位元 ECC 錯誤）                             | Ampere+ 走 row remapping；持續出現評估更換        |
| 79  | GPU has fallen off the bus（驅動經 PCIe 訪問 GPU 失敗，多指向 PCIe 鏈路/硬件故障） | 官方建議整機重啟；復現時檢查 PCIe 插槽、供電、Riser，跑 DCGM diag |
| 119 | GSP RPC Timeout（GSP 韌體響應超時）                                 | 記錄日誌並觀察；高頻復現先更新驅動，仍復現報支援  |

---

## 六、我要改點什麼？「功耗 / 計算模式 / 時鐘 / 持久化」

```bash
# 功耗
nvidia-smi -i 0 -pl 300              # 限制 GPU 0 最大 300W
nvidia-smi -i 0 -q -d POWER          # 確認生效

# 計算模式
nvidia-smi -i 0 -c 0                 # 0=Default（共享）
#                                    2=Prohibited（禁止新行程，測試用）
#                                    3=EXCLUSIVE_PROCESS（單行程獨佔）

# 時鐘（基準測試需要穩定 clock 時）
nvidia-smi -lgc 1500,2100            # 鎖定 GPU 時鐘在 1500-2100 MHz
nvidia-smi -lmc 5001,5001            # 鎖定顯存時鐘
nvidia-smi -rgc && nvidia-smi -rmc   # 恢復預設

# 持久化模式
nvidia-smi -pm 1                     # 啟用（推薦生產環境）
nvidia-smi -q -i 0 | grep Persistence # 確認
```

**持久化模式**值得單獨說明：關閉時，GPU 在最後一個行程退出後會被驅動解除安裝（`nvidia-smi` 仍然能看到但延遲顯著升高）。啟用後驅動常駐，避免空閒 GPU 的冷啟動延遲（通常 1-2 秒）。生產環境建議 `nvidia-persistenced` 服務。

---

## 七、多實例 GPU（MIG）

A100/H100 支援將一張物理 GPU 切分為多個獨立的 GPU 實例，每個實例有專屬的顯存、SM 和頻寬。

```bash
nvidia-smi mig -lgip                  # 列出可用的 GPU 實例配置
nvidia-smi mig -cgi 19,19,19 -C       # 建立 3 個 2g.20gb 實例（A100-80GB 上限即 3 個；
                                      # profile ID 19 等取值以現場 -lgip 輸出為準）
nvidia-smi mig -dci                   # 銷燬所有實例
nvidia-smi mig -dci -gi 0             # 銷燬指定 GPU 實例
```

> MIG 模式需要重啟 GPU 才能切換（`nvidia-smi -i <ID> -r`：需 root，GPU 上無執行中的行程，NVLink peer 也須空閒），且與 P2P 互斥：切分為 MIG 后 GPU 間不再支援 P2P 通信。

---

## 八、實時監控

```bash
nvidia-smi -l 5                       # 每 5 秒刷新概要
nvidia-smi dmon -s mucp -d 2          # 每 2 秒滾動
watch -n 1 nvidia-smi --query-gpu=utilization.gpu,utilization.memory,temperature.gpu,power.draw --format=csv,noheader
```

容器環境（Docker/K8s）中，`nvidia-smi` 預設只顯示容器可見的 GPU（透過 `NVIDIA_VISIBLE_DEVICES` 控制）。如果容器內看不到預期的 GPU，檢查 `NVIDIA_VISIBLE_DEVICES` 或容器的 `--gpus` 參數。

---

## 九、`--query-gpu` 指令碼化速查

指令碼化場景下，`--query-gpu` + `--format=csv,noheader,nounits` 是最佳組合：輸出乾淨、可管道、不依賴 `-q` 的冗長格式。

```bash
# 通用格式
nvidia-smi --query-gpu=<屬性1>,<屬性2> --format=csv,noheader,nounits
```

| 場景     | `--query-gpu=` 屬性                                                         |
| -------- | --------------------------------------------------------------------------- |
| 顯存     | `memory.total,memory.used,memory.free`                                      |
| 利用率   | `utilization.gpu,utilization.memory`                                        |
| 溫度     | `temperature.gpu,temperature.memory`                                        |
| 功耗     | `power.draw,power.limit`                                                    |
| 時鐘     | `clocks.current.sm,clocks.current.memory`                                   |
| PCIe     | `pcie.link.gen.current,pcie.link.width.current`                             |
| 風扇     | `fan.speed`                                                                 |
| ECC      | `ecc.errors.corrected.volatile.total,ecc.errors.uncorrected.volatile.total` |
| 計算模式 | `compute_mode`                                                              |
| MIG      | `mig.mode.current`                                                          |
| 行程     | 用 `--query-compute-apps` 替代                                              |

**一行監控指令碼示例**（打印所有 GPU 的 ID + GPU 利用率 + 顯存佔用 + 溫度）：

```bash
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,temperature.gpu \
  --format=csv,noheader,nounits | \
  awk -F', ' '{printf "GPU %s: %s%% util | %s MiB | %s°C\n", $1, $2, $3, $4}'
```

---

## 十、相關資源

- [GPU 利用率是一個誤導性指標](02_gpu_utilization_myth.md)：讀完再回頭看 `GPU-Util` 這列
- [GPU 忙不忙怎麼判斷](09_gpu_busy_check.md)：util + 功耗溫度排假忙，DCGM SMACT 看真實 SM 占用
- [GPU 叢集健康檢查](06_gpu_health_check.md)：L1/L2/L3 三層檢查流程，含 GPU 7 真實異常案例
- [NVLink 診斷與實操](../../01_hardware_architecture/nvlink/nvlink_diagnostics.md)：`nvlink --status` 輸出的深度解讀
- [DCGM 監控實操](05_dcgm_monitoring.md)：長期趨勢和 Prometheus 集成
- [GPU 行程與資源管理](07_gpu_process_management.md)：Compute Mode、CUDA_VISIBLE_DEVICES、NUMA 親和性
- [NVIDIA nvidia-smi 文件](https://docs.nvidia.com/deploy/driver-nvidia-smi/index.html)
