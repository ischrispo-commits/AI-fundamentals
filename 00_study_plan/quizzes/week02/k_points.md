# 第 2 週可測知識點（K 點）清單

> 格式同[第 1 週](../week01/k_points.md)：`編號 | 難度 | 可檢驗的陳述 | 來源 file:line | 適合受眾`。難度：1 事實、2 機制、3 應用、4 遷移。由 `course-handout-builder` 產生講義時同步寫入；來源行號以 2026-11-24 的 repo 狀態為準。

## D1（11/23）PCIe 基礎：lane、代際與編碼、樹狀拓撲、鏈路訓練

```text
W02D01-K1 | 1 | PCIe 連結（Link）由 1～32 條 lane 組成（x1、x2、x4、x8、x16、x32）；每條 lane 有 TX、RX 兩對差分線，全雙工，所以頻寬分單向與雙向 | 01_hardware_architecture/pcie/01_pcie_comprehensive_guide.md:122-123 | 工程師
W02D01-K2 | 1 | PCIe x16 單向理論頻寬：Gen3 15.75、Gen4 31.51、Gen5 63.02、Gen6 121.0、Gen7 242.0 GB/s；約每 3～4 年一代、頻寬翻倍 | 01_pcie_comprehensive_guide.md:29-39 | 工程師、CxO
W02D01-K3 | 2 | 編碼開銷：Gen1／2 用 8b/10b 損失 20%；Gen3～5 用 128b/130b 約 1.5%；Gen6 起 PAM-4 + FLIT + FEC 約 5～6% | 01_pcie_comprehensive_guide.md:43-47,282-284 | 工程師
W02D01-K4 | 2 | PCIe 是點對點樹狀拓撲：Root Complex 是樹根、整合在 CPU 內；Switch 有一個上游埠與多個下游埠，負責扇出與轉發；Endpoint 是末端裝置（GPU、NVMe、網卡） | 01_pcie_comprehensive_guide.md:125-130 | 工程師、TAM
W02D01-K5 | 2 | 開機時 LTSSM 依序 Detect → Polling → Configuration（協商寬度）→ L0；出錯或換速率時進 Recovery 重新訓練，所以實際寬度與代際可能低於卡規格 | 01_pcie_comprehensive_guide.md:291-298 | 工程師、TAM
W02D01-K6 | 3 | 確認 PCIe 實際狀態用 `nvidia-smi -q -d PCIE`，Current Link Width 應等於 Max；Gen4 卡跑在 Gen3 或 x16 掉到 x8 時，查 BIOS、PCIe 擴展器與 Riser 卡 | 03_ai_cluster_ops/01_gpu_ops/03_nvidia_smi_guide.md:174-177 | TAM、工程師
W02D01-K7 | 3 | 同一張 Gen5 x16 卡：協商成 Gen4 x16 單向約 31.5 GB/s（減半），再掉到 x8 約 15.8 GB/s（剩四分之一）；報價時卡與伺服器平台要一起規劃 | 01_pcie_comprehensive_guide.md:15,36-37,295 | CxO、業務
```

## D2（11/24）PCIe 拓撲層級、Switch vs Bridge、NUMA

