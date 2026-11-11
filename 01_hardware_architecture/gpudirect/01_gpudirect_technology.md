# NVIDIA GPUDirect RDMA 與 Storage 技術詳解

## 1. 引言

GPU 和網卡、儲存裝置之間交換資料，預設路徑要經過 CPU 記憶體：傳送前先從顯存搬到系統記憶體，接收後還要再搬一次。這段中轉消耗 PCIe 頻寬和 CPU 記憶體頻寬，也讓 CPU 被迫參與資料搬運。

GPUDirect 系列技術做的事情，就是把 CPU 從資料路徑上拿掉：節點內 GPU 之間走 [GPUDirect P2P](02_gpudirect_p2p.md)，跨節點 GPU 與網卡走 **GPUDirect RDMA**，GPU 與 NVMe 儲存走 **GPUDirect Storage (GDS)**。本文講後兩個的機制、部署前提和邊界；P2P 的原理與程式碼見 GPUDirect P2P 篇。

## 2. GPUDirect RDMA 技術

> 官方文件參考：[GPUDirect RDMA Documentation](https://docs.nvidia.com/cuda/gpudirect-rdma/index.html)

GPUDirect RDMA (Remote Direct Memory Access) 是一項允許第三方 PCIe 裝置（如網路介面卡 NIC、儲存介面卡等）直接訪問 NVIDIA GPU 顯存的技術。這項技術最早在 Kepler 架構 GPU 和 CUDA 5.0 中引入，旨在消除 GPU 與第三方裝置通訊時 CPU 的介入和不必要的系統記憶體複製。

整體架構：

![high level view](assets/gpudirect-rdma.png)

### 2.1 技術背景與痛點

在未啟用 GPUDirect RDMA 的傳統架構中，當 GPU 需要透過網路傳送資料時，資料流必須經歷“GPU 顯存 -> 系統記憶體 (CPU 參與) -> 網卡”的路徑：

1. **資料複製**：GPU DMA 引擎將資料從 GPU 顯存搬運到源主機的系統記憶體 (CPU 記憶體)，CPU 不參與資料搬運。
2. **網路傳輸**：CPU 參與控制，網卡 (NIC) 透過 DMA 從系統記憶體讀取資料並透過網路傳送。
3. **接收與複製**：目標主機網卡透過 DMA 將資料寫入系統記憶體，再由 GPU DMA 引擎搬運到目標 GPU 顯存。

這帶來了顯著的效能瓶頸：

- **高延遲**：資料在 PCIe 匯流排上往返，且需要 CPU 處理中斷和上下文切換。
- **頻寬瓶頸**：資料流經系統記憶體，受限於 CPU 記憶體頻寬。
- **CPU 負載**：CPU 必須參與緩衝區管理和 DMA 描述符設定，無法專注於計算任務。

### 2.2 工作原理詳解

GPUDirect RDMA 利用了標準 PCIe 匯流排的功能，使第三方裝置能夠透過 **PCI BAR (Base Address Register)** 直接對 GPU 顯存進行讀寫操作。

#### 2.2.1 核心機制

當兩個 PCIe 裝置（例如 GPU 和 NIC）共享同一個上游 Root Complex 時，它們可以透過實體地址直接通訊。路徑品質取決於中間經過什麼：路徑上只有 PCIe Switch 時最優；經過單個 CPU/IOH 時可用，但部分處理器平台的 P2P 讀頻寬嚴重受限；跨 QPI/HT（跨 CPU Socket）路徑可能嚴重受限甚至不可靠。

IOMMU 是硬性前提：GPUDirect RDMA 假設所有 PCI 裝置看到同一套實體地址，所以開啟地址翻譯的 IOMMU 必須關閉或配置成 1:1 passthrough。ACS 重定向也會影響 P2P 流量的走向，配置細節見 [Linux PCIe P2PDMA 技術介紹](../pcie/02_p2pdma_technology.md)。

- **PCI BARs 映射**：GPU 將其顯存的一定區域透過 BARs 暴露在實體地址空間中。
- **P2P Direct Access**：NIC 可以像訪問系統記憶體一樣，直接向這些 GPU BAR 地址发起 PCIe Read/Write 事務。

![host view](assets/gdr.jpeg)

#### 2.2.2 驅動層互動 (Kernel & Userspace)

GPUDirect RDMA 的實現依賴於 NVIDIA Kernel Driver 和使用者態 CUDA 庫 (Userspace CUDA Library) 的協同工作：

1. **地址區分**：使用者態 CUDA 庫提供 API 幫助通訊庫（如 MPI, NCCL）區分指標是指向 CPU 記憶體還是 GPU 顯存。
2. **Pinning GPU Memory (頁面鎖定)**：
   - 對於 CPU 記憶體，Linux 核心使用 `get_user_pages()` 進行 Pinning。
   - 對於 GPU 顯存，NVIDIA Kernel Driver 提供了專用的核心 API（`nvidia_p2p_get_pages` 等）來鎖定 GPU 頁面，並將其匯流排地址（bus address）列表返回給 NIC 驅動。
   - NIC 驅動用這些匯流排地址程式設計 DMA 引擎，從而建立直接的資料傳輸通道。

### 2.3 效能優勢

GPUDirect RDMA 在 GPU 和第三方裝置之間建立直接的資料傳輸通道，消除了系統記憶體複製和 CPU 介入。

- **Zero-Copy (零複製)**：完全消除了 GPU 顯存到系統記憶體的緩衝複製。
- **降低延遲**：資料直接在裝置間傳輸，少一次 PCIe 穿越和系統記憶體中轉。
- **完全解除安裝**：CPU 僅需負責建立連線和控制流，資料路徑完全旁路 CPU。

還有一個容易忽略的正確性問題：NIC 的 DMA 寫完 GPU 顯存，不等於 GPU 上後續 kernel 已經能看到新資料。官方只承諾 CUDA synchronization 與 work submission API 提供記憶體序，通訊庫仍要遵守 stream/event 順序，不能只看 RDMA 完成中斷就認為資料可見。

### 2.4 開發者視角：程式碼與 API

雖然上層應用通常使用 CUDA-aware MPI 或 NCCL 來隱式使用 GPUDirect RDMA，但在底層驅動開發中，涉及以下關鍵步驟：

```c
// 虛擬碼示例：展示 NIC 驅動如何註冊 GPU 顯存以進行 RDMA
// 實際上，這通常由 InfiniBand Verbs (libibverbs) 庫在使用者態封裝

// 1. 使用者態分配 GPU 記憶體
void* d_buffer;
cudaMalloc(&d_buffer, size);

// 2. 註冊記憶體區域 (Memory Region Registration)
// 此時，libibverbs 會檢測指標類型。如果是 GPU 指標，
// 它會呼叫 NVIDIA 核心驅動提供的 nvidia_p2p_get_pages 等接口
// 來獲取 GPU 頁面的實體地址，並將其寫入 NIC 的頁表 (MTT/MKEY)。

struct ibv_mr *mr = ibv_reg_mr(pd, d_buffer, size,
                               IBV_ACCESS_LOCAL_WRITE |
                               IBV_ACCESS_REMOTE_WRITE |
                               IBV_ACCESS_REMOTE_READ);

if (!mr) {
    // 註冊失敗，可能因硬體不支援或未載入 nvidia-peermem 模組
    fprintf(stderr, "GPUDirect RDMA registration failed\n");
}

// 3. 執行 RDMA 操作 (Send/Recv/Write/Read)
// NIC 硬件 DMA 引擎直接透過 PCIe 匯流排訪問 d_buffer 的物理地址
ibv_post_send(qp, &wr, &bad_wr);
```

**注意**：要啟用此功能，系統需要載入 `nvidia-peermem` 核心模組，該模組充當 NVIDIA 驅動與 InfiniBand 核心驅動之間的橋樑。它要求核心帶 RDMA peer memory 支持（上游核心或 MLNX_OFED 提供），NIC 側 ConnectX-3 VPI 及更新版本可用，InfiniBand 和 RoCE 都支持。舊版 `nv_peer_mem` 與 `nvidia-peermem` 只能載入一個，啟用前先解除安裝舊模組。

記憶體類型也有邊界：GPUDirect RDMA 只作用於 `cudaMalloc()` 分配的 GPU 頁；Unified Memory 沒有被官方支援，註冊後可能讀到舊資料甚至丟資料。BAR1 頁 pinning 是毫秒級開銷，驅動靠延遲解對映來攤薄，頻繁註冊/登出小塊顯存會放大這個成本。

節點內的實際驗證流程和實測數字見 [GPUDirect RDMA 跨節點驗證](04_gpudirect_rdma_verification.md)；從 DMA engine 視角看描述符、地址對映和完成語義，見 [DMA engine：從描述符到完成，一次搬運發生了什麼](../dma/01_dma_engine.md)。

---

## 3. GPUDirect Storage (GDS) 技術

> 官方文件參考：[GPUDirect Storage Documentation](https://docs.nvidia.com/gpudirect-storage/)

隨著 AI、HPC 以及資料分析領域的資料集規模持續增長，資料載入所消耗的時間開始對應用整體效能產生顯著影響。高速 GPU 往往受限於緩慢的 I/O，尤其是在將資料從儲存系統載入到 GPU 顯存以進行計算處理的過程中。

GPUDirect Storage (GDS) 旨在建立一條在本地或遠端儲存（如 NVMe 或 NVMe over Fabrics, NVMe-oF）與 GPU 記憶體之間的直接資料通路。該技術避免了透過 CPU 記憶體中的中轉緩衝區（Bounce Buffer）進行額外的資料複製，使位於網卡或儲存裝置附近的直接記憶體訪問（DMA）引擎能夠沿著一條直達路徑將資料直接傳入或傳出 GPU 記憶體，全程無需給 CPU 帶來額外負擔。

整體架構：

![high level view](assets/gpudirect-storage.png)

### 3.1 技術背景與痛點

在傳統的儲存 I/O 路徑中，將資料從磁碟讀取到 GPU 顯存是一個多階段、低效率的過程：

1. **核心態緩衝**：儲存裝置（如 NVMe SSD）透過 DMA 將資料寫入作業系統核心空間的 Page Cache。
2. **使用者態複製**：CPU 將資料從核心空間複製到使用者空間的應用程式緩衝區 (CPU 記憶體)。
3. **H2D 複製**：GPU DMA 引擎將資料從 pinned buffer 搬運到 GPU 顯存 (Host-to-Device)，CPU 僅設定 DMA 描述符，不參與資料搬運。

這種被稱為“Bounce Buffer”效應的機制存在三大問題：

- **CPU 瓶頸**：CPU 必須參與中間的 memcpy（page cache → user buffer），隨著 NVMe 速度提升，CPU 逐漸成為瓶頸。
- **延遲增加**：多次資料搬運（DMA + CPU memcpy）和上下文切換顯著增加了端到端延遲。
- **PCIe 頻寬浪費**：資料在 PCIe 匯流排上來回傳輸（SSD -> CPU -> GPU），實際上佔用了兩倍的 PCIe 頻寬。

### 3.2 工作原理與軟體架構

GPUDirect Storage 不僅是一項硬體技術，更依賴於一套深度的軟硬體協同棧，引入了全新的檔案系統直通機制。

#### 3.2.1 軟體架構與依賴

GDS 的實現依賴於以下核心軟體元件：

- **cuFile API (libcufile)**：使用者態核心庫。它提供了類似於 POSIX (`read`/`write`) 的 API，但專門針對 GPU 顯存指標進行了過載。它負責攔截 I/O 請求，進行參數檢查，並智慧選擇最佳的傳輸路徑（GDS 路徑或相容回退路徑）。
- **nvidia-fs.ko (cufile.ko)**：這是 GDS 的核心核心模組。由於標準的 Linux 核心 VFS（虛擬檔案系統）和塊裝置層無法直接處理 GPU 顯存地址，`nvidia-fs` 必須介入。它負責：
  - 與檔案系統（如 ext4, xfs）互動以獲取檔案後設資料和物理塊佈局。
  - 呼叫 NVIDIA GPU 驅動介面鎖定 GPU 顯存頁面。
  - 將 I/O 請求轉換為下層驅動可理解的格式。
- **儲存驅動適配**：
  - **傳統模式 (Legacy / MOFED)**：標準的 NVMe 驅動通常期望 DMA 目標是系統記憶體。為了支援 P2P DMA，舊版本的 GDS 往往需要經過補丁修改的 NVMe 驅動（通常由 MOFED 提供）或特定的核心補丁。在這種模式下，`nvidia-fs` 透過特定的回撥介面與塊裝置層互動，甚至可能傳遞特殊的“偽地址”或句柄，以便驅動能識別並正確建立指向 GPU 顯存的 DMA 映射。
  - **原生 P2PDMA 模式 (Modern / Upstream)**：隨著 Linux 核心的發展（Kernel >= 6.2），上游核心引入了標準的 **PCI P2PDMA** 基礎設施。從 CUDA 12.8 開始，GDS 可以利用這一標準機制，無需修改 NVMe 驅動即可實現 P2P 傳輸。這顯著降低了部署門檻，消除了對定製核心或驅動的依賴。

#### 3.2.2 核心流程：地址轉換與 DMA

GDS 的 I/O 流程並非簡單的“把 GPU 地址給硬碟”，而是一個複雜的地址轉換與編排過程。由於 PCIe 裝置間無法直接透過 GPU 虛擬地址通訊，且作業系統核心主要管理 CPU 實體記憶體，因此需要經過多層轉換：

1. **使用者態請求**：應用程式呼叫 `cuFileRead`，傳入 GPU 虛擬地址（Device Virtual Address, DVA）。
2. **核心態捕獲**：`libcufile` 將請求傳遞給核心模組 `nvidia-fs`。
3. **地址轉換與鎖定 (Pinning)**：
   - `nvidia-fs` 無法直接將 GPU DVA 傳遞給 NVMe 驅動。它首先需要呼叫 NVIDIA GPU 驅動 API，將 GPU 虛擬地址鎖定，並獲取對應的 **GPU 物理地址 (GPU Physical Address)** 或 **PCIe 匯流排地址 (Bus Address)**。
   - **Legacy 模式實現細節**：為了適配現有的核心塊裝置介面，`nvidia-fs` 可能會構建包含特殊標記（如“偽 CPU 地址”）的 BIO（Block I/O）結構體。當底層的 NVMe 驅動（需支持 GDS）識別到這些特殊標記時，會透過回撥 `nvidia-fs` 提供的接口，將這些偽地址替換為真實的 GPU BAR 物理地址，從而構建正確的 DMA 描述符（PRP/SGL）。
4. **DMA 描述符構建**：
   - 最終，DMA 引擎的目標地址被填入了 GPU 的 BAR 空間實體地址，而非 CPU 記憶體地址。
5. **P2P 直接傳輸**：NVMe 控制器啟動 DMA，資料透過 PCIe 匯流排直接寫入 GPU 顯存，完全繞過 CPU 記憶體和 CPU 快取。

#### 3.2.3 路徑選擇與回退

如果硬體或系統配置不支援 P2P（例如裝置不在同一個 PCIe Root Complex 下，ACS 未旁路，或 IOMMU 未設為 passthrough），`libcufile` 會自動檢測並回退到相容模式（System Memory Bounce Buffer），但仍會嘗試最佳化路徑。

> **GDS 硬體前提條件**：ACS bypass（PCIe Switch 下行埠關閉 ACS 轉發限制）、`iommu=pt`（核心啟動參數，避免 DMA 地址轉換開銷）、O_DIRECT 對齊（檔案開啟必須使用 O_DIRECT 標誌）。任一條件不滿足將導致回退。

### 3.3 核心優勢

GDS 透過構建儲存到 GPU 的直通高速公路，打破了傳統 I/O 的頻寬和延遲瓶頸，並徹底解放了 CPU 算力。

- **頻寬提升**：直接利用 PCIe P2P 特性，吞吐量可接近儲存裝置或 PCIe 匯流排的物理極限。官方口徑是繞開 CPU 的直達路徑"峰值頻寬至少是經過 CPU 路徑的兩倍"；這是對硬體路徑的判斷，不是對所有配置都成立的通用加速倍數。
- **延遲最小化**：消除了中間的記憶體複製步驟，I/O 延遲顯著降低。
- **CPU 解除安裝 (CPU Offloading)**：CPU 僅需處理控制流，不再參與繁重的資料搬運，從而釋放 CPU 算力用於預處理或其他邏輯。

### 3.4 部署與上手

GDS 的部署前提已在 3.2.3 覆蓋（ACS、IOMMU、O_DIRECT）。cuFile API 的完整呼叫流程（包括緩衝註冊 `cuFileBufRegister`）、環境檢查指令碼與前置條件核對，見 [GPU Direct Storage 基礎](03_gds_basics.md)；該文基於 RTX 5090 + CUDA 12.8 (GDS 1.13.1) 環境，可直接照做。

## 4. GPUDirect 生態系統支援

GPUDirect 技術（涵蓋 RDMA 和 Storage）已經建立了龐大的軟硬體生態系統，從底層的網卡和儲存裝置，到中介軟體通訊庫，再到上層的 AI 框架，均有廣泛支援。

### 4.1 GPUDirect RDMA 生態

- **網路硬體**：NVIDIA Mellanox ConnectX 系列（`nvidia-peermem` 從 ConnectX-3 VPI 起支持，5/6/7 代最完善）、AWS EFA、Broadcom/Chelsio 的部分網卡。
- **通訊庫**：NCCL 的集合通信、CUDA-aware MPI（OpenMPI/MVAPICH2）、NVSHMEM 的單邊通訊、UCX 框架，都在檢測到可用拓撲後自動走 GPUDirect RDMA，應用層通常無感。

### 4.2 GPUDirect Storage (GDS) 生態

本地檔案系統 ext4、xfs 原生支持；Lustre、IBM Spectrum Scale、WekaFS、VAST、BeeGFS 等並行/分散式檔案系統經各自整合支援 GDS；NetApp、Dell PowerScale、Pure FlashBlade 等儲存陣列也在產品層面做了整合。版本與功能的支援矩陣以 [NVIDIA GDS Release Notes](https://docs.nvidia.com/gpudirect-storage/release-notes/index.html) 為準。

### 4.3 上層框架整合

DALI 原生支持 GDS 加速資料預處理流水線；PyTorch 經 DALI 插件使用 GDS，分散式訓練經 NCCL 走 GPUDirect RDMA；RAPIDS cuDF 用 GDS 讀取 Parquet/CSV/ORC；TensorFlow 經 NCCL 和 I/O 外掛獲得同樣的加速能力。具體版本與配置要求（核心、OFED）見各廠商文件與上面的支援矩陣。

---

## 5. 總結

RDMA 和 GDS 是同一個思想在兩個方向上的應用：資料面繞開 CPU 記憶體，控制面留在 CPU。RDMA 管跨節點的梯度與 KV cache 傳輸，GDS 管儲存到顯存的資料載入，兩者在一個大規模訓練叢集裡通常同時存在。

決定能不能用、快多少的不是 API，而是三件事：裝置的相對位置（是否同一 root complex、是否經 PCIe Switch）、地址翻譯的配置（IOMMU 關閉或 1:1、ACS、BAR1）、以及記憶體類型是否在支援範圍內（`cudaMalloc` 顯存、對齊的 buffer）。部署前核對這三件事，驗證流程見 [RDMA 跨節點驗證](04_gpudirect_rdma_verification.md) 與 [GDS 基礎](03_gds_basics.md)；把搬運放回完整 DMA 模型，見 [DMA engine](../dma/01_dma_engine.md)。
