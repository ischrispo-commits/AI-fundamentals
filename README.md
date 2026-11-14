# AI Fundamentals

本倉庫是一個全面的人工智慧基礎設施（AI Infrastructure）學習資源集合，涵蓋從硬體基礎到高階應用的完整技術棧。內容包括 GPU 架構與程式設計、CUDA 開發、大語言模型、AI 系統設計、效能最佳化、企業級部署等核心領域，旨在為 AI 工程師、研究人員和技術愛好者提供系統性的學習路徑和實踐指導。

> - **適用人群**：AI 工程師、系統架構師、GPU 程式設計開發者、大模型應用開發者、技術研究人員。
> - **技術棧**：CUDA、GPU 架構、LLM、AI 系統、分散式計算、容器化部署、效能最佳化。
> - **想直接跑程式碼？** 全倉庫 12 處可執行 Demo 的總索引見 **[Demos 總索引](demos.md)**——含依賴要求、對應文章與驗證狀態。
> - **本 fork 新增**：面向 AI Infra TMM／Evangelist／PMM／TAM 求職的 **[12 周個人讀書計劃](00_study_plan/README.md)**（繁體中文；課綱、提取測驗、講義 skill、視覺化路線圖）。

---

**Star History**:

![Star History Chart](https://star-history.dera.page/svg?repos=ForceInjection/AI-fundamentals&type=date&legend=top-left)

---

## 1. 硬體架構與互連技術

涵蓋單機基礎計算晶片（GPU、TPU）設計原理，PCIe、NVLink 高速互連匯流排協議，GPUDirect 跨節點直通技術，GPU/NIC/NVMe/DPU/CXL 的 DMA engine 路徑，以及 NVIDIA GB300 NVL72 等異構融合超級晶片的系統級架構與延遲金字塔模型。詳細內容請訪問：**[硬體架構與互連技術](01_hardware_architecture/README.md)**。

- **基礎計算晶片架構**
  - [深入理解 GPU 架構](./01_hardware_architecture/nvidia/understand_gpu_architecture/README.md)
  - [TPU 101：深度學習專用加速器架構解析](./01_hardware_architecture/tpu/tpu_101.md)
  - [GPGPU vs NPU：大模型推理訓練對比](./01_hardware_architecture/nvidia/GPGPU_vs_NPU_大模型推理训练对比.md)
  - [Ascend950 稀疏注意力 Forward 算子與最佳化技術簡析](./01_hardware_architecture/ascend/Ascend950_稀疏注意力Forward算子与优化技术简析.md) — 深度求索官方 950 微架構解析（1 Cube + 2 Vector、L1 雙 bank、FixPipe），DSA 稀疏注意力 prefill/decode 最佳化轉載存檔
- **高速互連與資料傳輸技術**
  - [PCIe 匯流排技術大全](./01_hardware_architecture/pcie/01_pcie_comprehensive_guide.md)
  - [Linux PCIe P2PDMA 技術介紹](./01_hardware_architecture/pcie/02_p2pdma_technology.md)
  - [CXL 互聯協議全景解讀：從 PCIe 時代到可組合資料中心](./01_hardware_architecture/pcie/08_cxl_interconnect_overview.md)
  - [CXL 命令列工具鏈全景：cxl / daxctl / ndctl 從檢視到配置](./01_hardware_architecture/pcie/09_cxl_cli_tools.md)
  - [NVLink 技術入門](./01_hardware_architecture/nvlink/nvlink_intro.md)
  - [NVIDIA GPUDirect P2P 技術詳解：節點內 GPU 高速互聯](./01_hardware_architecture/gpudirect/02_gpudirect_p2p.md)
  - [NVIDIA GPUDirect RDMA 與 Storage 技術詳解](./01_hardware_architecture/gpudirect/01_gpudirect_technology.md)
  - [DMA engine：從描述符到完成，一次搬運發生了什麼](./01_hardware_architecture/dma/01_dma_engine.md)
- **異構融合架構與系統效能評估**
  - [NVLink-C2C：晶片級高速互連技術詳解](./01_hardware_architecture/superchips/nvlink_c2c.md)
  - [NVIDIA GB300 NVL72：機架級計算系統架構解析](./01_hardware_architecture/superchips/nvidia_gb300.md)
  - [AI 基礎設施延遲金字塔](./01_hardware_architecture/performance/ai_latency_pyramid.md)

---

## 2. AI 叢集運維與高效能通訊

構建高吞吐 AI 計算叢集的完整運維體系，涵蓋基於 Device Query、nvidia-smi 和 nvtop 的 GPU 狀態監控，InfiniBand (IB) 網路架構與健康檢查，以及 NCCL 分散式通訊庫的基準測試與多節點部署實戰。詳細內容請訪問：**[AI 叢集運維與通訊](03_ai_cluster_ops/README.md)**。

- **GPU 基礎運維**
  - [裝置查詢：Device Query](./03_ai_cluster_ops/01_gpu_ops/01_device_query.md)
  - [誤區解讀：GPU 利用率指標分析](./03_ai_cluster_ops/01_gpu_ops/02_gpu_utilization_myth.md)
  - [狀態監控：nvidia-smi 指南](./03_ai_cluster_ops/01_gpu_ops/03_nvidia_smi_guide.md)
  - [狀態監控：nvtop 指南](./03_ai_cluster_ops/01_gpu_ops/04_nvtop_guide.md)
- **InfiniBand 高效能網路**
  - [理論基礎：IB 網路架構與協議](./03_ai_cluster_ops/02_infiniband/01_ib_network_theory.md)
  - [網路運維：健康檢查與效能監控實戰](./03_ai_cluster_ops/02_infiniband/README.md)
- **資料中心市場與容量**
  - [中國資料中心有多大、建在哪、誰在租：SemiAnalysis 模型精讀](./03_ai_cluster_ops/05_datacenter/china-dc-boom-semianalysis.md) - 逐棟模型精讀：雙速市場（高空置與 AI 容量短缺並存）、四階段史、東數西算的配額傳導機制與需求側五家打法
- **NCCL 分散式通訊測試**
  - [理論基礎：NCCL 教程](./03_ai_cluster_ops/03_nccl/01_nccl_theory.md)
  - [實戰指南：基準測試與多節點部署](./03_ai_cluster_ops/03_nccl/README.md)

---

## 3. 云原生 AI 基礎設施

基於 Kubernetes 的 AI 基礎設施構建方案，涵蓋 NVIDIA Container Toolkit 與 Device Plugin 底層機制、Kueue/HAMi 細粒度 GPU 資源切分與池化、LWS/llm-d 分散式推理排程，以及 JuiceFS、DeepSeek 3FS 等高效能分散式儲存系統的架構實踐。詳細內容請訪問：**[云原生 AI 平台](04_cloud_native_ai_platform/README.md)**。

### 3.1 Kubernetes AI 基礎設施

解析 Kubernetes AI 場景核心元件，包括容器執行時 GPU 支援底層機制、裝置外掛原始碼分析、Kueue 排程整合，以及基於 LWS 的大模型推理排程架構。

- [Kubernetes GPU 管理與 AI 工作負載](./04_cloud_native_ai_platform/k8s/README.md)：云原生 AI 基礎設施建設指南與技術導圖
- [NVIDIA Container Toolkit 原理](./04_cloud_native_ai_platform/k8s/01_nvidia_container_toolkit_analysis.md)：容器使用 GPU 的底層機制解析
- [Device Plugin 原理](./04_cloud_native_ai_platform/k8s/02_nvidia_k8s_device_plugin_analysis.md)：Kubernetes 裝置外掛機制原始碼分析
- [Kueue + HAMi 排程方案](./04_cloud_native_ai_platform/k8s/03_kueue_hami_integration.md)：雲原生作業佇列與細粒度 GPU 共享機制
- [vLLM + LWS：Kubernetes 上的多機多卡推理方案](./04_cloud_native_ai_platform/k8s/04_lws_intro.md)：Kubernetes 原生的大模型推理排程抽象
- [分布式推理框架](./04_cloud_native_ai_platform/k8s/05_llm_d_intro.md)：基於 Kubernetes 的 LLM 推理架構設計
- [Containerd 日志分析](./04_cloud_native_ai_platform/k8s/06_containerd_log_analysis.md)：雲原生容器執行時的日誌排查與分析

### 3.2 GPU 資源管理與虛擬化

提供異構算力環境下的 GPU 資源精細化管理方案，涵蓋硬體級/核心態/使用者態虛擬化機制、CUDA 流與 MPS 排程最佳化，並提供 HAMi 資源隔離、GPU 虛擬化實現對比與生產環境落地配置。

- [GPU 管理技術深度解析](./04_cloud_native_ai_platform/gpu_manager/README.md)：GPU 虛擬化與切分專題的子門戶，按文件、程式碼、配置三條線組織內容

**基礎系列文件**：

- [第一部分：基礎理論篇](./04_cloud_native_ai_platform/gpu_manager/01_basic_theory.md)：構建技術認知框架，解析傳統模式侷限性與核心技術體系
- [第二部分：虛擬化技術篇](./04_cloud_native_ai_platform/gpu_manager/02_virtualization.md)：深入剖析硬體級、核心態與使用者態虛擬化的核心實現機制
- [第三部分：資源管理與最佳化篇](./04_cloud_native_ai_platform/gpu_manager/03_resource_management.md)：探討 GPU 切分、CUDA 流及 MPS 等高效資源排程與最佳化策略
- [第四部分：實踐應用篇](./04_cloud_native_ai_platform/gpu_manager/04_practice.md)：涵蓋環境部署、監控運維及雲平台整合的生產落地指南

**HAMi 專題**：

- [HAMi GPU 資源管理完整指南](./04_cloud_native_ai_platform/gpu_manager/hami/hami-gpu-resources-guide.md)：異構算力管理與隔離實戰指南
- [HAMi-WebUI 的 Prometheus 監控指標](./04_cloud_native_ai_platform/gpu_manager/hami/hami-prometheus-metrics.md)：構建完善的 GPU 虛擬化可觀測性體系
- [KAI vs HAMi 對比分析](./04_cloud_native_ai_platform/gpu_manager/hami/KAI_vs_HAMi_Comparison.md)：以 KAI Scheduler 架構解析為主，含與 HAMi 的對比
- [GPU-Virtual-Service 與 HAMi-Core 實現對比](./04_cloud_native_ai_platform/gpu_manager/hami/flex_ai_intro.md)：解析 CUDA 劫持機制與 LD_PRELOAD 使用者態虛擬化方案，附與 HAMi-Core 的原始碼級對比

**程式碼實現與配置**：

- [完整實現程式碼](./04_cloud_native_ai_platform/gpu_manager/code/)：GPU 排程器、虛擬化攔截與遠端呼叫的參考實現程式碼
- [配置文件集合](./04_cloud_native_ai_platform/gpu_manager/configs/)：提供適用於生產環境和多雲平台的完整部署與配置參考

### 3.3 高效能分散式儲存

針對 AI 訓練中海量小檔案讀取與跨節點共享的效能瓶頸，解析 JuiceFS 資料與後設資料分離架構、DeepSeek 3FS 高效能設計及面向推理的 ICMS (KV Cache) 儲存層機制。

- [AI 儲存：訓練 I/O 和推理 KV Cache 的資料底座](./04_cloud_native_ai_platform/storage/README.md)：JuiceFS、DeepSeek 3FS 與 ICMS 三個子專題的門戶導航
- [JuiceFS 分散式檔案系統](./04_cloud_native_ai_platform/storage/juicefs/README.md)：資料與後設資料分離的架構設計，兼容 POSIX 接口
  - [檔案修改機制分析](./04_cloud_native_ai_platform/storage/juicefs/01_juicefs_file_modification_mechanism_analysis.md)：底層資料一致性與寫入流程解析
  - [後端儲存變更手冊](./04_cloud_native_ai_platform/storage/juicefs/02_juicefs_backend_storage_migration_guide.md)：生產環境下的儲存運維與資料遷移指南
- [DeepSeek 3FS 設計筆記](./04_cloud_native_ai_platform/storage/deepseek_3fs/01_deepseek_3fs_design_notes.md)：高效能儲存系統架構設計與特性分析
- [NVIDIA ICMS 架構解析](./04_cloud_native_ai_platform/storage/inference_context_memory_storage/01_icms_architecture.md)：面向推理的 KV Cache 儲存層架構解析（NVIDIA 已於 2026-03 更名為 CMX，本文沿用釋出時名稱）

---

## 4. 底層計算與異構程式設計

系統級 AI 底層程式設計路徑，剖析 GPU 並行架構、CUDA 執行緒/網格與流處理機制、SIMT 與 Tile-Based (TileLang) 程式設計模型對比、DPU/DOCA 程式設計，以及華為 Ascend NPU/CANN 程式設計。

### 4.1 GPU 與 CUDA 程式設計

涵蓋 NVIDIA 容器映象構建、CUDA 執行緒塊/網格與流併發、SIMT 與 Tile-Based 程式設計模型、TileLang 算子開發、顯存與 PCIe 頻寬調優，以及 GPU 訪問系統記憶體、跨 GPU 顯存互訪和多卡通訊；並連結 200+ Tensor Core/CUDA Core 最佳化核心的進階學習資源。詳細內容請訪問：[GPU 程式設計基礎](02_gpu_programming/README.md)。

**開發環境配置**：

- [NVIDIA 容器環境配置](./02_gpu_programming/01_environment/01_nvidia_container_setup.md)：NVIDIA Container Toolkit 原理與構建指南
- [CUDA 映象構建分析](./02_gpu_programming/01_environment/02_cuda_image_build_analysis.md)：大模型訓練與推理框架的 GPU 映象構建深度解析

**核心程式設計正規化**：

- [GPU 程式設計入門指南](./02_gpu_programming/02_cuda/01_gpu_programming_introduction.md)：平行計算基礎與 CUDA 程式設計模型
- [CUDA 核心概念詳解](./02_gpu_programming/02_cuda/02_cuda_cores.md)：執行緒塊、網格等基礎概念的深度解析
- [CUDA 流詳解](./02_gpu_programming/02_cuda/03_cuda_streams.md)：CUDA 併發程式設計之流處理機制
- [SIMT vs Tile-Based 程式設計模型對比](./02_gpu_programming/02_cuda/04_simt_vs_tile_based.md)：架構差異與演進分析

**多卡與顯存訪問**：

- [GPU 記憶體管理：從推理工程師的日常問題出發](./02_gpu_programming/02_cuda/12_gpu_memory_management.md)：虛擬記憶體、碎片化、DMA、UVM、拓撲與跨行程共享
- [GPU 訪問系統記憶體：MMU、IOMMU、MMIO、mmap、ioremap 五種機制對照](./02_gpu_programming/02_cuda/19_gpu_system_memory_access.md)：GPU 頁表、IOMMU、BAR、CUDA VMM 與 zero-copy / managed memory 的機制對照
- [GPU 顯存互訪：同行程 P2P、跨行程 IPC 與 VMM Fabric](./02_gpu_programming/02_cuda/20_gpu_peer_memory_access.md)：跨 GPU 訪問的地址機制、效能邊界，以及 FlashAttention 與 SGLang KV Cache 的選擇
- [Multi-GPU CUDA 程式設計：從 P2P 到 NCCL](./02_gpu_programming/02_cuda/15_multi_gpu_programming.md)：Peer Access、P2P 頻寬、跨 GPU 同步與 NCCL 集合通信
- [手搓 Attention：從三行迴圈到看懂 FlashAttention](./02_gpu_programming/02_cuda/21_write_attention_from_scratch.md)：小白入門向，四版遞進實跑驗證，含 6 張手繪圖

**Tile-Based 程式設計**：

- [TileLang 快速入門](./02_gpu_programming/03_tilelang/01_tilelang_quick_start.md)：語法詳解、算子開發實戰與效能最佳化技巧
- [57 行程式碼的 FlashAttention](./02_gpu_programming/03_tilelang/02_tilelang_flash_attention.md)：TileLang 前向算子原始碼級拆解，online softmax 與軟體流水演進，附 H100 實測
- [把權重壓到 4-bit](./02_gpu_programming/03_tilelang/03_dequant_gemm_lowprecision.md)：反量化 GEMM 的兩條路徑與快速解碼指令族，wgmma/TMA 發射形態實測

**Kernel 編譯器與 Megakernel**：

- [launch、occupancy、overlap：什麼時候手寫 kernel，什麼時候交給編譯器](./02_gpu_programming/05_compiler/01_kernel-compiler-megakernel.md)：TVM（schedule 分離）、Mirage（三層聯合超優）、MPK（整模型 megakernel）三級遞進，配三 regime 決策軸與 launch-bound 微基准

**效能分析與調優**：

- [nvbandwidth 最佳實踐](./02_gpu_programming/04_profiling/01_nvbandwidth_best_practices.md)：顯存頻寬與 PCIe 傳輸頻寬測量指南

**進階學習資源**：

- [CUDA-Learn-Notes](https://github.com/xlite-dev/CUDA-Learn-Notes)：涵蓋 200+ 個 Tensor Core/CUDA Core 極致最佳化核心示例 (HGEMM, FA2 via MMA and CuTe)
- [Nvidia 官方 CUDA 示例](https://github.com/NVIDIA/cuda-samples)：官方標準範例庫
- [Multi GPU Programming Models](https://github.com/NVIDIA/multi-gpu-programming-models)：多卡程式設計模型示例

### 4.2 DPU 程式設計

基於 DOCA 框架的資料處理單元 (DPU) 開發指南，解析架構元件與網路加速、零複製 DMA、控制平面解除安裝、壓縮、NVMe 模擬及近資料處理等典型場景的程式設計實踐。詳細內容請訪問：[DPU 程式設計](02_dpu_programming/README.md)。

- **DOCA 框架**
  - [DOCA 程式設計入門](./02_dpu_programming/doca/doca_programming_guide.md)：涵蓋架構簡介、核心元件及典型場景程式設計實踐

### 4.3 華為 NPU 程式設計

基於昇騰 NPU 硬件特性和 CANN 軟體棧的系統級程式設計路徑，涵蓋 Da Vinci 架構、PyTorch NPU 適配與遷移、MindSpore 原生框架、Ascend 工具鏈、自定義算子開發，以及 RAG pipeline、FlashAttention、Mini-GPT 和 LLM 推理（Qwen2.5-7B BF16 + LoRA 微調）等端到端實戰。詳細內容請訪問：[華為 NPU 程式設計入門](02_npu_programming/README.md)。

- [NPU 開發環境搭建](02_npu_programming/01_environment/README.md) — CANN 驅動、torch_npu 安裝與版本對齊
- [RAG Pipeline on NPU](02_npu_programming/07_rag_on_npu/01_rag_pipeline_on_npu.md) — Embedding + FAISS + LLM 全鏈路 NPU 化
- [LLM 推理 on NPU](02_npu_programming/11_llm_inference/01_llm_inference_on_npu.md) — Qwen2.5 本地推理、ChatML、NaN 診斷
- [LoRA 微調 on NPU](02_npu_programming/13_finetune/01_lora_finetune.md) — BF16 + peft + 梯度檢查點，HBM 峰值 16.4 GB
- 更多主題：[Da Vinci 架構與 CANN 軟體棧](02_npu_programming/02_ascend_architecture/README.md)、[PyTorch NPU 適配](02_npu_programming/03_pytorch_npu/README.md)、[MindSpore 框架](02_npu_programming/04_mindspore/README.md)、[Ascend 工具鏈](02_npu_programming/05_tools/README.md)、[Ascend C 自定義算子](02_npu_programming/06_advanced/README.md)、[NPU 性能分析](02_npu_programming/08_npu_profiling/README.md)、[FlashAttention](02_npu_programming/09_flash_attention/README.md)、[Mini-GPT](02_npu_programming/10_mini_gpt/README.md)

---

## 5. 大語言模型應用開發與編排

探索以自然語言驅動與 Agent 自主決策為核心的 Software 3.0 開發正規化，包含 Spring AI 企業級 Java 接入、LangGraph 有狀態多智能體圖計算模型，以及 Coze/n8n 無程式碼工作流編排技術。詳細的深度探討可參考 [大模型程式設計指南](98_llm_programming/README.md)。

### 5.1 Java AI 開發

剖析 Java 生態 AI 開發技術棧，透過 Spring AI 工程框架實現企業級 Java 應用對 LLM 能力的接入，並演示基於 Spring AI 構建高效 LLM 代理的工程實踐。

- [Java AI 開發指南](98_llm_programming/java_ai/README.md) - Java 生態系統中的 AI 開發技術總覽。
- [使用 Spring AI 構建高效 LLM 代理](98_llm_programming/java_ai/spring_ai_cn.md) - 基於 Spring AI 框架的企業級 AI 應用開發實踐。

### 5.2 LangGraph 開發

LangGraph 透過圖計算模型解決 LLM 應用在迴圈邏輯與狀態持久化上的瓶頸，提供狀態機機制以支援多輪推理、自我反思的複雜 Agent 工作流構建（如 AI 客服系統 Notebook 實戰）。

- [LangGraph 框架學習資源](98_llm_programming/langgraph/README.md) - LangGraph 框架的學習資源與實踐案例總覽。
- [LangGraph 簡介](98_llm_programming/langgraph/langgraph_intro.md) - LangGraph 的核心概念與入門指南。
- [AI 客服系統實戰](98_llm_programming/langgraph/aics.ipynb) - 基於 LangGraph 構建的 AI 客服系統 Notebook 實戰。

### 5.3 AI 工作流與編排

無程式碼/低程式碼（No-Code/Low-Code）AI 應用落地指南，包含 Coze 私有化部署配置、n8n 多智能體編排實踐，以及 Dify、Ragflow 等主流開源編排平台的架構與商業許可對比。文章收錄於 [7.5 工作流編排與應用平台](#75-工作流編排與應用平台-workflow)（文件在 `06_llm_theory_and_fundamentals/workflow/`）。

---

## 6. 機器學習基礎

基於 NJU 與 SJTU 課程資源的系統化學習路徑，涵蓋線性代數與機率論等數學基礎、SVM 與 HMM 等核心演算法數學原理（《統計學習方法》《PRML》），並提供心臟病預測與房價評估等專案驅動的程式碼實戰。

### 6.1 動手學機器學習

結合特徵工程、模型評估與超參數調優，系統講解監督/無監督學習、整合學習、推薦系統與機率圖模型，配套心臟病預測、鳶尾花分類與房價預測等專案完成從理論推導到工程化實戰的完整閉環。

[動手學機器學習](https://github.com/ForceInjection/hands-on-ML/blob/main/README.md) - 全面的機器學習學習資源庫，包含理論講解、程式碼實現和實戰案例。

**核心特色：**

- **理論與實踐結合**：以 NJU 課程為主線，輔以 SJTU 配套資源，從數學原理到程式碼實現的完整學習路徑。
- **演算法全覆蓋**：涵蓋監督學習、無監督學習、整合學習、推薦系統、機率圖模型及深度學習。
- **專案驅動學習**：提供心臟病預測、鳶尾花分類、房價預測等實戰案例。
- **工程化實踐**：深入特徵工程、模型評估、超參數調優及特徵選擇。

### 6.2 參考資料

彙集 3Blue1Brown 線性代數視覺化、MIT 18.06 線性代數課程、李航《統計學習方法》、周志華《機器學習》與 Bishop《PRML》等經典教材，以及 Andrew Ng Coursera 入門課程、Stanford CS229 進階課程與 Kaggle 競賽實戰平台資源。

**數學基礎：**

- [線性代數的本質](https://www.bilibili.com/video/BV1ys411472E) - 3Blue1Brown 視覺化教程，直觀理解線性變換與矩陣運算。
- [MIT 18.06 線性代數](https://ocw.mit.edu/courses/mathematics/18-06-linear-algebra-spring-2010/) - Gilbert Strang 經典課程，深入矩陣分解與子空間理論。
- [機率論與統計學基礎](https://book.douban.com/subject/35798663/) - 掌握貝葉斯定理、最大似然估計與機率分佈。
- [Datawhale 數學基礎](https://datawhalechina.github.io/math-for-ai/#/) - Datawhale 開源的 AI 數學基礎教程，涵蓋微積分、線性代數與機率論。
- [華東師大矩陣計算課程](https://math.ecnu.edu.cn/~jypan/Teaching/MC/index.html) - 華東師範大學潘建瑜教授的《矩陣計算》課程主頁與講義資源。

**經典教材：**

- **《統計學習方法》** - 李航著，系統闡述感知機、SVM、HMM 等核心演算法的數學原理。
- **《機器學習》** - 周志華著（西瓜書），全面覆蓋機器學習基礎理論與正規化。
- **《模式識別與機器學習》** - Bishop 著（PRML），貝葉斯視角的機器學習聖經。

**線上課程與實戰：**

- [Andrew Ng 機器學習課程](https://www.coursera.org/learn/machine-learning) - Coursera 經典入門，強調直覺理解。
- [CS229 機器學習](http://cs229.stanford.edu/) - 斯坦福進階課程，深入數學推導。
- [Kaggle](https://www.kaggle.com/) - 全球最大的資料科學競賽平台，提供真實資料集與 Notebook 環境。

---

## 7. 大語言模型理論與基礎

LLM 核心理論與架構基石，深入解析 Tokenizer 分詞機制、Embedding 向量表示學習、混合專家模型 (MoE) 與模型壓縮量化技術，並前瞻思維鏈 (CoT) 推理增強、基於 LLM 的意圖識別及 Deep Research (深度研究) 前沿應用架構。

> 詳細內容請訪問：[LLM 理論與基礎](06_llm_theory_and_fundamentals/README.md) - 核心文件門戶，涵蓋基礎理論、深度研究與工作流編排。

### 7.1 基礎理論與概念

拆解 LLM 底層運作機制，包括 Tiktokenizer 分詞編碼、大模型檔案格式儲存規範、Chain-of-Thought (CoT) 邏輯推理增強技術，以及模型幻覺 (Hallucination) 的成因分析與工程化應對策略。

- [基礎理論與概念導航](06_llm_theory_and_fundamentals/llm_basic_concepts/README.md) - LLM 核心概念的完整學習路徑。
- [Transformer 架構詳解](06_llm_theory_and_fundamentals/llm_basic_concepts/transformer/transformer_architecture.md) — 從 RNN 序列瓶頸到自注意力機制，拆解 Attention、FFN、位置編碼、LayerNorm 等核心元件，目標是讀完能看懂 `modeling_llama.py`。
- [手搓 RoPE：一百行 numpy 講透旋轉位置編碼](06_llm_theory_and_fundamentals/llm_basic_concepts/positional_encoding/hand_roll_rope.md) - 一百行 numpy 實測 RoPE 全部主張：配對約定差 3.385、相對不變性 3e-13、隨機向量無衰減、三種外推策略頻率譜，配 5 張手繪圖。
- [當記憶成為模型狀態：MemT-1.0 的架構、訓練與邊界](06_llm_theory_and_fundamentals/llm_basic_concepts/memory_native/memt_1_0_memory_native.md) - 記憶原生基礎模型：local/hyper memory、GDN-2、34B token 訓練與 11 項記憶基準，含原始碼核對與許可/部署邊界。
- [EdgeRock-4B 拆解：把 KV Cache 變成固定容量記憶](06_llm_theory_and_fundamentals/llm_basic_concepts/memory_native/edgerock-4b-constant-memory.md) - 用 1024 token 區域性視窗與 1024 條 RMA 錨點替換 8 層全注意力，历史固定 97.76 MiB/序列；拆 RMA 機制、訓練路徑、AIME/吞吐資料與口徑邊界。
- [Andrej Karpathy ： Deep Dive into LLMs like ChatGPT （B 站影片）](https://www.bilibili.com/video/BV16cNEeXEer) - 深度學習領域權威專家的 LLM 技術解析。
- [大模型基礎元件 - Tokenizer](https://zhuanlan.zhihu.com/p/651430181) - 文字分詞與編碼的核心技術。
- [解密大語言模型中的 Tokens](06_llm_theory_and_fundamentals/llm_basic_concepts/token/README.md) - Token 機制的深度解析與實踐應用。
  - [LLM Token 機制詳解](06_llm_theory_and_fundamentals/llm_basic_concepts/token/llm_token_intro.md) - Token 的基礎概念與應用原理。
  - [手搓 Tokenizer：從字元級到 BPE](06_llm_theory_and_fundamentals/llm_basic_concepts/token/hand_roll_bpe_tokenizer.md) - 一百行 Python 手搓 BPE，壓縮曲線與過擬合實測，tiktoken 同語料對照。
  - [Tiktokenizer 線上版](https://tiktokenizer.vercel.app/?model=gpt-4o) - 交互式 Token 分析工具。
- [一文讀懂思維鏈（Chain-of-Thought, CoT）](06_llm_theory_and_fundamentals/llm_basic_concepts/cot/chain_of_thought_cot_intro.md) - 推理能力增強的核心技術。
- [大模型的幻覺及其應對措施](06_llm_theory_and_fundamentals/llm_basic_concepts/hallucination/llm_hallucination_and_mitigation.md) - 幻覺問題的成因分析與解決方案。
- [AI 水印：道高一尺，魔高一丈](06_llm_theory_and_fundamentals/llm_basic_concepts/watermark/ai_watermark_attack_and_defense.md) - AI 水印的攻防博弈：嵌入與檢測技術、去除攻擊與工程應對。
- [大模型文件格式完整指南](06_llm_theory_and_fundamentals/llm_basic_concepts/file_formats/llm_file_formats_complete_guide.md) - 模型儲存與部署的技術規範。

### 7.2 嵌入技術與表示學習

離散文字到連續向量的表示學習體系，解析 Text Embeddings 的演變歷史、距離度量演算法，以及獨立 Embedding 模型與 LLM 原生 Embedding 層的架構選型與應用權衡。

- [文字嵌入學習資源](06_llm_theory_and_fundamentals/llm_basic_concepts/embedding/README.md) - 深入探討文字嵌入原理與應用的綜合指南門戶。
- [深入瞭解文字嵌入技術](06_llm_theory_and_fundamentals/llm_basic_concepts/embedding/text_embeddings_comprehensive_guide.md) - 全面解析 Text Embeddings 的演變、距離度量及應用。
- [LLM 嵌入技術詳解：圖文指南](06_llm_theory_and_fundamentals/llm_basic_concepts/embedding/LLM_embeddings_explained_visual_guide.zh-CN.md) - 視覺化直觀理解大模型 Embeddings。
- [文字嵌入技術快速入門](06_llm_theory_and_fundamentals/llm_basic_concepts/embedding/text_embeddings_guide.md) - 快速上手文字嵌入技術的實用指南。
- [大模型 Embedding 層與獨立 Embedding 模型：區別與聯絡](06_llm_theory_and_fundamentals/llm_basic_concepts/embedding/embedding.md) - 嵌入層架構設計與選型策略。

### 7.3 高階架構與應用技術

探索提升模型效能與壓縮比的關鍵技術，透過視覺化指南解析 MoE 稀疏激活原理與量化加速機制，並結合 ChatBox 實戰剖析基於 LLM 的語義理解與意圖檢測系統設計。

- [大模型視覺化指南](https://www.maartengrootendorst.com/) - 大模型內部機制的視覺化分析。
- [混合專家模型 (MoE) 視覺化指南](06_llm_theory_and_fundamentals/llm_basic_concepts/moe/mixture_of_experts_moe_visual_guide.zh-CN.md) - 深入解析 MoE 架構原理。
- [量化技術視覺化指南](06_llm_theory_and_fundamentals/llm_basic_concepts/quantization/visual_guide_to_quantization.md) - 模型壓縮與加速的核心技術。
- [基於 LLM 的意圖檢測](06_llm_theory_and_fundamentals/llm_basic_concepts/intent_detection/intent_detection_using_llm.zh-CN.md) - 意圖識別系統設計與實現。
  - 參見：[ChatBox 意圖識別與語義理解](06_llm_theory_and_fundamentals/llm_basic_concepts/intent_detection/chatbox_intent_recognition_and_semantic_understanding.md) - ChatBox 中意圖識別的實際案例分析。

### 7.4 Deep Research 深度研究

多步推理規劃在複雜資訊檢索中的應用，解構 DeepWiki、通義 DeepResearch 與 Cursor DeepSearch 等主流系統架構，並提供面向科研助手與複雜訂單履約場景的 Agent 需求分析與架構設計方案。

- [Deep Research 深度研究資源指南](06_llm_theory_and_fundamentals/deep_research/README.md) - Deep Research 相關的技術解析與實踐案例總覽。
- [《Building Research Agents for Tech Insights》深度解讀](06_llm_theory_and_fundamentals/deep_research/research_agents/building_research_agents_for_tech_insights.md) - 技術洞察研究 Agent 構建指南。
- [DeepWiki 使用方法與技術原理](06_llm_theory_and_fundamentals/deep_research/deepwiki/deepwiki_usage_and_technical_analysis.md) - 技術實現細節與使用指南。
- [DeepWiki 深度研究報告](06_llm_theory_and_fundamentals/deep_research/deepwiki/deepwiki_research_report.pdf) - DeepWiki 的研究成果與深度分析報告。
- [通義 DeepResearch 深度分析](06_llm_theory_and_fundamentals/deep_research/research_agents/qwen_deepresearch_analysis.md) - 對通義 DeepResearch 的技術剖析。
- [Cursor DeepSearch 解析](06_llm_theory_and_fundamentals/deep_research/research_agents/cursor-deepsearch.md) - Cursor AI 深度搜尋功能技術分析。
- [Databricks Data Agent](06_llm_theory_and_fundamentals/deep_research/research_agents/databricks_data_agent.md) - Databricks 資料 Agent 技術架構與實現。
- [科研助手 Agent 設計](06_llm_theory_and_fundamentals/deep_research/design/research_assistant.md) - 面向研究者全生命週期的智慧助手設計方案。
- [訂單履約 Agent 需求分析](06_llm_theory_and_fundamentals/deep_research/design/order_fulfillment_agent_requirement_analysis.md) - 複雜業務場景下的 Agent 系統需求分析。
- [訂單履約 Agent 系統設計](06_llm_theory_and_fundamentals/deep_research/design/order_fulfillment_agent_system_design.md) - 複雜業務場景下的 Agent 系統架構與實現。

### 7.5 工作流編排與應用平台 (Workflow)

將 LLM 能力轉化為自動化業務流，橫向評測 Dify、AnythingLLM 等開源應用編排平台功能與商用許可，並提供基於 Coze 與 n8n 構建多智能體系統的私有化部署實踐。

- [工作流編排指南](06_llm_theory_and_fundamentals/workflow/README.md) - 大模型應用編排平台與自動化工作流實踐總覽。
- [開源大模型應用編排平台功能與商用許可對比分析](06_llm_theory_and_fundamentals/workflow/open_source_llm_orchestration_platforms_comparison.md) - Dify、AnythingLLM、Ragflow 與 n8n 的深度橫評。
- [使用 n8n 構建多智能體系統的實踐指南](06_llm_theory_and_fundamentals/workflow/n8n_multi_agent_guide.md) - 基於 n8n 構建 Multi-Agent 系統。
- [Coze 部署和配置手冊](06_llm_theory_and_fundamentals/workflow/coze_deployment_and_configuration_guide.md) - Coze 平台的私有化部署與配置指南。

### 7.6 參考書籍

精選《大模型技術 30 講》《Hands-On Large Language Models》《百面大模型》等著作，涵蓋從 Transformer 理論解構、模型從零預訓練到全棧工程落地的系統性閱讀指南。

- [從晶片到 Agent：AI 基礎設施的閱讀地圖](99_misc/book-recommendations.md) - 按本倉庫章節體系組織的系統書單，覆蓋硬體、叢集、云原生、GPU 程式設計、LLM 理論/訓練/推理、Agent、RAG 全鏈路。
- [大模型技術 30 講](https://mp.weixin.qq.com/s/bNH2HaN1GJPyHTftg62Erg) - 大模型時代，智能體崛起：從技術解構到工程落地的全棧指南。
  - 第三方：[大模型技術 30 講（英文 & 中文批注）](https://ningg.top/Machine-Learning-Q-and-AI) - 帶有中英文對照及批註的版本。
- [大模型基礎](https://github.com/ZJU-LLMs/Foundations-of-LLMs)

  <img src="https://raw.githubusercontent.com/ZJU-LLMs/Foundations-of-LLMs/main/figure/cover.png" height="300"/>

- [Hands-On Large Language Models](https://github.com/HandsOnLLM/Hands-On-Large-Language-Models)

  <img src="https://raw.githubusercontent.com/HandsOnLLM/Hands-On-Large-Language-Models/main/images/book_cover.png" height="300"/>

- [從零構建大模型](https://mp.weixin.qq.com/s/FkBjsQmeXEPlsdFXETYSng) - 從理論到實踐，手把手教你打造自己的大語言模型。
- [百面大模型](https://mp.weixin.qq.com/s/rBJ5an0pr3TgjFbyJXa0WA) - 打通大模型求職與實戰的關鍵一書。
- [圖解大模型：生成式 AI 原理與實踐](https://mp.weixin.qq.com/s/tYrHrpMrZySgWKE1ECqTWg) - 超過 300 幅全綵圖示 × 實戰級專案程式碼 × 中文獨家 DeepSeek-R1 彩蛋內容。

---

## 8. 大模型訓練

涵蓋從 SFT 監督微調、RL 後訓練到大規模預訓練的完整工程路徑，結合 70B 模型從零訓練實戰，剖析資料清洗、硬體叢集配置、超參數最佳化 (CARBS) ，以及面向 AIOps 場景的 Kubernetes 模型後訓練 (Post-Training) 與評估框架設計。詳細指南可參考：[模型訓練與微調總覽](05_model_training_and_fine_tuning/README.md) 。

### 8.1 指令微調與監督學習

基於高品質指令-響應資料的模型行為對齊技術，包含 Qwen 2 大模型的微調 Notebook 實戰，以及垂直領域模型 SFT 的理論指南與最佳實踐。

- [SFT 微調實戰與指南](05_model_training_and_fine_tuning/sft_example/README.md) - 包含基於 Qwen2 的微調程式碼實戰及垂域模型微調理論指南。
- [Qwen 2 大模型指令微調實戰](05_model_training_and_fine_tuning/sft_example/train_qwen2.ipynb) - 基於 Qwen 2 的指令微調 Notebook 實踐。
- [Qwen 2 指令微調教程](https://mp.weixin.qq.com/s/Atf61jocM3FBoGjZ_DZ1UA) - 詳細的圖文教程。
- [一文入門垂域模型 SFT 微調](05_model_training_and_fine_tuning/sft_example/一文入门垂域模型SFT微调.md) - 垂直領域模型的監督微調技術與應用實踐。

### 8.2 大規模模型訓練實踐

覆盤 70B 參數模型從零訓練全生命週期，深度解析開源資料集清洗與評估策略、裸金屬基礎設施配置與自動化指令碼，以及擴展至超大規模參數的最佳化器選型策略。

- [Training a 70B model from scratch: open-source tools, evaluation datasets, and learnings](https://imbue.com/research/70b-intro/) - 70B 參數模型從零訓練的完整技術路徑與經驗總結。
- [Sanitized open-source datasets for natural language and code understanding: how we evaluated our 70B model](https://imbue.com/research/70b-evals/) - 大規模訓練資料集的清洗、評估與品質控制方法。
- [From bare metal to a 70B model: infrastructure set-up and scripts](https://imbue.com/research/70b-infrastructure/) - 大模型訓練基礎設施的搭建、配置與自動化指令碼。
- [Open-sourcing CARBS: how we used our hyperparameter optimizer to scale up to a 70B-parameter language model](https://imbue.com/research/70b-carbs/) - 超參數最佳化器在大規模模型訓練中的應用與調優策略。

### 8.3 模型後訓練與評估

保障模型生產環境表現的評估體系，解析 AIOps 後訓練策略、基於 Kubernetes 的自動化模型評估框架構建，以及基準測試資料集的生成方法。

- [AIOps 後訓練技術](05_model_training_and_fine_tuning/ai_ops_design/aiops_post_training.md) - 面向智慧運維場景的模型後訓練技術與實踐。
- [Kubernetes 模型評估框架](05_model_training_and_fine_tuning/ai_ops_design/kubernetes_model_evaluation_framework.md) - 基於 K8s 的大模型評估框架設計與實現。
- [Kubernetes AIOps 基準測試生成框架](05_model_training_and_fine_tuning/ai_ops_design/kubernetes_aiops_benchmark_generation_framework.md) - 自動化生成 AIOps 基準測試資料集的框架設計。

### 8.4 RL 後訓練的系統約束

SFT 之后把推理能力推上去要靠 RL，而 RL 的 rollout 由推理引擎產生、梯度由訓練框架計算——兩個系統對同一份權重算出的 log-probability 並不相同，這個差異會直接把策略梯度帶偏。

- [訓練不穩，可能是推理引擎的鍋：Miles 的三條對齊路線](05_model_training_and_fine_tuning/rl_training/miles-train-rollout-alignment.md) - 逐位對齊、量化路徑統一、路由重放與重要性取樣修正三條路線的原始碼級拆解，含各自的適用邊界與實測數字。

---

## 9. 大模型推理

企業級大模型推理系統落地指南，解構 Mooncake 以 KV Cache 為中心的排程架構、vLLM/llm-d 核心推理框架底層機制，深度剖析 LMCache 多層儲存體系與 Tair 跨實例快取共享，並提供 DeepSeek 等前沿模型在多硬體平台的部署調優實踐。

### 9.1 推理系統架構設計

剖析現代推理系統的底層架構創新，重點解構 Mooncake 等以 KV Cache 為中心的高效 LLM 排程系統設計模式與效能調優策略。

- [手搓 KV Cache：從靜態預留到 PagedAttention 的頁表](09_inference_system/kv_cache/01_concepts/01_basic/03_hand_roll_kv_cache.md) - 可執行模擬器實測三種顯存管理策略：碎片入住失敗與 5 倍容量的數字來源。
- [手搓 MLA：從 MHA 到 weight absorption](09_inference_system/kv_cache/01_concepts/01_basic/07_hand_roll_mla.md) - 四版注意力遞進 + 真實權重驗證吸收等價（fp32 逐位一致），KV 壓縮三口徑辨析。
- [手搓系列導航](hand_roll_series.md) - 手搓系列 5 篇的閱讀順序與實測產出彙總。
- [Mooncake 架構詳解：以 KV Cache 為中心的高效 LLM 推理系統設計](09_inference_system/kv_cache/02_systems/04_mooncake/01_mooncake_architecture.md) - 新一代推理系統的架構創新與效能最佳化策略
- [當 KV Cache 裝不進記憶體：FAST'26 五篇論文給出的五個不同答案](09_inference_system/kv_cache/03_fast26/01_fast26-kv-storage-five-scenarios.md) - FAST'26「AI and LLMs」九篇論文中五篇精讀的五象限彙總：端側/智能體/對話/資料中心/冷啟動各自的核心矛盾、招式與數字，共同支點是可復現的 I/O 特徵；附 4 篇 Agent 精讀報告
- [當 KV 裝不進顯存：四篇論文的四種記憶體賬，與一個「統一名稱空間 + 成本旋鈕」的設想](09_inference_system/kv_cache/04_memory_tiering/01_memory-tiering-overview.md) - DirectKV / NEO / eLLM / Strata 四篇論文記憶體層級路線的橫切總綱：去搬運 / 挪計算 / 並賬本 / 重排排程，附按條件選路的對號表與「數字怎麼讀」口徑清單
- [當 KV Cache 跨過信任邊界：三篇論文給出的三種洩露面，與一個「共享層級 + 預設加密」的設想](09_inference_system/kv_cache/05_kv_security/01_kv-security-overview.md) - 讀行為 / 讀資料 / 讀時延三種取證位置：PromptPeek / Shadow in the Cache / Auditing Prompt Caching，附按角色選路的對號表，以及取證距離與防禦動作同軸的成本賬
- [當複用跨出同字首與同模型：四條路線與四種對齊開銷](09_inference_system/kv_cache/06_kv_reuse/01_kv-reuse-overview.md) - KVLink（文件級預計算 + link token）、DroidSpeak（跨微調變體共享 + 關鍵層重算）與 CacheBlend（免訓練非字首複用）四條路線與「數字怎麼讀」口徑清單
- [當壓縮表示被繼續使用：三篇論文給出的三種二次決策](09_inference_system/kv_cache/07_kv_compression/01_kv-compression-overview.md) - Self-Indexing KVCache / SALS / EchoKV 把壓縮產物繼續用作檢索索引、token 選擇場與重建素材
- [TTFT 多了 15 毫秒之后：一套實證過的 KV Cache 效能分析方法論](09_inference_system/kv_cache/08_methodology/01_kv-cache-perf-methodology.md) - 真機排查總結的六件工具與六類問題：時鐘鏈閉合、排除鏈判死、儀器紀律、native 對齊，配操作清單與脫敏後的實測數字
- [當 Agent 流量成為推理系統的主要負載](09_inference_system/agent_serving/agent-workload-serving.md) - KV 生命週期錯配、排程語義失真、會話粘性與容量公式失效：Agent 負載下的四連鎖問題與兩引擎原始碼級現狀
- [約束解碼的效能賬單：vLLM 與 SGLang 的結構化輸出實現拆解](09_inference_system/agent_serving/constrained-decoding-engines.md) - 結構化輸出的編譯賬/每步賬/互動賬：雙引擎實現逐項對照與 jump-forward 差異
- [線性注意力與推理系統](09_inference_system/linear_attention/README.md) - delta-rule 一脈（KDA/Gated DeltaNet）落地後的系統挑戰：prefill 串行化、狀態檢查點快取、狀態語義深水區——總覽 + 機制/排程/狀態語義四篇
- [HBF 是 HBM 的替代嗎？單位儲存便宜了，Token 成本卻可能更高](09_inference_system/hbf-vs-hbm.md) - Hot Chips 2026 的 (β, α) 座標系與 $/token 公式：單位容量便宜 8–16 倍、單位容量頻寬只有 HBM 的 1/25，折算成頻寬單價反而貴 1.7 倍，HBF 只在一個很窄的低頻寬區間裡划算
- [Engram：條件記憶與主機記憶體參數](09_inference_system/engram/README.md) - DeepSeek 條件記憶（N-gram Embedding）首篇原始碼深讀：官方 422 行 demo + SGLang 巨頁手術，LPDDR 換 HBM 的優勢與代價逐項算賬
- [DeepSeek 把家底搬上了昇騰：六個元件、三種雙端模式與一份 950 微架構報告](09_inference_system/deepseek_ascend/deepseek-ascend-open-source.md) - 逐倉拆解 TileLang/DeepGEMM/DeepEP/TileKernels/FlashMLA/DeepSelect 的昇騰版：三種雙端模式、950 微架構要點與誠實缺口清單
- [KV 壓縮推到極限：從架構改造到分層快取](09_inference_system/kv_cache/07_kv_compression/README.md) - V4 與 K3 架構重寫後的 KV 體積賬（1M 上下文 250GB 量級 → 個位數 GB）、V4.1-Flash 技術報告精讀（CED / CSA2 / FP4 KV）與 HiCache 七池八池的系統後果，三篇互為時間線
- [Prefill 與 Decode：兩階段的推理機制](09_inference_system/prefill_decode/README.md)（[互動視覺化](09_inference_system/prefill_decode/prefill_decode_visual.html) · [校驗指令碼](09_inference_system/prefill_decode/prefill_decode_validate.py)） - 逐步標註每步矩陣形狀與計算量，從 compute-bound vs memory-bound 推導 GQA、量化、PagedAttention、Offloading、PD 分離的必然性
  - [Continuous Batching 深度解析](09_inference_system/prefill_decode/continuous_batching.md) - 靜態批處理的三重浪費、vLLM V1 的 token-level 統一排程與 SGLang prefill-first 主動驅逐
- [大模型推理並行策略](09_inference_system/parallelism/parallelism_strategies.md)（[互動視覺化](09_inference_system/parallelism/parallelism_visual.html)） - DP、TP、PP、EP、SP 五種策略的統一拆解與混合部署案例
  - [專家並行（EP）深度解析](09_inference_system/parallelism/expert_parallelism_deep_dive.md) - EP 獨立深度文章：DP/TP/PP 為什麼解決不了 MoE、All-to-All 通信模式、EP+DP 耦合、DeepEP 低延遲後端、EPLB 負載均衡、選型決策

### 9.2 核心框架與平台

雲原生推理基礎設施全景，涵蓋基於 LWS 的 Kubernetes 多機多卡分散式推理排程，以及高性能 llm-d 框架在不同叢集規模下的技術選型與最佳實踐。

- [推理最佳化技術方案](09_inference_system/README.md) - 企業級推理最佳化全景指南，涵蓋叢集規模分析、核心最佳化技術及實施路徑
- [vLLM + LWS：Kubernetes 上的多機多卡推理方案](04_cloud_native_ai_platform/k8s/04_lws_intro.md) - 大模型推理在 Kubernetes 上的最佳實踐
- [云原生高性能分布式 LLM 推理框架 llm-d 介紹](04_cloud_native_ai_platform/k8s/05_llm_d_intro.md) - 雲原生架構下的高效能推理服務棧
- **[nano-vllm](https://github.com/ForceInjection/nano-vllm) ★** — 從零構建的輕量級 vLLM 實現（~1400 行 Python），在極簡程式碼中保留 PagedAttention、連續批處理、張量並行與 CUDA Graph 等核心機制，推理速度與 vLLM 相當。配套 8 課 **[線上 PPT 實戰課程](https://forceinjection.github.io/nano-vllm/)**，逐步拆解 Sequence 生命周期、排程器佇列、KV Cache 管理與注意力算子分支

### 9.3 KV Cache 核心技術

長文字與高併發推理的核心瓶頸突破，解析自迴歸生成機制、Prefix Caching 字首快取與 RadixTree 自動複用原理，並深度對比 LMCache 分層架構與阿里雲 Tair KVCache 的企業級分散式部署方案。

- [KV Cache 技術體系](09_inference_system/kv_cache/README.md) - KV Cache 技術體系全景指南
- [KV Cache 原理簡介](09_inference_system/kv_cache/01_concepts/01_basic/01_kv_cache_basics.md) - 自迴歸生成的挑戰與 KV Cache 的工作機制
- [Prefix Caching 技術詳解](09_inference_system/kv_cache/01_concepts/02_prefix_caching/02_prefix_caching.md) ([配套 PPT](09_inference_system/kv_cache/01_concepts/02_prefix_caching/02_prefix_caching.pptx)) - 從原理到 vLLM/LMCache 實踐的字首快取技術
- [RadixAttention 技術詳解](09_inference_system/kv_cache/01_concepts/02_prefix_caching/01_radix_attention.md) ([配套 PPT](09_inference_system/kv_cache/01_concepts/02_prefix_caching/01_radix_attention.pptx)) - 基於 Radix Tree 自動複用 KV Cache 的核心原理與 SGLang 實踐

#### 9.3.1 LMCache 核心架構與後端實現

本小節詳細解析 LMCache 的四層儲存架構及其在跨實例快取複用中的技術細節。

**基礎與架構概覽**：

- [LMCache 原始碼分析指南](09_inference_system/kv_cache/02_systems/01_lmcache/README.md) - 完整學習路徑與文件索引
- [LMCache 架構概覽](09_inference_system/kv_cache/02_systems/01_lmcache/01_lmcache_overview.md) - 四層儲存架構 (L1-L4)、核心元件互動與典型工作流
- [vLLM KV Offloading 與 LMCache 深度對比](09_inference_system/kv_cache/01_concepts/07_offloading/01_kv_offloading.md) - 架構設計、儲存層級及跨實例共享能力上的核心差異與效能權衡

**核心執行時元件**：

- [LMCacheEngine 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/03_lmcache_engine.md) - 核心排程中樞、非同步事件管理與層級流水線
- [LMCacheConnector 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/02_lmcache_connector.md) - vLLM 整合介面卡、檢視轉換與流水線載入
- [分層儲存架構與排程機制](09_inference_system/kv_cache/02_systems/01_lmcache/05_lmcache_storage_overview.md) - StorageManager 排程器、Write-All 策略與 Waterfall 檢索

**儲存後端實現**：

- [LocalCPUBackend 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/06_local_cpu_backend.md) - 本地 CPU 記憶體後端與併發控制
- [LocalDiskBackend 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/09_local_disk_backend.md) - O_DIRECT 直通 I/O 與非同步最佳化
- [P2PBackend 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/07_p2p_backend.md) - RDMA 零複製與去中心化傳輸
- [GdsBackend 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/10_gds_backend.md) - GPUDirect Storage 零複製
- [NixlStorageBackend 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/11_nixl_backend.md) - 高效能網路儲存、S3 物件儲存對接
- [Remote Connector 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/12_remote_connector.md) - Redis/S3/Mooncake 多後端適配
- [PDBackend 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/08_pd_backend.md) - 預填充-解碼分離、Push-based 主動推送機制

**控制面**：

- [LMCache Controller (控制平面)](09_inference_system/kv_cache/02_systems/01_lmcache/04_lmcache_controller.md) - 叢集後設資料管理、ZMQ 三通道通訊與節點協調
- [LMCache Server 原始碼分析](09_inference_system/kv_cache/02_systems/01_lmcache/13_lmcache_server.md) - 輕量級中心化儲存服務、自定義 TCP 協議

**高階特性**：

- [CacheBlend 技術詳解](09_inference_system/kv_cache/02_systems/01_lmcache/14_cache_blend.md) - RAG 場景下的動態融合機制、選擇性重算與精度保持
- [CacheGen 技術詳解](09_inference_system/kv_cache/02_systems/01_lmcache/15_cachegen.md) - KV Cache 壓縮與流式傳輸、自適應量化與算術編碼

#### 9.3.2 阿里云 Tair KVCache

本小節介紹阿里雲企業級的 KVCache 管理系統架構及大規模部署實踐。

- [Tair KVCache 架構與設計深度分析](09_inference_system/kv_cache/02_systems/02_tair_kvcache/01_tair-kvcache-architecture-design.md) - 阿里雲企業級 KVCache 管理系統架構詳解，包含與 LMCache 的全面對比分析、中心化管理模式及大規模部署最佳實踐

#### 9.3.3 SGLang 推理引擎

SGLang 以 RadixAttention 字首快取和高效排程器著稱，涵蓋 KV Cache 管理原始碼系列（UnifiedRadixTree、KV Pool、HiCache、HiSparse）、排程器原始碼（Chunked Prefill、Overlap Scheduling）、版本解讀、超大規模推理調優實踐與互動式視覺化演示。

- [SGLang 內容索引](09_inference_system/sglang/README.md) - 原始碼分析、案例研究與視覺化演示導航
- [SGLang UnifiedRadixTree：一棵樹，四種注意力](09_inference_system/sglang/sglang-unified-radix-tree.md) - 0.5.16 預設化的統一 Radix Tree：FULL/MAMBA/SWA 統一索引與可插拔快取語義
- [SGLang 0.5.16 解讀：一棵 Radix Tree 統一四種 Attention，DSpark 讓投機解碼不再一刀切](09_inference_system/sglang/sglang-0.5.16-release.md) - 574 個 PR 的重大版本：DSpark 置信度驅動投機解碼與 Inkling 975B Day-0 支持，含破壞性變更清單
- [HiCache 深入詳解](09_inference_system/sglang/hicache_deep_dive.md) - SGLang 分層 KV Cache 架構（L1/L2/L3）與 HiRadixTree 原始碼分析
- [SGLang KV Pool 管理：物理儲存、Radix Tree 索引與請求檢視](09_inference_system/sglang/sglang-kv-pool-management.md) - KV Pool/Radix Tree/ReqToTokenPool 三層結構與 L1→L2→L3 多級逐出
  - [KV Cache L1↔L2 資料流深度分析](09_inference_system/sglang/sglang-kv-cache-dataflow-analysis.md) - write_backup/eviction/load_back 逐操作程式碼路徑與 CXL 場景適配
- [三本賬：圖解 GLM-5.3-Flash 的 KV Cache 布局](09_inference_system/sglang/glm53-flash-kv-layout.md) - 按一個 token、一個 request、HBM KV Pool + RadixTree、DRAM 四個問題拆 45 層裡的三本賬：11 層 MLA latent KV、11 層 DSA indexer、34 層 KDA state；含 7.26 KB/token 邊界（KDA 預設 fp32、按 5 個 state slot/request 另算）、indexer page 布局、`value` / `host_value` 與 HiCache 覆蓋範圍（只換出 KV + KDA，indexer 和 compress tail 沒有 HiCache 副本），配五張手繪圖
- [SGLang 排程器](09_inference_system/sglang/sglang-scheduler.md) - Prefill > Decode 優先順序決策、PrefillAdder 五種准入預算與 retract_decode 記憶體壓力保護
- [SGLang Overlap Scheduling 深度解析](09_inference_system/sglang/sglang-overlap-scheduling.md) - CPU-GPU 雙流水線：result_queue 打破序列依賴與 FutureMap relay 輸入
- [SGLang HiSparse 深度解析](09_inference_system/sglang/hisparse_deep_dive.md) - 將 DSA 稀疏選擇提升到系統 coordinator 層：page 級選擇性載入與雙模式索引轉換
- [SGLang Scaling Pain 超大規模推理調優案例](09_inference_system/sglang/sglang-scaling-case-study.md) - 利用投機取樣定位 PD 分離架構下的 KV Cache 競態與時序缺陷
- [Chunked Prefill 原理與程式碼實現](09_inference_system/sglang/chunked_prefill.md) - 長 prompt 切分、PrefillAdder 截斷決策、排程迴圈與 HiCache 協同的完整原始碼級分析
- [SGLang 推理流水線視覺化](09_inference_system/sglang/assets/inference-pipeline.html) - 交互式 Prefill & Decode 流水線演示，追蹤 HiCache 三級快取全流程
- [SGLang 排程器視覺化](09_inference_system/sglang/assets/scheduler-visual.html)（[GIF 預覽](09_inference_system/sglang/assets/scheduler-visual.gif)） - 模擬多請求到達與 Chunked Prefill 的排程過程

### 9.4 推理最佳化技術體系

多維度提升推理吞吐的系統級技術，包含 vLLM 注意力機制演進 (MLA/NSA)、CUDA Graphs 與 Hybrid KV Cache 管理，結合參數顯存佔用估算、KV Block Manager 記憶體機制與 Layer-wise 流水線進行深度調優。

**vLLM 核心機制分析**：

- [vLLM 推理系統最佳化與分析](09_inference_system/vllm/README.md) - vLLM 底層機制和系統架構的深度解構
- [vLLM 注意力機制演進與支援全景](09_inference_system/vllm/module_analysis/attention_mha_mla_nsa.md) ([配套 PPT](09_inference_system/vllm/module_analysis/attention_mha_mla_nsa.pptx)) - 從 MHA 到 MLA 與 NSA 的架構解析及 vLLM 支援現狀
- [vLLM 內建 KV Cache Offloading 模組解析](09_inference_system/vllm/module_analysis/native_kv_offloading.md) - 原生 KV Cache CPU Offloading 功能原理與實現
- [vLLM Hybrid KV Cache Manager](09_inference_system/vllm/module_analysis/hybrid_kv_cache_manager_deep_dive.md) - vLLM 針對混合注意力架構的顯存最佳化機制
- [vLLM CUDA Graphs 深度解析](09_inference_system/vllm/module_analysis/cuda_graph_deep_dive.md) - 深入探討 vLLM 解碼階段 CUDA Graphs 的核心機制與實踐
- [vLLM Router 架構解析](09_inference_system/vllm/routing/router.md) - 高性能、輕量級請求轉發系統
- [vLLM Semantic Router](09_inference_system/vllm/routing/semantic_router_deep_dive.md) - 基於語義的智慧路由策略
- [DeepSeek V4 長上下文注意力支援解析](09_inference_system/vllm/module_analysis/deepseek_v4_attention_support.md) - 深入探討 vLLM 對 DeepSeek V4 模型高效注意力機制的底層實現與算子最佳化
- [PagedAttention 退役的技術原因](09_inference_system/vllm/module_analysis/pagedattention_retirement.md) - 從 MLA 不兼容、兩遍遍歷浪費頻寬、無原生 FP8 計算、模板爆炸等角度分析 PagedAttention 被取代的技術必然性
- [gpu-memory-utilization 的謝幕：vLLM 如何用「實測」替代「估算」](09_inference_system/vllm/module_analysis/gpu-memory-utilization-retirement.md) - VMM 機制、四步顯存核算流程與可增長 KV Cache 的前瞻分析
- [MLA 的 TP 切分：KV Cache 冗余分析](09_inference_system/vllm/module_analysis/mla_tp_kv_redundancy.md) - MLA 將 KV cache 壓縮到標準 MHA 的 ~1.8%，但 TP 對其顯存節省為 0%，冗餘率達 87.5%

**顯存與快取最佳化**：

- [LLM 顯存佔用分析與計算](09_inference_system/memory_calc/memory_analysis.md) - 模型參數、KV Cache 與中間激活值的顯存估算方法
- [KV Block Manager 分析](09_inference_system/kv_cache/02_systems/03_kvbm/01_KVBM_Analysis.md) - KV Cache 記憶體管理機制深度解析
- [分層流水線技術](09_inference_system/kv_cache/01_concepts/07_offloading/02_layerwise_pipeline.md) - Layer-wise Pipeline 技術原理與效能最佳化

**網路與模型工具**：

- [模型最佳化導航](09_inference_system/model_optimization/README.md) - 模型最佳化技術概覽與導讀
- [NIXL 網路儲存介紹](09_inference_system/kv_cache/02_systems/05_nixl/01_nixl_introduction.md) - 高效能網路儲存架構與應用
- [NVIDIA 模型最佳化器](09_inference_system/model_optimization/nvidia_model_optimizer.md) - NVIDIA 模型最佳化工具鏈詳解
- [圖解投機解碼](09_inference_system/model_optimization/illustrated-speculative-decoding.md) - Speculative Decoding 的核心思想、系統實現與工程調優要點
- [一次前向，白賺 4 個 token：DFlash 2 塊擴散投機解碼技術詳解](09_inference_system/model_optimization/dflash-block-diffusion-speculative-decoding.md) - 塊擴散式的投機解碼架構與實現深度解析
- [draft 不再重建历史：DLite 的 history-free 投機解碼](09_inference_system/model_optimization/dlite-history-free-speculative-decoding.md) - Agent 負載下把歷史建模留給 target 的投機解碼：2.07–2.74× 加速、兩階段訓練與工程邊界
- [vLLM GB200 最佳化](09_inference_system/vllm/hardware_optimization/gb200_optimization.pptx) - vLLM 在 GB200 硬體上的效能最佳化策略

### 9.5 推理最佳化參考設計

企業級 LLM 推理服務全流程實施指南，從叢集規模特徵評估、異構執行圖排程架構設計，到邊緣裝置/多模態模型專項最佳化，並提供安全合規、指標體系與上線檢查清單。

- [推理最佳化參考設計導航](09_inference_system/reference_design/README.md) - 企業級 LLM 推理服務架構設計全景導讀

**基礎理論與技術選型**：

- [背景與目標](09_inference_system/reference_design/01-背景与目标.md) - 推理最佳化的背景分析與核心目標
- [叢集規模分類與特徵分析](09_inference_system/reference_design/02-集群规模分类与特征分析.md) - 不同規模叢集的特點與需求
- [核心推理最佳化技術深度解析](09_inference_system/reference_design/03-核心推理优化技术深度解析.md) - KV Cache、批處理、量化等核心技術
- [不同叢集規模的技術選型策略](09_inference_system/reference_design/04-不同集群规模的技术选型策略.md) - 針對性的技術方案選擇

**架構設計與評估體系**：

- [推理服務架構設計](09_inference_system/reference_design/06-推理服务架构设计.md) - 企業級推理服務架構設計方案
- [面向推理執行圖的異構排程系統架構設計](09_inference_system/reference_design/15-异构调度系统架构设计.md) - 跨裝置、跨階段、跨模型的精細化排程方案
- [效能評估指標體系](09_inference_system/reference_design/05-性能评估指标体系.md) - 推理效能評估指標與方法

**專業領域最佳化**：

- [多模態推理最佳化](09_inference_system/reference_design/10-多模态推理优化.md) - 多模態模型推理最佳化策略
- [邊緣推理最佳化](09_inference_system/reference_design/11-边缘推理优化.md) - 邊緣裝置上的推理最佳化方案
- [安全性與合規性](09_inference_system/reference_design/09-安全性与合规性.md) - 推理服務的安全與合規要求

**實施落地與運維**：

- [實施建議與最佳實踐](09_inference_system/reference_design/07-实施建议与最佳实践.md) - 落地實施的指導建議
- [實施檢查清單](09_inference_system/reference_design/13-实施检查清单.md) - 推理系統上線檢查清單
- [常見問題解答（FAQ）](09_inference_system/reference_design/12-常见问题解答.md) - 常見問題與解決方案
- [參考資料與延伸閱讀](09_inference_system/reference_design/08-参考资料与延伸阅读.md) - 推薦閱讀與延伸資料
- [總結與展望](09_inference_system/reference_design/14-总结与展望.md) - 推理最佳化技術發展趨勢

### 9.6 推理成本與容量規劃

大模型推理成本的定量分析與容量規劃決策，涵蓋 API 按量計費、Coding Plan 包月訂閱的定價資料建模、DeepSeek 推理叢集的單卡生產經濟學，以及基於業務字首複用率的 KV Cache 各級儲存（HBM/DRAM/NVMe）容量推演。

- [推理成本分析](09_inference_system/cost_analysis/llm_api_pricing_analysis.md) — 基於 OpenRouter 的多模型成本測算與動態抓取指令碼
- [Coding Plan 訂閱對比](09_inference_system/cost_analysis/coding_plan/coding_plan_report.md) — 11 款 AI 程式設計工具訂閱成本與隱藏條款解析
- [DeepSeek 推理叢集單卡經濟學](09_inference_system/cost_analysis/deepseek_inference_cluster_unit_economics.md) — 155 萬億 tokens/天、96% 快取命中、38 美元/卡時：單卡年收入 33 萬美元、93–96% 運營利潤率，附價格/成本假設與敏感性
- **[Token Factory：AI 推理的成本革命（圖文講解）](99_misc/token_factory_talk/talk-illustrated.md)** — 對外演講的 PPT 24 頁逐頁配圖講解：AI 白菜化與 Token 單位化 → 從「算力房東」到「產品製造商」→ 提升產能的成本革命 → 讓 token 更值錢，附國產算力差距的現場互動。配套素材庫（可排練提綱 + 產能度量文件 + 12 份參考資料）見 [專案 README](99_misc/token_factory_talk/README.md)

  <img src="./99_misc/token_factory_talk/img/cover.jpg" width="600" alt="Token Factory：AI 推理的成本革命 — 演講封面"/>

- [L1 KV Pool 與系統併發上限](09_inference_system/kv_cache/01_concepts/10_capacity_planning/01_hbm_kv_pool_concurrency.md) — 併發上限公式、三態記賬與指標觀測；為什麼 L2 空余救不了 P99 TTFT（SGLang/vLLM 對照）
- [KV Cache 容量規劃](09_inference_system/kv_cache/01_concepts/10_capacity_planning/03_glm5_kv_cache_capacity_planning.md) — GLM-5 顯存容量推演與 ROI 評估
- [KV Cache 壓縮技術](09_inference_system/kv_cache/01_concepts/06_compression/01_kv_cache_compression.md) — INT8/FP8 量化、稀疏化與注意力最佳化
- [Claude Prompt Caching 機制分析](09_inference_system/kv_cache/01_concepts/02_prefix_caching/03_claude_prompt_caching.md) — 提示詞快取的終端 Agent 原始碼實現與成本最佳化

### 9.7 模型部署與運維實踐

跨硬體平台的模型服務化落地指南，涵蓋 Mac 本地 DeepSeek-R1 執行、Ollama 架構原理，以及 DeepSeek-V3 MoE 在 H20、Qwen2-VL 在華為昇騰、B300 在 Blackwell Ultra 上的專項部署調優。

- [動手跑大模型](99_misc/mac-deepseek-r1.md) - 手把手教你如何跑大模型
- [Ollama 推理框架詳解](99_misc/ollama/README.md) - Ollama 的架構原理與進階配置
- [輸出差了一點點？用 logprobs 分清「噪聲」還是「bug」](09_inference_system/deployment/logprobs-precision-diagnosis.md) - logprobs 精度判別與推理排錯實戰
- [DeepSeek-V3 H20 推理最佳化：基於 vLLM 原始碼的深度分析](09_inference_system/deployment/deepseek_v3_h20_vllm_deep_dive.md) - PD 分離、EPLB、DP 適配、MTP 加速、FP8 量化的原始碼級分析
- [Qwen2-VL-7B 華為昇騰部署](09_inference_system/deployment/qwen2_vl_7b_huawei.md) - 國產硬體平台的部署最佳化
- [B300 上的模型部署與 KV Cache：官方手冊最佳實踐](09_inference_system/deployment/b300-deployment-and-kv-cache.md) - vLLM/SGLang 官方手冊的推薦配置與調優判據：SM103 三道門檻、Kimi-K3/DeepSeek-V4 啟動配方、-O0~-O3 與 2+N 物理核公式、KV 量化官方精度表、HiCache 三檔配置、NVFP4 KV 禁用理由；含 §三 K3 從 16 卡到 64 卡的權重/KV/通訊三筆賬
- [大模型啟動，七成時間花在載入權重上：FAST'26 論文用可程式設計頁快取把延遲砍了 79%](09_inference_system/deployment/fast26-programmable-page-cache.md) - FAST'26 華為論文精讀：三個測量驅動的觀察（SSD 頻寬只用 17%、NUMA 親和夠不著、一次性讀撞上 LRU），PPC 用 stacking 只讀 FS 加使用者態策略執行時滿足透明/非侵入/無硬體依賴三約束，MAIO 以 I/O 模板驅動三機制拿下模型載入延遲 −79%、彈性吞吐 +36%；含 openEuler ModelFS 落地路徑與 3 張手繪圖

### 9.8 DeepSeek 專題

DeepSeek 模型極致效能最佳化實戰，深度解析 vLLM 寬端點 (Wide Endpoint) 專有並行架構，以及在 Blackwell 等下一代高效能運算平台上的可擴展性評估與部署策略。

- [vLLM WideEP 架構](09_inference_system/vllm/hardware_optimization/deepseek_blackwell_wide_ep.md) - vLLM 寬端點 (Wide Endpoint) 架構解析
- [Scaling DeepSeek on Blackwell](09_inference_system/vllm/hardware_optimization/scaling_deepseek_blackwell.pptx) - DeepSeek 在 Blackwell 平台上的擴展性最佳化
- [從 MLA 到 CSA + HCA：DeepSeek 注意力架構的進化之路](09_inference_system/vllm/module_analysis/deepseek_attention_evolution_mla_to_csa_hca.md) - 結合 vLLM 推理引擎原始碼，深度解析 DeepSeek 注意力機制演進
- [155 萬億 tokens/天背后的引擎：DeepInfer 原始碼拆解](09_inference_system/deepinfer/deepinfer-source-deep-dive.md) - DeepSeek V4.1-Flash 生產推理引擎的原始碼級拆解：ZOS 非同步流水線、DSpark 變長驗證、YOCO/SWA 截斷與 Wide-EP；引擎核心在倉庫裡，3FS KV 儲存、Entrypoint 字首匹配、請求級 LB 不在

---

## 10. 企業級 AI Agent 開發

構建生產級 AI Agent 的系統化指南，涵蓋 BDI 認知理論、ReAct/12-Factor 等架構模式，深度拆解動態上下文工程、MemoryOS 多層記憶架構與 MCP 互操作協議，並提供基於 LangGraph 的企業級多智能體系統與 Kagent 基礎設施演進分析。

> 詳細內容請訪問：[AI Agent 開發與實踐](08_agentic_system/README.md) - 核心文件門戶，涵蓋理論、架構與實戰。

### 10.1 核心理論與架構設計

解析多智能體協作機制與企業級落地框架，包含 ReAct 推理機制、複雜寫作/指代消解系統設計模式，並深度剖析世界模型認知引擎與 Data Agent 資料智能體的新興架構正規化。

**多智能體系統**：

- [理論基礎與框架](08_agentic_system/multi_agent/02_part1_multi_agent_ai_fundamentals.md) - BDI 架構、多 Agent 協作機制與企業級落地
- [企業級構建實戰](08_agentic_system/multi_agent/03_part2_enterprise_multi_agent_system_implementation.md) - 基於 LangGraph 的架構設計與企業級程式碼落地
- [Claude Code 多會話協作實踐手冊](08_agentic_system/multi_agent/01_claude-code-multi-session-playbook.md) - 從上下文隔離與多視角評審出發，跨窗口消息、Agent Teams 與 Dynamic Workflow 三種協作路線，含評判者設計與排錯

**智能體設計模式**：

- [ReAct Agent 模式詳解](08_agentic_system/agent_design/docs/react-agent.md) - 推理與行動深度協同的經典機制
- [寫作 Agent 設計](08_agentic_system/agent_design/docs/writing-agentic-agent.md) - 針對複雜長文字內容創作的架構設計
- [指代消解系統設計](08_agentic_system/agent_design/docs/coreference-resolution-dialogue-system.md) - 高階對話狀態管理與多輪互動技術
- [12-Factor Agents](08_agentic_system/concepts/12-factor-agents-intro.md) - 構建高可靠、可擴展 LLM 應用的 12 要素原則
- [TradingAgents-CN 設計](08_agentic_system/agent_design/docs/trading-agents-cn.md) - 交易領域的智能體設計與互動分析
- [AI Agent 設計模式](08_agentic_system/agent_design/docs/ai-agent-design-patterns.pptx) - 企業級智能體架構設計模式
- [All Agentic Architectures 深入詳解](08_agentic_system/agent_design/docs/all-agentic-architectures-deep-dive.md) - 17 種 Agent 架構深度對比與實現解析

**資料智能體 (Data Agents)**：

- [資料智能體綜述](08_agentic_system/data_agent/data-agent-survey.md) ([配套 PPT](08_agentic_system/data_agent/data-agent-survey.pptx)) - Data Agent 新興正規化的核心架構與應用挑戰
- [企業級 Data Agent 產品需求文件](08_agentic_system/data_agent/enterprise-data-agent-prd.md) ([配套 PPT](08_agentic_system/data_agent/enterprise-data-agent-prd.pptx)) - 完整的商業級 L2 條件自動化 Data Agent PRD
- [企業級 Data Agent 敏捷落地規劃](08_agentic_system/data_agent/data-agent-skill-mvp.md) ([配套 PPT](08_agentic_system/data_agent/data-agent-skill-mvp.pptx)) - 針對 MVP 階段透過技能掛載盤活存量 API 的落地戰術

**認知與基礎理論**：

- [世界模型簡介](08_agentic_system/concepts/world-model-introduction.md) - 解析智能體理解世界的內部引擎

### 10.2 核心工程元件與基礎設施

解構構建高可靠 Agent 的底層支撐體系，涵蓋動態上下文組裝與壓縮工程、Claude/Mem0 記憶架構機制、MCP 工具互操作協議規範，以及 Agent Sandbox 與 Kubernetes 運維智能體基礎設施演進。

**上下文與記憶系統**：

- [上下文工程原理](08_agentic_system/context/context-engineering-principles.md) - 動態資料組裝、壓縮與檢索技術
  - [快速入門](08_agentic_system/context/context-engineering-intro.md) | [Anthropic 指南](08_agentic_system/context/anthropic-context-engineering-zh.md) | [LangChain 實踐](08_agentic_system/context/langchain-with-context-engineering.md) | [OpenViking 剖析](08_agentic_system/context/openviking-deep-dive.md) | [Claude Code 上下文壓縮](08_agentic_system/context/claude-code-context-compression.md)
- [記憶系統架構總覽](08_agentic_system/memory/README.md) - 賦予智能體長期記憶與個性化能力的核心機制
  - [理論與實踐綜述](08_agentic_system/memory/research/theory/ai-agent-memory-theory.md) | [大模型記憶綜述](08_agentic_system/memory/research/theory/llm-agent-memory-survey.md) | [記憶系統演進思考](08_agentic_system/memory/research/theory/memory-systems-are-dead.md)
  - [MemoryOS 架構](08_agentic_system/memory/research/systems/memoryos-architecture-guide.md) | [MemMachine 深度解析](08_agentic_system/memory/research/systems/memmachine-deep-dive.md) | [Mem0 快速入門](08_agentic_system/memory/research/systems/mem0-quickstart.md) | [Hermes 記憶體架構解析](08_agentic_system/memory/research/systems/hermes-agent-memory-management.md)
  - [Claude Code: 記憶機制解析](08_agentic_system/memory/research/case-studies/claude-code-memory-analysis.md) | [Claude-Mem: 系統介紹](08_agentic_system/memory/research/case-studies/claude-mem-system-analysis.md) | [Claude Code: Agent 執行流程解析](08_agentic_system/memory/research/case-studies/claude-code-agent-execution-flow.md) | [SuperMemory: 集成分析](08_agentic_system/memory/research/case-studies/supermemory-agent-integration-analysis.md)

**工具及協議**：

- [Model Context Protocol (MCP)](08_agentic_system/mcp/docs/01_deep_dive_into_mcp_and_the_future_of_ai_tooling.md) - MCP 原理與實戰，探討 AI 工具鏈的未來
  - [用 agent 逆向一個 agent：REA 拆解 Codex.app 實戰](08_agentic_system/mcp/docs/02_reverse_engineer_anything_in_practice.md) - 27 萬 star 的逆向工程 MCP 本機實測：fail-closed 三道閘門、預算對照實驗與檢視投影階梯，附手繪圖

**Agent Skill**：

- [Claude Skills 開發指南](08_agentic_system/agent_skills/01_claude_skills_guide.md) - 擴展智能體能力的工具定義規範與最佳實踐
  - [構建完整指南 (PDF)](08_agentic_system/agent_skills/01_the_complete_guide_to_building_skill_for_claude.pdf)
  - [一個人排程四個角色：多會話協作 Skill 的實測與邊界](08_agentic_system/agent_skills/02_multi-role-agent-skill.md) - 四個角色各開一個會話：三層結構 + 端到端實測與邊界
  - [12 小時、636 個測試：自驅型 Skill 能走多遠](08_agentic_system/agent_skills/03_self-driving-skill-for-complex-projects.md) - 從 SPARQLite 實驗切入，拆 Skill 的策略層與執行時：單會話有界任務可只用 Skill，跨 session 複雜專案要 Workflow 或 Agent SDK harness
- [Agent Skill 開發指南](https://github.com/ForceInjection/awesome-skills)（[線上版](https://forceinjection.github.io/awesome-skills/)）- 由原力注入博主維護的優秀認知技能（Agent Skill）合集，包含深度程式碼閱讀、架構分析、文件評審等自動化工作流。
- [CUDA Code Skill](https://github.com/ForceInjection/cuda-code-skill) - 面向 AI IDE（Claude Code、Trae 等）的 CUDA 知識增強程式碼生成與效能分析技能庫。
- [mmx-cli](https://github.com/MiniMax-AI/cli) - MiniMax AI 平台的 CLI 技能，支持文本、圖片、影片、語音、音樂生成與 Web 搜索，遵循 agentskills.io 標準。

**AI Agent Infra**：

- [基礎設施技術棧](08_agentic_system/agent_infra/01_ai-agent-infra-stack.md) - 全面梳理工具層、資料層與編排層
- [基礎設施的崛起](08_agentic_system/agent_infra/02_the-rise-of-ai-agent-infrastructure.md) - 生態演進趨勢與未來投資方向
- [OpenHarness 深入淺出：解密開源智能體基礎設施](08_agentic_system/agent_infra/03_openharness-deep-dive.md) ([配套 PPT](08_agentic_system/agent_infra/03_openharness-deep-dive.pptx)) - 大型語言模型 (LLM) 在推理與生成能力上取得了突破性進展，但它們本身受限於靜態的上下文視窗，無法直接與真實世界進行互動。要讓模型成為能夠自主解決複雜任務的工程化智能體 (Agent) ，必須為其配備執行動作的工具、持久化的記憶以及安全隔離的執行邊界。這就是“智能體基礎設施” (Agent Harness) 的核心使命。
- [4 個工具、42 家供應商、11 萬 star：Pi 的極簡 harness，與 DeepSeek Harness、OpenHarness 的路線對比](08_agentic_system/agent_infra/04_pi-agent-deep-dive.md) - 極簡 harness 原始碼深讀：預設 4 工具、系統提示 677 token、可替換協議與 42 家供應商；含與 DeepSeek Harness、OpenHarness 的三路線對比
- [Agent Sandbox 的演進與設計正規化](08_agentic_system/agent_infra/08_agent-sandbox-design.md) ([配套 PPT](08_agentic_system/agent_infra/08_agent-sandbox-design.pptx)) - 探討 Agent Sandbox 的核心設計理念，對比 OpenShell、Sandlock 等沙箱方案，揭示從“硬體級隔離”向“策略優先”演進的技術趨勢。
- [深度解析 Kagent：以構建 Kubernetes 運維智能體為例](08_agentic_system/agent_infra/09_deep-dive-kagent-k8s-ops-agent.md) ([配套 PPT](08_agentic_system/agent_infra/09_deep-dive-kagent-k8s-ops-agent.pptx)) - 深度解析 Kagent 的核心架構與工作機制，並以“構建阿里雲 ACK 運維智能體”為實戰案例，展示大模型與運維工具的編排。
- [OpenClaw Operator 架構深度解析](08_agentic_system/agent_infra/10_openclaw-operator-deep-dive.md) - 雲原生時代 AI Agent 執行時環境編排機制
- [DeepSeek-TUI 實戰](08_agentic_system/agent_infra/12_deepseek-tui-in-practice.md) - 榨干 DeepSeek V4 長上下文紅利的命令列程式設計 Agent 實戰指南
- [Claude Code Sandbox 安全隔離機制解析](08_agentic_system/agent_infra/11_claude-code-sandbox.md) - Linux 環境下基於 Bubblewrap 的底層隔離架構
- [擴展託管智能體](08_agentic_system/agent_infra/13_scaling-managed-agents.md) - 讓決策與執行解耦，各行其職的 AI 原生基礎設施
- [在 Elasticsearch 之上實現虛擬檔案系統](08_agentic_system/agent_infra/14_virtual-filesystem-elasticsearch_zh.md) - Elasticsearch 虛擬檔案系統實現解析（[英文原文](08_agentic_system/agent_infra/15_virtual-filesystem-elasticsearch.md)）

### 10.3 實戰程式碼與演示專案

從理論走向落地的工程實踐程式碼庫，包含基於非同步通訊匯流排的企業級多智能體系統、多輪指代消解微服務、MCP 客戶端/服務端互動 Demo，以及結合 LangChain 的記憶功能與 PDF 智慧翻譯器實現。

**完整端到端系統**：

- [企業級多智能體系統](08_agentic_system/multi_agent/multi_agent_system/README.md) - 包含非同步通訊匯流排、狀態監控與容錯機制的完整 MAS 實現
- [多輪指代消解對話系統](08_agentic_system/agent_design/coref-dialogue-system/README.md) - 支援實體識別、狀態管理與微服務部署的 NLP 實戰

**專項工具與演示**：

- [MCP 智能體演示](08_agentic_system/mcp/mcp_demo/README.md) - MCP 服務端與客戶端互動的完整示例
- [LangChain 記憶功能整合](08_agentic_system/memory/langchain/code/README.md) - 包含基礎記憶類型、智慧客服應用和 LangGraph 記憶管理的演示
  - [程式碼實現示例](08_agentic_system/memory/langchain/langchain_memory.md)
- [Agent Skill：PDF 智慧翻譯器](08_agentic_system/agent_skills/pdf_translator/README.md) - 結合 OCR 與 LLM 的多模態文件處理工具
- [Agent Skill：多會話協作（評審/修改/測試/裁決）](08_agentic_system/agent_skills/multi-session-collab/README.md) - 跨窗口消息 / Agent Teams / Workflow 的協作協議與啟動清單

### 10.4 前沿學術與行業研究

彙集 24 種主流 Agent Workflow 模式綜述、Deep Research 深度研究架構等核心學術論文，以及 2025 年度 LangChain 開發者訴求與 Agent 工程化現狀等權威行業報告。

**學習路徑**：

- [Agent 學習課程 Hub](08_agentic_system/agent_course_hub/README.md) - 從零學 AI Agent 的課程與專案導航：七階段學習路線圖、系統課程與開源框架清單、27 個高頻術語速查（[對外發布版路線圖](08_agentic_system/agent_course_hub/2026-agent-learning-roadmap-blog.md)適合公眾號等渠道轉發）

**學術論文**：

- [Agent Workflow 綜述](08_agentic_system/papers/agent-workflow-survey.md) - 涵蓋 24 種主流 Agent 工作流模式的權威系統性總結
- [Deep Research Agents](08_agentic_system/papers/deep-research-agent.md) - 探討深度研究智能體的多步推理規劃能力與核心架構
- [論文資源庫彙總](08_agentic_system/papers/README.md) - AI Agent 領域必讀核心論文持續更新索引

**行業報告**：

- [LangChain Agent 工程現狀報告](08_agentic_system/reports/langchain-state-of-agent-engineering.md) - 2025 年度 Agent 領域最新技術趨勢與開發者訴求

---

## 11. 檢索增強生成與文件智慧

解構從非結構化資料解析到高可信知識庫構建的完整技術棧，涵蓋 Naive/Advanced RAG 架構演進、Embedding 選型與 Chunking 策略，並深入 GraphRAG (Neo4j/KAG) 複雜關係推理與 MinerU/Marker 等文件智慧解析引擎應用。

> 詳細內容請訪問：[rag 與工具生態](07_rag_and_tools/README.md) - 核心文件門戶，涵蓋 `RAG`、`GraphRAG` 與文件智慧工具。

### 11.1 檢索增強生成基礎與進階

RAG 技術全景演進導航，對比不同檢索架構優劣勢，系統評估文字分塊 (Chunking) 策略，並提供面向中文場景的 Embedding 模型深度評測與選型指南。

- [rag 快速開發實戰（從 0 到 1 搭建）](https://mp.weixin.qq.com/s/89-bwZ4aPor4ySj5U3n5zw) - `RAG` 技術全景導航，涵蓋基礎概念到進階最佳化
- [rag 策略對比](07_rag_and_tools/rag_basics/rag_comparison.md) - 不同 `RAG` 架構（`Naive RAG`、`Advanced RAG` 等）的優劣勢分析
- [chunking 策略評估總結](07_rag_and_tools/rag_basics/evaluating_chunking_strategies_summary.md) - 檢索分塊策略的深度總結與最佳實踐
- [中文 rag 系統 embedding 選型指南](07_rag_and_tools/rag_basics/chinese_rag_embedding_model_selection.md) - 面向中文場景的 `Embedding` 模型評測與推薦

### 11.2 圖檢索增強生成與知識圖譜

解決複雜多跳關係推理難題的圖計算架構，深度解析 GraphRAG 核心概念與 KAG 框架，並提供圖資料庫 Neo4j 安裝配置與 Cypher 查詢語言的實戰教程。

- [graphrag 學習指南](07_rag_and_tools/graph_rag/graph_rag_learning_guide.md) - `GraphRAG` 的核心概念、架構原理與入門路徑
- [kag 框架介紹](07_rag_and_tools/graph_rag/kag_introduction.md) - `Knowledge Augmented Generation`（`KAG`）框架深度解析
- [neo4j 實戰指南](07_rag_and_tools/knowledge_graph/neo4j_handson_guide.md) - 圖資料庫 `Neo4j` 的安裝、配置與企業級實戰
- [neo4j cypher 教程](07_rag_and_tools/knowledge_graph/neo4j_cypher_tutorial.md) - `Neo4j` 查詢語言 `Cypher` 完整教程

### 11.3 大模型與知識圖譜協同應用

構建高可信、可解釋智慧應用的最佳實踐，結合完整原始碼與圖譜資料，深入剖析基於 LLM+KG 架構的銀行反電詐智慧風控系統設計方案。

- [銀行反電詐智慧系統設計](07_rag_and_tools/synergized_llms_kgs/anti_fraud_design.md) - 基於 `LLM` + `KG` 的金融風控系統設計方案，實戰反欺詐場景
- [反欺詐 demo 原始碼](07_rag_and_tools/synergized_llms_kgs/demo/README.md) - 完整的反欺詐系統演示程式碼，包含資料生成、圖譜構建與智能體推理

### 11.4 文件智慧解析

突破 RAG 系統的資料品質瓶頸，解析 MinerU 與 Marker 等基於深度學習的複雜 PDF 佈局檢測與公式提取引擎，以及 Microsoft MarkItDown 跨格式文件轉換工具。

- [mineru 文件解析](07_rag_and_tools/pdf_tools/miner_u_intro.md) - 上海人工智慧實驗室開源工具，助力複雜 `PDF` 高效解析
- [marker pdf 佈局檢測](07_rag_and_tools/pdf_tools/marker_zh_cn.md) - 基於深度學習的高精度 `PDF` 解析與佈局分析引擎
- [markitdown 入門](07_rag_and_tools/pdf_tools/markitdown/markitdown_intro.md) - Microsoft 開源的文件轉換工具，支援多種辦公文件格式到 `Markdown` 的高品質轉換

---

## 12. 課程體系與學習路徑

系統化學習路徑與進階指南集合，包含 ZOMI 醬 AI System 全棧硬體架構、大模型底層原理與演進基礎、Trae AI 輔助程式設計實戰、KV Cache 專題課，以及基於 LangGraph 的企業級多智能體系統培訓資源。

### 12.1 AI System 全棧課程（ZOMI 醬）

ZOMI 醬主導的高分開源 AI 基礎設施架構體系，從底層 AI 晶片架構、硬件加速器到 AI 編譯器原理、推理效能調優與分散式框架設計進行深度解構。

[AISystem](https://github.com/chenzomi12/AISystem) - AI 系統全棧課程程式碼與資料庫。

- [系統介紹](https://github.com/chenzomi12/AISystem/tree/main/01Introduction) - AI 系統概述、發展歷程與技術演進路徑。
- [硬體基礎](https://github.com/chenzomi12/AISystem/tree/main/02Hardware) - AI 晶片架構、硬體加速器與計算平台深度解析。
- [編譯器技術](https://github.com/chenzomi12/AISystem/tree/main/03Compiler) - AI 編譯器原理、最佳化技術與工程實踐。
- [推理最佳化](https://github.com/chenzomi12/AISystem/tree/main/04Inference) - 模型推理加速技術、效能調優與部署策略。
- [框架設計](https://github.com/chenzomi12/AISystem/tree/main/05Framework) - AI 框架架構設計、分散式計算與並行最佳化。

### 12.2 AI Infra 基礎課程（入門）

面向初學者的 AI 基礎設施普及講座（90 分钟），圍繞一條主線：**一切 AI 基礎設施最佳化的最終目標，都是降低每 token 成本**。沿"模型架構 → 硬件 → 推理引擎 → 基礎設施與生態"四層槓桿展開，覆蓋 2026 年最新格局（DeepSeek-V4、Kimi K3、開源價格戰、1M 上下文、Agentic 程式設計）。

- [大模型原理與最新進展](10_ai_related_course/ai_coding/index.html) - 互動式線上課程平台。
- [AI 程式設計入門](10_ai_related_course/ai_coding/AI%20编程入门.md) - AI 程式設計基礎知識與應用入門。
- [Token Factory 講座大綱與講稿](10_ai_related_course/ai_infra_lecture/%E5%85%A5%E9%97%A8%E7%BA%A7/) - 40 頁 PPT 大綱（單一資料來源）+ 552 行完整演講逐字稿 + 自制 PPT 成品。
- **學習目標**：理解 AI 推理成本四年下降 100 倍背後的四層槓桿（架構/硬件/引擎/生態）。
- **核心內容**：
  - **Token 工廠概念**：token 作為 AI 經濟基本單位，四年價格下降 100 倍（對數座標曲線）。
  - **第一層槓桿·模型架構**：MLA（KV Cache -93.3%）、MoE（激活 5.5%）、CSA/HCA（DeepSeek V4 成本 -73%）、KDA（Kimi K3 線性注意力）。
  - **第二層槓桿·硬件**：Blackwell FP4、HBM3e 8 TB/s、NVLink-C2C、CUDA 最佳化、GPU 虛擬化共享。
  - **第三層槓桿·推理引擎**：KV Cache 四層解法、連續批處理、DSpark 投機解碼、FP8/FP4 量化。
  - **第四層槓桿·基礎設施與生態**：PD 分離、開源價格戰（28 倍價差）、成本下降開啟 AI 程式設計/長上下文/Agent 三大應用形態。

### 12.3 Trae 程式設計實戰課程

系統掌握 AI 輔助開發工作流，從 IDE 環境配置與互動模式，進階至 Web 開發、資料庫設計與 DevOps 微服務架構等複雜場景的實戰演練。

- [Trae 程式設計實戰教程](10_ai_related_course/trae/README.md) - 從基礎入門到高階應用的完整 Trae 程式設計學習路徑。

**課程結構：**

- **第一部分：Trae 基礎入門**：環境配置、交互模式、HelloWorld 專案實戰。
- **第二部分：常見程式設計場景實戰**：前端開發、Web 開發、后端 API、資料庫設計、安全認證。
- **第三部分：高階應用場景**：AI 模型集成、實時通訊、資料分析、微服務架構。
- **第四部分：團隊協作與最佳實踐**：程式碼品質管理、專案管理、效能最佳化、DevOps 實踐。
- **第五部分：綜合專案實戰**：企業級應用開發、核心功能實現、部署運維實戰。

### 12.4 多智能體 AI 系統培訓

面向企業研發團隊的生產級架構指南，深度解析 LangGraph 核心排程機制、LangSmith 監控平台整合以及企業級 Multi-Agent 架構設計模式。

- [多智能體 AI 系統培訓材料](10_ai_related_course/multi_agent_system/multi_agent_training/README.md)：涵蓋 LangGraph 框架深度解析、LangSmith 監控整合及企業級架構設計。

### 12.5 KV Cache 八講

從 token 賬本、page/slot 口徑到 nano-vllm / vLLM / SGLang 原始碼，再到 GLM-5.3-Flash 與 DeepSeek-V4.1-Flash 的容量分析。詳見 [KV Cache 八講](10_ai_related_course/kv_cache_course/README.md)。

- **課程結構**：8 講 × 120 分钟；前四講公式、分頁與引擎，第五講複用與分層，第六、七講模型原始碼，第八講容量規劃與選型。
- **課程產出**：token/state 容量表、原始碼對映、Agent 長會話選型備忘。
- **術語與實驗**：[術語表](10_ai_related_course/kv_cache_course/glossary.md)、[實驗環境](10_ai_related_course/kv_cache_course/lab-environment.md)。

### 12.6 微軟 AI Agents for Beginners 課程

由微軟提供的初學者課程，旨在幫助學習者全面瞭解 AI Agent 的構建與應用。

- [AI Agents for Beginners 課程之 AI Agent及使用場景簡介](10_ai_related_course/AI%20Agents%20for%20Beginners%20课程之%20AI%20Agent及使用场景简介.md) - 涵蓋 AI Agent 基礎概念、開發框架、設計模式與應用場景。

### 12.7 哈佛 CS2680 Modern AI Systems

哈佛 SEAS 2026 秋季課程（Juncheng Yang / MaDSys 組主講），沿「Agent 迴圈 → LLM serving → 底層硬體」一條線講 AI 系統最佳化。已收錄 Efficient LLM serving basics 三講：Intro to LLM、Intro to GPUs（roofline、nsys/ncu、FlashAttention 譜系）與 scheduling/paging/parallelism（TTFT/TPOT 口徑、batching、PagedAttention、五種並行）。詳見 [哈佛 CS2680 課件存檔](10_ai_related_course/cs2680_modern_ai_systems/README.md)。

---

## 13. AI Native 全棧實踐

以"認知性質決定技術分層"為裁斷準則的 AI Native 方法論體系，包含應用架構（Agent / Skill / Tool 三層 + 七項工程治理）和 DevOps（AI 增強而非替代的全流程協同框架），透過真實電力交易場景推導可複用架構。詳細內容請訪問：[AI Native 全棧實踐](11_ai_native_everything/README.md)，配套 DevOps 參考：[ai-native-devops](https://github.com/ForceInjection/ai-native-devops)（[線上版](https://forceinjection.github.io/ai-native-devops/)）。

### 13.1 AI 時代的軟體工程

軟體工程正向以 Agent First 與自主推理為核心的 **Software 3.0** 時代演進，涵蓋駕馭工程 (Harness Engineering) 體系與 Spec 驅動開發工作流。

- [Agent First：軟體工程的下一個正規化轉移](98_llm_programming/Agent_First.md) - 梳理程式設計正規化的演變歷史，探討 Agent First 的核心理念與實戰指南。
- [駕馭工程](98_llm_programming/Harness_Engineering.md) - 深度解析如何構建駕馭系統，提升 AI 程式設計助手的可控性與效能。
- [OpenSpec 實戰指南](https://github.com/ForceInjection/OpenSpec-practise/blob/main/README.md) - Spec 驅動開發 (Spec-Driven Development) 的工程實踐，演示了"意圖 → Spec → AI → 程式碼 & 驗證"的新一代開發工作流。

### 13.2 把 AI 交付到客戶業務現場

AI 進入**開發流程**與**應用架構**之外，還有一條線：進入**客戶的業務流程**。這一步發生在組織邊界之外，靠的不只是工具鏈，還有人的派駐、語義層的沉澱和交付模式的設計。

- [模型不稀缺了，稀缺的是把模型塞進業務的人](11_ai_native_everything/fde/forward-deployed-engineer.md) - 從 80/95/99 規律出發講清 FDE：是什麼、不是什麼（不是售前、不是駐場外包、不是諮詢顧問、不是產品工程師）；三道成本門檻如何被 AI 拉低；本體層、Skill 與聯結器如何構成規模化的地基。含騰訊研究院報告與範冰開源手冊兩份材料的用法指引
- [《FDE：AI落地實戰指南》導讀](11_ai_native_everything/fde/fde-ai-landing-guide.md) - 樊中愷（百度主任架構師、文心應用技術負責人）著，人民郵電出版社 2026 年 10 月出版。七篇三十章的骨架，五種死法、訪談提問法與"工作化石"三處要點，以及第 22 章按周覆盤的案例寫法
- [FDE 落地最大的難點：有結果責任，沒有組織權力](11_ai_native_everything/fde/fde-result-responsibility-without-authority.md) - 把五種死法、24 個案例與 80/95/99 歸結為責任、權力、激勵三個錯位；提出責任、許可權、能力、知識四次移交，以及合同、效果基線與產品化閘門的落地做法
- [別讓寫程式碼的 Agent 評審自己：AI 程式碼評審的三道閘門](11_ai_native_everything/vibe_coding/docs/ai-code-review-three-gates.md) - 生成成本歸零後評審成為新瓶頸：METR 實驗自評 +20% 實測 −19% 的感知差、LLM 評審的否定盲區、假統計傳播三個訊號失真；給出機械門（確定性指令碼）、流程門（六步自評審）、多 Agent 門（Builder–Critic 資訊邊界）三道閘門，融合 OpenCodeReview 三階段架構與公開研究資料，含 6 張手繪圖

---

## Buy Me a Coffee

如果您覺得本專案對您有幫助，歡迎購買我一杯咖啡，支援我繼續創作和維護。

| **微信**                                                 | **支付寶**                                            |
| -------------------------------------------------------- | ----------------------------------------------------- |
| <img src="./img/weixinpay.JPG" alt="wechat" width="200"> | <img src="./img/alipay.JPG" alt="alipay" width="200"> |

---
