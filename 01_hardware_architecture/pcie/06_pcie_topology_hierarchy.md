# PCIe 拓撲層次：Root Complex、Switch、Bridge 與 Device

> 基於雙路 Sapphire Rapids (24 個 PCIe 根匯流排段) + RTX 5090 實測。從 sysfs 出发，逐層解析 PCIe 拓撲的四個核心元件。

---

## 1. 四層模型

```text
CPU Socket
  └── Root Complex (RC)
        ├── Root Port 0 → PCIe Bridge → Device (GPU)
        ├── Root Port 1 → Device (NVMe)
        ├── Root Port 2 → PCIe Switch → Device × N (NVMe陣列)
        └── Root Port 3 → Device (網卡)
```

| 元件                  | class code                       | 職責                                                     |
| --------------------- | -------------------------------- | -------------------------------------------------------- |
| **Root Complex (RC)** | —                                | CPU 內部，連線 CPU 與 PCIe 匯流排，每個 domain 對應一個 RC |
| **Root Port**         | 0x060400                         | RC 的下行端口，一個 domain 可有多個 Root Port            |
| **PCIe Switch**       | 0x060400（上行/下行端口同值）    | 擴展 PCIe 端口：1 個上行 + N 個下行埠                  |
| **PCIe Bridge**       | 0x060400                         | 簡單的 1:1 橋接，無埠擴展                              |
| **Endpoint**          | 0x030000 (VGA) / 0x010802 (NVMe) | 終端裝置：GPU、NVMe、網卡等                              |

> Switch 和 Bridge 的 class code 相同 (0x060400)—區別在於埠數量和 sysfs 子樹結構。

---

## 2. sysfs 識別各層

### 2.1 識別根匯流排段 (Root Complex)

每個 `pci0000:XX` 目錄是一個根匯流排段（都在 domain 0000 內，各占一段 bus 號），對應一個 RC stack：

```bash
ls /sys/devices/ | grep pci
```

本環境輸出（24 個根匯流排段）：

```text
pci0000:00  pci0000:15  pci0000:26  ...  pci0000:7f  pci0000:80
pci0000:97  pci0000:a7  ...  pci0000:fe  pci0000:ff
```

```bash
# 各 domain 的裝置數量
for d in /sys/devices/pci*; do
    count=$(ls "$d" 2>/dev/null | grep -c "^0000:")
    echo "$(basename $d): $count devices"
done
```

本環境（部分）：

```text
pci0000:00: 18 devices    ← 晶片組/VGA
pci0000:7f: 122 devices   ← Socket 0 高密度 I/O
pci0000:97: 5 devices     ← GPU 所在 domain
pci0000:ff: 122 devices   ← Socket 1 高密度 I/O
```

### 2.2 識別 Bridge vs Switch

Bridge 下游只有 1 個裝置；Switch 有多個下游埠：

```bash
# 本環境：GPU 經單 Bridge 連線
ls /sys/devices/pci0000:97/0000:97:01.0/ | grep "^0000:"
# 0000:98:00.0           ← 僅 1 個下游裝置 = Bridge，非 Switch

# Bridge class code
cat /sys/devices/pci0000:97/0000:97:01.0/class
# 0x060400               ← PCI-to-PCI bridge
```

如果有 Switch，會看到：

```text
# 示例（非本環境）：Switch 有多個下游埠
ls /sys/devices/pci0000:7f/0000:7f:00.0/ | grep "^0000:"
# 0000:80:00.0  0000:81:00.0  0000:82:00.0  ...  ← 多個下游裝置
```

### 2.3 追蹤裝置完整路徑

```bash
readlink -f /sys/bus/pci/devices/0000:98:00.0
# /sys/devices/pci0000:97/0000:97:01.0/0000:98:00.0
#                ↑RC      ↑Bridge       ↑GPU
```

解析：`pci0000:97`（根匯流排）→ `0000:97:01.0`（Bridge, Intel 0x352a，完整身份以 `lspci -s 97:01.0` 輸出為準）→ `0000:98:00.0`（GPU）。

---

