# DMA engine：從描述符到完成，一次搬運發生了什麼

> Linux 側按 kernel DMA-API、DMA engine provider 與 PCI P2PDMA 文件核對；CUDA 側按 CUDA 13.4 Runtime API 與 Programming Guide 核對；GPUDirect RDMA / Storage、DOCA DMA 按 NVIDIA 官方文件核對；CXL 部分按 CXL Consortium 文件核對。

一台訓練機在載入 checkpoint。`nvidia-smi` 顯示顯存佔用在漲，CPU 核並沒有忙著逐位元組複製；一次推理請求要把 KV cache 從一張卡送到另一張卡，應用只提交了一個 `cudaMemcpyAsync`。資料是誰搬的？

`memcpy` 是接口名，真正執行搬運的通常是 DMA engine。它不跑模型計算，也不執行 CUDA kernel；它讀描述符、訪問記憶體、寫完成記錄。理解這條路徑，才能回答幾個實際問題：為什麼小複製不一定快，為什麼 pinned memory 重要，為什麼 `cudaMemcpyAsync` 沒有讓計算和傳輸重疊，以及為什麼 GPUDirect 有時快、有時退回 CPU 中轉。

## 1. 先建立直覺：DMA 是什麼

把 DMA 想成一次“委託”。CPU 不親自逐位元組搬資料，而是把源地址、目標地址、長度寫成一個任務，交給專門的搬運硬體；CPU 繼續做排程或計算，硬體在後台讀寫記憶體，完成后通知 CPU。控制面在 CPU/驅動，資料面在 DMA engine，這是理解後面所有路徑的起點。

DMA 解決的是“CPU 親自搬資料太浪費”的問題，不是“零複製”的同義詞，也不保證一定比 CPU 複製快。資料小、對映開銷高、engine 被佔滿時，DMA 可能並不划算；它真正的價值通常在於把搬運和計算重疊。

DMA（Direct Memory Access）是一種訪問機制：裝置不經過 CPU 的逐位元組搬運，直接讀寫記憶體。DMA engine 是執行這件事的硬體單元。GPU 里的 copy engine（CE）是 DMA engine 的一種實現，專門承擔複製；NIC、NVMe 控制器、DPU 也各自有 DMA engine。

| 概念        | 是什麼                             | 不要混淆                                   |
| ----------- | ---------------------------------- | ------------------------------------------ |
| DMA         | 裝置直接訪問記憶體的機制             | 不是某個函式，也不等於一定比 CPU 複製快    |
| DMA engine  | 讀描述符、發起讀寫、報告完成的硬體 | 不是 CPU 核，也不一定是 GPU 的 copy engine |
| copy engine | GPU 上承擔複製的 DMA engine        | 不是每次 `cudaMemcpy*` 都必然走它          |
| SM copy     | kernel 里的普通 load/store         | 不走 copy engine，但仍可能發生跨裝置訪問   |

![DMA 宏觀示意](assets/dma-engine-01-overview.png)

_圖 1：CPU/驅動負責提交任務，DMA engine 執行資料面搬運；Host DRAM、GPU HBM/CXL 都可能成為源或目標。_

## 2. 一次 DMA 的生命周期

### 2.1 Buffer、pin 和地址映射

DMA 的目標記憶體必須對裝置可見。GPU 訪問 host 記憶體時，頁被換出會破壞正在進行的傳輸，所以驅動通常要求 page-locked（pinned）記憶體；普通 pageable 記憶體則可能先被複制到臨時 pinned buffer，再交給 engine。`cudaHostAlloc` / `cudaHostRegister` 的意義就在這裡：它們讓 host 記憶體保持駐留，並建立裝置可訪問的對映。

另一個容易寫錯的點是地址。CPU 虛擬地址不能直接交給裝置；驅動要建立 DMA/bus address（在虛擬化平台通常是 IOVA），再由 IOMMU 或裝置頁表翻譯到實體記憶體。說“DMA 只認實體地址”不準確，應該說“DMA 使用 DMA/bus address，是否需要翻譯取決於平台和 IOMMU”。

這一步也解釋了為什麼“把 `malloc` 的指標直接傳給 GPU”不是好的路徑。CUDA 可能替你做 staging，但 staging 有額外複製，非同步性也可能丟失。

### 2.2 Descriptor 和 doorbell

