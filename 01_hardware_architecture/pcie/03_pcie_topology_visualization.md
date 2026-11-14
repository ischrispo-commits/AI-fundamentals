# PCIe 拓撲視覺化：從 sysfs 到 nvidia-smi

> 基於 Intel Xeon Platinum 8470Q + RTX 5090 實際環境。`lspci` 需要安裝 `pciutils` 且在新環境中可能不可用：本文展示透過 sysfs 和 nvidia-smi 推斷 PCIe 拓撲的方法。

---

## 1. 快速路線

| 需求              | 工具                  | 說明                                       |
| ----------------- | --------------------- | ------------------------------------------ |
| 列出所有 PCI 裝置 | `lspci`               | 需安裝 `pciutils`                          |
| 樹狀拓撲          | `lspci -t`            | 顯示 PCIe 樹結構                           |
| GPU 鏈路狀態      | sysfs 或 `nvidia-smi` | 零依賴                                     |
| NUMA 親和性       | sysfs                 | `/sys/bus/pci/devices/<bdf>/numa_node`     |
| 鏈路速度和寬度    | sysfs                 | `current_link_speed`, `current_link_width` |

---

## 2. sysfs 讀取 PCIe 信息

### 2.1 列出所有 PCI 裝置

```bash
ls /sys/bus/pci/devices/
```

本環境輸出（部分）：

```text
0000:00:00.0
0000:00:00.1
0000:00:00.2
...
0000:97:01.0    ← PCIe bridge
0000:98:00.0    ← GPU (RTX 5090)
```

### 2.2 GPU PCIe 關鍵資訊

```bash
GPU_BDF="0000:98:00.0"   # Bus:Device.Function

# 廠商和裝置 ID
cat /sys/bus/pci/devices/$GPU_BDF/vendor   # 0x10de (NVIDIA)
cat /sys/bus/pci/devices/$GPU_BDF/device   # 0x2b85

# 裝置類別
cat /sys/bus/pci/devices/$GPU_BDF/class    # 0x030000 (VGA display controller)

# NUMA 親和性
cat /sys/bus/pci/devices/$GPU_BDF/numa_node   # 1

# 鏈路狀態
cat /sys/bus/pci/devices/$GPU_BDF/current_link_speed   # 2.5 GT/s (Gen 1)
cat /sys/bus/pci/devices/$GPU_BDF/current_link_width   # 16
cat /sys/bus/pci/devices/$GPU_BDF/max_link_speed       # 32.0 GT/s (Gen 5)
cat /sys/bus/pci/devices/$GPU_BDF/max_link_width       # 16
```

### 2.3 完整 PCIe 路徑

```bash
readlink -f /sys/bus/pci/devices/0000:98:00.0
# 輸出: /sys/devices/pci0000:97/0000:97:01.0/0000:98:00.0
```

路徑解讀：

```text
pci0000:97              ← PCI domain 0000 的根匯流排（host bridge）
  └── 0000:97:01.0      ← PCIe Bridge (bus 97, device 01, function 0)
        └── 0000:98:00.0 ← GPU (bus 98, device 00, function 0)
```

---

## 3. PCIe 樹結構分析

### 3.1 理解 sysfs 路徑

sysfs 路徑體現了 PCIe 層次結構。以上述路徑為例：

```text
pci0000:97          → 根匯流排（host bridge；其下的 97:01.0 才是 Root Port）
  0000:97:01.0      → PCIe Switch/Bridge 的上游端口
    0000:98:00.0    → GPU (下游裝置)
```

### 3.2 檢查是否有 PCIe Switch

```bash
# 查看 bridge 的裝置類別
cat /sys/bus/pci/devices/0000:97:01.0/class
# 0x060400 = PCI-to-PCI bridge (標準 PCIe bridge)
```

### 3.3 查詢同橋下的其他裝置

```bash
# 列出與 GPU 共享同一上游 bridge 的裝置
GPU_PATH="/sys/devices/pci0000:97/0000:97:01.0"
ls "$GPU_PATH" | grep "0000:"
# 輸出: 0000:98:00.0  (可能還有 0000:98:00.1 = GPU audio function)
```