## 3. 本環境完整拓撲

```text
Socket 0 (NUMA node 0)
├── pci0000:00  18 devices  (chipset, VGA, legacy)
├── pci0000:7e  37 devices  (I/O subsystem)
└── pci0000:7f  122 devices (高密度 I/O)

Socket 1 (NUMA node 1)
├── pci0000:97   5 devices  (GPU domain)
│     └── 97:01.0 [Bridge, Intel 0x352a]
│           └── 98:00.0 [RTX 5090, NVIDIA 0x2b85]
├── pci0000:d7          (NVMe domain: nvme0n1/1n1/2n1)
├── pci0000:fe  37 devices  (I/O subsystem)
└── pci0000:ff  122 devices (高密度 I/O)
```

關鍵觀察：

- **GPU 獨佔一個 domain** (pci0000:97)，無其他高速裝置共享 RC——這是最優拓撲
- **NVMe 分布在 domain d7**（3 塊 NVMe，`nvme0-2n1`，與 GPU 同在 Socket 1 / NUMA node 1）和 domain 7f/ff（高密度 I/O，各 122 devices）
- **GPU 與 3 塊 NVMe 在同一個 Socket**：GDS (GPU Direct Storage) 的 NVMe↔GPU 資料路徑在本地 socket 內完成，無跨 UPI 開銷，參見 [GPU Direct Storage 基礎](../gpudirect/03_gds_basics.md)。跨 socket 需經過 UPI（Ultra Path Interconnect，Intel 雙路 CPU 之間的點對點互連匯流排，NUMA distance 21 vs 本地 10），會增加 ~2× 延遲

---

## 4. 識別 Root Port vs Switch Port

```bash
# Root Port 通常在 domain 根目錄下 (BDF 的 device=00)
ls /sys/devices/pci0000:97/ | grep "0000:97:00"
# 0000:97:00.0  0000:97:00.1  0000:97:00.2  0000:97:00.4
# 這些是 Root Port（BDF 的 bus = 0x97，即 domain 根匯流排）

# Bridge 掛在 Root Port 下游（device=01；bridge 自身仍在 bus 0x97 上，其下游 secondary bus 是 0x98）
ls /sys/devices/pci0000:97/ | grep "0000:97:01"
# 0000:97:01.0  ← Bridge
```

Root Port 的特徵：BDF 中 bus = domain bus (通常是 0x97)，device = 0x00。

---

## 5. 查看 Bridge 的上下游

```bash
# Bridge 的上游 (指向 Root Port)
# 透過 PCIe 拓撲推斷：97:01.0 的上游是 97:00.x (某個 Root Port)

# Bridge 的下游裝置
ls /sys/devices/pci0000:97/0000:97:01.0/ | grep "0000:"
# 0000:98:00.0  ← GPU

# 檢查下游是否有更多 bridge (級聯)
cat /sys/bus/pci/devices/0000:98:00.0/class
# 0x030000  ← VGA controller: 這是 Endpoint，不再級聯
```

---

## 6. 總結

| 層級         | 本環境                    | 如何識別                                |
| ------------ | ------------------------- | --------------------------------------- |
| Root Complex | 24 個 domain (pci0000:XX) | `/sys/devices/pci*` 的數量              |
| Root Port    | domain 內 BDF device=00   | `class = 0x060400` + bus=domain bus     |
| PCIe Switch  | **不存在**                | 下游有 ≥2 個 device 的 bridge           |
| PCIe Bridge  | 97:01.0 (Intel 0x352a)    | `class = 0x060400` + 下游僅 1 個 device |
| Endpoint     | 98:00.0 (RTX 5090)        | class 非 0x060400/0x060000              |

GPU 路徑為最簡拓撲：Root Complex → Bridge → GPU，無 Switch 引入額外延遲，無同級裝置競爭頻寬。

---

## 參考

- [PCIe 技術大全](01_pcie_comprehensive_guide.md)
- [PCIe 拓撲視覺化](03_pcie_topology_visualization.md)
- [PCIe AER 錯誤監控](04_pcie_aer_monitoring.md)
