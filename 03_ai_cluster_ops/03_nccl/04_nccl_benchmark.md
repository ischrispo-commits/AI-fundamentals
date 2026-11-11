# NCCL 基準測試方法論

> NCCL 決定了多卡訓練的通訊效率。當吞吐"莫名掉一截"卻找不到程式碼原因時，十有八九在 NCCL 這一層。本文覆蓋從編譯 `all_reduce_perf`、跑出真實頻寬、到與拓撲對照診斷的全流程。
>
> as-of 2026-11-05：實測環境為 libnccl2 v2.29.3 + 8×A100-SXM4-80GB（NVSwitch Gen2，宿主驅動版本文中未記錄）；NCCL 演算法選擇與頻寬數字隨版本、機型變化，引用前請按當前版本複核。

---

## 1. NCCL 基準測試是什麼

NCCL 自帶的 `nccl-tests` 提供標準化的集合通訊效能測試：

| 測試                     | 測量物件           | 對應訓練場景     |
| ------------------------ | ------------------ | ---------------- |
| `all_reduce_perf`        | AllReduce 頻寬     | 資料並行梯度同步 |
| `all_gather_perf`        | AllGather 頻寬     | ZeRO 參數收集    |
| `reduce_scatter_perf`    | ReduceScatter 頻寬 | ZeRO 梯度分发    |
| `broadcast_perf`         | Broadcast 頻寬     | 模型參數廣播     |

每個測試在不同資料量（1B → 8 GB）和 GPU 數量（2 → 8）下各跑一輪，輸出頻寬 vs 資料量的完整曲線。

---

## 2. 編譯 `nccl-tests`

```bash
git clone https://github.com/NVIDIA/nccl-tests.git
cd nccl-tests
make MPI=1 CUDA_HOME=/usr/local/cuda
```

編譯產物：`build/all_reduce_perf`、`build/all_gather_perf` 等。

> `NCCL_HOME` 不要指向 `/usr/lib/x86_64-linux-gnu`：nccl-tests 的 Makefile 會去 `$(NCCL_HOME)/include` 和 `$(NCCL_HOME)/lib64` 找標頭檔案與庫，裝的是 Ubuntu 包（libnccl2 在 `/usr` 下）時直接編不過。包安裝場景不設 `NCCL_HOME`，或顯式設 `NCCL_HOME=/usr`。

> MPI 依賴：單節點測試不需要 MPI（`MPI=0`）。多節點需要 OpenMPI。

---

## 3. 執行 AllReduce 基準測試

### 3.1 基本命令

```bash
# 8 GPU 全部參與，資料範圍 1M → 8G
./build/all_reduce_perf -b 1M -e 8G -f 2 -g 8

# 只測 NVLink 正常的 7 GPU（排除 GPU 7）
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6 ./build/all_reduce_perf -b 1M -e 8G -f 2 -g 7

# 單對 GPU（驗證 NVLink 路徑）
CUDA_VISIBLE_DEVICES=0,3 ./build/all_reduce_perf -b 64M -e 1G -g 2
```

| 參數 | 含義                     |
| ---- | ------------------------ |
| `-b` | 起始資料量               |
| `-e` | 結束資料量               |
| `-f` | 倍增因子（2 = 每次翻倍） |
| `-g` | GPU 數量                 |

### 3.2 期望頻寬

A100 NVLink 3.0 (NV12) 的單向 P2P 頻寬為 239 GB/s（實測，參見 [P2P 頻寬實測](../../02_gpu_programming/04_profiling/08_p2p_bandwidth.md)）。A100 上大消息走 Ring，busbw 上限就是 NVLink 單向頻寬；演算法頻寬（algbw）按 Ring 的流量係數 `2(N-1)/N` 折算：

| AllReduce 算法 | A100 (NVSwitch Gen2) 期望值                                 | 瓶頸           |
| -------------- | ------------------------------------------------------------ | -------------- |
| Ring           | busbw 上限 ≈ 239 GB/s；8 GPU algbw ≈ 239 × (8-1)/8 ≈ 209 GB/s | NVLink 單向頻寬 |
| Tree           | 僅小訊息回退使用；大消息 busbw 不會高於 Ring                 | 同上           |