```text
W02D02-K1 | 1 | PCIe 四層：Root Complex（在 CPU 內）→ Root Port → Bridge 或 Switch → Endpoint；Root Port、Bridge、Switch 的 class code 都是 0x060400，要看下游掛幾個裝置區分 | 01_hardware_architecture/pcie/06_pcie_topology_hierarchy.md:9-26 | 工程師
W02D02-K2 | 2 | Bridge 一上一下、透明轉發、每跳數十 ns；Switch 一上 N 下、每埠約 100～200 ns，支援 ACS 與多播；sysfs 下游 1 個裝置是 Bridge、≥ 2 個是 Switch | 01_hardware_architecture/pcie/07_pcie_switch_vs_bridge.md:15-22 | 工程師
W02D02-K3 | 3 | Switch 下多個裝置共用上行頻寬；GPU 獨佔 Bridge 時 H2D 實測 56.3 GB/s，約 Gen5 x16 理論值的 89% | 07_pcie_switch_vs_bridge.md:137-146 | 工程師、TAM
W02D02-K4 | 2 | GPU 之間的 PCIe P2P：同一顆 Switch（PIX）Gen5 x16 單向約 63 GB/s；經 Root Complex（PHB）約 32 GB/s，頻寬減半 | 01_hardware_architecture/performance/05_pcie_nvlink_speed_reference.md:89-90 | 工程師、TAM
W02D02-K5 | 2 | nvidia-smi 拓撲標識：NV12 為 12 條 NVLink 直連約 600 GB/s 雙向；PIX 同一 PCIe switch（Gen4 約 32 GB/s）；NODE 同 NUMA 經 host bridge（約 28 GB/s）；SYS 跨 NUMA 經 QPI／UPI，最慢 | 03_ai_cluster_ops/01_gpu_ops/03_nvidia_smi_guide.md:162-167 | TAM、工程師
W02D02-K6 | 2 | 跨 socket 經 UPI：NUMA distance 21 對本地 10，延遲約 2 倍；NVMe I/O 本身 10～100 µs，多出的約 100 ns 影響很小 | 01_hardware_architecture/performance/04_pcie_domain_numa.md:109-115 | 工程師
W02D02-K7 | 3 | Linux 裝置名 `0000:98:00.0` 中 0000 是 domain、98 是 bus；Sapphire Rapids 每個 socket 有多個 RC stack，`pci0000:97` 是 domain 0 內以 bus 0x97 為根的段，不是 domain 97 | 04_pcie_domain_numa.md:9-16 | 工程師
W02D02-K8 | 3 | 同一個 host bridge 下的 P2P 通常暢通；跨 host bridge 的 P2P 依賴韌體 ACPI DMAR 表支援，雲環境可能受限 | 04_pcie_domain_numa.md:133-135 | TAM
```

## D3（11/25）NVLink、NVSwitch、SHARP、NVLink-C2C

```text
W02D03-K1 | 2 | NVLink 物理層用「減少每鏈路線對、增加鏈路數」換頻寬：每鏈路差分線對 V100 8、A100 4、H100 2，鏈路數 6 → 12 → 18；2.0～4.0 單鏈路單向都是 25 GB/s，B200 升到 50 GB/s | 01_hardware_architecture/nvlink/nvlink_intro.md:79-86 | 工程師
W02D03-K2 | 2 | NVLink 支援 Load／Store 記憶體語義與原生原子操作，NVLink 域內所有 GPU 的 HBM 編在統一位址空間；協議以 Flit 為單位，有效載荷效率 94% 以上 | nvlink_intro.md:31,96-111 | 工程師
W02D03-K3 | 2 | NVSwitch 把點對點 Mesh 升級為交換式 Fabric：任兩顆 GPU 直連、非阻塞全速；聚合頻寬 = 埠數 × 每埠雙向頻寬，Gen3（DGX H100）64 × 50 = 3.2 TB/s，Gen4（GB200 NVL72）72 × 100 = 7.2 TB/s | nvlink_intro.md:128-156 | 工程師、TMM
W02D03-K4 | 3 | SHARP（Gen3 NVSwitch 起）在交換晶片內用 ALU 完成 All-Reduce 的歸約，只回傳結果；網路流量減半，集合通訊效能提升 2～3 倍（文章口徑） | nvlink_intro.md:160-166 | 工程師、PMM
W02D03-K5 | 1 | NVLink-C2C 是封裝級 CPU 對 GPU 互連：GH200 中雙向 900 GB/s（每方向 450），約 PCIe Gen5 x16 的 7 倍，鏈路能耗 1.3 pJ/bit | 01_hardware_architecture/superchips/nvlink_c2c.md:60-69 | 工程師、CxO
W02D03-K6 | 3 | GH200 = 1 Grace CPU + 1 Hopper GPU：96 GB HBM3 + 最多 480 GB LPDDR5X（512 GB 為 CPU 上限口徑）；GPU 經 C2C 直接存取 CPU 記憶體，可做 KV Cache offloading | nvlink_c2c.md:157-162,223-227 | CxO、PMM
W02D03-K7 | 3 | 同樣寫 900 GB/s：GH200 是 CPU 對 GPU 的 NVLink-C2C，HGX H100 是每張 GPU 的 NVLink 4.0（GPU 對 GPU）；引用時先說清連的是哪兩顆晶片 | nvlink_c2c.md:268-281 | 業務、TMM
W02D03-K8 | 1 | GB200 NVL72 用 9 個 NVSwitch Tray（每個 2 顆 Gen4 NVSwitch）連接 72 顆 GPU，機架內用 5000 多根銅纜背板而非光模組 | nvlink_intro.md:170-175 | PMM、CxO
```

