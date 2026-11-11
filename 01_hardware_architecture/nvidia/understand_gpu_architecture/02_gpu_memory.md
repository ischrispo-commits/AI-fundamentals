# GPU Memory (GPU 記憶體)

**原文：[Cornell University -> Cornell Virtual Workshop -> Understanding GPU Architecture -> GPU Memory](https://cvw.cac.cornell.edu/gpu-architecture/gpu-memory/index)**

Just like a CPU, the GPU relies on a memory hierarchy—from RAM, through cache levels—to ensure that its processing engines are kept supplied with the data they need to do useful work. And just like the cores in a CPU, the streaming multiprocessors (SMs) in a GPU ultimately require the data to be in registers to be available for computations. This topic looks at the sizes and properties of the different elements of the GPU's memory hierarchy and how they compare to those found in CPUs.

就像 CPU 一樣，GPU 依賴於記憶體層次結構——從 RAM 到各級快取——以確保其處理引擎能夠持續獲得資料以進行有用工作。就像 CPU 中的核心一樣，GPU 中的流式多處理器（SMs）最終也需要資料位於暫存器中才能用於計算。本主題探討了 GPU 記憶體層次結構中不同元素的大小和屬性，以及它們與 CPU 中發現的元素的比較。

## Memory Levels（記憶體級別）

Compared to a CPU core, a streaming multiprocessor (SM) in a GPU has many more registers. For example, an SM in the NVIDIA Tesla V100 has 65536 registers in its register file. Taken as a whole, its register file is larger in terms of its total capacity, too, despite the fact that the SM's 4-byte registers hold just a single float, whereas the vector registers in an Intel AVX-512 core hold 16 floats.

與 CPU 核心相比，GPU 中的流式多處理器（SM）擁有更多的暫存器。例如，NVIDIA Tesla V100 中的 SM 擁有 65536 個暫存器在其暫存器檔案中。總體而言，儘管 SM 的 4 位元組暫存器僅儲存一個浮點數，而 Intel AVX-512 核心的矢量寄存器可以保存 16 個浮點數，但其暫存器檔案在總容量上仍然更大。

But CPUs have an advantage in total cache size. Every Intel CPU core comes with L1 and L2 data caches, and the size of these caches plus its share of the shared L3 cache is easily larger than the equivalent caches in a GPU, which has nothing beyond a shared L2 cache. The figure shows the full picture of the memory hierarchy in the Tesla V100. The roles of the different caches and memory types are explained on the [Memory Types](#Memory_Types).

但 CPU 在總快取大小上有優勢。每個 Intel CPU 核心都帶有 L1 和 L2 資料快取，這些快取的大小加上其共享的 L3 快取的份額，很容易就比 GPU 中的等效快取大，GPU 除了共享的 L2 快取之外沒有其他快取。下圖展示了 Tesla V100 的完整記憶體層次結構。不同快取和記憶體類型的作用在“記憶體類型”中進行了解釋。

![GPU memory levels and sizes for the NVIDIA Tesla V100](img/GPUMemLevels.png)

GPU memory levels and sizes for the NVIDIA Tesla V100.
(Based on diagrams by NVIDIA and Citadel at GTC 2018)

Arrows in the above diagram show how the layers of memory are linked together. Depending on where the data start, they may have to hop through several layers of cache to enter the registers of an SM and become accessible to the CUDA cores. Global memory (including areas for local, texture, and constant memory) is by far the largest layer, but it is also furthest from the SMs.

上圖中的箭頭顯示了記憶體層是如何相互連線的。根據資料的起始位置，它們可能需要透過幾個快取層才能進入 SM 的暫存器併成為 CUDA 核心可訪問的資料。全域記憶體（包括局部、紋理和常量記憶體區域）是迄今為止最大的層，但它也距離 SM 最遠。

Clearly it would be favorable for 4-byte operands to travel together in groups of 32 as they move back and forth between caches and registers and CUDA cores. Why? A 32-wide group is exactly right to supply a warp of 32 threads, all at once. Therefore, it makes perfect sense that the size of the cache line in a GPU is 32 x (4 bytes) = 128 bytes.

顯然，對於 4 位元組的運算元來說，當它們在快取和暫存器以及 CUDA 核心之間來回移動時，以 32 組的形式一起移動是有利的。為什麼？一個 32 寬的組正好可以一次性供應一個包含 32 個執行緒的 warp。因此，GPU 中的快取行大小是 32 x (4 位元組) = 128 位元組是完全合理的。

Notice that data transfers onto and off of the device are mediated by the L2 cache. In most cases, the incoming data will proceed from the L2 into the large global memory of the device.

請注意，資料傳輸到裝置上和從裝置傳輸出去都是由 L2 快取介導的。在大多數情況下，傳入的資料將從 L2 進入裝置的大容量全域記憶體。

## <span id="Memory_Types">Memory Types(記憶體類型)</span>

The picture on the preceding page is more complex than it would be for a CPU, because the GPU reserves certain areas of memory for specialized use during rendering. Here, we summarize the roles of each type of GPU memory for doing GPGPU computations.

前一頁的圖比 CPU 的情況要複雜，因為 GPU 為渲染過程中的專門使用預留了某些記憶體區域。這裡，我們總結了每種類型的 GPU 記憶體在進行 GPGPU 計算時的作用。

The first list covers the on-chip memory areas that are closest to the CUDA cores. They are part of every SM.

第一個列表涵蓋了最接近 CUDA 核心的片上記憶體區域。它們是每個 SM 的一部分。

* **Register File** - denotes the area of memory that feeds directly into the CUDA cores. Accordingly, it is organized into 32 _banks_, matching the 32 threads in a warp. Think of the register file as a big matrix of 4-byte elements, having many rows and 32 columns. A warp operates on full rows; within a given row, each thread (CUDA core) operates on a different column (bank).
* **L1 Cache** - refers to the usual on-chip storage location providing fast access to data that are recently read from, or written to, main memory (RAM). Additionally, L1 serves as the overflow region when the amount of active data exceeeds what an SM's register file can hold, a condition which is termed "register spilling". In L1, the cache lines and spilled registers are organized into banks, just as in the register file.
* **Shared Memory** - is a memory area that physically resides in the same memory as the L1 cache, but differs from L1 in that all its data may be accessed by any thread in a thread block. This allows threads to communicate and share data with each other. Variables that occupy it must be declared explicitly by an application. The application can also set the dividing line between L1 and shared memory.
* **Constant Caches** - are special caches pertaining to variables declared as read-only constants in global memory. Such variables can be read by any thread in a thread block. The main and best use of these caches is to broadcast a single constant value to all the threads in a warp.

* **寄存器文件** - 表示直接進入 CUDA 核心的記憶體區域。相應地，它被組織成 32 個銀行，與一個 warp 中的 32 個執行緒相匹配。將暫存器檔案視為一個由 4 位元組元素組成的大矩陣，有很多行和 32 列。一個 warp 在完整的行上操作；在給定的行中，每個執行緒（CUDA 核心）在不同的列（銀行）上操作。

* **L1 快取** - 指的是通常的片上儲存位置，提供對最近從主記憶體（RAM）讀取或寫入的資料的快速訪問。此外，當活動資料量超過 SM 的暫存器檔案可以容納的量時，L1 還充當溢位區域，這種情況被稱為“寄存器溢出”。在 L1 中，快取行和溢位的暫存器被組織成銀行，就像暫存器檔案一樣。

* **共享記憶體** - 是一個物理上位於與 L1 快取相同的記憶體中的記憶體區域，但它與 L1 不同，因為它的所有資料都可以被一個執行緒塊中的任何執行緒訪問。這允許執行緒相互通訊和共享資料。佔用它的變數必須由應用程式顯式宣告。應用程式還可以設定 L1 和共享記憶體之間的分界線。

* **常量快取** - 是專門用於全域記憶體中宣告為只讀常量的變數的特殊快取。這些變數可以被執行緒塊中的任何執行緒讀取。這些快取的主要和最佳用途是將單個常量值廣播到 warp 中的所有執行緒。

The second list pertains to the more distant, larger memory areas that are shared by all the SMs.

第二個列表涉及更遙遠、更大的記憶體區域，這些區域由所有 SM 共享。

* **L2 Cache** - is a further on-chip cache for retaining copies of the data that travel back and forth between the SMs and main memory. Like the L1, the L2 cache is intended to speed up subsequent reloads. But unlike the L1 cache(s), there is just one L2 that is shared by all the SMs. The L2 cache is also situated in the path of data moving on or off the device via PCIe or NVLink.
* **Global Memory** - represents the bulk of the main memory of the device, equivalent to RAM in a CPU-based processor. For performance reasons, the Tesla V100 has special HBM2 high-bandwidth memory, while the Quadro RTX 5000 has fast GDDR6 graphics memory.
* **Local Memory** - corresponds to specially mapped regions of main memory that are assigned to each SM. Whenever "register spilling" overflows the L1 cache on a particular SM, the excess data are further offloaded to L2, then to "local memory". The performance penalty for reloading a spilled register becomes steeper for every memory level that must be traversed in order to retrieve it.
* **Texture and Constant Memory** - are regions of main memory that are treated as read-only by the device. When fetched to an SM, variables with a "texture" or "constant" declaration can be read by any thread in a thread block, much like shared memory. Texture memory is cached in L1, while constant memory is cached in the constant caches.

* **L2 快取** - 是一個進一步的片上快取，用於保留在 SM 和主記憶體之間來回傳輸的資料的副本。像 L1 一樣，L2 快取旨在加速後續的重新載入。但與 L1 快取不同，只有一個 L2 被所有 SM 共享。L2 快取也位於透過 PCIe 或 NVLink 在裝置上或下移動的資料的路徑上。

* **全域記憶體** - 代表裝置的大部分主記憶體，相當於基於 CPU 的處理器中的 RAM。出於效能原因，Tesla V100 擁有特殊的 HBM2 高頻寬記憶體，而 Quadro RTX 5000 擁有快速的 GDDR6 圖形記憶體。

* **區域性記憶體** - 對應於分配給每個 SM 的主記憶體的特定對映區域。每當“寄存器溢出”溢出特定 SM 的 L1 快取時，超出的資料會被進一步解除安裝到 L2，然后是“區域性記憶體”。重新載入溢位暫存器的效能懲罰隨著必須遍歷的每個記憶體級別而變得更加嚴重。

* **紋理和常量記憶體** - 是被視為裝置只讀的記憶體區域。當它們被傳輸到 SM 時，具有“紋理”或“常量”宣告的變數可以被執行緒塊中的任何執行緒讀取，就像共享記憶體一樣。紋理記憶體被快取在 L1 中，而常量記憶體被快取在常量快取中。

## <span id="comparison_cpu_mem">Comparison to CPU Memory(與 CPU 記憶體對比)</span>

The organization of memory in a GPU largely resembles a CPU's—but there are significant differences as well. This is particularly true of the total capacities available at each level of the memory hierarchy. As mentioned previously, the GPU is characterized by very large register files, while the CPU is much more cache-heavy and has generally wider data paths.

GPU 的記憶體組織在很大程度上類似於 CPU 的，但也存在顯著差異。這在記憶體層次結構的每個級別上可用的總容量上尤為明顯。如前所述，GPU 的特點是非常大的暫存器檔案，而 CPU 更多地依賴快取，並且通常具有更寬的資料路徑。

The table below makes a comparison between the memory hierarchies found in the NVIDIA GPUs in TACC's Longhorn system and the Intel Xeon CPUs in TACC's Frontera and Stampede2 systems. In each row, the entry shown in bold highlights the type of device that has the bigger capacity _per computational unit_ at that level.

下表比較了 TACC 的 Longhorn 系統中的 NVIDIA GPU 和 TACC 的 Frontera 和 Stampede2 系統中的 Intel Xeon CPU 的記憶體層次結構。在每一行中，加粗的條目突出顯示了在該級別上每個計算單元可用的更大容量的裝置類型。

Available memory per SM or core at each level in the memory hierarchy of the NVIDIA Tesla V100 vs. Intel Xeon SP processors.

NVIDIA Tesla V100 與 Intel Xeon SP 處理器的每個記憶體層次結構級別的每個 SM 或核心可用記憶體。

| **Memory Type** | **NVIDIA Tesla V100<br>- per SM -** | **Intel Cascade Lake SP, Skylake SP<br>- per core -** |
|---|---|---|
| **Register file** | 256 kB | 10.5 kB |
| **L1 cache** | 128 kB (max) | 32 kB |
| **Constant caches** | 64 kB | - N/A - |
| **L2 cache** | 0.075 MB | 1 MB |
| **L3 cache** | - N/A - | 1.375 MB |
| **Global or RAM** | 0.4 GB | >3.4 GB |

Since the table compares what is available to a single GPU SM to the equivalent for a single CPU core, the processor-wide memory levels are treated as though they are distributed evenly among all the SMs or cores. A more precise comparison might break down these computational units even further and look at the sizes of the memory slices that pertain to a GPU CUDA core vs. a CPU vector lane. For those interested, this approach is pursued in the [Appendix](#Appendix).

由於表格比較的是一個 GPU SM 與一個 CPU 核心的等效情況，因此將處理器範圍的記憶體級別視為均勻分佈在所有 SM 或核心之間。更精確的比較可能會進一步細分這些計算單元，並檢視與 GPU CUDA 核心相關的記憶體切片的大小與 CPU 矢量通道的大小。對於感興趣的人，這種方法在附錄中進行了探討。

The memory levels do not match up exactly because in the Xeon processors, every core has a private L2 cache plus a slice of the shared L3, while in the V100 GPU, every SM has special constant caches, but no caches beyond a slice of the shared L2. Generally, though, the table shows that the GPU has the greater concentration at the closest memory levels, while the CPU has an evident size advantage as one moves further out in memory.

記憶體級別並不完全匹配，因為在 Xeon 處理器中，每個核心都有一個私有的 L2 快取加上共享的 L3 的一部分，而在 V100 GPU 中，每個 SM 都有特殊的常量快取，但沒有超出共享的 L2 的快取。通常，表格顯示 GPU 在最接近的記憶體級別上有更大的集中度，而 CPU 在記憶體向外移動時有明顯的尺寸優勢。

In considering memory _speed_, the roles of GPUs and CPUs become reversed. Latency and bandwidth are two relevant measures of memory speed. The next table shows that the Intel Xeon CPUs feature superior latencies for the caches that are closest to the cores, while the Tesla V100 has an edge in bandwidth at the more distant, global memory level.

在考慮記憶體速度時，GPU 和 CPU 的角色發生了逆轉。延遲和頻寬是衡量記憶體速度的兩個相關指標。下一個表格顯示，Intel Xeon CPU 的最近核心的快取具有更優越的延遲，而 Tesla V100 在更遙遠的全域記憶體級別上具有頻寬優勢。

Latency and available bandwidth per SM or core at each level in the memory hierarchy of the NVIDIA Tesla V100 vs. Intel Xeon SP processors.

NVIDIA Tesla V100 與 Intel Xeon SP 處理器的每個記憶體層次結構級別的每個 SM 或核心的延遲和可用頻寬。

| **Memory Type** | **NVIDIA Tesla V1001[[1](#ref1)]<br>- per SM -** | **Intel Cascade Lake SP, Skylake SP[[2](#ref2)]<br>- per core -** |
|---|---|---|
| **Latency** | Bandwidth | Latency | Bandwidth |
| **L1 cache** | 28 cycles | 128 B/cycle | 4 cycles | 192 B/cycle |
| **Private L2 cache** | - N/A - | - N/A - | 14 cycles | 64 B/cycle |
| **Shared L2 or L3** | 193 cycles | 17.6 B/cycle | 50-70 cycles | 14.3 B/cycle |
| **Global or RAM** | 220-350 cycles | 7.4 B/cycle | 190-220 cycles | 1.9-2.5 B/cycle |

Latencies are not stated for registers because latency is dependent on the particular instruction being executed, not on data movement. Likewise, bandwidth is not an appropriate metric for registers; instead, one speaks of instruction throughput, which may reach or exceed one per cycle (if the pipelines of operands are kept full).

沒有為暫存器宣告延遲，因為延遲取決於正在執行的特定指令，而不是資料移動。同樣，頻寬不是暫存器的適當指標；相反，人們談論的是指令吞吐量，它可能達到或超過每個週期一個（如果運算元的管道保持滿）。

Despite the impressive bandwidth of the GPU's global memory, reads or writes from individual threads have high read/write latency. The SM's shared memory and L1 cache can be used to avoid the latency of direct interactions with with DRAM, to an extent. But in GPU programming, the best way to avoid the high latency penalty associated with global memory is to launch very large numbers of threads. That way, at least one warp is able to grab its next instruction from the instruction buffer and go, whenever another warp is stalled waiting for data. This technique is known as _latency hiding_.

儘管 GPU 的全域記憶體頻寬令人印象深刻，但來自個別執行緒的讀寫操作具有很高的讀寫延遲。SM 的共享記憶體和 L1 快取可以在一定程度上避免與 DRAM 直接互動的延遲。但在 GPU 程式設計中，避免與全域記憶體相關的高延遲懲罰的最佳方法是啟動大量的執行緒。這樣，每當另一個 warp 因等待資料而停滯時，至少有一個 warp 能夠從指令緩衝區獲取其下一個指令並繼續執行。這種技術被稱為 _延遲隱藏_。

> 譯註：原文此句寫作 "direct interactions with with DRAM"，"with" 重複，系原文排版筆誤，譯文按原意（與 DRAM 的直接交互）譯出。

Effectively, there is one additional layer of memory that ought to be considered for a GPU: the memory of the host. The need to transfer data between the host and the GPU can place a heavy constraint on the GPU's overall performance—particularly if the GPU is attached to the host via PCIe. Ideally, once the necessary data are transferred to the GPU, they remain there for computations as much as possible.

實際上，對於 GPU 來說，還有一個額外的記憶體層應該被考慮：主機的記憶體。主機和 GPU 之間傳輸資料的需求可能會嚴重限制 GPU 的整體效能——特別是如果 GPU 透過 PCIe 連線到主機的話。理想情況下，一旦將必要的資料傳輸到 GPU，它們就儘可能地保留在那裡進行計算。

Since the latency cost for communicating data to and from the GPU is relatively high, data should be sent in big chunks or batches. Furthermore, different batches may be sent over separate _streams_, so that computation can begin on some batches while others are in transit. CUDA provides techniques for using streams to overlap computation with communication.

由於與 GPU 通訊資料的延遲成本相對較高，因此應該以大塊或批次傳送資料。此外，不同的批次可以透過不同的流傳送，以便在某些批次在傳輸時開始計算。CUDA 提供了使用流來重疊計算和通訊的技術。

In the next section, we will continue to dig into the unique properties of the specific NVIDIA GPU devices that are incorporated into Frontera and contemporary HPC systems.

在下一節中，我們將繼續深入探討 Frontera 和當代 HPC 系統中整合的特定 NVIDIA GPU 裝置的獨特屬性。

<span id="ref1">1</span>. Reference for Tesla V100 data: Z. Jia et al., [Dissecting the NVIDIA Volta GPU Architecture via Microbenchmarking](https://arxiv.org/pdf/1804.06826.pdf), Tables 3.1, 3.2, and 3.4, and Fig. 3.12. Theoretical peak rates are shown above; if the peak rate is unknown, the measured value is shown instead. Global bandwidths for the V100, such as 2155 GB/s for the L2 cache bandwidth, are converted to B/cycle/SM by dividing by 1.53 GHz and 80 SMs. (Note, the L1 "upper bound" rate in Table 3.2 of the reference is incorrect and should be computed by the formula in the accompanying text, i.e., LSUs\*bytes.) - Tesla V100 資料參考：Z. Jia 等人，透過微基準測試解剖 NVIDIA Volta GPU 架構，表 3.1、3.2 和 3.4，以及圖 3.12。上面顯示的是理論峰值速率；如果峰
值速率未知，則顯示測量值。V100 的全域性頻寬，如 L2 快取頻寬的 2155 GB/s，透過除以 1.53 GHz 和 80 個 SM 轉換為 B/cycle/SM。（注意，參考表 3.2 中的 L1 “上限”速率是不正確的，應該使用隨附文字中的公式計算，即 LSUs \* 位元組。）

<span id="ref2">2</span>. The memory hierarchies of [Cascade Lake](https://en.wikichip.org/wiki/intel/microarchitectures/cascade_lake#Memory_Hierarchy) and [Skylake](https://en.wikichip.org/wiki/intel/microarchitectures/skylake_(server)#Memory_Hierarchy) are identical up to RAM, according to WikiChip. Published data puts the minimum RAM latency of [Cascade Lake](https://images.anandtech.com/doci/16594/ICX_briefing_51.png) at 81 nsec and [Skylake](https://www.anandtech.com/show/11544/intel-skylake-ep-vs-amd-epyc-7000-cpu-battle-of-the-decade/13) at 90 nsec; these values are converted to cycles by multiplying by 2.7 GHz and 2.1 GHz, respectively. The L3 bandwidth is taken to be the 30 GB/s asymptote seen in Fig. 3 of [Hammond, Vaughn, and Hughes (2018)](https://www.osti.gov/biblio/1515123), normalized by 2.1 GHz for their Xeon 8160 (same model as in Stampede2); the result should apply to Cascade Lake as well. The RAM bandwidths assume that all 6 channels are populated with the maximum [2933 MT/s DDR4](https://en.wikipedia.org/wiki/DDR4_SDRAM) for Cascade Lake or [2666 MT/s DDR4](https://en.wikipedia.org/wiki/DDR4_SDRAM) for Skylake; the global results are then divided by the number of cores per chip, either 28 for Cascade Lake or 24 for Skylake, and normalized by the same frequencies as above (to match [Frontera](https://frontera-portal.tacc.utexas.edu/user-guide/system/#cascade-lake-clx-compute-nodes) and [Stampede2](https://portal.tacc.utexas.edu/user-guides/stampede2#overview-skxcomputenodes), respectively). - 根據 WikiChip，Cascade Lake 和 Skylake 的記憶體層次結構直到 RAM 都是相同的。釋出的資料顯示 Cascade Lake 的最小 RAM 延遲為 81 納秒，Skylake 為 90 納秒；這些值透過乘以 2.7 GHz 和 2.1 GHz 分別轉換為週期。L3 頻寬取自 Hammond、Vaughn 和 Hughes（2018 年）圖 3 中看到的 30 GB/s 漸近值，按 2.1 GHz 歸一化，適用於他們的 Xeon 8160（與 Stampede2 中的型號相同）；結果應該也適用於 Cascade Lake。RAM 頻寬假設所有 6 個通道都裝滿了最大 2933 MT/s DDR4 對於 Cascade Lake 或 2666 MT/s DDR4 對於 Skylake；全域性結果然後除以每個晶片的核心數，分別是 28 個對於 Cascade Lake 或 24 個對於 Skylake，並透過上述相同的頻率歸一化（以匹配 Frontera 和 Stampede2）。

## <span id="Appendix">Appendix: Finer Memory Slices(附錄：更細的記憶體切片)</span>

The table [in the main text](#comparison_cpu_mem) illuminates the per-SM or per-core capacities that pertain to different memory levels. However, it is perhaps fairer to look at how large a slice of each memory type is available to a single CUDA core in a GPU, vs. a single vector lane in a CPU. We again take the NVIDIA Tesla V100 and a couple of contemporary Intel Xeon server-grade processors as the examples.

正文中的表格闡明瞭與不同記憶體級別相關的每個 SM 或每個核心的容量。然而，也許更公平地看待的是，查看 GPU 中的單個 CUDA 核心與 CPU 中的單個向量通道可用的每種記憶體類型的切片有多大。我們再次以 NVIDIA Tesla V100 和一些當代 Intel Xeon 伺服器級處理器為例。

1. **_Register file._** In the NVIDIA Tesla V100, the register file of an SM stores (65536)/(2x32) = 1024 floats per CUDA core. In the Intel Cascade Lake and Skylake chips, a [CPU core](https://en.wikichip.org/wiki/intel/microarchitectures/cascade_lake#Individual_Core) has a [physical register file](https://travisdowns.github.io/blog/2020/05/26/kreg2.html#the-register-files) that stores [168 vector registers](https://en.wikichip.org/wiki/intel/microarchitectures/skylake_(server)#Scheduler_.26_512-SIMD_addition) of 64B, or 10.5 kB in total. This works out to (16x168)/(2x16) = 84 floats per vector lane, which is an order of magnitude _less_ than what is available to a CUDA core. (The factors of 2 appear because a CPU core can handle 2x16-float vectors/cycle, and a GPU SM can handle 2x32-float warps/cycle.) - **_寄存器文件。_** 在 NVIDIA Tesla V100 中，SM 的暫存器檔案儲存 (65536)/(2x32) = 1024 個每個 CUDA 核心的浮點數。在 Intel Cascade Lake 和 Skylake 芯片中，CPU 核心有一個物理暫存器檔案，儲存 168 個 64B 的矢量寄存器，總共 10.5 kB。這相當於 (16x168)/(2x16) = 84 個每個向量通道的浮點數，這比 CUDA 核心可用的少一個數量級。（2 的因子是因為 CPU 核心可以處理 2x16-float 向量/周期，GPU SM 可以處理 2x32-float warps/周期。）

2. **_Cache sizes._** In the NVIDIA Tesla V100, an SM has 128 kB (max) in its L1 data cache, and 64 kB in its constant cache. Adding these to its share of the 6 MB shared L2 (6/80 = 0.075 MB) yields 0.26 MB per SM, or 0.0041 MB per CUDA core. In the Intel Cascade Lake and Skylake chips, a CPU core has 32 kB in its L1 plus 1 MB in its L2 data cache. Adding these to its share of the shared L3 cache (1.375 MB) yields 2.4 MB, or 0.75 MB per vector lane, which is _two_ orders of magnitude _more_ than what is available to a CUDA core. - **_快取大小。_** 在 NVIDIA Tesla V100 中，SM 在其 L1 資料快取中有 128 kB（最大）和在其常量快取中有 64 kB。將這些新增到其共享的 6 MB L2（6/80 = 0.075 MB）中，每個 SM 有 0.26 MB，或者每個 CUDA 核心有 0.0041 MB。在 Intel Cascade Lake 和 Skylake 芯片中，CPU 核心在其 L1 中有 32 kB，在其 L2 資料快取中有 1 MB。將這些新增到其共享的 L3 快取（1.375 MB）中，得到 2.4 MB，或者每個向量通道有 0.75 MB，這比 CUDA 核心可用的多兩個數量級。

3. **_Cache lines._** In any GPU, the 128-byte cache lines consist of four 32-byte sectors. In the event of a cache miss, not all 4 sectors in the cache line have to be filled, just the ones that need updating. This means that 4 sectors from 4 different cache lines can be fetched just as readily as 1 full cache line. The [32-byte sector size persists today](https://forums.developer.nvidia.com/t/pascal-l1-cache/49571/20), even though the Volta's HBM2 memory has a 64-byte interface. By contrast, in an Intel Cascade Lake or Skylake processor, data always travel all the way from RAM to registers in full cache lines of 64 bytes. - **_快取行。_** 在任何 GPU 中，128 位元組的快取行由四個 32 位元組的扇區組成。在快取未命中的情況下，不必填充快取行中的所有 4 個扇區，只需要更新需要更新的扇區。這意味著可以像獲取一個完整的快取行一樣輕鬆地獲取來自 4 個不同快取行的 4 個扇區。32 位元組的扇區大小即使在 Volta 的 HBM2 記憶體有 64 位元組的介面的情況下也持續存在。相比之下，在 Intel Cascade Lake 或 Skylake 處理器中，資料總是以完整的 64 位元組快取行從 RAM 傳輸到暫存器。

---