> A100 的 NVSwitch 是 Gen2：沒有 SHARP 在網歸約，也沒有 NVLS。NVLS 需要 NVSwitch Gen3 加 NCCL 2.17+（Hopper 世代起）。所以 A100 上超過 ~2 MB 的消息 NCCL 仍選 Ring（與 [NCCL 技術理論](01_nccl_theory.md) §1.2 一致）。實測 225 GB/s 約為 239 GB/s 上限的 94%，正是 Ring 的典型特徵；「Tree 大消息接近 600 GB/s per GPU」是不可達的理論口徑，不要拿它當期望值。

### 3.3 A100 實測資料

在 8 × A100-SXM4-80GB (NVSwitch Gen2) 上編譯執行 nccl-tests，得到 2/4/7 GPU 的真實 AllReduce 頻寬（`alg_bw` = 演算法頻寬 per GPU, `bus_bw` = 等效匯流排頻寬）：

| GPU 數               | 1 GB bus_bw  | 256 MB bus_bw | 觀測                                                      |
| -------------------- | ------------ | ------------- | --------------------------------------------------------- |
| **2** (GPU 0,3 NV12) | **197 GB/s** | 189 GB/s      | 接近 P2P 單向實測 (239 GB/s)，損耗來自 AllReduce 協議開銷 |
| **4** (GPU 0-3 NV12) | **220 GB/s** | 213 GB/s      | Ring 的每跳經 NVSwitch 全互聯轉發，頻寬不被組內 GPU 數攤薄 |
| **7** (GPU 0-6 NV12) | **225 GB/s** | 206 GB/s      | GPU 數增加但匯流排頻寬不降：每 GPU 的 NVLink 頻寬是獨享的    |

完整 1 GB AllReduce 輸出：

```text
# 2 GPU: 每個 GPU alg_bw ~197 GB/s, bus_bw = 197 GB/s
  1073741824     268435456     float     sum      -1  5438.06  197.45  197.45

# 4 GPU: alg_bw ~147 GB/s, bus_bw = 220 GB/s (N/(N-1) × alg_bw)
  1073741824     268435456     float     sum      -1  7304.94  146.99  220.48

# 7 GPU: alg_bw ~131 GB/s, bus_bw = 225 GB/s
  1073741824     268435456     float     sum      -1  8191.38  131.08  224.71
```

**關鍵發現**：

- `bus_bw` 從 197 → 220 → 225 GB/s 隨 GPU 數量增長而**上升**：Ring 的每步通訊都走獨享 NVLink，鏈路隨組擴大被利用得更充分
- 7 GPU 的 bus_bw (225 GB/s) 與 P2P 單向實測 (239 GB/s) 差距僅 ~6%：Ring 已把 NVLink 單向頻寬用到 94%，離硬體上限不遠
- 小資料量頻寬：1 MB 僅 16.8 GB/s (8.5% 峰值), 8 MB 升至 89 GB/s (45%), 64 MB 達到 170 GB/s (86%)。資料量 < 64 MB 時 launch latency + 傳輸未飽和主導開銷

---

## 4. 結果解讀流程

拿到 `all_reduce_perf` 的頻寬曲線後，對照 GPU 拓撲可以快速定位問題：

```text
理想的頻寬曲線（8 × A100 NVSwitch 環境，busbw 口徑，大消息走 Ring）：
          ▲
  225 ─── ┤                              ┌ Ring 飽和（單向頻寬的 94%）
          ┤                         ╱╱╱
  150 ─── ┤                    ╱╱╱
          ┤               ╱╱╱
   75 ─── ┤          ╱╱╱
          ┤     ╱╱╱╱
    0 ─── ┼─────┬─────┬─────┬─────┬─────▶ 資料量
          1M    8M    64M  512M   4G   8G
```

**如果頻寬遠低於期望，可能的根因**：