---

## 4. 與 nvidia-smi 拓撲對照

### 4.1 sysfs 信息 → nvidia-smi 列

| sysfs                      | nvidia-smi 對應                     |
| -------------------------- | ----------------------------------- |
| `numa_node`                | `topo -m` 的 NUMA Affinity          |
| `current_link_speed/width` | `--query-gpu=pcie.link.gen.current` |
| `max_link_speed/width`     | `--query-gpu=pcie.link.gen.max`     |
| `vendor/device`            | `--query-gpu=pci.device_id`         |
| BDF (bus:device.function)  | `--query-gpu=pci.bus_id`            |

### 4.2 對照表示例 (本環境)

| 資訊來源           | 值                      |
| ------------------ | ----------------------- |
| sysfs BDF          | `0000:98:00.0`          |
| nvidia-smi BDF     | `00000000:98:00.0`      |
| sysfs NUMA         | 1                       |
| nvidia-smi NUMA    | 1 (CPUs 52-103,156-207) |
| sysfs max speed    | 32.0 GT/s (Gen 5)       |
| nvidia-smi max gen | 5                       |

### 4.3 完整的 PCIe 拓撲驗證指令碼

```bash
#!/bin/bash
# 從 sysfs 和 nvidia-smi 交叉驗證 GPU PCIe 拓撲
GPU_BDF="0000:98:00.0"

echo "=== GPU: $GPU_BDF ==="
echo "PCIe path:  $(readlink -f /sys/bus/pci/devices/$GPU_BDF)"
echo "NUMA node:  $(cat /sys/bus/pci/devices/$GPU_BDF/numa_node)"
echo "Max speed:  $(cat /sys/bus/pci/devices/$GPU_BDF/max_link_speed)"
echo "Current:    $(cat /sys/bus/pci/devices/$GPU_BDF/current_link_speed)"
echo "Max width:  $(cat /sys/bus/pci/devices/$GPU_BDF/max_link_width)"
echo "Current:    $(cat /sys/bus/pci/devices/$GPU_BDF/current_link_width)"
echo
echo "=== nvidia-smi verify ==="
nvidia-smi --query-gpu=index,name,pci.bus_id,pcie.link.gen.current,pcie.link.width.current,pcie.link.gen.max,pcie.link.width.max --format=csv
```

---

## 5. lspci 安裝與替代

### 5.1 安裝 lspci

```bash
apt install pciutils
lspci | grep -i nvidia
lspci -t           # PCIe 樹
lspci -vvv -s 98:00.0  # GPU 詳細
```

### 5.2 或使用 sysfs（零依賴）

如果無法/不想安裝 lspci，sysfs 提供所有必要信息：

```bash
# 列出所有 NVIDIA 裝置 (vendor 0x10de)
for dev in /sys/bus/pci/devices/*; do
    v=$(cat "$dev/vendor" 2>/dev/null)
    if [ "$v" = "0x10de" ]; then
        echo "$(basename $dev): vendor=$v device=$(cat $dev/device)"
    fi
done
```

---

## 6. 與多卡/HPC 場景對比

| 維度         | 單卡 RTX 5090          | 多卡 DGX/叢集                  |
| ------------ | ---------------------- | ------------------------------ |
| PCIe 樹深度  | 淺 (RC → Bridge → GPU) | 深 (RC → Switch → 多層 → GPU)  |
| sysfs 路徑數 | 1                      | N 個                           |
| 拓撲關鍵資訊 | NUMA node              | PCIe Switch affinity           |
| 推薦工具     | sysfs + nvidia-smi     | lspci -t + nvidia-smi topo -m |

---

## 參考

- [PCIe 技術大全](01_pcie_comprehensive_guide.md)
- [PCIe P2PDMA 技術介紹](02_p2pdma_technology.md)
- [單卡 GPU 拓撲與 NUMA 分析](../performance/02_single_gpu_topology_analysis.md)