驅動把源地址、目標地址、長度、方向、完成標記寫進 descriptor。大塊傳輸常用 scatter-gather list，把一個邏輯傳輸拆成多個物理頁或段。隨後 CPU 寫 doorbell 或裝置暫存器，告訴 engine“這組 descriptor 可以取了”。

NVMe 的 Submission/Completion Queue 和 doorbell 是這套流程的一個具體例子。descriptor 的格式、啟動方式和完成通知由裝置定義，不存在所有 DMA engine 通用的描述符規範。

doorbell 是 MMIO 寫。某些匯流排上，CPU 的寫是 posted write，CPU 可以在事務真正到達裝置前繼續執行；需要確認裝置已經看到 doorbell 時，驅動會讀回一個暫存器或執行 barrier。這個細節在“複製已經提交”和“engine 已經開始搬運”之間劃出邊界。

### 2.3 Engine 執行與完成

engine 按 descriptor 讀源、寫目標，完成后更新 completion 記錄。CPU 可以透過中斷或輪詢知道完成。完成有兩種常見含義：engine 已經把資料寫完，和 CPU/GPU 已經能看到新資料。兩者不是同一件事。

對 coherent allocation，裝置寫通常能被處理器直接看到；對 streaming/non-coherent 記憶體，需要 `dma_sync_single_for_device()` / `dma_sync_single_for_cpu()` 這類 ownership 轉移。GPUDirect RDMA 的順序更嚴格：NVIDIA 文件只承諾 CUDA synchronization 和 work submission API 提供記憶體序；GPU 可能在後續同步前看到舊資料或亂序資料。

![DMA 生命周期](assets/dma-engine-02-lifecycle.png)

_圖 2：控制面準備 descriptor，資料面由 engine 執行；completion 只說明 engine 寫完。_

## 3. GPU 的 copy engine

### 3.1 Copy engine 與 SM copy

GPU 有兩類搬運路徑。copy engine 獨立於 SM，適合大塊、連續、可以和計算重疊的 H2D/D2H/D2D 複製；SM copy 是 kernel 里的 load/store，適合小塊、稀疏、需要和其他計算融合的訪問。peer access 開啟後，GPU 0 的 kernel 可以直接解引用 GPU 1 的指標，這條路徑走 SM，不走 `cudaMemcpyPeer`。

CUDA 裝置屬性 `asyncEngineCount` 表示非同步引擎數量，官方最佳實踐用它說明 GPU 可以同時做非同步傳輸和 kernel 執行；雙 copy engine 的 GPU 可以同時做一路 H2D、一路 D2H 和執行 kernel。這個欄位只能說明潛在併發上限，不能證明任意多 stream 一定各佔一個 engine。不同 stream 的複製可能落到同一 work queue，產生 false dependency，實際併發要用 Nsight Systems 看時間線。

### 3.2 `cudaMemcpyAsync` 的承諾與邊界

`cudaMemcpyAsync` 對 host 非同步，可以繫結 stream，H2D/D2H 在非零 stream 上可能與其他 stream 的操作重疊。但它不保證一定走 copy engine：CUDA 文件說會利用 dedicated copy engine 和 NVLink，Tegra 平台甚至明確由驅動在 SM 和 copy engine 之間做 heuristic 選擇。

pageable memory 是另一個邊界。只有 pinned memory 才保證 host 非同步；pageable H2D 可能先做 stream sync，函式返回時只完成了到 staging buffer 的複製，最終 DMA 可能還沒完成。`cudaMemcpyAsync` 遇到 pageable 記憶體也可能同步。不要把“非同步 API”直接等同於“已經非同步執行”。

`cudaMemcpy` 本身也不能簡單寫成“host 同步”。按 CUDA Runtime API 的口徑：pageable H2D 可能在 staging 后返回，pinned H2D 對 host 同步，D2H 等複製完成，D2D 不做 host-side 同步，H2H 完全同步。`cudaMemcpyPeer` 的文件同時出現“非同步於 host”和“多數場景同步”兩種說法，跨裝置依賴不要依賴它的阻塞行為，統一用 stream/event。

`cudaMemcpyPeerAsync` 只有一個 stream 參數，官方沒有定義這個 stream 屬於源 GPU 還是目標 GPU，也沒有說它同時給兩個裝置排序。正確做法是用 event 建依賴：生產者在自己的 stream 上 record，複製 stream 上 `cudaStreamWaitEvent`，複製完成後再 record 給消費者。`cudaEventRecord` 要求 event 和 stream 屬於同一 device，`cudaStreamWaitEvent` 可以跨 device。