| 現象                     | 可能原因                    | 排查命令                                                                                |
| ------------------------ | --------------------------- | --------------------------------------------------------------------------------------- |
| < 10 GB/s on any size    | 走了 PCIe 而非 NVLink       | `nvidia-smi topo -m` 檢查連線類型                                                       |
| 某個 GPU 拖慢全組        | 該 GPU NVLink 故障          | `nvidia-smi nvlink --status -i <ID>`                                                    |
| < 100 GB/s on large data | 部分 GPU 對退化走 PCIe（NVLink 部分鏈路故障；A100 上 >2 MB 正常應走 Ring + NVLink） | `nvidia-smi topo -m` 逐對檢查連線類型                                                   |
| 波動劇烈                 | 其他行程搶佔 GPU            | `nvidia-smi` 檢查 `compute processes`                                                   |
| 小資料量 (< 1M) 頻寬極低 | launch latency 主導（正常） | 參照 [Kernel Launch 開銷](../../02_gpu_programming/02_cuda/08_kernel_launch_latency.md) |

---

## 5. GPU 7 案例：MIG + NVLink 雙重異常

本環境中 GPU 7 同時存在兩個問題：**NVLink 硬件故障**（topo 顯示 SYS/NODE/PXB）和 **MIG Enabled 但無實例**。實測影響：

```bash
# 嘗試將 GPU 7 納入 AllReduce 組
CUDA_VISIBLE_DEVICES=3,7 ./build/all_reduce_perf -b 1M -e 1G -g 2
# 輸出: Invalid number of GPUs: 2 requested but only 1 were found.

# 8 GPU 全量
./build/all_reduce_perf -b 1M -e 1G -g 8
# 輸出: Invalid number of GPUs: 8 requested but only 7 were found.
```

**根因分析**：

| GPU 7 問題                      | 表現                                               | 影響                           |
| ------------------------------- | -------------------------------------------------- | ------------------------------ |
| MIG Enabled, 無 GI/CI           | CUDA `cudaGetDeviceCount()` 返回 7（不包含 GPU 7） | NCCL 根本無法發現 GPU 7        |
| NVLink 全部 `_` (Not Supported) | 即使 MIG 修復，topo 也是 SYS/PXB                   | 頻寬上限 ~28 GB/s (PCIe Gen 4) |

**兩個問題的組合效果**：MIG 狀態使 GPU 7 完全透明，比 NVLink 故障本身更隱蔽：`nvidia-smi` 能看到 GPU 7，但 `all_reduce_perf` 看不到。排查時先用 `cudaGetDeviceCount()` 檢查裝置數量是否與物理 GPU 數量一致。

```bash
#!/bin/bash
# 檢查所有 GPU 的 NVLink 狀態，任何異常直接退出
BAD_GPUS=$(nvidia-smi topo -m 2>/dev/null | grep -c "SYS" || true)
if [ "$BAD_GPUS" -gt 0 ]; then
    echo "WARNING: $BAD_GPUS SYS connections detected — possible NVLink fault"
fi
```

---

## 6. 參考

- [NCCL 官方文件](https://docs.nvidia.com/deeplearning/nccl/)
- [NCCL 環境變數完整列表](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html)
- [nccl-tests GitHub](https://github.com/NVIDIA/nccl-tests)
- [`01_nccl_theory.md`](01_nccl_theory.md)：NCCL 演算法理論（AllReduce/RDMA/性能建模）
- [`02_nccl_helloworld.md`](02_nccl_helloworld.md)：單卡 NCCL 驗證
- [`03_nccl_tutorial.md`](03_nccl_tutorial.md)：完整使用教程與部署
- [GPU P2P 頻寬實測](../../02_gpu_programming/04_profiling/08_p2p_bandwidth.md)：NCCL 期望頻寬的硬體上限
- [NVLink 診斷與實操](../../01_hardware_architecture/nvlink/nvlink_diagnostics.md)：NVLink 故障對 NCCL 路徑的影響
- [GPU 叢集健康檢查](../01_gpu_ops/06_gpu_health_check.md)：NCCL 驗證作為 L3 壓力測試
