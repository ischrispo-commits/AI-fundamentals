# NVLink 技術入門

> 本文參考了 [NVIDIA 官方文件](https://www.nvidia.com/en-us/data-center/nvlink/) 及網際網路相關技術資料整理而成，旨在深入解析 NVIDIA 高速互連技術 NVLink 的原理與演進。
>
> **適用 GPU 範圍**：NVLink 是資料中心級 GPU（Tesla/Quadro/A100/H100/B200 等）的專有特性。**消費級 GeForce RTX 系列 GPU（包括 RTX 5090）不支持 NVLink**，可透過 `nvidia-smi nvlink -s` 確認（不支援時輸出 `Device does not have or support Nvlink`）。

---

## 1. 前言：打破“通訊牆”

在深度學習時代，模型參數量呈現指數級增長（從 ResNet 的 2500 萬參數到 GPT-4 的 1.8 萬億參數——非官方公開數字，為 SemiAnalysis 估計），對算力的需求快速攀升（OpenAI 2018 年的分析曾得出「AI 算力每 3.5 個月翻一番」，該結論截至 2018 年）。然而，傳統硬體架構中**資料傳輸頻寬**的增長速度遠滯後於計算能力的增長，這種“剪刀差”導致了嚴重的**通訊牆 (Communication Wall)** 問題。

在標準的 x86 伺服器架構中，GPU 通常作為 PCIe 外設存在。雖然 PCIe 標準在不斷迭代，但在處理多 GPU 協同任務時仍面臨兩大挑戰：

1. **頻寬瓶頸**：即便是 PCIe 5.0 x16，其 128 GB/s 的雙向總頻寬對於動輒 TB 級參數交換的分散式訓練（如張量並行、專家混合 MoE）來說杯水車薪。
2. **拓撲限制**：PCIe 採用樹狀拓撲，GPU 間的 P2P (Peer-to-Peer) 通訊往往需要經過 PCIe Switch 甚至 CPU Root Complex 轉發，引入了不可忽視的延遲。

**NVLink** 的出現，正是為了繞過 PCIe 的限制，構建一條專屬於 GPU 的高速資料高速公路。

### 1.1 什麼是 NVLink

**NVLink** 是 NVIDIA 推出的一種專有**高速互連協議**，旨在解決多 GPU 之間（以及部分支持的 CPU 與 GPU 之間）的高頻寬、低延遲通訊問題。

不同於 PCIe 的匯流排式共享架構，NVLink 采用**點對點 (Point-to-Point)** 連線方式，支援多條鏈路聚合。從邏輯上看，它打破了單顆 GPU 的物理邊界，允許 GPU 叢集共享統一的記憶體地址空間，使其表現為一顆擁有海量顯存和算力的“邏輯巨型 GPU”。

### 1.2 核心優勢

NVLink 不僅僅是提升了傳輸速度，更重要的是它改變了 GPU 之間的協作方式。透過提供高頻寬、低延遲和統一記憶體訪問能力，NVLink 將多顆獨立的 GPU 緊密耦合在一起，使其能夠像單顆巨型晶片一樣高效協同工作。以下是其四大核心技術優勢：

- **數量級的頻寬提升**：NVLink 5.0 (Blackwell) 提供高達 **1.8 TB/s** 的雙向頻寬，是 PCIe 5.0 x16 (128 GB/s) 的 **14 倍**以上，徹底釋放了 HBM 高頻寬記憶體的潛力。
- **原生記憶體語義 (Native Memory Semantics)**：這是 NVLink 與傳統網路互連最大的區別。它支援處理器直接使用 `Load/Store` 指令訪問遠端 GPU 的顯存，無需經過繁瑣的 DMA 驅動棧，極大地簡化了程式設計模型並降低了通訊延遲。
- **極低延遲**：透過輕量級的資料鏈路層設計，NVLink 實現了微秒級的端到端延遲，非常適合細粒度（Fine-grained）的梯度同步操作。
- **線性擴展能力**：配合 **NVSwitch** 芯片，NVLink 可從單機內的 Mesh 互連擴展為機架級甚至叢集級的 Switch Fabric 網路，支援數百個 GPU 建立無阻塞的全互連通訊（官方最大拓撲為 Blackwell Ultra 的 576 GPU 計算fabric；數千卡規模是 IB/Ethernet scale-out 的領地）。

---

## 2. NVLink 版本演進

NVLink 隨著 NVIDIA GPU 架構的迭代不斷進化，單 GPU 頻寬逐代提升（多數代際翻倍）。

### 2.1 技術代際回顧

NVLink 的发展史就是 NVIDIA GPU 叢集架構的進化史。每一代 NVLink 的推出都伴隨著特定的架構創新：

- **NVLink 1.0 (Pascal, 2016)**：技術的誕生。首次在 P100 上引入，旨在打破 PCIe 的頻寬限制，支持 4 GPU 互連。
- **NVLink 2.0 (Volta, 2017)**：**NVSwitch 的引入**。配合 V100 和第一代 NVSwitch，實現了單機 8 卡或 16 卡的全互連 (All-to-All) 拓撲。
- **NVLink 3.0 (Ampere, 2020)**：**效率與密度的平衡**。在 A100 上將差分訊號對減半（8對->4對），從而在不增加太多晶片面積的情況下將鏈路數翻倍（6->12），總頻寬達到 600 GB/s。
- **NVLink 4.0 (Hopper, 2022)**：**網內計算 (In-Network Computing)**。引入 **SHARP** 技術，利用 NVSwitch 上的計算單元直接處理歸約操作，減輕 GPU 負擔。
- **NVLink 5.0 (Blackwell, 2024)**：**機架級擴展**。支持 **GB200 NVL72** 架構，透過銅纜背板將 72 顆 GPU 連線為一個統一的計算域。
- **NVLink 6.0 (Vera Rubin, 2026)**：第六代 NVSwitch 引入控制面冗余、Switch Tray 熱插拔等 RAS 特性。頻寬口徑注意：GTC 2025 釋出時為單 GPU 3.6 TB/s、NVL72 機架聚合 260 TB/s；當前 NVIDIA 官方 NVLink 頁已更新為單 GPU 3,000 GB/s、Vera Rubin NVL72 聚合 216 TB/s——以官方頁為最新口徑（2026-11 核對）。

### 2.2 關鍵參數對比表

| 版本    | 发布年份 | 對應架構         | 訊號調製 | 訊號對數量 (Pairs/Link) | 單鏈路頻寬 (單向) | 鏈路數 (每GPU) | 總雙向頻寬 (每GPU) | 備註                     |
| :------ | :------- | :--------------- | :------- | :---------------------- | :---------------- | :------------- | :----------------- | :----------------------- |
| **1.0** | 2016     | Pascal (P100)    | NRZ      | 8 (Sub-link)            | 20 GB/s           | 4              | 160 GB/s           | 首次引入                 |
| **2.0** | 2017     | Volta (V100)     | NRZ      | 8 (Sub-link)            | 25 GB/s           | 6              | 300 GB/s           | 引入 NVSwitch 1.0        |
| **3.0** | 2020     | Ampere (A100)    | NRZ      | 4 (Sub-link)            | 25 GB/s           | 12             | 600 GB/s           | 訊號對減半，鏈路數翻倍   |
| **4.0** | 2022     | Hopper (H100)    | PAM-4    | 2 (Diff-pair)           | 25 GB/s           | 18             | 900 GB/s           | 引入 SHARP               |
| **5.0** | 2024     | Blackwell (B200) | PAM-4    | 2 (Diff-pair)           | 50 GB/s           | 18             | 1.8 TB/s           | 支持 NVL72 機架級擴展    |
| **6.0** | 2026     | Rubin (Vera)     | -        | -                       | -                 | -              | 3.6 TB/s           | NVLink Switch 6, RAS增強。頻寬雙口徑：3.6 TB/s/GPU、域聚合 260 TB/s（GTC 2025 宣傳口徑）；當前官網 3,000 GB/s/GPU、域 216 TB/s（2026-11 核對） |

> **注**：
>
> 1. **頻寬單位**：表中“GB/s”指 GigaBytes per second。
> 2. **計算公式**：總雙向頻寬 = 單鏈路單向頻寬 × 2 (雙向) × 鏈路數。
> 3. **PCIe 對比**：PCIe 5.0 x16 的總雙向頻寬僅為 128 GB/s，NVLink 5.0 是其 14 倍以上，NVLink 6.0 更是達到了 28 倍。

---

## 3. 技術原理解析

NVLink 的設計理念與 PCIe 有本質區別，它不僅僅是 I/O 匯流排，更是處理器內部匯流排的**片外擴展**。

### 3.1 物理層 (Physical Layer)：用“減法”做“加法”

NVLink 的物理層演進遵循一個獨特的邏輯：**不斷減少每條 Link 的訊號線數量，同時成倍提升單線速率**。這種設計使得在晶片引腳數（Package Pins）有限的情況下，能夠容納更多的 Link，從而構建更密集的網狀拓撲。

- **訊號對與速率演進**：
  - **NVLink 2.0 (V100)**：8 對差分訊號線/Link × 25 Gbps NRZ = 25 GB/s (單向)。
  - **NVLink 3.0 (A100)**：**4 對**差分訊號線/Link × 50 Gbps NRZ = 25 GB/s。
    - _關鍵點_：雖然單鏈路頻寬沒變，但訊號線減半，使得 A100 的 Link 數量從 6 個翻倍到 12 個，總頻寬翻倍。
  - **NVLink 4.0 (H100)**：**2 對**差分訊號線/Link × 100 Gbps PAM-4 = 25 GB/s。
    - _關鍵點_：引入 **PAM-4** 調製，再次將訊號線減半，Link 數量增加到 18 個。
  - **NVLink 5.0 (B200)**：2 對差分訊號線/Link × 200 Gbps PAM-4 = **50 GB/s**。
    - _關鍵點_：SerDes 速率翻倍至 224 Gbps，終於實現了單鏈路頻寬的翻倍。

- **訊號調製技術**：
  - **NRZ (Non-Return-to-Zero)**：NVLink 1.0-3.0 采用。高低電平代表 1/0，抗干擾能力強但頻寬效率較低。
  - **PAM-4 (Pulse Amplitude Modulation 4-level)**：NVLink 4.0+ 采用。一個時鐘週期傳輸 2 bit (4 種電平)，在相同波特率下頻寬翻倍，但對訊雜比 (SNR) 要求極高。

### 3.2 協議層 (Protocol Layer)：極簡與高效

為了追求極致的低延遲，NVLink 拋棄了 PCIe 繁重的協議包袱，採用了極簡的 Flit 傳輸機制。

- **Flit (Flow Control Unit) 架構**：
  - 資料以 **Flit** 為基本單位傳輸，大大降低了協議開銷 (Overhead)。
  - 相比 PCIe 需要封裝複雜的 TLP (Transaction Layer Packet) 頭，NVLink 的有效載荷效率 (Payload Efficiency) 高達 **94%** 以上。
- **低延遲設計**：
  - 由於不需要複雜的 ACK/NAK 重傳機制（依賴極高品質的物理層訊號），NVLink 的鏈路級延遲在數十 ns 量級（Switch 內部轉發）；跨節點（IB scale-out）另計。下表的對比取常見量級口徑，具體數值隨拓撲與測量方法變化。
- **原生原子操作 (Native Atomics)**：
  - 支持 `Atomic Add`, `Compare-and-Swap` 等指令直接在遠端 GPU 顯存上執行。這對於 **All-Reduce** 中的梯度累加操作至關重要，避免了“讀回-修改-寫回”的昂貴開銷。

### 3.3 記憶體一致性 (Cache Coherency)

這是 NVLink 區別於傳統網路的關鍵能力。

- **統一記憶體空間**：在 NVLink 連線域內，所有 GPU 的 HBM 顯存被編址到一個統一的實體地址空間。GPU A 可以直接透過指標訪問 GPU B 的顯存，就像訪問本機顯存一樣。
- **硬體級一致性**：
  - 當 GPU A 修改了 GPU B 顯存中的資料，NVLink 提供一致性語義與系統級原子操作支援；但 CUDA 程式設計模型下跨 GPU 的 L1/L2 快取預設不自動一致，可見性仍需同步/fence 保證。
  - 程式設計模型上，開發者可以使用標準的 `Load/Store` 指令進行跨卡通訊，無需顯式呼叫 `cudaMemcpy`，極大地簡化了 **Tensor Parallelism** (模型被切分到多張卡) 的程式碼實現。

### 3.4 軟體生態：從硬體到應用

NVLink 的硬體特性並非孤立存在，而是透過 NVIDIA 的軟體棧轉化為實際的應用效能。這部分內容與 **GPUDirect** 和 **NIXL** 等技術緊密相關：

- **驅動層支撐：GPUDirect P2P**
  - NVLink 是 **GPUDirect P2P (Peer-to-Peer)** 技術在高效能場景下的物理載體。
  - 透過 **UVA (Unified Virtual Addressing)**，CUDA 驅動將 NVLink 連線的多顆 GPU 顯存對映到統一虛擬地址空間，使得上層應用可以直接透過指標訪問遠端顯存，實現了真正的 Zero-Copy。
- **中介軟體應用：NIXL (Inference Xfer Library)**
  - 在推理場景中，**NIXL** 庫利用 NVLink 的高頻寬特性，在 Context/Decode 分離架構（Disaggregated Serving）中實現 **KV Cache** 的極速搬運。
  - NIXL 能夠智慧識別 NVLink 拓撲，優先選擇 Load/Store 指令進行本地 NVLink 域內的資料傳輸，從而避免了傳統 PCIe 路徑的延遲。

---

## 4. NVSwitch：從 Mesh 到 Fabric

早期的 NVLink（如 P100/V100 部分場景）采用 **Hybrid Cube Mesh** 拓撲，GPU 之間點對點連線。這種方式在 GPU 數量較少（如 4 卡或 8 卡）時有效，但隨著叢集規模擴大，點對點連線的複雜度呈指數級上升，且跨節點的通訊跳數增加導致延遲不可控。

為了解決全互連擴展性問題，NVIDIA 引入了 **NVSwitch** 芯片，將互連拓撲從 **Mesh (網狀)** 升級為 **Switch Fabric (交換式網路)**。

### 4.1 NVSwitch 的核心價值

NVSwitch 類似於乙太網交換機，但它專門用於交換 NVLink 訊號，具有以下特性：

- **全互連 (All-to-All)**：在單節點（如 DGX H100）甚至機架（如 GB200 NVL72）範圍內，實現任意兩顆 GPU 之間的直連通訊，無需經過中間 GPU 轉發。
- **非阻塞 (Non-Blocking)**：所有埠可以同時以滿速頻寬傳輸資料，消除內部爭用。
- **物理隔離**：將計算（GPU）與通訊（Switch）解耦，使得通訊網路的擴展不再受限於 GPU 晶片的引腳數量。

### 4.2 NVSwitch 代際演進

NVSwitch 作為 NVLink 技術的核心擴展元件，其代際演進直接決定了多 GPU 系統的擴展性 (Scalability) 和全互連 (All-to-All) 通信能力。從首款支援 16 GPU 全互連的 Gen 1 NVSwitch 到支撐 72 GPU 機架級架構的 Gen 4 NVSwitch，每一代產品都針對前一代的埠數、頻寬和核心特性進行了針對性最佳化，以滿足不斷增長的 AI 和 HPC 負載需求。

| 代際      | 對應架構  | 典型系統    | 埠數/芯片 | 聚合頻寬/芯片 | 核心特性                          |
| :-------- | :-------- | :---------- | :---------- | :------------ | :-------------------------------- |
| **Gen 1** | Volta     | DGX-2       | 18          | 900 GB/s      | 首款 NVSwitch，支持 16 GPU 全互連 |
| **Gen 2** | Ampere    | DGX A100    | 36          | 1.8 TB/s      | 針對 A100 最佳化，埠數翻倍        |
| **Gen 3** | Hopper    | DGX H100    | 64          | 3.2 TB/s      | 引入 **SHARP**，支持 FP8 計算     |
| **Gen 4** | Blackwell | GB200 NVL72 | 72          | 7.2 TB/s      | 支持 72 GPU 機架級全互連          |

> **注：頻寬計算詳解**
>
> NVSwitch 的聚合頻寬 = 埠數 × 單埠雙向頻寬。
>
> - **Gen 3 (Hopper)**: 64 端口 × 50 GB/s (NVLink 4.0) = 3200 GB/s = **3.2 TB/s**。
> - **Gen 4 (Blackwell)**: 72 端口 × 100 GB/s (NVLink 5.0) = 7200 GB/s = **7.2 TB/s**。
>
> 值得注意的是，雖然 NVLink 2.0/3.0/4.0 的單鏈路雙向頻寬均保持在 50 GB/s（單向 25），但 NVIDIA 透過持續減少單鏈路所需的訊號線數量（8對 -> 4對 -> 2對），得以在晶片物理尺寸受限的情況下大幅增加埠密度，從而實現了 Switch 總頻寬的代際飛躍。

### 4.3 關鍵技術：SHARP (網內計算)

**SHARP (Scalable Hierarchical Aggregation and Reduction Protocol)** 是 NVSwitch 3.0 引入的網內計算協議：聚合/歸約操作在交換機內完成，不再需要資料在節點間多輪搬運。

- **傳統 All-Reduce**：資料需要在 GPU 之間多次傳輸，並在 GPU 上進行求和/平均計算，佔用了寶貴的 GPU 算力和顯存頻寬。
- **SHARP 最佳化**：NVSwitch 晶片內部整合了 **ALU (算術邏輯單元)**。當多個 GPU 发起 All-Reduce 操作時，資料在流經 NVSwitch 時直接被截獲並進行歸約計算 (FP8/FP16/FP32/BF16)，Switch 僅將最終計算結果返回給 GPU。
- **性能收益**：大幅減少了網路流量（資料量減半），並將集合通訊效能提升了 **2-3 倍**，對於大模型訓練至關重要。

### 4.4 架構巔峰：GB200 NVL72 與銅纜背板

Blackwell 時代的 **GB200 NVL72** 把 NVLink 的擴展能力推到了機架級。

- **機架即 GPU (Rack-Scale GPU)**：透過 9 個 NVSwitch Tray (每個含 2 顆 Gen4 NVSwitch)，將 72 顆 B200 GPU 連線成一個巨大的單一邏輯 GPU。這 72 顆 GPU 共享統一的 HBM 記憶體池，總頻寬高達 130 TB/s。而在 **Vera Rubin NVL72** 機架中，官方頁當前口徑的聚合頻寬為 **216 TB/s**（GTC 2025 釋出口徑曾為 260 TB/s，以官方頁為準）。
- **銅纜互連 (Copper Cable Backplane)**：
  - NVL72 放棄了機架內昂貴且高功耗的光模組 (Optics)，轉而使用 **5000+ 根銅纜** 構建背板。
  - **為何迴歸銅纜？** NVLink 為短距離設計，機架尺度內銅纜相比光纖功耗更低、成本更低、延遲更低（官方口徑為 5000+ 根銅纜；第三方測算整機架可省約 20 kW，精確比例無官方數字）。

---

## 5. 常見誤區與深度辨析

在評估高效能運算系統時，頻寬單位的混用和互連協議的差異常常導致誤解。本章將對這些關鍵概念進行深度辨析。

### 5.1 頻寬計量：Bit vs Byte 與 單向 vs 雙向

在閱讀技術規格時，需嚴格區分以下兩種視角：

- **網路通訊視角 (Network View)**
  - **單位**：通常使用 **Gbps (Gigabits per second)**。
  - **方向**：常指**單向**接口速率（例如 400G 以太網卡指單向傳送或接收能力為 400 Gbps）。
- **系統匯流排視角 (System Bus View)**
  - **單位**：通常使用 **GB/s (GigaBytes per second)** (1 Byte = 8 Bits)。
  - **方向**：常指**雙向總和**頻寬（Total Aggregate Bandwidth）。

**NVLink 的頻寬計算實例 (以 Blackwell B200 為例)**：
NVIDIA 標稱的 **1.8 TB/s** 是指單顆 GPU 的**雙向總頻寬**。

- **物理構成**：B200 包含 18 條 NVLink 鏈路 (Links)。
- **單鏈路速率**：每條鏈路的單向頻寬為 50 GB/s (即 400 Gbps，采用 PAM-4 調製)。
- **計算公式**：
  `Total Bandwidth = Link Count × One-way Bandwidth per Link × 2 (Bi-direction)`
  `1.8 TB/s = 18 × 50 GB/s × 2`

### 5.2 協議對比：NVLink vs PCIe

NVLink 並非 PCIe 的替代品，而是為了解決 PCIe 在多 GPU 協同場景下的瓶頸而生。

| 維度         | PCIe (Gen 5.0)                              | NVLink (Gen 4.0 / 5.0 / 6.0)            |
| :----------- | :------------------------------------------ | :-------------------------------------- |
| **設計初衷** | 通用外設互連 (相容性優先)                   | 高性能 GPU 互連 (效能優先)              |
| **拓撲結構** | 樹狀拓撲 (Root Complex - Switch - Endpoint) | 網狀 (Mesh) 或 交換式 Fabric (NVSwitch) |
| **雙向頻寬** | ~128 GB/s (x16 通道)                        | 900 GB/s ~ 3.6 TB/s                     |
| **通訊延遲** | 高 (需經過 CPU 或 PCIe Switch，~20 μs 級)   | 極低 (GPU 直連或經 NVSwitch，~2 μs 級)  |
| **記憶體語義** | DMA 為主，原子操作支持有限                  | **Load/Store 語義**，支援快取一致性     |
| **生態系統** | 開放標準，x86/ARM/RISC-V 均支持             | NVIDIA 專有封閉生態                     |
| **系統成本** | 低                                          | 極高 (需專用基板和 NVSwitch 芯片)       |

### 5.3 應用場景決策：何時必須使用 NVLink？

NVLink 主要用於解決 **Scale-up (節點內/機架內擴展)** 的通訊瓶頸。

- **關鍵場景 (必須使用)**：
  - **超大規模模型訓練**：當模型參數量超過單卡顯存 (如 GPT-4, Llama 3 70B+)，必須使用 **模型並行 (Model Parallelism)**。
  - **張量並行 (Tensor Parallelism, TP)**：需要在每層計算中頻繁進行 All-Reduce 操作，對頻寬和延遲極其敏感。
  - **專家混合模型 (MoE)**：不同 Expert 之間的 Token 路由需要極高的 All-to-All 通訊頻寬。
- **非關鍵場景 (可以使用 PCIe)**：
  - **單卡推理**：無跨卡通訊需求。
  - **資料並行 (Data Parallelism, DP)**：主要通訊發生在反向傳播後的梯度同步，通常瓶頸在於節點間的網路互連 (Scale-out)，而非節點內。
  - **小參數模型微調 (LoRA)**：通訊量相對較小。

## 6. 總結

NVLink 是 NVIDIA 構建 AI 算力霸權的核心護城河之一。它透過“暴力”的頻寬提升和先進的記憶體語義，成功打破了單晶片的物理極限，將數千顆 GPU 融合成一台邏輯上的“巨型超級計算機”。

對於架構師而言，理解 NVLink 的本質在於理解 **Scale-up** (透過 NVLink 做強節點/機架) 與 **Scale-out** (透過 InfiniBand/Ethernet 做大叢集) 的協同關係。在摩爾定律放緩的今天，互連技術的進步已成為推動 AI 算力增長的新引擎。

---

## 7. 參考資料

1. **NVIDIA Official Documentation**: [NVLink & NVSwitch](https://www.nvidia.com/en-us/data-center/nvlink/)
2. **WikiChip**: [NVLink - Nvidia](https://en.wikichip.org/wiki/nvidia/nvlink) - 提供了詳細的物理層參數和歷史演進資料。
3. **Wikipedia**: [NVLink](https://en.wikipedia.org/wiki/NVLink) - 包含各個版本的頻寬對比和生態系統介紹。
