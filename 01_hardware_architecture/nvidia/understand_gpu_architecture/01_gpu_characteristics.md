# GPU Characteristics（GPU 特性）

**原文：[Cornell University -> Cornell Virtual Workshop -> Understanding GPU Architecture -> GPU Characteristics](https://cvw.cac.cornell.edu/gpu-architecture/gpu-characteristics/index)**

The hardware design for graphics processing units (GPUs) is optimized for highly parallel processing. As a result, application programs for GPUs rely on programming models like NVIDIA CUDA that can differ substantially from traditional serial programming models based on CPUs. Still, one may ask: is the world of GPUs really so different from the world of CPUs? If one looks more closely, one discovers that many aspects of a GPU's architecture resemble those of modern CPUs, and the differences are at least partly a matter of terminology.

圖形處理單元（GPU）的硬體設計最佳化了高度並行處理。因此，GPU的應用程式依賴於像NVIDIA CUDA這樣的程式設計模型，與傳統的基於CPU的序列程式設計模型有很大不同。儘管如此，人們可能會問：GPU的世界真的與CPU的世界如此不同嗎？如果仔細研究，就會發現GPU的許多架構方面與現代CPU相似，差異至少部分是術語上的問題。

## Design: GPU vs. CPU（設計：GPU 與 CPU）

GPUs were originally designed to render graphics. They work very well for shading, texturing, and rendering the thousands of independent polygons that comprise a 3D object. CPUs, on the other hand, are meant to control the logical flow of any general-purpose program, where lots of number crunching may (or may not) be involved. Due to these very different roles, GPUs are characterized by many more processing units and higher aggregate memory bandwidth, while CPUs feature more sophisticated instruction processing and faster clock speed.

GPU最初是為渲染圖形而設計的。它們非常適合著色、紋理化和渲染構成3D物件的數千個獨立多邊形。而CPU則是設計用來控制任何通用程式的邏輯流程，其中可能涉及（也可能不涉及）大量的數字計算。由於這些非常不同的作用，GPU的特點是擁有更多的處理單元和更高的總記憶體頻寬，而CPU則具有更復雜的指令處理和更快的時鐘速度。

The figure below illustrates the main differences in hardware architecture between CPUs and GPUs. The transistor counts associated with various functions are represented abstractly by the relative sizes of the different shaded areas. In the figure, green corresponds to computation; gold is instruction processing; purple is L1 cache; blue is higher-level cache, and orange is memory (DRAM, which should really be thousands of times larger than the caches).

下面的圖表展示了CPU和GPU硬體架構之間的主要區別。與各種功能相關的電晶體數量透過不同陰影區域的相對大小抽象表示。在圖表中，綠色代表計算；金色是指令處理；紫色是L1快取；藍色是更高階別的快取，橙色是記憶體（DRAM，實際上應該比快取大幾千倍）。

![Comparing the relative capabilities of the basic elements of CPU and GPU architectures](img/ArchCPUGPUcores.png)

Comparing the relative capabilities of the basic elements of CPU and GPU architectures.

This diagram, which is taken from the [CUDA C++ Programming Guide (v.11.2)](https://docs.nvidia.com/cuda/archive/11.2.0/pdf/CUDA_C_Programming_Guide.pdf), does not depict the actual hardware design of any particular CPU or GPU. However, based on the size, color, and number of the various blocks, the figure does suggest that:

這張圖表取自CUDA C++程式設計指南（第11.2版），並不描繪任何特定CPU或GPU的實際硬體設計。然而，根據不同區域的大小、顏色和數量，該圖表確實表明：

1. CPUs can handle more complex workflows compared to GPUs.
2. CPUs don't have as many arithmetic logic units or floating point units as GPUs (the small green boxes above, roughly speaking), but the ALUs and FPUs in a CPU core are individually more capable.
3. CPUs have more cache memory than GPUs.

1. CPU 可以處理比 GPU 更復雜的工作流程。
2. CPU 沒有 GPU 那麼多的算術邏輯單元或浮點單元（上面的小綠盒，大致來說），但 CPU 核心中的 ALU 和 FPU 每個都更有能力。
3. CPU 擁有比 GPU 更多的快取記憶體。

A final point is that GPUs are really designed for workloads that can be parallelized to a significant degree. This is indicated in the diagram by having just one gold control box for every row of the little green computational boxes.

最後一點是，GPU確實設計用於能夠顯著並行化的工作負載。這在圖表中透過每一行小綠計算盒有一個金色控制盒來表示。

## Performance: GPU vs. CPU（性能：GPU 與 CPU）

GPUs and CPUs are intended for fundamentally different types of workloads. CPUs are typically designed for multitasking and fast serial processing, while GPUs are designed to produce high computational throughput using their massively parallel architectures.

GPU和CPU旨在處理根本不同類型的工作負載。CPU通常設計用於多工處理和快速序列處理，而GPU旨在使用其大規模並行架構產生高計算吞吐量。

The chart below, which is adapted from the [CUDA C Programming Guide (v.9.1)](https://docs.nvidia.com/cuda/archive/9.1/pdf/CUDA_C_Programming_Guide.pdf), shows the raw computational speed of different CPUs and GPUs. The purpose of the figure is to show the computational potential of GPUs, as measured in billions of floating-point operations per second (Gflop/s). One can ask: given a device that delivers such impressive floating-point performance, is it possible to use it for something besides graphics?

下面的圖表，改編自 CUDA C 程式設計指南（第9.1版），展示了不同 CPU 和 GPU 的原始計算速度。該圖表的目的是展示GPU的計算潛力，以每秒數十億次浮點運算（Gflop/s）為單位。人們可能會問：給定一個裝置能夠提供如此出色的浮點效能，是否有可能將其用於除了圖形以外的其他用途？

![Peak performance in Gflop/s of GPUs and CPUs in single and double precision, 2009-2016](img/PeakFlopsCPUGPU.png)

Peak performance in Gflop/s of GPUs and CPUs in single and double precision, 2009-2016.

> Info:
>
> Note, "single precision" refers to a 32-bit representation for floating point numbers (sometimes called FP32), while "double precision" refers to a 64-bit representation (FP64). Single precision numbers can often be processed twice as fast as the longer doubles.

---

> 信息：
>
> 注意，“單精度”指的是 32 位的浮點數表示（有時稱為 FP32），而“雙精度”指的是 64 位表示（FP64）。單精度數字通常可以比更長的雙精度處理得快兩倍。

## Heterogeneous Applications（異構應用程式）

It turns out that almost any application that relies on huge amounts of floating-point operations and simple data access patterns can gain a significant speedup using GPUs. This is sometimes referred to as GPGPU, or General-Purpose computing on Graphics Processing Units.

結果表明，幾乎所有依賴大量浮點運算和簡單資料訪問模式的應用程式都可以利用GPU獲得顯著的加速。這有時被稱為GPGPU，或者在圖形處理單元上進行通用計算。

Historically, NVIDIA CUDA is one of the key enabling technologies for GPGPU. CUDA was among the first APIs to simplify the task of programming numerically intensive routines such as matrix manipulation, Fast Fourier Transforms, and decryption algorithms so they could be accelerated on GPUs. In the time since CUDA was introduced, a number of techniques have arisen to make GPGPU even easier for application programmers, including directive\-based methods such as OpenACC and OpenMP offloading.

历史上，NVIDIA CUDA 是 GPGPU 的關鍵使能技術之一。CUDA 是最早簡化程式設計數值密集型例程（如矩陣操作、快速傅立葉變換和解密演算法）以便在 GPU 上加速的 API 之一。自 CUDA 引入以來，出現了許多技術，使 GPGPU 對應用程式開發人員來說更容易，包括基於指令的方法如 OpenACC 和 OpenMP offloading。

The following are some of the scientific and engineering fields that have successfully used CUDA and NVIDIA GPUs to accelerate the performance of important applications:

以下是一些科學和工程領域，它們成功地使用 CUDA 和 NVIDIA GPU 加速了重要應用程式的效能：

- **Deep Learning - 深度學習**
- **Computational Fluid Dynamics - 計算流體動力學**
- **Computational Structural Mechanics - 計算結構力學**
- **Seismic Processing - 地震處理**
- **Bioinformatics - 生物資訊學**
- **Materials Science - 材料科學**
- **Molecular Dynamics - 分子動力學**
- **Quantum Chemistry - 量子化學**
- **Computational Physics - 計算物理學**

Numerous examples of applications in the above areas can be found in the NVIDIA document [GPU-Accelerated Applications](https://www.nvidia.com/en-us/gpu-accelerated-applications/).

在 NVIDIA 文件 GPU-Accelerated Applications 中可以找到以上領域的許多應用程式的示例。

Of course, GPUs are hosted on CPU-based systems. Given a heterogeneous computer containing both CPUs and GPUs, it may be a good strategy to offload the massively parallel and numerically intensive tasks to one or more GPUs. Since most HPC applications contain both highly parallel and less-parallel parts, adopting a heterogeneous programming model is frequently the best way to utilize the strengths of both GPUs and CPUs. It allows the application to take advantage of the highly parallel GPU hardware to produce higher overall computational throughput.

當然，GPU 是宿主在基於 CPU 的系統上。鑑於包含 CPU 和 GPU 的異構計算機，將大規模並行和數值密集型任務解除安裝到一個或多個 GPU 上可能是一個好策略。由於大多數 HPC 應用程式包含高度並行和不太平行的部分，採用異構程式設計模型通常是利用 GPU 和 CPU 優勢的最佳方式。它允許應用程式利用高度並行的 GPU 硬體產生更高的總體計算吞吐量。

In heterogeneous systems, the GPUs can be supplied through standard graphics cards, such as the NVIDIA Quadro, or through high-end accelerator cards, such as the NVIDIA Tesla. The Tesla comes with extra processing power, double-precision capability, special memory, and other features to make it even more favorable for HPC. But NVIDIA devices of both kinds are capable of accelerating a variety of computational tasks, e.g., half-precision arithmetic for machine learning.

在異構系統中，GPU 可以透過標準圖形卡供應，如 NVIDIA Quadro，或透過高階加速卡，如 NVIDIA Tesla。Tesla 提供了額外的處理能力，雙精度能力，特殊記憶體和其他功能，使其更適合 HPC。但 NVIDIA 的兩種裝置類型都能夠加速各種計算任務，例如機器學習的半精度算術。

Either way, GPUs may outperform CPU-based processors by quite a lot, assuming the application is able to make full use of the hardware's inherent parallelism. As we will see, in TACC's Frontera system, the raw speed of single-precision computations in one of its CPU-based Intel "Cascade Lake" processors—specifically, an Intel Xeon Platinum 8280—is 4.3 Tflop/s; whereas just one of its GPUs, a Quadro RTX 5000, can potentially reach 11.2 Tflop/s, and a single one of the Tesla V100s in the companion Longhorn system (now decommissioned) might go as high as 15.7 Tflop/s.

不管怎樣，GPU 可能會比基於 CPU 的處理器效能高出很多，假設應用程式能夠充分利用硬體的固有並行性。正如我們將看到的，在 TACC 的 Frontera 系統中，其基於 CPU 的Intel "Cascade Lake"處理器之一——特別是 Intel Xeon Platinum 8280 —— 的單精度計算原始速度為 4.3 Tflop/s；而其中的一個 GPU，Quadro RTX 5000，可能達到 11.2 Tflop/s，而配套的 Longhorn 系統（現已退役）中的一個 Tesla V100 可能高達 15.7 Tflop/s。

## Threads and Cores Redefined（重新定義執行緒和核心）

What is the secret to the high performance that can be achieved by a GPU? The answer lies in the graphics pipeline that the GPU is meant to "pump": the sequence of steps required to take a scene of geometrical objects described in 3D coordinates and render them on a 2D display.

GPU 實現高效能的秘訣是什麼？答案在於 GPU 所要“傳輸”的圖形流水線：獲取以 3D 座標描述的幾何物件場景並將其渲染到 2D 顯示屏上所需的一系列步驟。

Two key properties of the graphics pipeline permit its speed to be accelerated. First, a typical scene is composed of many independent objects (e.g., a mesh of tiny triangles approximating a surface). Second, the sequence of steps needed to render each of the objects is basically the same for all of the objects, so that the computational steps may be performed in parallel on all them at once. By their very nature, then, GPUs must be highly capable parallel computing engines.

圖形流水線的兩個關鍵特性使其速度得以加快。首先，典型的場景由許多獨立的物件組成（例如，近似表面的微小三角形網格）。其次，渲染每個物件所需的步驟順序對於所有物件基本相同，因此可以同時對所有物件並行執行計算步驟。因此，就其本質而言，GPU 必須是功能強大的平行計算引擎。

But CPUs, too, have evolved to become highly capable parallel processors in their own right—and in this evolution, they have acquired certain similarities to GPUs. Therefore, it is not surprising to find a degree of overlap in the terminology used to describe the parallelism in both kinds of processors. However, one should be careful to understand the distinctions as well, because the precise meanings of terms can differ signficantly between the two types of devices.

但 CPU 也已經發展成為功能強大的並行處理器，並且在這一發展過程中，它們與 GPU 具有某些相似之處。因此，在描述這兩種處理器的並行性時使用的術語有一定程度的重疊也就不足為奇了。但是，人們也應該小心理解其中的區別，因為這兩種裝置之間術語的確切含義可能有很大不同。

For example, with CPUs as well as GPUs, one may speak of **_threads_** that run on different **_cores_**. In both cases, one envisions distinct _streams of instructions_ that are scheduled to run on different _execution units_. Yet the ways in which _threads_ and _cores_ act upon data are quite different in the two cases.

例如，對於 CPU 和 GPU，我們可能會說 **_執行緒_** 執行在不同 **_核心_** 上。在這兩種情況下，我們都會設想不同的 _指令流_，它們被安排在不同的 _執行單元_ 上執行。然而，在這兩種情況下， _執行緒_ 和 _核心_ 對資料的操作方式卻截然不同。

It turns out that a single core in a GPU—which we'll call a **_CUDA core_** hereafter, for clarity—is much more like a single vector lane in the vector processing unit of a CPU. Why? Because CUDA cores are essentially working in teams of 32 to execute a [Single Instruction on Multiple Data](https://cvw.cac.cornell.edu/parallel/hpc/taxonomy-parallel-computers), a type of parallelism known as SIMD. In CPUs, SIMD operations are possible as well, but they are carried out by vector units, based on smaller data groupings (typically 8 or 16 elements).

事實證明，GPU 中的單個核心（為清楚起見，我們以下將其稱為 **_CUDA 核心_**）更像是 CPU 向量處理單元中的單個向量通道。為什麼？因為 CUDA 核心本質上是以 32 個為一組來執行 [多資料上的單條指令](https://cvw.cac.cornell.edu/parallel/hpc/taxonomy-parallel-computers)，這是一種稱為 SIMD 的並行類型。在 CPU 中，也可以進行 SIMD 操作，但它們是由向量單元基於較小的資料分組（通常為 8 個或 16 個元素）執行的。

The table below attempts to reduce the potential sources of confusion. It lists and defines the terms that apply to the various levels of parallelism in a GPU, and gives their rough equivalents in CPU terminology. (Several new terms are introduced below; they are further explained on succeeding pages.)

下表旨在減少可能引起混淆的地方。它列出並定義了適用於 GPU 中各種並行級別的術語，並給出了它們在 CPU 術語中的粗略對應。（下面介紹了幾個新術語；它們將在後續頁面中進一步解釋。）

| **GPU term**                     | **Quick definition for a GPU**                                                                                                                                                                                                                | **CPU&nbsp;equivalent** |
|----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------|
| **thread**                       | <br>                        The stream of instructions and data that is assigned to one CUDA core; note, a Single Instruction applies <br>                        to Multiple Threads, acting on multiple data (SIMT)<br>                     | N/A                     |
| **CUDA core**                    | Unit that processes one data item after another, to execute its portion of a SIMT instruction stream                                                                                                                                          | vector lane             |
| **warp**                         | Group of 32 threads that executes the same stream of instructions together, on different data                                                                                                                                                 | vector                  |
| **kernel**                       | Function that runs on the device; a kernel may be subdivided into thread blocks                                                                                                                                                               | **thread(s)**               |
| **SM, streaming multiprocessor** | Unit capable of executing a thread block of a kernel; multiple SMs may work together on a kernel                                                                                                                                              | **core**                    |

Comparison of terminology between GPUs and CPUs.

## SIMT and Warps（SIMT 和 Warps）

On the preceding page we encountered two new GPU\-related terms, SIMT and warp. Let's explore their meanings and implications more thoroughly.

在上一頁中，我們遇到了兩個與 GPU 相關的新術語，SIMT 和 warp。讓我們更深入地探討它們的含義和影響。

## SIMT（單指令多執行緒）

As you might expect, the NVIDIA term "Single Instruction Multiple Threads" (SIMT) is closely related to a better known term, Single Instruction Multiple Data (SIMD). What's the difference? In pure SIMD, a single instruction acts upon _all_ the data in _exactly_ the same way. In SIMT, this restriction is loosened a bit: selected threads can be activated or deactivated, so that instructions and data are processed only on the active threads, while the local data remain unchanged on inactive threads.

正如我們所料，NVIDIA 術語“單指令多執行緒”(SIMT) 與更廣為人知的術語“單指令多資料”(SIMD) 密切相關。兩者有什麼區別？在純 SIMD 中，一條指令以完全相同的方式作用於所有資料。在 SIMT 中，此限制略有放松：可以激活或停用選定的執行緒，以便僅在活動執行緒上處理指令和資料，而非活動執行緒上的本地資料保持不變。

As a result, SIMT can accommodate branching, though not very efficiently. Given an _if-else_ construct beginning with _if (condition)_, the threads for which _condition==true_ will be active when running statements in the _if_ clause, and the threads for which _condition==false_ will be active when running statements in the _else_ clause. The results should be correct, but the inactive threads will do no useful work while they are waiting for statements in the active clause to complete. Branching within SIMT is illustrated in the figure below.

因此，SIMT 可以適應分支，儘管效率不高。給定一個以 _if (condition)_ 開頭的 _if-else_ 構造，在執行 _if_ 子句中的語句時，_condition==true_ 的執行緒將處於活動狀態，在執行 _else_ 子句中的語句時，_condition==false_ 的執行緒將處於活動狀態。結果應該是正確的，但不活動的執行緒在等待活動子句中的語句完成時不會做任何有用的工作。下圖說明了 SIMT 中的分支。

![Threads in the same warp cannot execute statements in the if-block in parallel with statements in the else-block. The timeline shows that only one group of threads or the other can be active.](img/simtVolta.png)

How an if-else is executed in the Volta implementation of SIMT.

The figure, like several others in this topic, is taken from NVIDIA's [Volta architecture whitepaper](https://images.nvidia.com/content/volta-architecture/pdf/volta-architecture-whitepaper.pdf). It illustrates how an _if-else_ construct can be executed by a recent GPU such as the Tesla V100 (or later).

該圖與本主題中的其他幾張圖一樣，取自 NVIDIA 的 [Volta 架構白皮書](https://images.nvidia.com/content/volta-architecture/pdf/volta-architecture-whitepaper.pdf)。它說明了如何透過最新的 GPU（例如 Tesla V100（或更高版本））執行 _if-else_ 構造。

> Info:
>
> Note that in NVIDIA GPUs prior to Volta, the entire _if_ clause (i.e., both statements A and B) would have to be executed by the relevant threads, then the entire _else_ clause (both statements X and Y) would have to be executed by the remainder of the threads, then all threads would have to synchronize before continuing execution (statement Z). Volta's more flexible SIMT model permits synchronization of shared data at intermediate points (say, after A and X).

---

> 信息：
>
> 請注意，在 Volta 之前的 NVIDIA GPU 中，整個 _if_ 子句（即語句 A 和 B）必須由相關執行緒執行，然後整個 _else_ 子句（語句 X 和 Y）必須由其餘執行緒執行，然後所有執行緒必須同步才能繼續執行（語句 Z）。Volta 更靈活的 SIMT 模型允許在中間點（例如，在 A 和 X 之后）同步共享資料。

It is worth observing that a form of SIMT also exists on CPUs. Many vector instructions in Intel's x86\_64 have masked variants, in which a vector instruction can be turned on/off for selected vector lanes according to the true/false values in an extra vector operand. This extra operand is called a "mask" because it functions like one: it "hides" certain vector lanes. And the masking trick enables branching to be vectorized on CPUs, too, to a limited extent.

值得注意的是，CPU 上也存在一種 SIMT 形式。英特爾 x86\_64 中的許多向量指令都有掩碼變體，其中可以根據額外向量運算元中的真/假值針對選定的向量通道開啟/關閉向量指令。這個額外的運算元被稱為“掩碼”，因為它的功能就像掩碼一樣：它“隱藏”某些矢量通道。而且掩碼技巧也使分支在 CPU 上能夠在一定程度上向量化。

In contrast to how CPU code is written, SIMT parallelism on the GPU does not have to be expressed through "vectorized loops". Instead—at least in CUDA—every GPU thread executes the kernel code as written. This somewhat justifies NVIDIA's "thread" nomenclature.

與 CPU 程式碼的編寫方式不同，GPU 上的 SIMT 並行性不必透過“向量化迴圈”來表達。相反，至少在 CUDA 中，每個 GPU 執行緒都會按編寫的方式執行核心程式碼。這在某種程度上證明了 NVIDIA 的“執行緒”命名法的合理性。

> Info:
>
> Note that GPU code can also be written by applying OpenMP or OpenACC directives to loops, in which case it can end up looking very much like vectorized CPU code.

---

> 信息：
>
> 請注意，GPU 程式碼也可以透過將 OpenMP 或 OpenACC 指令應用於迴圈來編寫，在這種情況下，它最終看起來非常像向量化的 CPU 程式碼。

## Warps

At runtime, a block of threads is divided into warps for SIMT execution. One full warp consists of a bundle of 32 threads with consecutive thread indexes. The threads in a warp are then processed together by a set of 32 CUDA cores. This is analogous to the way that a vectorized loop on a CPU is chunked into vectors of a fixed size, then processed by a set of vector lanes.

在執行時，執行緒塊被劃分為 Warp 以用於 SIMT 執行。一個完整的 Warp 由一組具有連續執行緒索引的 32 個執行緒組成。然后，Warp 中的執行緒由一組 32 個 CUDA 核心一起處理。這類似於將 CPU 上的向量化迴圈劃分為固定大小的向量，然後由一組向量通道進行處理的方式。

The reason for bundling threads into warps of 32 is simply that in NVIDIA's hardware, CUDA cores are divided into fixed groups of 32. Each such group is analogous to a vector processing unit in a CPU. Breaking down a large block of threads into chunks of this size simplifies the SM's task of scheduling the entire thread block on its available resources.

將 32 個執行緒捆綁由一個 Warp 執行的原因很簡單，因為在 NVIDIA 的硬件中，CUDA 核心被分成 32 個固定組。每個這樣的組都類似於 CPU 中的向量處理單元。將一大塊執行緒分解成這種大小的塊可以簡化 SM 在可用資源上排程整個執行緒塊的任務。

Apparently NVIDIA borrowed the term "warp" from weaving, where it refers to the set of vertical threads through which the weaver's shuttle passes. To quote the [original paper by Lindholm et al.](https://ieeexplore.ieee.org/document/4523358) that introduced SIMT, "The term _warp_ originates from weaving, the first parallel-thread technology." (NVIDIA continues to use this quote in their [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#simt-architecture).)

顯然，NVIDIA 借用了“warp”一詞，該詞指的是織布機梭子穿過的一組垂直線。引用介紹 SIMT 的 [Lindholm 等人的原始論文](https://ieeexplore.ieee.org/document/4523358)，“warp”一詞源自編織，這是第一種並行執行緒技術。”（NVIDIA 繼續在其 [CUDA C++ 程式設計指南](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#simt-architecture) 中使用這句話。）

One could argue that the existence of warps is a hardware detail that isn't directly relevant to application programmers. However, the warp-based execution model has implications for performance that can influence coding choices. For example—as the figure above illustrates—branching can complicate the execution flow of a warp, if two threads in the same warp branch to different instructions. Thus, a programmer might want to avoid branching within warp-sized sets of loop iterations.

有人可能會認為 Warp 的存在是硬體細節，與應用程式程式設計師沒有直接關係。但是，基於 Warp 的執行模型對效能有影響，可能會影響編碼選擇。例如，如上圖所示，如果同一 Warp 中的兩個執行緒分支到不同的指令，分支會使 Warp 的執行流程複雜化。因此，程式設計師可能希望避免在 Warp 大小的迴圈迭代集內進行分支。

## Kernels and SMs

We continue our survey of GPU-related terminology by looking at the relationship between kernels, thread blocks, and streaming multiprocessors (SMs).

我們透過研究核心、執行緒塊和流多處理器（SM）之間的關係來繼續對 GPU 相關術語的調查。

## Kernels (in software)

A function that is meant to be executed in parallel on an attached GPU is called a _kernel_. In CUDA, a kernel is usually identified by the presence of the `__global__` specifier in front of an otherwise normal-looking C++ function declaration. The designation `__global__` means the kernel may be called from either the host or the device, but it will execute on the device.

要在連線的 GPU 上並行執行的函式稱為 _kernel_。在 CUDA 中，核心通常透過在看似正常的 C++ 函式宣告前面新增 `__global__` 說明符來標識。`__global__` 表示核心可以從主機或裝置呼叫，但它將在裝置上執行。

Instead of being executed only once, a kernel is executed N times in parallel by N different threads on the GPU. Each thread is assigned a unique ID (in effect, an index) that it can use to compute memory addresses and make control decisions.

核心並非只執行一次，而是由 GPU 上的 N 個不同執行緒並行執行 N 次。每個執行緒都分配有一個唯一 ID（實際上是一個索引），可用於計算記憶體地址並做出控制決策。

![Each thread works on a different index (threadID) in an array of inputs to produce an array of outputs](img/kernelThreads.png)

Showing how a CUDA kernel is executed by an array of threads.  
Source: [NVIDIA CUDA Zone](https://www.nvidia.com/content/cudazone/download/Getting_Started_w_CUDA_Training_NVISION08.pdf)

展示 CUDA 核心如何透過執行緒陣列執行。  
來源：[NVIDIA CUDA 區域](https://www.nvidia.com/content/cudazone/download/Getting_Started_w_CUDA_Training_NVISION08.pdf)

Accordingly, kernel calls must supply special arguments specifying how many threads to use on the GPU. They do this using CUDA's "execution configuration" syntax, which looks like this: `fun<<<1, N>>>(x, y, z)`. Note that the first entry in the configuration (1, in this case) gives the number of _blocks_ of N threads that will be launched.

因此，核心呼叫必須提供特殊參數，指定在 GPU 上使用多少個執行緒。它們使用 CUDA 的“執行配置”語法來實現這一點，如下所示：`fun<<<1, N>>>(x, y, z)`。請注意，配置中的第一個條目（在本例中為 1）給出了將啟動的 N 個執行緒的 _blocks_ 數量。

## Streaming multiprocessors (in hardware)

On the GPU, a kernel call is executed by one or more streaming multiprocessors, or SMs. The SMs are the hardware homes of the CUDA cores that execute the threads. The CUDA cores in each SM are always arranged in sets of 32 so that the SM can use them to execute full warps of threads. The exact number of SMs available in a device depends on its NVIDIA processor family (Volta, Turing, etc.), as well as the specific model number of the processor. Thus, the Volta chip in the Tesla V100 has 80 SMs in total, while the more recent Turing chip in the Quadro RTX 5000 has just 48.

在 GPU 上，核心呼叫由一個或多個流式多處理器 (SM) 執行。SM 是執行執行緒的 CUDA 核心的硬件之家。每個 SM 中的 CUDA 核心始終以 32 個為一組排列，以便 SM 可以使用它們來執行完整的執行緒束。裝置中可用的 SM 的確切數量取決於其 NVIDIA 處理器系列（Volta、Turing 等）以及處理器的具體型號。因此，Tesla V100 中的 Volta 晶片總共有 80 個 SM，而 Quadro RTX 5000 中較新的 Turing 芯片只有 48 個。

However, the number of SMs that the GPU will actually use to execute a kernel call is limited to the number of thread _blocks_ specified in the call. Taking the call `fun<<<M, N>>>(x, y, z)` as an example, there are at most M blocks that can be assigned to different SMs. A thread block may not be split between different SMs. (If there are more blocks than available SMs, then more than one block may be assigned to the same SM.) By distributing blocks in this manner, the GPU can run independent blocks of threads in parallel on different SMs.

但是，GPU 實際用於執行核心呼叫的 SM 數量受限於呼叫中指定的執行緒塊數量。以呼叫 `fun<<<M, N>>>(x, y, z)` 為例，最多有 M 個塊可以分配給不同的 SM。執行緒塊不能在不同的 SM 之間分割。（如果塊的數量多於可用的 SM，則可以將多個塊分配給同一個 SM。）透過以這種方式分配塊，GPU 可以在不同的 SM 上並行執行獨立的執行緒塊。

Each SM then divides the N threads in its current block into warps of 32 threads for parallel execution internally. On every cycle, each SM's schedulers are responsible for assigning full warps of threads to run on available sets of 32 CUDA cores. (The Volta architecture has 4 such schedulers per SM.) Any leftover, partial warps in a thread block will still be assigned to run on a set of 32 CUDA cores.

然后，每個 SM 將其當前塊中的 N 個執行緒劃分為 32 個執行緒的 Warp，以便在內部並行執行。在每個週期中，每個 SM 的排程程式負責分配完整的執行緒 Warp，以在可用的 32 個 CUDA 核心組上執行。（Volta 架構每個 SM 有 4 個這樣的排程程式。）執行緒塊中任何剩餘的部分 Warp 仍將分配在一組 32 個 CUDA 核心上執行。

The SM includes several levels of memory that can be accessed only by the CUDA cores of that SM: registers, L1 cache, constant caches, and shared memory. The exact properties of the per-SM and global memory available in Volta GPUs will be outlined shortly.

SM 包含多個級別的記憶體，這些記憶體只能由該 SM 的 CUDA 核心訪問：寄存器、L1 快取、常量快取和共享記憶體。Volta GPU 中可用的每個 SM 和全域記憶體的確切屬性將很快概述。

## Compute Capability（計算能力）

The technical properties of the SMs in a particular NVIDIA GPU are represented collectively by a version number called the _compute capability_ of the device. This serves as a reference to the set of features that is supported by the GPU. It can even be discovered by applications at run time to find out whether certain hardware properties and/or instructions are present on the GPU.

特定 NVIDIA GPU 中 SM 的技術屬性由稱為裝置_計算能力_的版本號統一表示。這可作為 GPU 支援的功能集的參考。應用程式甚至可以在執行時發現它，以查明 GPU 上是否存在某些硬體屬性和/或指令。

Devices with the same first number in their compute capability share the same core architecture. For example, if a device's compute capability starts with a 7, it means that the GPU is based on the Volta architecture; 8 means the Ampere architecture; and so on. Minor version numbers correspond to incremental improvements to the base architecture. For instance, Turing is assigned a compute capability of 7.5 because it is an incremental update of the Volta architecture.

計算能力中第一個數字相同的裝置共享相同的核心架構。例如，如果裝置的計算能力以 7 開頭，則表示 GPU 基於 Volta 架構；8 表示 Ampere 架構；依此類推。次要版本號對應於對基礎架構的增量改進。例如，Turing 被分配了 7.5 的計算能力，因為它是 Volta 架構的增量更新。

> 譯註：主版本號與架構的對應關係補充：7.5=Turing、8.9=Ada、9.0=Hopper，原文寫作年代較早，未涵蓋這些後繼架構。另外「Turing 是 Volta 的增量更新」是 compute capability 視角的說法，Turing 在硬件上新增了 RT Core 和第二代 Tensor Core，並不是簡單的小改款。

![NVIDIA Quadro RTX 5000 image](img/QuadroRTX5000small.png)

NVIDIA Tesla V100, based on the Volta architecture, and NVIDIA Quadro RTX 5000, based on the Turing architecture.

基於Volta架構的NVIDIA Tesla V100，以及基於Turing架構的NVIDIA Quadro RTX 5000。

Are you thinking about writing CUDA programs for the NVIDIA graphics card in your personal computer? First, make sure this is a real possibility by searching through the lists of [GPUs that are enabled for CUDA](https://developer.nvidia.com/cuda-gpus#compute). If your card is listed, then note its compute capability, because this number lets you learn all kinds of things about the [features and technical specifications](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#compute-capabilities) of your GPU (much more than a beginner needs to know).

大家是否正在考慮在個人電腦中為 NVIDIA 顯示卡編寫 CUDA 程序？首先，透過搜尋 [啟用 CUDA 的 GPU](https://developer.nvidia.com/cuda-gpus#compute) 列表，確保這確實可行。如果顯示卡已列出，請記下它的計算能力，因為這個數字可以讓我們瞭解有關 GPU 的 [功能和技術規格](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#compute-capabilities) 的各種資訊（遠遠超過初學者需要了解的內容）。

---
