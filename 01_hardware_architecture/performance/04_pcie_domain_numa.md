# 多 PCIe 根匯流排段與 NUMA 映射

> 基於雙路 Sapphire Rapids（domain 0 內 24 個根匯流排段，2 個 NUMA node）。詳解 PCIe 根匯流排段與 NUMA 的對應關係、如何查詢，以及跨 NUMA 訪問 NVMe 的效能影響。實測環境為雙路 Sapphire Rapids + RTX 5090 + 3 塊 NVMe，實測時間未記錄（按 RTX 5090 上市時間推斷約 2025 年），核心與驅動版本未留存記錄。

---

## 1. 背景：Sapphire Rapids 的 PCIe 架構

先澄清一個常見的誤讀：Linux 裝置名 `0000:98:00.0` 中，`0000` 是 PCI domain 號，`98` 是 bus 號。Sapphire Rapids 平台上的裝置全部位於 domain 0，並不存在「GPU 在 domain 97」這回事；`pci0000:97` 指的是 domain 0 內以 bus 0x97 為根的一段匯流排，即一個 host bridge（RC stack）所轄的 bus 號段。

| 代際                | PCIe 拓撲                      | 特點                                         |
| ------------------- | ------------------------------ | -------------------------------------------- |
| Ice Lake            | 單 RC per socket, 多 Root Port | 裝置集中在一個 bus 號段                      |
| **Sapphire Rapids** | **多 RC per socket**           | 每個 RC stack 占一段 bus 號段，裝置分佈更分散 |

每個 socket 有多個獨立的 RC stack，各自占用一段 bus 號。本文環境的 24 個 `pci0000:xx` 目錄是 24 個根匯流排段，而不是 24 個 PCIe domain；GPU 在 bus 0x98 段，NVMe 在 bus 0xd7 段。

---

## 2. 本環境根匯流排段分佈

```bash
# 列出各根匯流排段及裝置數
for d in /sys/devices/pci*; do
    count=$(ls "$d" 2>/dev/null | grep -c "^0000:")
    echo "$(basename $d): $count devices"
done
```

| 根匯流排段           | 裝置數  | 推測用途           | NUMA  |
| ------------------ | ------- | ------------------ | ----- |
| 00                 | 18      | 晶片組, VGA        | —     |
| 7e, 7f             | 37, 122 | Socket 0 I/O       | 0     |
| 97                 | **5**   | **GPU** (RTX 5090) | **1** |
| d7                 | 3       | NVMe 陣列 (3 塊)   | 1     |
| fe, ff             | 37, 122 | Socket 1 I/O       | 1     |
| 其他 (15/26/37/ek) | 4-8     | 系統外設           | 分布  |

---

## 3. 查詢根匯流排段的 NUMA 親和性

### 3.1 sysfs 方法

```bash
# 方法 1: host bridge 的 numa_node（需核心支援）
cat /sys/devices/pci0000:97/numa_node 2>/dev/null

# 方法 2: 透過段內任意裝置查詢
cat /sys/bus/pci/devices/0000:98:00.0/numa_node    # GPU → 1
```

> 本環境 host bridge 級 `numa_node` 返回空——核心版本未暴露。但裝置級正常。

### 3.2 查詢各段內的代表性裝置

```bash
for d in /sys/bus/pci/devices/0000:7f:*/0000:* 0000:97:*/0000:* 0000:ff:*/0000:*; do
    [ -d "$d" ] || continue
    bdf=$(basename "$d")
    cls=$(cat "$d/class" 2>/dev/null)
    numa=$(cat "$d/numa_node" 2>/dev/null)
    echo "$bdf | class=$cls | NUMA=$numa"
done 2>/dev/null | head -20
```

### 3.3 透過裝置 BDF 規律推斷

Sapphire Rapids 按 socket 劃分 bus 號段，BDF 中的 bus 號直接給出 socket 歸屬：

| Bus Pattern             | Socket/NUMA            |
| ----------------------- | ---------------------- |
| `bus 0x00` ~ `bus 0x7f` | Socket 0 (NUMA node 0) |
| `bus 0x80` ~ `bus 0xff` | Socket 1 (NUMA node 1) |

