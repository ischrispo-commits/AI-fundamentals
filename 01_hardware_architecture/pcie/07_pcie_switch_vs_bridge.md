# PCIe Switch 識別與驗證

> 基於雙路 Sapphire Rapids 實測。GPU 經簡單 Bridge 連線（無 Switch），NVMe 經高密度 domain（可能含 Switch）。本文教讀者從 sysfs 分辨 Switch、Bridge 與 Root Port。

---

## 1. 為什麼區分 Switch 和 Bridge

PCIe 體系中，Bridge 和 Switch 是最容易混淆的兩個元件。兩者 class code 相同 (0x060400)，但在硬體架構中的作用截然不同。

**PCIe Bridge** 是 PCIe bridge 的最簡形態（2 端口）：提供一條 1:1 的透明轉發通道，上游匯流排的一個埠對映到下游匯流排的一個裝置。配置空間為 Type 1 Header，primary/secondary/subordinate 三個 bus number 暫存器齊備（bridge 的 subordinate = secondary，只掛一條下游匯流排）。大多數桌面和工作站系統中，GPU 前面就是一個簡單的 Bridge。

**PCIe Switch** 是現代高速 I/O 的核心元件：1 個上游埠連線 Root Complex，N 個下游埠各連線一個裝置（GPU、NVMe 等）。Switch 內部有多條 PCI bus——自身內部匯流排 1 條 + 每個下游埠各 1 條，每個下行埠分配獨立的 secondary bus number，允許各埠並行轉發互不阻塞。Switch 還支援 ACS (Access Control Services) 來控制 P2P 流量的訪問隔離。

|             | PCIe Bridge                        | PCIe Switch                                                           |
| ----------- | ---------------------------------- | --------------------------------------------------------------------- |
| 埠數      | 2 (1 up + 1 down)                  | N+1 (1 up + N down)                                                   |
| Bus 數量    | 1 條 secondary bus（= subordinate）| 自身內部 bus 1 條 + 下游各 1 條                                       |
| 功能        | 透明轉發                           | 支持多播、ACS (Access Control Services)、VC (Virtual Channel)         |
| 延遲        | 每跳數十 ns 量級                   | 每個埠 ~100-200ns                                                   |
| 對 P2P 影響 | 不適用（單下游口，無 P2P 轉發場景）| 取決於 ACS 配置                                                       |
| sysfs 表現  | 下游 1 個 device                   | 下游 ≥2 個 device                                                     |

Switch 每個下行埠分配獨立的 secondary bus number。Bridge 也分配 bus number，但只有一個。

---

## 2. 從 sysfs 區分

### 2.1 檢查下游裝置數量

```bash
# 已知一個 bridge/switch 的 BDF
BDF="0000:97:01.0"

# 查找 sysfs 路徑
path=$(readlink -f /sys/bus/pci/devices/$BDF)
downstream=$(ls "$path" 2>/dev/null | grep -c "^0000:")
echo "Downstream devices: $downstream"
# = 1 → Bridge
# ≥ 2 → Switch
```

### 2.2 本環境實測

```bash
# GPU 下游（實際上 GPU 是 endpoint，無下游）
# 上游 Bridge: 97:01.0
ls /sys/devices/pci0000:97/0000:97:01.0/ | grep "^0000:"
# 0000:98:00.0    ← 僅 1 個 = Bridge
```

```bash
# domain 7f 有 122 devices——檢查其 Root Port 下游結構
ls /sys/devices/pci0000:7f/ | grep "^0000:"
# 0000:7f:00.0  0000:7f:00.1  ... ← Root Port 函式
```

> 本環境 7f/ff 的高裝置數來自 NVMe namespace 和 Root Port 的多 function，不是來自 Switch 的下游端口。

### 2.3 確認沒有 Switch