## 4. 裝置側 DMA：NIC、NVMe、DPU 與 CXL

| 路徑           | 誰發起搬運                       | 目標                               | 關鍵前提                                               |
| -------------- | -------------------------------- | ---------------------------------- | ------------------------------------------------------ |
| GPU → host     | GPU copy engine                  | pinned host buffer                 | pageable 需要 staging                                  |
| GPU → GPU      | GPU copy engine 或 SM load/store | peer HBM                           | peer access、拓撲、PCIe/NVLink                         |
| NIC → GPU      | NIC DMA engine                   | GPU BAR1/顯存                      | 同一 upstream root complex、IOMMU 關閉或 1:1、驅動支援 |
| NVMe → GPU     | NVMe 控制器 DMA                  | GPU 顯存                           | nvidia-fs/P2PDMA、BAR1 aperture、對齊                  |
| DPU → host/GPU | DPU DMA engine                   | host 或 DPU 記憶體；GPU 需 GPUDirect | DOCA DMA API、版本和映射                               |
| GPU → CXL      | GPU copy engine 或 SM load/store | CXL 共享記憶體                       | CXL BAR/DAX、P2P、GPU 映射                             |

### 4.1 GPUDirect RDMA

GPUDirect RDMA 讓 NIC 透過 PCIe 讀寫 GPU BAR1，把 GPU 顯存當作對端裝置記憶體。它要求 NIC 和 GPU 共享 upstream PCI root complex；IOMMU 需要關閉或配置成 1:1 passthrough；`nvidia-peermem` 是 InfiniBand/RoCE 路徑上把 GPU 頁固定並暴露給 NIC 的橋接模組，其他驅動可以直接使用 `nvidia_p2p_*` API。

這條路徑的控制面仍由 CPU 驅動完成，資料面由 NIC 的 DMA engine 執行。CUDA 側的同步 API 負責記憶體序，應用不能只看“DMA 完成中斷”就假設 GPU 一定看到了完整資料。

### 4.2 GPUDirect Storage

GPUDirect Storage 讓 NVMe 控制器把資料直接 DMA 到 GPU 顯存，繞過 CPU 記憶體裡的 bounce buffer。控制路徑仍然經過 CPU 上的 VFS 和驅動；資料路徑可以經過 CPU root port，但不經過 CPU memory。`nvidia-fs.ko` 負責 GPU 虛擬地址到實體地址的回撥和 DMA 映射。CUDA 12.8 以后，受支持的 NVMe 配置可以走 Linux 核心的 P2PDMA 基礎設施（例如 Ubuntu 6.2+、OpenRM 570+），不再依賴 `nvidia-fs.ko` 或定制的 `nvme.ko`；非 NVMe 掛載和更早版本仍走原有路徑。

這裡有幾個常見誤寫。O_DIRECT 是常見的直通條件，但 CUDA 12.2 以後對頁對齊 buffer 有例外；直接傳輸也不是永遠可行，超過 BAR1 aperture、地址不對齊或檔案系統不支援時會回退。GDS 不是“只要開啟就 2 倍頻寬”，NVIDIA 的口徑是部分系統上可能達到傳統路徑的兩倍，不能外推成通用數字。

### 4.3 DPU 的 DMA

DOCA DMA 提供 `doca_dma_task_memcpy`、`doca_mmap`、`doca_task_submit` 等 API，在 host 記憶體、DPU 本地記憶體之間做硬體加速複製，任務和事件可以非同步提交。GPU 顯存不是 DPU 的普通本地 buffer，仍然需要 GPUDirect 路徑。DOCA 的版本和可用的 memory region 類型要看對應版本文件，文章不把 DPU 內部 descriptor 或引擎數量寫成公開事實。

### 4.4 GPU → CXL

CXL Type-3 記憶體可以以 PCIe BAR 或 DAX 形式暴露。GPU 側完成地址對映後，kernel load/store 或 `cudaMemcpy` 可以直接讀寫。多張 GPU 對映同一個 CXL BAR 時，一張卡寫入的資料可以被另一張卡讀取，不需要 CPU memory 中轉。

