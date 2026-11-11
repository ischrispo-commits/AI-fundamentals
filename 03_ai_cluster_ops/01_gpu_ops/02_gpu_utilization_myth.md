# GPU 利用率是一個誤導性指標

> 原文: "GPU Utilization is a Misleading Metric"，作者 Roanak Baviskar，Trainy，發表於 2024-08-22。
> 原文連結（`https://www.trainy.ai/blog/gpu-utilization-misleading`）已失效（404），Wayback 存檔：<https://web.archive.org/web/20241205065943/https://www.trainy.ai/blog/gpu-utilization-misleading>。文中資料與工具狀態為 2024-08 口徑。

機器學習團隊最常用於評估 `GPU` 使用情況的指標是 **`GPU` 利用率**，通常透過在終端執行 `nvidia-smi` 命令獲取。許多整合可觀測性工具也將 `GPU` 利用率作為其主要效能監測指標。我們發現這並非總是衡量 `GPU` 效能的最佳指標：僅透過記憶體讀寫操作（不進行任何計算）就能獲得 `100%` 的 `GPU` 利用率。本文旨在揭示這一發現的過程，並分享我們在此過程中獲得的其他洞見。

在 [Trainy](https://trainy.ai/)，我們專注於 `GPU` 叢集管理基礎設施的研發，因此長期深耕該領域。去年我們與某基礎模型公司合作，致力於擴展其大語言模型（`LLM`）訓練規模並提升效率。我們遵循了幾乎所有 `PyTorch` 效能調優指南都會提及的基礎步驟，具體包括：

- 透過調整資料載入器預設參數（`num_workers`、`batch_size`、`pin_memory`、`prefetch_factor` 等）使 `GPU` 達到飽和狀態；
- 使用混合精度訓練（`fp16`, `bf16`）以最大化張量核心利用率；
- 使用 `apex`/`deepspeed` 提供的融合最佳化器（如 `FusedAdam`、`FusedAdamW` 等）；
- 使用專為訓練設計的實例/網路架構（`H100SXM`、`A100SXM`）。同時儘可能使用更新代的實例：`H100` > `A100` > `V100`。

這些簡單調整使我們實現了 `100% GPU` 利用率和顯著提升的功耗，這很棒！為了驗證是否還有最佳化空間，我們計算了訓練任務的 `MFU` 指標。

> **簡要回顧**：如 [Google 的 PaLM 論文](https://arxiv.org/pdf/2204.02311) 所述，`MFUs`（模型浮點運算利用率）是理解 `GPU` 效能的最佳指標之一。其定義為“觀察到的吞吐量（每秒處理 token 數）與系統在峰值 FLOPs 狀態下理論最大吞吐量的比值”。簡而言之，它反映了當前工作負載的每秒浮點運算量佔 `GPU` 理論最大能力的百分比。該指標的主要侷限在於，相較於 `GPU` 利用率等指標，其數值依賴於具體參數和框架實現。

然而，該模型訓練僅達到約 `20%` 的 `MFU`（模型浮點利用率）。作為參考，目前大多數 `LLM` 訓練的 `MFU` 水平在 [35%-45% 之間](https://github.com/mosaicml/llm-foundry/tree/main/scripts/train/benchmarking) 。這就引出了核心問題：在 `GPU` 利用率顯示 `100%` 的情況下，為何我們僅使用了 `GPU` 理論最大計算能力的 `20%`？

要解答這個問題，我們需要更深入地理解 `GPU` 利用率指標的實際監測物件。

## `GPU` 利用率的本質是什麼？

在 [Nvidia 官方文件](https://developer.nvidia.com/management-library-nvml) 中，`GPU` 利用率被模糊地定義為“當前利用率指標同時反映 `GPU` 計算資源和記憶體介面的使用率”，這種表述具有顯著的語義不確定性。

[`Datadog` 的 `NVML` 文件](https://docs.datadoghq.com/integrations/nvml/#metrics) 提供了更明確的定義：“**過去取樣週期內，`GPU` 執行一個或多個核心運算的時間佔比**”。要理解這個指標的誤導性，我們需要簡要回顧 `GPU` 的工作原理。

`GPU` 具有[核心和多處理管理器](https://cvw.cornell.edu/gpu-architecture/gpu-characteristics/kernel_sm) 。在英偉達 `GPU` 中這些多處理管理器被稱為流式多處理器（`SM`），而 `AMD` 硬體上則稱為計算單元（`CU`）。下圖展示了包含 `144` 個流式多處理器（`SM`）的 `GH100 GPU` 架構示意圖。

![GH100 GPU結構示意圖](assets/144-SMs.png)

這些多處理管理器可視為一組工人（即核心）的工頭。當啟動 `CUDA` 核心時，工作會透過一個或多個流式多處理器（`SM`）在 `CUDA` 核心上執行。如下圖所示，`GH100` 晶片中的單個流式多處理器（`SM`）包含大量 `CUDA` 核心。

![img](assets/H100-SM.png)

**這意味著 `GPU` 利用率這個指標僅測量核心在給定時間內是否正在執行。** 它無法反映核心是否使用了所有可用核心，或是否將工作負載並行化至 `GPU` 的最大處理能力。在最極端的情況下，僅透過記憶體讀寫操作（執行 `0` 次浮點運算）即可獲得 `100%` 的 `GPU` 利用率。

現在我們需要澄清的是：這種情況僅對缺乏系統背景知識的人群（如許多機器學習工程師）具有誤導性。正如 [此處](https://arthurchiao.art/blog/understanding-gpu-performance/#24-the-use-methodology) 所述，在 ["USE 方法論"](https://www.brendangregg.com/usemethod.html) 框架下，`GPU` 利用率的定義確實具有特定意義。

但回到當前問題，這個定義確實解釋了我們在 `GPU` 利用率與 `MFU` 之間觀察到的差距！顯然還有潛在效能未被充分挖掘，我們只需找到它。

## 深入挖掘

下一步尋找更多效能提升的方向自然是分析模型的訓練迴圈。我們使用 `PyTorch` 分析器仔細檢視了訓練迴圈以獲取更深入的理解。

如下圖所示，`Softmax` 核心顯示出高 `GPU` 利用率，但名為流多處理器效率的指標卻較低。這立即引起了我們的警覺，因為原生 `softmax` 是大型語言模型中眾所周知的瓶頸，為此業界開發了諸如 [FlashAttention](https://github.com/Dao-AILab/flash-attention) 的 [核心融合技術](https://triton-lang.org/main/getting-started/tutorials/02-fused-softmax.html#motivations) 來解決其記憶體受限的特性。基於這些資訊，流多處理器效率指標可能正揭示著我們模型執行過程中的低效環節。

![profiler_tool](assets/profiler_tool.png)

## 但流多處理器效率究竟代表什麼？

流多處理器效率（亦稱 `SM` 活動度）是英偉達 `GPU` 上的一個度量指標，用於描述特定時間間隔內活躍流多處理器（`SM`）的百分比。如前所述，流多處理器可視為 `CUDA` 核心叢集的排程中樞。以 [英偉達 H100 GPU](https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/) 為例，其擁有 `132` 個流多處理器，每個 `SM` 包含大量 `CUDA` 核心。透過測量流多處理器效率，我們可以判斷 `CUDA` 核心是否有效利用了流多處理器資源。若某個 `CUDA` 核心持續執行 `10` 秒但僅使用 `1` 個流多處理器，在 `H100` 上該操作會顯示 `100%` 利用率，但流多處理器效率僅為 `1/132=0.7%`。

這正是我們需要的指標：透過逐層監測流多處理器效率，我們可以明確最佳化過程中最容易實現的效能增益點。

## 進行最佳化

既然我們可以輕鬆識別哪些核心在 `GPU` 上未充分執行，就可以著手最佳化這些層。由於這是一個 `Transformer` 堆疊，主要最佳化收益將來自對 `Transformer` 塊定義中的層進行融合。下圖總結了我們的最佳化內容。

![fused](assets/fused.png)

所謂融合，是指我們不使用 `PyTorch` 原生定義的層集合，而是將其替換為用 `CUDA` 或 `Triton` 實現的 `GPU` 核心——該核心將所有層合併為一個。這種加速源於：對於某些層（如 [Softmax](https://triton-lang.org/main/getting-started/tutorials/02-fused-softmax.html) ），相比執行數學運算的時間，減少核心讀寫 `GPU` 記憶體的時間更為關鍵。[Flash Attention](https://github.com/Dao-AILab/flash-attention) 就是這種融合核心的典型示例。其他需要融合的核心包括 [MLP（`FusedMLP`）](https://github.com/Dao-AILab/flash-attention/blob/main/flash_attn/ops/fused_dense.py) 和 [dropout + layer norm + residual add（`DropoutAddLayerNormFn`）](https://github.com/Dao-AILab/flash-attention/blob/main/flash_attn/ops/layer_norm.py) 操作。

這些核心是我們自己編寫的嗎？並非如此。其中大部分已透過 `Flash Attention` 等庫實現為 `nn.Modules` 層，因此您無需擔心從零開始使用核心實現 `torch.autograd.function`。此外，這些實現通常已進行硬體級最佳化，不僅執行速度更快，還能減少記憶體佔用。

最大的挑戰在於確定程式碼中需要替換具體網路層的位置。雖然 `torch.compile` 試圖自動完成這項工作，但截至原文撰寫時（2024-08），該工具 [與 FSDP 等新型分布式策略兼容性不佳](https://dev-discuss.pytorch.org/t/torch-compile-fsdp-dec-8th/1718) ，且由於計算圖中斷問題，實踐中未能兌現預期的加速效果。展望未來，我們期待 `torch` 編譯器能自動完成這些最佳化，但目前仍需手動整合融合實現方案。（時敏口徑：截至 2026-11，FSDP2 與 `torch.compile` 的組合已基本可用，並被 PyTorch 官方作為推薦搭配演進，實際相容性以所用版本實測為準。）

在成果方面，我們為該客戶實現了訓練速度 `4` 倍的提升，模型浮點利用率（`MFU`）從最初的 `20%` 提升至 `38%`。大部分最佳化來源於融合核心技術的應用，以及根據其模型規模和可用的 `3.2 Tbps Infiniband` 網路頻寬，確定的最優模型並行層級配置。

## 結論

我們強烈建議各 AI 團隊在監控 `GPU` 叢集時，除 `GPU` 利用率外還應關注流多處理器效率（`SM Efficiency`）。該指標能更真實反映 `GPU` 的效能壓榨程度，而 `GPU` 利用率僅能體現裝置是否處於空閒狀態。當然，計算模型浮點利用率（`MFUs`）也很有價值，但這並非一個可實時逐層監控的指標。值得注意的是，[英偉達 DCGM](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html#profiling-metrics) （資料中心 GPU 管理器）預設就提供流多處理器活動的監控資料。

除此之外，還存在更細粒度的指標，例如流多處理器佔用率（在 `PyTorch` 分析器中稱為“實際佔用率”），這些指標能反映每個流多處理器實際執行的工作量。然而，理解這些指標並不像單純追求流多處理器效率最大化那麼直觀。如果您希望深入了解，我建議您查閱以下資源：[PyTorch 分析器博客](https://pytorch.org/blog/pytorch-profiler-1.9-released/#gpu-metric-on-timeline) 、[DCGM 文件](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html#profiling-metrics) 、[Nsight 核心效能分析指南](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html) 以及 [Nsight 文件](https://docs.nvidia.com/gameworks/content/developertools/desktop/analysis/report/cudaexperiments/kernellevel/achievedoccupancy.htm) 。

---

### MFU vs SM Efficiency vs GPU Utilization 對比表

| 指標名稱                                                | 關注層級 | 表示意義                                     | 典型使用場景              | 優點               | 局限性                         | 計算公式（含說明）                                                                                                          | 舉例解釋                                                                       |
| ------------------------------------------------------- | -------- | -------------------------------------------- | ------------------------- | ------------------ | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `MFU` (`Model Flops Utilization`)                       | 模型級   | 模型實際執行的 `FLOPs` 佔理論 `FLOPs` 的比例 | 深度學習訓練、推理        | 準確反映模型計算利用率 | 不適用於非模型任務，需已知模型結構 | `MFU` = 實際執行的 `FLOPs` / 理論最大 `FLOPs`<br>（需透過 `profiler` 獲取模型實際 `FLOPs`）                               | 理論 `FLOPs` 為 `1000 GFLOPs`，實際執行了 `900 GFLOPs`，則 `MFU = 0.9`             |
| `SM Efficiency` (`Streaming Multiprocessor Efficiency`) | GPU 核心級   | `SM` 上有活躍 `warp` 的週期佔總週期比例      | `CUDA kernel` 最佳化        | 可反映執行緒排程活躍性   | 活躍 `warp` 不代表充分利用核心     | `SM Efficiency` = 有 `warp` 活躍的週期數 / `SM` 總週期數                                                                    | `SM` 在 `100` 個週期中有 `40` 個週期有活躍 `warp`，則 `SM Efficiency` = `40%`      |
| `GPU Util` (`GPU Utilization`)                          | 整體硬體級   | `GPU` 在某時間段內是否“忙碌”（無論執行類型） | 粗略判斷 GPU 是否在被使用 | 簡單直觀，易於採集     | 可能誤判記憶體讀寫或輕負載為滿載     | `GPU Util = 忙碌時間 / 總取樣時間`<br>說明：1) “忙碌”定義為有任意核心在執行；2) 不考慮是否佔滿 `CUDA` 核心；3) 哪怕只是執行記憶體 `copy`，也可能顯示為 `100%` | `GPU` 執行記憶體 `copy` 操作時，即使 `CUDA` 核心空閒，`GPU Util` 也可能顯示為 `100%` |

### 補充說明：GPU Utilization 的誤區

- `GPU Utilization` ≠ 實際計算能力利用率。
- 只要有任何核心在執行（包括僅做 `memory copy`），就會視為“忙碌”；
- 即使 CUDA 核心空閒，`GPU Utilization` 也可能是 100%；
- 若要精確評估 `GPU` 的計算利用情況，建議結合 `MFU` 或 `SM Efficiency`；
- 結合 `MFU` 和 `SM Efficiency`，可以更全面地評估 GPU 的計算效率，而不是隻依賴 `GPU Utilization` 這個粗略指標。