GPU BDF = `0000:98:00.0` → bus 0x98 > 0x7f → Socket 1 → NUMA node 1。與 `numa_node` 返回的 `1` 一致。

### 3.4 NVMe 的 NUMA 位置

```bash
# 本環境 NVMe (3 塊均在 bus 0xd7 段 / Socket 1)
for nvme in /sys/block/nvme*/device; do
    bdf=$(readlink -f "$nvme" 2>/dev/null | grep -oP "0000:[0-9a-f:]+" | head -1)
    numa=$(cat /sys/bus/pci/devices/$bdf/numa_node 2>/dev/null)
    echo "$(basename $(dirname $nvme)): $bdf, NUMA=$numa"
done
```

本環境所有 3 塊 NVMe (nvme0-2n1) 均在 bus 0xd7 段，與 GPU (bus 0x98 段) 同屬 Socket 1。

GPU 和 NVMe 在同一 NUMA node，GDS (GPU Direct Storage) 場景下資料路徑全部在本地 socket 內，無需跨 UPI（Ultra Path Interconnect，Intel 雙路 CPU 之間的點對點互連匯流排）。

---

## 4. 跨 NUMA PCIe 訪問的效能影響

### 4.1 場景分析

```text
Socket 0 (NUMA 0)          Socket 1 (NUMA 1)
  ├── NVMe (bus 7f 段) ←?→   ├── GPU (bus 98 段)
  └── ...                    └── NVMe (bus d7 段) ← ✓ 本地
```

假設某塊 NVMe 掛在 Socket 0（左列），GPU 在 Socket 1，就是一條跨 NUMA 路徑。本環境 GPU 和 NVMe 同在 Socket 1（右列 ✓ 標記），GDS 無跨 NUMA 開銷。

### 4.2 跨 NUMA 的 PCIe 路徑

如果 GPU (Socket 1) 訪問 Socket 0 的 NVMe (bus 7f 段)：

```text
NVMe (S0) → RC (bus 7f 段) → UPI → RC (bus 98 段) → Bridge → GPU (S1)
```

經過 UPI 跨 socket 鏈路，NUMA distance 21 vs 10，預計增加 ~2× 延遲。但由於 NVMe I/O 延遲本就 ~10-100 μs，額外的 NUMA 延遲 (~100ns) 影響很小。

---

## 5. PCIe 拓撲與 GPU 程式設計

### 5.1 確認裝置選對匯流排段

CUDA 的 `cudaDeviceGetByPCIBusId` 可確保選中特定 BDF 的 GPU：

```c
int device_id;
cudaDeviceGetByPCIBusId(&device_id, "0000:98:00.0");
cudaSetDevice(device_id);
```

這在多根匯流排段環境中尤其重要，多張 GPU 可能分散在不同的 bus 號段。

### 5.2 跨 host bridge 的 P2P 可達性

P2P DMA 在同一個 host bridge（RC stack）轄屬範圍內通常暢通。跨 host bridge 的 P2P（如 GPU 訪問另一個 RC stack 下的 NVMe）依賴系統 firmware 的 ACPI DMAR 表支持，雲環境可能受限。

---

## 6. 總結

| 問題                   | 本環境答案                                |
| ---------------------- | ----------------------------------------- |
| GPU 在哪個 NUMA?       | Node 1 (bus 0x98 > 0x7f)                  |
| NVMe 在哪個 NUMA?      | Node 1 (bus 0xd7 段)，與 GPU 同 socket    |
| 有跨 NUMA PCIe 訪問嗎? | 本環境無，GPU 和 NVMe 在同一 socket       |
| BDF 編碼規則           | bus 0x00-0x7f = S0, bus 0x80-0xff = S1    |
| 多根匯流排段影響程式設計嗎?  | 需 `cudaDeviceGetByPCIBusId` 確保選對裝置 |

---

## 參考

- [單卡 GPU 拓撲與 NUMA 分析](02_single_gpu_topology_analysis.md)
- [PCIe 拓撲層次](../pcie/06_pcie_topology_hierarchy.md)
- [PCIe Switch 識別與驗證](../pcie/07_pcie_switch_vs_bridge.md)
- [CUDA NUMA API 程式設計實踐](../../02_gpu_programming/02_cuda/05_cuda_numa_api.md)