它適合做共享 KV Cache 池或容量層，不適合替代本地 HBM：CXL 的延遲和頻寬通常低於 HBM，且依賴 CXL 裝置、PCIe P2P/ACS 和驅動支援。這裡只把它作為“裝置側 DMA 到共享記憶體”的一個例子，不展開裝置配置。

![常見 DMA 路徑與 CXL](assets/dma-engine-03-paths.png)

_圖 3：GPU copy engine、SM copy、NIC DMA、NVMe/DPU DMA 的路徑與邊界；CXL 是另一類共享記憶體目標。_

## 5. 性能：頻寬、延遲與併發

DMA engine 的效能沒有單一數字。它受 PCIe/NVLink 代際和 lane 數、拓撲、transfer size、engine 數量、stream/work queue、IOMMU/ACS 以及目標記憶體的頻寬共同影響。下面這些倉庫數字只能作為量級參考，不能跨平台橫向比較：

| 場景                   | 數字                    | 口徑                                    |
| ---------------------- | ----------------------- | --------------------------------------- |
| A100 NVLink P2P        | 239.28 GB/s             | `simpleP2P`，64 MB，單向                |
| A100 CPU relay         | 11.76 GB/s              | 128 MB 往返測試的每方向等效速率         |
| A100 copy engine vs SM | ~818 GB/s vs ~1453 GB/s | HBM D2D 測試，分別約佔峰值的 40% 和 71% |
| 兩台 H100 節點 GDR     | ~23 GB/s                | 跨節點 RDMA 驗證，網路和拓撲相關        |

copy engine 的數字不能當作 HBM 峰值。它說明 D2D 複製經過 engine 后，有效頻寬可能只有 SM copy 的一部分；但不同 buffer 大小、方向和測試方法會改變結論。小傳輸的固定開銷佔比高，官方建議合併小傳輸；是否該用 copy engine、SM copy 還是 CPU copy，要在目標平台實測。

診斷時至少看三層：`nvidia-smi topo -m` 和 `nvidia-smi topo -p2p r` 看拓撲；`nvidia-smi dmon -s pucv` 看 PCIe 吞吐；nsys 的 `cuda_gpu_mem_time_sum` 看複製時間線；需要看單個 kernel 的訪存效率時再用 ncu。`asyncEngineCount` 只能告訴你潛在引擎數量，實際是否並行要以時間線為準。

## 6. 常見誤解與怎麼選

| 誤解                                    | 更準確的說法                                                       |
| --------------------------------------- | ------------------------------------------------------------------ |
| zero-copy 就沒有 DMA                    | zero-copy 通常指去掉 CPU bounce buffer，DMA 仍然存在               |
| P2P 就沒有複製                          | P2P 可以是 copy engine 複製，也可以是 kernel 直接 load/store       |
| `cudaMemcpyAsync` 就是 copy engine 複製 | 官方只承諾複製語義，具體走 CE、NVLink 還是其他路徑由平台和驅動決定 |
| pageable 記憶體不能非同步                   | pageable 不保證 host 非同步，驅動可能 staging 並同步                 |
| GDS 一定繞過 CPU、一定有 2 倍頻寬       | 控制面仍走 CPU；資料面可能經過 root port；直通和收益都受平台限制   |
| ACS 一開就一定不能用 P2P                | ACS 會重定向流量，影響程度取決於拓撲和配置                         |

選擇時先問四個問題：

1. 資料從哪到哪：host、GPU、NIC、NVMe、DPU，還是 CXL 共享記憶體？
2. 誰有 DMA engine，目標記憶體是否對該 engine 可見？
3. 地址怎麼翻譯：IOMMU、GPU 頁表、BAR1、P2PDMA 還是 CXL 映射？
4. 完成和可見性誰負責：stream/event、CUDA sync、`dma_sync_*`，還是驅動回撥？

這四個問題答完，再決定用 `cudaMemcpyAsync`、kernel load/store、GPUDirect RDMA、GDS、DOCA DMA 還是 CXL 共享記憶體對映。API 只是最後一層，engine、地址和完成語義才是決定效能與正確性的部分。

![路徑選擇](assets/dma-engine-04-selection.png)

_圖 4：先問資料從哪到哪，再決定 engine、地址和同步方式。_

## 源文件索引

### Linux 與 PCIe

