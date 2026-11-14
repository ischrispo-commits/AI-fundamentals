# GPU 忙不忙怎麼判斷

`nvidia-smi` 的 `GPU-Util` 只回答"有沒有 Kernel 在跑"：任何 Kernel 在跑它就報 100%，即便只有一個 SM 在執行一個 `memcpy`。它回答不了另一個更重要的問題：算力到底被用掉了多少。

本文給一套判斷流程：先用 nvidia-smi 的 util、功耗、溫度排除假忙，再上 DCGM 的 SM Active 量化算力占用。

## 先澄清：nvidia-smi 沒有 SM 利用率這個指標

流傳較廣的一種說法是：`--query-gpu=utilization.gpu` 和預設輸出的 `GPU-Util` 不是同一個東西，前者是 SM 利用率。這是錯的。官方口徑只有一條（NVML 的 `nvmlDeviceGetUtilizationRates`）：GPU utilization 指取樣週期內有一個或多個 kernel 在執行的時間佔比。預設輸出的 `GPU-Util` 列、`utilization.gpu` 查詢、`dmon` 的 `sm` 列全部出自這一個介面，NVML 裡沒有第二個利用率查詢。

真正的 SM Active（SM 上至少一個 warp 活躍的週期佔比）在 NVML 里查不到，只能從 DCGM 的 profiling 指標取：Field ID 1002（`DCGM_FI_PROF_SM_ACTIVE`）。詳見 [DCGM 監控實操](05_dcgm_monitoring.md)。

## nvidia-smi 能看的：util + 功耗 + 溫度

```bash
nvidia-smi dmon -s u -d 2 -c 3
```

輸出示例：

```text
# gpu   sm   mem   enc   dec
    0   95    42     0     0
    0   92    38     0     0
    0   97    45     0     0
```

`sm` 列就是 GPU-Util 那個口徑（kernel 執行時間佔比），`mem` 列是顯存頻寬利用率。兩個一起看能區分幾類狀態：

| sm   | mem   | 狀態             | 怎麼回事                                                                                   |
| ---- | ----- | ---------------- | ------------------------------------------------------------------------------------------ |
| > 80% | < 30% | 疑似計算重負載   | kernel 執行時間佔比高且不走顯存頻寬，像 GEMM 這類計算密集負載。是否真飽和要看功耗、溫度或 DCGM SMACT |
| < 30% | > 80% | Memory-bound 訊號 | GPU 時間花在資料搬運上。查 pinned memory、增大 batch、用 kernel fusion                      |
| < 30% | < 30% | 空閒             | 沒有有效負載                                                                               |
| 任意 | 任意  | 不能直接判飽和   | `sm > 80%` 只說明 kernel 執行時間佔比高：一個持續跑的 `memcpy` 同樣能把這列推到 100%        |

功耗和溫度是價效比最高的佐證。矽片發熱和功耗直接反映電晶體翻轉量，`memcpy` 騙不過它們：

```bash
nvidia-smi --query-gpu=index,temperature.gpu,power.draw,power.limit --format=csv,noheader
```

| 溫度               | 功耗                | 可能狀態                                                  |
| ------------------ | ------------------- | --------------------------------------------------------- |
| 空閒溫度 (25-35°C) | 空閒功耗 (45-70W)   | GPU 沒幹活，即使 `GPU-Util` 顯示 100%                     |
| 滿載溫度 (55-75°C) | 滿載功耗 (250-400W) | GPU 真的在算                                              |
| 空閒溫度           | 中等功耗 (100-200W) | 有殘留行程佔顯存但沒跑計算                                |
| 滿載溫度           | 低功耗 (< 200W)     | 被功耗牆限制：`nvidia-smi -pl` 設得太低或散熱不足觸發降頻 |

典型假忙場景：`GPU-Util` = 100%，但溫度 30°C、功耗 60W，說明 GPU 沒在算。正常的滿載計算一定伴隨溫升和功耗提升。

## 經典誤判：GPU-Util 100% 但實際沒在算

一個 `memcpy` 操作持續跑：`GPU-Util` 顯示 100%，CUDA Core 一個沒用，功耗和溫度紋絲不動。靠功耗、溫度就能排除這類假忙；要量化計算單元的真實佔用，需要 DCGM 的 SMACT（Field ID 1002）。

Kernel 很短但頻繁 launch 也會造成類似假象：`GPU-Util` 的取樣視窗看到"有 Kernel 在跑"，其實每個 Kernel 只占 GPU 的千分之一時間。

## 要量化算力占用：DCGM SM Active

`nvidia-smi` 的 util 回答不了"SM 被用到了几成"。DCGM 在 util 之外提供 profiling 指標，兩者對照如下：

| nvidia-smi 字段                  | 含義                                        | 對應 DCGM                                                                                              |
| -------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 預設輸出 `GPU-Util`              | 取樣週期內有 kernel 執行的時間佔比          | 203 `DCGM_FI_DEV_GPU_UTIL`（同口徑）；1001 `DCGM_FI_PROF_GR_ENGINE_ACTIVE`（比例形式）                 |
| `--query-gpu=utilization.gpu`    | 同 `GPU-Util`，同一 NVML 接口               | 同上                                                                                                   |
| `--query-gpu=utilization.memory` | 顯存頻寬利用率                              | 204 `DCGM_FI_DEV_MEM_COPY_UTIL`；1005 `DCGM_FI_PROF_DRAM_ACTIVE`（比例形式）                           |
| （NVML 無對應查詢）              | SM Active：SM 上至少一個 warp 活躍的週期佔比 | 1002 `DCGM_FI_PROF_SM_ACTIVE`                                                                          |

```bash
# SMACT 是 SM Active，DRAMA 是 DRAM Active
dcgmi dmon -e 1002,1005,150 -d 3000 -c 3
```

Field ID 的完整對照見 [DCGM 監控實操](05_dcgm_monitoring.md)。

## 速決流程

```text
SSH 上去 → nvidia-smi --query-gpu=utilization.gpu,utilization.memory,temperature.gpu,power.draw
         ├─ util 100% + 溫度 30°C + 功耗 60W?   → 🛑 假忙，GPU 沒在實際計算
         ├─ util < 30% 且 mem > 80%?            → ⚠️ Memory-bound 訊號，最佳化資料搬運
         ├─ util > 80% 且功耗接近 power limit?  → ✅ 在真算；是否飽和看 DCGM SMACT (1002)
         └─ 需要量化 SM 占用?                   → dcgmi dmon -e 1002 看 SM Active
```

## 相關資源

- [GPU 利用率是一個誤導性指標（原文翻譯）](02_gpu_utilization_myth.md)：MFU vs SM Efficiency 的深入對比
- [DCGM 監控實操](05_dcgm_monitoring.md)：DCGM 安裝和完整 Field ID 參考
- [nvidia-smi 場景速查](03_nvidia_smi_guide.md)：nvidia-smi 全部命令