```bash
# 全系統掃描：查找下游 ≥2 device 的非 Root Port bridge
for dev in /sys/bus/pci/devices/*; do
    cls=$(cat "$dev/class" 2>/dev/null)
    [ "$cls" != "0x060400" ] && continue
    bdf=$(basename "$dev")
    path=$(readlink -f "$dev")
    # 排除 Root Port（device=00 的埠掛根匯流排下；按 domain_bus 上的 00 裝置判斷）
    bus=$(echo "$bdf" | cut -d: -f2)
    [ "$bus" = "00" ] && continue
    count=$(ls "$path" 2>/dev/null | grep -c "^0000:")
    [ "$count" -gt 1 ] && echo "POTENTIAL SWITCH: $bdf, downstream=$count"
done
# 本環境：無輸出 → 無 Switch
```

---

## 3. 確認 Switch 的補充方法

如果上述掃描找到候選 Switch，進一步驗證：

### 3.1 檢查 PCIe Capability

```bash
# Switch 通常有 PCIe Extended Capability: Device Serial Number, AER 等
lspci -vvv -s $BDF | grep -i "capabilities\|switch\|upstream\|downstream"
# 如果 lspci 未安裝，用 setpci：
setpci -s $BDF 0x34.l  # Capability pointer
```

### 3.2 檢查 PCIe Express Capability

Switch 的 PCIe Express Capability 中 `Device/Port Type` 欄位會標明：

| 值  | 類型                           |
| --- | ------------------------------ |
| 0x0 | PCIe Endpoint                  |
| 0x1 | Legacy Endpoint（顯示卡常見）    |
| 0x4 | Root Port of PCIe Root Complex |
| 0x5 | Upstream Port of PCIe Switch   |
| 0x6 | Downstream Port of PCIe Switch |
| 0x7 | PCIe-to-PCI/PCI-X Bridge       |

```bash
# 透過 sysfs 間接判斷：Switch 的 class 為 0x060400
# 但 "Upstream Port" 和 "Downstream Port" 的詳細類型需要 lspci -vvv
```

### 3.3 ACS (Access Control Services)

Switch 下游端口通常有 ACS 能力：

```bash
# ACS 能力判據有侷限：Root Port 同樣可能有 acs_*，
# 更可靠的是看 lspci -vvv 的 ACSCap + 下游裝置數
ls /sys/bus/pci/devices/$BDF/acs_* 2>/dev/null
```

---

## 4. Bridge 與 Switch 的效能差異

### 4.1 延遲

```text
路徑A: GPU ←Bridge→ Root Complex          (本環境)
路徑B: GPU ←Switch→ Switch → Root Complex (多層級)
```

Bridge 不引入額外匯流排層，延遲可忽略。Switch 每層增加 ~100-200ns（內部 crossbar 轉發）。

本環境 GPU 路徑：`RC → Bridge → GPU` 為最優——最少的中間層級，延遲最低。

### 4.2 頻寬共享

```text
Bridge:     [RC]────[Bridge]────[GPU]          ← GPU 獨佔 bridge
Switch:     [RC]────[Switch]──┬──[GPU 0]        ← 多 GPU 共享上行
                              ├──[GPU 1]
                              └──[NVMe]
```

本環境 GPU 獨佔 bridge，無其他裝置競爭 PCIe 頻寬——這解釋了為什麼 H2D 實測達到 56.3 GB/s（PCIe Gen 5 ×16 效率 ~89%）。

---

## 5. 總結

| 專案         | 本環境結論                                      |
| ------------ | ----------------------------------------------- |
| PCIe Switch  | **不存在**——全系統掃描未發現                    |
| GPU 連線方式 | Root Complex → Bridge (97:01.0) → GPU (98:00.0) |
| 拓撲優勢     | GPU 獨佔 bridge，無頻寬競爭，延遲最低           |
| NVMe 連線    | 經高密度 Root Port (domain 7f/ff)，非 Switch    |
| 驗證方法     | class + downstream device count + bus exclusion |

---

## 參考

- [PCIe 技術大全](01_pcie_comprehensive_guide.md)
- [PCIe 拓撲層次](06_pcie_topology_hierarchy.md)
- [PCIe 拓撲視覺化](03_pcie_topology_visualization.md)
- [PCI-SIG: PCIe Switch Specification](https://pcisig.com/)
