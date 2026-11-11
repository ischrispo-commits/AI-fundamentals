# 單卡 GPU 拓撲與 NUMA 分析

> 基於 Intel Xeon Platinum 8470Q (Sapphire Rapids) + RTX 5090 實際環境。本文聚焦單 GPU 場景下的拓撲分析方法，與多卡 NVLink/NVSwitch 場景形成互補。實測在 Seetacloud 容器內進行，實測時間未記錄（按 RTX 5090 上市時間推斷約 2025 年），驅動與核心版本未留存記錄。

---

## 1. 為什麼單卡也要關注拓撲

單 GPU 環境中沒有 NVLink 和 P2P，但拓撲仍然直接影響效能：

- **NUMA 親和性**：GPU 透過 PCIe 連線到特定 NUMA 節點，跨 NUMA 訪問系統記憶體會增加約 2 倍延遲
- **PCIe 鏈路狀態**：空閒時鏈路降級到 Gen 1 省電，負載下才恢復 Gen 5
- **CPU 執行緒繫結**：GPU 相關的 CPU 執行緒應繫結到 GPU 所在 NUMA 節點，避免跨 socket 通信

---

## 2. 環境資訊

### 2.1 硬體概覽

```bash
# CPU 架構
lscpu | grep -E "Model name|Socket|NUMA|Thread|Core"
```

本環境輸出：

```text
Model name:     Intel(R) Xeon(R) Platinum 8470Q
Socket(s):      2
Core(s)/socket: 52
Thread(s)/core: 2
CPU(s):         208
NUMA node(s):   2
```

### 2.2 NUMA 拓撲

```bash
# 各 NUMA 節點的 CPU 範圍
for f in /sys/devices/system/node/node*/cpulist; do
    echo "$f: $(cat $f)"
done
```

本環境輸出：

```text
/sys/devices/system/node/node0/cpulist: 0-51,104-155
/sys/devices/system/node/node1/cpulist: 52-103,156-207
```

```bash
# NUMA 距離矩陣
for f in /sys/devices/system/node/node*/distance; do
    echo "$f:"; cat $f
done
```

本環境輸出：

```text
/sys/devices/system/node/node0/distance:
10 21
/sys/devices/system/node/node1/distance:
21 10
```

**解讀**：本地 NUMA 訪問代價 = 10，跨 NUMA 訪問代價 = 21。約 2.1 倍延遲懲罰。

### 2.3 GPU PCIe 拓撲

```bash
# GPU 的 NUMA 親和性
cat /sys/bus/pci/devices/0000:98:00.0/numa_node
# 輸出: 1

# GPU PCIe 鏈路最大能力
cat /sys/bus/pci/devices/0000:98:00.0/max_link_speed   # 32.0 GT/s PCIe (Gen 5)
cat /sys/bus/pci/devices/0000:98:00.0/max_link_width    # 16

# GPU 在 PCIe 樹中的路徑
readlink -f /sys/bus/pci/devices/0000:98:00.0
# 輸出: /sys/devices/pci0000:97/0000:97:01.0/0000:98:00.0
```

---

## 3. nvidia-smi 拓撲檢視解讀

### 3.1 基本拓撲 (`topo -m`)

```bash
nvidia-smi topo -m
```

本環境輸出（單 RTX 5090）：

```text
        GPU0    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      52-103,156-207  1               N/A
```

圖例：

| 縮寫 | 含義                                       | 延遲 |
| ---- | ------------------------------------------ | ---- |
| X    | Self                                       | —    |
| PIX  | 單 PCIe bridge 內                          | 極低 |
| PXB  | 多 PCIe bridge，不出 PCIe Host Bridge      | 低   |
| PHB  | 跨 PCIe Host Bridge（經 CPU Root Complex） | 中   |
| NODE | 同 NUMA 節點內跨 PCIe Host Bridge          | 高   |
| SYS  | 跨 CPU Socket（經 UPI/IF）                 | 高   |
| NV#  | 經 NVLink                                  | 極低 |

多卡場景下，同一 NUMA 節點的 GPU 之間通常顯示為 `NODE` 或 `PIX`，跨 NUMA 則為 `SYS`。注意 `PIX`/`PXB`/`PHB` 本身是橋接層級分類，與 NUMA 無關：兩張卡即使在同一 NUMA 節點，只要路徑跨了 host bridge 也顯示 `PHB`；只有 `NODE`/`SYS` 才編碼 NUMA/socket 信息。