## D4（11/26）GPUDirect P2P／RDMA／Storage、DMA engine

```text
W02D04-K1 | 2 | DMA 是委託：CPU／驅動把來源、目的、長度寫成 descriptor 交給 DMA engine 搬運，控制面在 CPU、資料面在 engine；GPU 的 copy engine 是 DMA engine 的一種；零複製是去掉 CPU 中轉緩衝區，DMA 仍在 | 01_hardware_architecture/dma/01_dma_engine.md:11-15,130 | 工程師
W02D04-K2 | 2 | GPUDirect P2P 把 GPU 間傳輸從兩跳（D2H + H2D 經系統記憶體）縮成一跳；A100 實測 NVLink P2P 單向 239.28 GB/s，經 CPU 中轉約 11.76 GB/s | 01_hardware_architecture/gpudirect/02_gpudirect_p2p.md:98-104；01_dma_engine.md:117-118 | 工程師、CxO
W02D04-K3 | 2 | P2P 路徑優劣：NV# 最佳、PIX 次之、PXB 良好、PHB 一般、NODE 受限、SYS（跨 NUMA）不支援 GPUDirect P2P | 02_gpudirect_p2p.md:260-266 | TAM、工程師
W02D04-K4 | 2 | GPUDirect RDMA 讓網卡透過 PCIe BAR 直接讀寫 GPU 顯存，資料不經 CPU 記憶體；路徑只經 PCIe Switch 最佳，跨 CPU socket 可能嚴重受限；IOMMU 須關閉或 1:1 passthrough | 01_hardware_architecture/gpudirect/01_gpudirect_technology.md:13,35-44 | 工程師、TAM
W02D04-K5 | 2 | 傳統讀檔到 GPU 三步：NVMe → page cache → 使用者緩衝區（CPU 複製）→ H2D；PCIe 走兩趟。GDS 讓 NVMe 的 DMA 直接寫入 GPU 顯存，只走一趟 | 01_gpudirect_technology.md:122-132,160-162 | 工程師
W02D04-K6 | 3 | GDS 前提：ACS bypass、`iommu=pt`、O_DIRECT 開檔；任一不符，libcufile 自動退回系統記憶體中轉的相容模式 | 01_gpudirect_technology.md:166-168 | TAM
W02D04-K7 | 4 | Gen4 x4 NVMe 讀進 GPU：buffered 約 3.5、O_DIRECT 約 7、GDS 約 7 GB/s；NVMe 本身是瓶頸時 GDS 頻寬不一定提升，收益在少一次 PCIe 穿越與 CPU 卸載；「至少兩倍」是路徑判斷而非通用倍數 | 01_hardware_architecture/performance/05_pcie_nvlink_speed_reference.md:94-96；01_gpudirect_technology.md:174 | CxO、TAM
W02D04-K8 | 3 | copy engine 適合大塊、可與計算重疊的複製；A100 HBM 內複製實測 copy engine 約 818 GB/s（峰值 40%）、SM 複製約 1453 GB/s（71%），copy engine 數字不能當 HBM 峰值 | 01_dma_engine.md:60,119-122 | 工程師
```