| 資料                                                                                                                                  | 內容                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| [Linux DMA-API](https://docs.kernel.org/core-api/dma-api.html)                                                                        | DMA/bus address、coherent/streaming 記憶體、`dma_sync_*`       |
| [Linux DMA-API-HOWTO](https://docs.kernel.org/core-api/dma-api-howto.html)                                                            | bus address 與 CPU 虛擬地址的區別、對映與所有權              |
| [Linux DMA engine provider](https://docs.kernel.org/driver-api/dmaengine/provider.html)                                               | descriptor/SG、`issue_pending`、完成回撥；強調硬體相關格式   |
| [Linux PCI P2PDMA](https://docs.kernel.org/driver-api/pci/p2pdma.html)                                                                | P2PDMA、ACS、跨 hierarchy domain、whitelist                  |
| [Linux PCI 驅動文件](https://docs.kernel.org/PCI/pci.html)                                                                            | MMIO posted write 與讀回 flush                               |
| [NVMe Base Specification 2.0e](https://nvmexpress.org/wp-content/uploads/NVM-Express-Base-Specification-2.0e-2024.07.29-Ratified.pdf) | Submission/Completion Queue、doorbell、completion 的典型實現 |

### CUDA 與 GPUDirect

| 資料                                                                                                                                                       | 內容                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [CUDA Programming Guide: Multi-GPU Systems](https://docs.nvidia.com/cuda/cuda-programming-guide/03-advanced/multi-gpu-systems.html)                        | peer access、copy engine/NVLink、ACS 與 IOMMU                 |
| [CUDA Programming Guide: Page-Locked Host Memory](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-c-programming-guide/index.html#page-locked-host-memory) | pinned memory 與非同步傳輸                                      |
| [CUDA Runtime API: API Synchronization Behavior](https://docs.nvidia.com/cuda/cuda-runtime-api/api-sync-behavior.html)                                     | pageable/pinned、H2D/D2H/D2D 的同步語義                       |
| [GPUDirect RDMA](https://docs.nvidia.com/cuda/gpudirect-rdma/index.html)                                                                                   | BAR1、同一 root complex、IOMMU、`nvidia-peermem`、CUDA 記憶體序 |
| [GPUDirect Storage Overview](https://docs.nvidia.com/gpudirect-storage/overview-guide/index.html)                                                          | NVMe 到 GPU 的 DMA、bounce buffer、BAR1 與回退條件            |
| [GPUDirect Storage Release Notes](https://docs.nvidia.com/gpudirect-storage/release-notes/index.html)                                                      | 支援矩陣、GDS 模式與相容模式                                  |
| [DOCA DMA](https://docs.nvidia.com/doca/sdk/DOCA-DMA/index.html)                                                                                           | DPU 側 DMA API、buffer 與非同步任務                             |
| [CXL Consortium](https://computeexpresslink.org/)                                                                                                          | CXL Type-3 memory、BAR/DAX 與記憶體語義                         |

### 倉庫內文章與實測

- [GPU 記憶體管理](../../02_gpu_programming/02_cuda/12_gpu_memory_management.md)：pinned/pageable、GDS 鏈條與記憶體層級。
- [GPU 訪問系統記憶體](../../02_gpu_programming/02_cuda/19_gpu_system_memory_access.md)：MMU/IOMMU/MMIO/mmap/ioremap 與五條路徑。
- [GPU 顯存互訪](../../02_gpu_programming/02_cuda/20_gpu_peer_memory_access.md)：peer access、cudaIpc、VMM 與 P2P 順序。
- [Multi-GPU CUDA 程式設計](../../02_gpu_programming/02_cuda/15_multi_gpu_programming.md)：P2P memcpy、NCCL 與拓撲。
- [GPU P2P 頻寬實測](../../02_gpu_programming/04_profiling/08_p2p_bandwidth.md)：A100 `simpleP2P` 239.28 GB/s，64 MB 單向。
- [GPU 間資料傳輸方法實測](../../02_gpu_programming/04_profiling/09_gpu_transfer_methods.md)：A100 128 MB 往返口徑，CPU relay 11.76 GB/s。
- [HBM 頻寬測試](../../02_gpu_programming/04_profiling/03_hbm_bandwidth_test.md)：A100 copy engine ~818 GB/s、SM ~1453 GB/s。
- [GPUDirect RDMA 跨節點驗證](../../01_hardware_architecture/gpudirect/04_gpudirect_rdma_verification.md)：兩台 H100 節點單向 ~23 GB/s。