### 3.2 矩陣拓撲 (`topo -mp`)

`-mp` 選項以更緊湊的矩陣格式展示，適合多 GPU 場景：

```bash
nvidia-smi topo -mp
```

### 3.3 P2P 狀態 (`topo -p2p`)

```bash
nvidia-smi topo -p2p r    # r = 可訪問性
nvidia-smi topo -p2p w    # w = 頻寬矩陣
nvidia-smi topo -p2p n    # n = 路徑類型 (PIX/NODE/SYS等)
```

本環境輸出（單卡，僅 Self）：

```text
        GPU0
 GPU0    X
```

---

## 4. 跨 NUMA 訪問的實測影響

### 4.1 方法

以下指令碼分別在 GPU 所在 NUMA (node 1) 和遠端 NUMA (node 0) 分配記憶體，測量 H2D 頻寬差異。

```bash
# 如果 numactl 未安裝
apt install numactl

# 繫結到 GPU 所在 NUMA
numactl --cpunodebind=1 --membind=1 ./pcie_bw_test

# 繫結到遠端 NUMA
numactl --cpunodebind=0 --membind=0 ./pcie_bw_test
```

**本環境實測（taskset 綁核）**：

| CPU 繫結           | H2D 1 GB (GB/s) | D2H 1 GB (GB/s) |
| ------------------ | --------------- | --------------- |
| Node 0 (跨 NUMA)   | 52.60           | 53.33           |
| Node 1 (本地 NUMA) | 52.63           | 53.05           |

> 實測兩個 NUMA 節點頻寬幾乎一致。這是因為 Seetacloud 容器環境中 `membind` 策略被限制（`set_mempolicy: Operation not permitted`），實際記憶體分配策略為 `default`（不受 CPU binding 影響）。容器/VM 環境常掩蓋 NUMA 效應——裸金屬環境預計可觀測到 ~2.1× 差異。

### 4.2 建議

- GPU 程式應儘量從 GPU 所在 NUMA 節點分配 pinned memory
- 使用 `cudaMallocHost` (pinned memory) 時，系統自動從當前執行緒所在 NUMA 分配
- 可以用 `taskset -c 52-103` 或 `numactl --cpunodebind=1` 繫結行程到 GPU NUMA

---

## 5. CUDA 側查詢拓撲資訊

```c
cudaDeviceProp prop;
cudaGetDeviceProperties(&prop, 0);
printf("PCI Domain:  %04x\n", prop.pciDomainID);
printf("PCI Bus:     %02x\n", prop.pciBusID);
printf("PCI Device:  %02x\n", prop.pciDeviceID);
```

也可以透過 `cudaDeviceGetByPCIBusId` 反向查詢，確保選中正確的 GPU：

```c
cudaDeviceGetByPCIBusId(&device_id, "0000:98:00.0");
cudaSetDevice(device_id);
```

---

## 6. 與多卡場景的對比

| 維度        | 單卡 RTX 5090                   | 多卡 A100/H100 叢集           |
| ----------- | ------------------------------- | ----------------------------- |
| GPU 互連    | 無                              | NVLink / NVSwitch             |
| P2P         | 不支持                          | 支持 (GPUDirect P2P)          |
| NUMA 意識   | 關鍵（選錯節點損失大）          | 重要但被 NVLink 部分掩蓋      |
| 拓撲命令    | `topo -m` 即可                  | `topo -mp` + `topo -p2p` 全套 |
| NVLink 查詢 | `nvidia-smi nvlink -s` → 不支持 | 完整的鏈路狀態和計數          |

---

## 參考

- [PCIe 技術大全](../pcie/01_pcie_comprehensive_guide.md)
- [NVLink 技術入門](../nvlink/nvlink_intro.md)
- [nvidia-smi 快速入門](../../03_ai_cluster_ops/01_gpu_ops/03_nvidia_smi_guide.md)
- [CUDA Device Attribute 官方文件](https://docs.nvidia.com/cuda/cuda-runtime-api/structcudaDeviceProp.html)
- [PCIe 頻寬實測](../../02_gpu_programming/04_profiling/02_pcie_bandwidth_measurement.md) — H2D/D2H 基准程序
- [PCIe 頻寬 Benchmark](../../02_gpu_programming/04_profiling/code/02_pcie_bandwidth_bench.cu) — 可編譯執行的配套程式碼
