# AI Infra GTM 速成班：12 週從 GPU 到 Token 經濟 — 課程總綱

> 本文件是這個 fork 的「個人讀書計畫」核心 context。以本 repo（AI Fundamentals，簡體中文知識庫）為主要教材，目標是在 12 週內具備應徵外商 **Pre-sales／Solutions Engineer（主軸，2026-11-11 起）**，以及備選的 **Technical Marketing Manager（TMM）／AI Evangelist（DevRel）／Product Marketing Manager（PMM，AI Infra・GPU・Data Center）／Technical Account Manager（TAM）** 的技術深度與表達能力。學習方法依《Make It Stick》（中譯《超牢記憶法》）與 Daniel Willingham《學生為什麼不喜歡上學？》操作化，見 [02_assessment_spec.md](02_assessment_spec.md)。

## 0. 目前採用：每日 1 小時・Pre-sales 版（2026-11-11 起，優先於下文）

學習者是全職業務，**每天只能讀 1 小時**（含週末，每週約 7 小時，原設計是 12～15 小時）；目標職缺以 **Pre-sales／SE** 為主軸。週次與日期不變，以下規則覆蓋下文對應的段落：

| 項目     | 1 小時版                                                                                                                                           |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 平日     | 10 分鐘每日測驗（6 題，不變）→ **35 分鐘講義** → 10 分鐘口說 60 秒與錯題本 → 5 分鐘緩衝                                                              |
| 週六     | **週測 12 題（25 分鐘）** → 35 分鐘寫作業                                                                                                             |
| 週日     | 45 分鐘完成作業 → 15 分鐘週反思；22:00 前交                                                                                                          |
| 講義     | 35 分鐘版：中文 1100～1500 字、概念 3～5 個；第 5 節改為 **Pre-sales 口徑**（客戶 CxO／採購 30 秒、客戶工程師 3 分鐘、配置建議、反對意見應對）            |
| 原文     | 講義是主教材；repo 原文（★）**有空再讀**，不列入每日 1 小時                                                                                            |
| 每日口說 | 受眾輪替：一 客戶 CxO／採購、二 客戶工程師、三 自家業務（教業務怎麼講）、四 客戶反對意見（競品、價格）、五 面試官（英文）                                      |
| 作業     | 只做 **7 份必做**（見 6.1 表的「1 小時版」欄），皆改寫成 Pre-sales 文件；考試週與模擬面試週不交作業                                                    |
| 考試     | 模組考 60 分鐘（20 題筆試 + 1 長答 40 分鐘、白板 20 分鐘）；模擬面試 30 分鐘；間隔複習測驗 30 分鐘；期末綜合考 60 分鐘                                   |
| 評分     | 週作業改為「7 份必做取最佳 6 份」，其餘權重不變                                                                                                         |

時間真的不夠的那天，優先順序是：**每日測驗 > 講義第 3、5、7 節 > 其他**。測驗不可省，因為整套系統靠它記錄進度。

## 1. 基本資訊

| 項目         | 內容                                                                                                                                                                 |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 課程名稱     | AI Infra GTM 速成班：12 週從 GPU 到 Token 經濟                                                                                                                      |
| 期程         | 2026-11-16（一）～ 2027-02-05（五），共 12 週；第 7 週（12/28～1/3）為跨年假期的**間隔複習週**，不排新內容                                                            |
| 每週時數     | **1 小時版：每天 1 小時，每週約 7 小時（見第 0 節）**。原設計：12～15 小時（平日每天 2 小時，週六 3～4 小時，週日 1 小時） |
| 目標職缺     | **主軸：Pre-sales／SE**（伺服器・AI Infra）；備選：TMM／AI Evangelist／PMM／TAM，外商為主                                                                                                 |
| 先修         | 有伺服器或 IT 基礎知識，能讀英文技術文件與規格表；不要求會寫 CUDA、不要求 K8s 實作                                                                                   |
| 教材         | 本 repo 文章（簡中，引用時保留原文）+ 外部書目（第 4 節）+ 官方白皮書／資料表                                                                                        |
| 語言         | 講義、測驗、作業以**繁體中文**撰寫，術語保留英文；面試題庫中英並列，口說練習以英文為主                                                                              |
| 四條主線     | 「晶片 → 節點 → 集群 → 推理引擎 → Token 經濟」技術主線；「30 秒／3 分鐘／30 分鐘」三種長度的表達主線；「數字口徑」素養主線；「四種職缺」作品集主線                 |
| 課程產出     | 10 份週作業（皆為可直接放進作品集的 GTM 文件）、4 次模組考、4 次模擬面試、1 份期末作品集（2 件）與 1 份投遞清單                                                     |

## 2. 教學目標

- **知識目標**：能從晶片（SM、Tensor Core、HBM）、節點（PCIe、NVLink、GPUDirect）、集群（IB／Ethernet、NCCL、K8s 排程）、推理引擎（KV Cache、PagedAttention、PD 分離）到 Token 經濟（每百萬 token 成本、Goodput、TCO）完整講清楚 AI 基礎設施全棧，每個數字帶口徑。
- **能力目標**：對任一主題能在 30 秒內對 CxO 講清價值、3 分鐘內對工程師講清機制、30 分鐘內做一場 talk 或 demo；能獨立產出 one-pager、競品比較、參考架構簡報、TCO 模型、客戶升級（escalation）案例。
- **素養目標**：所有數字標註來源、日期與「廠商口徑／獨立實測」；分清規格表數字與可用數字（如 B300 的 288 vs 270/279 GB）；不知道就說不知道並給出查證路徑。

## 3. 課程邊界

| 內容                                       | 處理方式                                                                                  |
| ------------------------------------------ | ----------------------------------------------------------------------------------------- |
| CUDA kernel 撰寫、TileLang、profiling 工具 | 只讀概念（roofline、kernel launch latency、CUDA graph 的「為什麼」），不寫 code、不跑實驗 |
| K8s / HAMi 安裝部署                        | 只讀架構與元件職責，能畫架構圖、能解釋選型；不動手部署                                    |
| 華為 NPU／CANN、Ascend 950                 | 競品視角：只讀「與 GPU 的架構差異、甜蜜區與短板」                                         |
| Trae／AI 編程課程、Spring AI、LangGraph    | 不納入                                                                                    |
| 數學推導（attention、RoPE、量化誤差）      | 只到「能用一張圖解釋」，不做推導                                                          |

## 4. 指定閱讀書目

### 4.1 學習方法（前兩週讀完，之後只當工具書查）

| #   | 書目                                                                                                  | 讀什麼                                                                                                                                    |
| --- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| L1  | Peter Brown, Henry Roediger, Mark McDaniel, *Make It Stick: The Science of Successful Learning*（中譯《超牢記憶法》） | 第 1～4 章與第 8 章：提取練習、間隔、交錯、精緻化、生成、校準、避免流暢感錯覺。本課程所有測驗設計都出自這裡                                 |
| L2  | Daniel T. Willingham, *Why Don't Students Like School?*（中譯《學生為什麼不喜歡上學？》）             | 第 1～6 章：背景知識先於技能、「記憶是思考的殘留物」、具體例子先於抽象、練習到自動化、新手與專家的認知差異。本課程講義結構出自這裡           |

### 4.2 技術核心（搭配 repo 文章，只讀指定章節）

| #   | 書目／文件                                                                                                     | 讀什麼                                                                       | 搭配週次 |
| --- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | -------- |
| T1  | NVIDIA 官方：Blackwell Architecture Technical Brief、H100 Whitepaper、GB200/GB300 NVL72 產品頁與 datasheet  | 規格表每一欄的定義；「with sparsity」口徑；NVL72 機架規格                     | W1、W3   |
| T2  | David Kirk, Wen-mei Hwu, *Programming Massively Parallel Processors*（4th ed.）                               | 第 1～5 章：只讀概念（SIMT、記憶體層級、roofline），不寫 code                | W1       |
| T3  | NVIDIA DGX SuperPOD Reference Architecture（公開 PDF）                                                        | rail-optimized 網路、儲存與管理網分離、機櫃電力與冷卻的量級                  | W3、W5   |
| T4  | Hugging Face, *The Ultra-Scale Playbook*（線上）                                                               | 並行策略章節：DP／TP／PP／EP 各自的通訊模式與對互連的要求                    | W9       |
| T5  | Chip Huyen, *AI Engineering*（2025）                                                                           | 推理最佳化與評測章節                                                         | W8～W10  |
| T6  | Luiz Barroso, Urs Hölzle, Parthasarathy Ranganathan, *The Datacenter as a Computer*（3rd ed.，免費 PDF）     | 第 1 章與成本／電力章節：PUE、TCO 結構、資料中心作為計算單位                 | W3、W10  |
| T7  | 論文（只讀摘要、圖與結論）：*Attention Is All You Need*；*Efficient Memory Management for LLM Serving with PagedAttention*（vLLM）；Mooncake（FAST'25）；DeepSeek-V3 Technical Report 的 infra 章 | 每篇產出一張「一句話 + 一張圖」卡片                                           | W8～W10  |

### 4.3 GTM 與職能（第 7 週起每週一章，第 12 週整合）

| #   | 書目                                                                       | 用途                                                             |
| --- | -------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| G1  | April Dunford, *Obviously Awesome*                                         | 定位五要素：競爭替代品、獨特屬性、價值、目標客群、市場類別       |
| G2  | Chip Heath, Dan Heath, *Made to Stick*（中譯《創意黏力學》）               | 訊息六原則（SUCCESs），用於 one-pager 與 talk 開場               |
| G3  | Martina Lauchengco, *Loved: How to Rethink Marketing for Tech Products*   | PMM 四大職能：大使、說書人、策略師、傳道者                       |
| G4  | Nancy Duarte, *Resonate*                                                   | talk 結構（現狀 → 可能 → 行動呼籲），用於 Evangelist 作業        |
| G5  | David Maister, Charles Green, Robert Galford, *The Trusted Advisor*       | TAM 的信任方程式與升級溝通                                       |
| G6  | Adam DuVander, *Developer Marketing Does Not Exist*                        | DevRel／Evangelist 與開發者溝通的原則                            |

### 4.4 repo 內的「地圖型」文件（第 1 週先瀏覽，之後反覆回來）

- [本 repo 首頁 README](../README.md)：全棧目錄，每週對照一次「我學到哪一層了」。
- [從芯片到 Agent：AI 基礎設施的閱讀地圖](../99_misc/book-recommendations.md)：延伸書單。
- [AI 基礎設施延遲金字塔](../01_hardware_architecture/performance/ai_latency_pyramid.md)：全課程的「時間尺度地圖」。
- [Token Factory 演講專案](../99_misc/token_factory_talk/README.md)：一場成品 talk 的完整素材庫，是 Evangelist 作業的範本。
- [KV Cache 八講課程總綱](../10_ai_related_course/kv_cache_course/syllabus.md)：repo 原作者的課綱寫法，是本課程結構的參照。

## 5. 十二週安排

每週固定節奏：**週一上午做前測或日測 → 平日每日一份講義 → 週六週測 + 作業 → 週日反思 + 錯題本 + 22:00 前交作業**。講義由 `course-handout-builder` skill 產生，測驗由 `retrieval-quiz-builder` skill 產生（見 [README](README.md)）。

### 模組一：硬體與系統（W1～W3）

| 週  | 日期            | 主題                   | 核心問題                                                         | 主要閱讀（repo，★ 為必讀）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 作業／考試                                                                               |
| --- | --------------- | ---------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| W1  | 11/16～11/22    | GPU 本體：讀懂一張卡   | 為什麼 AI 需要 GPU？一張 H100／B200 規格表的每一欄在說什麼？       | ★[GPU 特性](../01_hardware_architecture/nvidia/understand_gpu_architecture/01_gpu_characteristics.md)、★[GPU 記憶體](../01_hardware_architecture/nvidia/understand_gpu_architecture/02_gpu_memory.md)、★[A100 架構實例](../01_hardware_architecture/nvidia/understand_gpu_architecture/07_a100_architecture.md)、★[HBM 演進](../01_hardware_architecture/performance/01_hbm_evolution.md)、★[PCIe & NVLink 頻寬速查表 §3](../01_hardware_architecture/performance/05_pcie_nvlink_speed_reference.md)、[MIG 實戰](../01_hardware_architecture/nvidia/mig_hands_on.md)、[HBF vs HBM](../09_inference_system/hbf-vs-hbm.md)；外部 T1、T2                                                             | 作業 1：GPU 規格表解讀 one-pager（11/22）                                                 |
| W2  | 11/23～11/29    | 節點內互連與資料路徑   | 八卡伺服器裡的資料怎麼走？瓶頸在哪一段？                          | ★[PCIe 總線技術大全](../01_hardware_architecture/pcie/01_pcie_comprehensive_guide.md)、★[PCIe 拓撲層級](../01_hardware_architecture/pcie/06_pcie_topology_hierarchy.md)、[Switch vs Bridge](../01_hardware_architecture/pcie/07_pcie_switch_vs_bridge.md)、★[PCIe 域與 NUMA](../01_hardware_architecture/performance/04_pcie_domain_numa.md)、★[NVLink 技術入門](../01_hardware_architecture/nvlink/nvlink_intro.md)、★[NVLink-C2C](../01_hardware_architecture/superchips/nvlink_c2c.md)、★[GPUDirect RDMA 與 Storage](../01_hardware_architecture/gpudirect/01_gpudirect_technology.md)、[GPUDirect P2P](../01_hardware_architecture/gpudirect/02_gpudirect_p2p.md)、[DMA engine](../01_hardware_architecture/dma/01_dma_engine.md)、[CXL 全景](../01_hardware_architecture/pcie/08_cxl_interconnect_overview.md) | 作業 2：HGX 8-GPU 伺服器資料路徑圖解（11/29）                                             |
| W3  | 11/30～12/06    | 機架級系統與競品地圖   | Scale-up 機架為什麼成了新的計算單位？GPU／TPU／NPU 各自的甜蜜區？ | ★[GB300 NVL72 架構解析](../01_hardware_architecture/superchips/nvidia_gb300.md)、★[AI 基礎設施延遲金字塔](../01_hardware_architecture/performance/ai_latency_pyramid.md)、★[TPU 101](../01_hardware_architecture/tpu/tpu_101.md)、★[GPGPU vs NPU](../01_hardware_architecture/nvidia/GPGPU_vs_NPU_大模型推理训练对比.md)、[AMX vs Tensor Core](../01_hardware_architecture/performance/03_amx_vs_tensorcore.md)、[Ascend 950 微架構速查](../01_hardware_architecture/ascend/Ascend950_微架构速查.md)、[中國資料中心市場精讀](../03_ai_cluster_ops/05_datacenter/china-dc-boom-semianalysis.md)；外部 T1、T3、T6                                                                                | 作業 3：競品定位一頁（12/06）；**模組考 I：12/05（六）**；**模擬面試 I（TMM）：12/06（日）** |

### 模組二：集群、網路與雲原生平台（W4～W6）

| 週  | 日期            | 主題                       | 核心問題                                                              | 主要閱讀（repo，★ 為必讀）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 作業／考試                                                                                   |
| --- | --------------- | -------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| W4  | 12/07～12/13    | GPU 運維、可觀測性與切分   | 客戶說「GPU 利用率 100% 但很慢」，你怎麼回？                           | ★[GPU 利用率迷思](../03_ai_cluster_ops/01_gpu_ops/02_gpu_utilization_myth.md)、★[nvidia-smi 指南](../03_ai_cluster_ops/01_gpu_ops/03_nvidia_smi_guide.md)、★[DCGM 監控](../03_ai_cluster_ops/01_gpu_ops/05_dcgm_monitoring.md)、★[GPU 健康檢查](../03_ai_cluster_ops/01_gpu_ops/06_gpu_health_check.md)、[驅動排障](../03_ai_cluster_ops/01_gpu_ops/08_gpu_driver_troubleshooting.md)、★[GPU 管理基礎理論](../04_cloud_native_ai_platform/gpu_manager/01_basic_theory.md)、★[虛擬化技術篇](../04_cloud_native_ai_platform/gpu_manager/02_virtualization.md)、[資源管理與最佳化](../04_cloud_native_ai_platform/gpu_manager/03_resource_management.md)                                          | 作業 4：TAM 升級案例手冊（12/13）                                                            |
| W5  | 12/14～12/20    | Scale-out 網路與集合通訊   | 訓練集群為什麼佈 rail-optimized？IB 和 Ethernet 怎麼選？               | ★[IB 網路架構與協定](../03_ai_cluster_ops/02_infiniband/01_ib_network_theory.md)、★[NCCL 理論](../03_ai_cluster_ops/03_nccl/01_nccl_theory.md)、★[NCCL 基準測試](../03_ai_cluster_ops/03_nccl/04_nccl_benchmark.md)、[NCCL 路徑基準](../03_ai_cluster_ops/03_nccl/06_nccl_path_benchmark.md)、★[GPU 排程問題](../03_ai_cluster_ops/04_gpu_scheduling/01_gpu_scheduling_problem.md)、★[Gang scheduling](../03_ai_cluster_ops/04_gpu_scheduling/02_gang_scheduling_for_training.md)、★[拓撲感知排程](../03_ai_cluster_ops/04_gpu_scheduling/03_topology_aware_scheduling.md)；外部 T3、NVIDIA Spectrum-X／Quantum-X 產品頁、Ultra Ethernet Consortium 1.0 概述 | 作業 5：IB vs Ethernet 競品比較 + 給 CIO 的選型建議（12/20）                                 |
| W6  | 12/21～12/27    | 雲原生 AI 平台與 AI 儲存   | K8s 上的 GPU 怎麼切、怎麼排、怎麼餵資料？                              | ★[Container Toolkit 原理](../04_cloud_native_ai_platform/k8s/01_nvidia_container_toolkit_analysis.md)、★[Device Plugin 原理](../04_cloud_native_ai_platform/k8s/02_nvidia_k8s_device_plugin_analysis.md)、★[Kueue + HAMi](../04_cloud_native_ai_platform/k8s/03_kueue_hami_integration.md)、★[vLLM + LWS](../04_cloud_native_ai_platform/k8s/04_lws_intro.md)、[llm-d](../04_cloud_native_ai_platform/k8s/05_llm_d_intro.md)、★[HAMi 完整指南](../04_cloud_native_ai_platform/gpu_manager/hami/hami-gpu-resources-guide.md)、[KAI vs HAMi](../04_cloud_native_ai_platform/gpu_manager/hami/KAI_vs_HAMi_Comparison.md)、★[GPU 共享排程](../03_ai_cluster_ops/04_gpu_scheduling/04_gpu_sharing_scheduling.md)、★[AI 儲存門戶](../04_cloud_native_ai_platform/storage/README.md)、[DeepSeek 3FS](../04_cloud_native_ai_platform/storage/deepseek_3fs/01_deepseek_3fs_design_notes.md)、[ICMS 架構](../04_cloud_native_ai_platform/storage/inference_context_memory_storage/01_icms_architecture.md) | 作業 6：企業 GPU 平台參考架構簡報（12/27）；**模組考 II：12/26（六）**；**模擬面試 II（TAM）：12/27（日）** |

### 第 7 週：間隔複習週（12/28～1/3，假期輕量）

不排新內容。每天 30～45 分鐘：模組一、二全部錯題重測，兩份跨模組累積交錯測驗（12/30、1/2），讀 G1《Obviously Awesome》，自錄一段 5 分鐘 talk（任選 W1～W6 主題）並對照評分表自評。**產出：錯題本清零 + Capstone 提案一頁（1/3 交）**。

### 模組三：LLM 理論、訓練與推理系統（W8～W10）

| 週  | 日期            | 主題                       | 核心問題                                                                 | 主要閱讀（repo，★ 為必讀）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 作業／考試                                                                                      |
| --- | --------------- | -------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| W8  | 01/04～01/10    | LLM 基礎與模型架構演進     | 一個 70B 模型要幾張卡？為什麼 FP8／FP4 是硬體賣點？                        | ★[Transformer 架構](../06_llm_theory_and_fundamentals/llm_basic_concepts/transformer/transformer_architecture.md)、★[Token 入門](../06_llm_theory_and_fundamentals/llm_basic_concepts/token/llm_token_intro.md)、★[Embedding](../06_llm_theory_and_fundamentals/llm_basic_concepts/embedding/embedding.md)、★[Scaling Laws](../06_llm_theory_and_fundamentals/llm_basic_concepts/scaling_laws/scaling_laws.md)、[Test-time Scaling](../06_llm_theory_and_fundamentals/llm_basic_concepts/scaling_laws/test_time_scaling.md)、★[MoE 圖解](../06_llm_theory_and_fundamentals/llm_basic_concepts/moe/mixture_of_experts_moe_visual_guide.zh-CN.md)、★[量化圖解](../06_llm_theory_and_fundamentals/llm_basic_concepts/quantization/visual_guide_to_quantization.md)、★[LLM 架構演進](../06_llm_theory_and_fundamentals/llm_basic_concepts/architecture_evolution/llm_architecture_evolution.md)、[模型檔案格式](../06_llm_theory_and_fundamentals/llm_basic_concepts/file_formats/llm_file_formats_complete_guide.md)、[LLM 評測](../06_llm_theory_and_fundamentals/llm_basic_concepts/evaluation/llm_evaluation.md)；外部 T5、T7 | 作業 7：模型規格 → 硬體需求計算 one-pager（01/10）                                               |
| W9  | 01/11～01/17    | 訓練並行與推理引擎核心     | 推理為什麼是記憶體頻寬問題？vLLM 到底做了什麼？                            | ★[KV Cache 基礎](../09_inference_system/kv_cache/01_concepts/01_basic/01_kv_cache_basics.md)、★[PagedAttention](../09_inference_system/kv_cache/01_concepts/01_basic/02_paged_attention.md)、★[為什麼只緩存 KV](../09_inference_system/kv_cache/01_concepts/01_basic/04_why_only_kv.md)、★[KV Cache 七張圖](../06_llm_theory_and_fundamentals/llm_basic_concepts/architecture_evolution/kv_cache_seven_charts.md)、★[Prefix Caching](../09_inference_system/kv_cache/01_concepts/02_prefix_caching/02_prefix_caching.md)、★[Chunked Prefill](../09_inference_system/kv_cache/01_concepts/03_scheduling/01_vllm_chunked_prefill.md)、[Speculative Decoding](../09_inference_system/kv_cache/01_concepts/03_scheduling/02_vllm_spec_decode.md)、★[PD 分離與 KV 傳輸](../09_inference_system/kv_cache/01_concepts/08_pd_transfer/01_disaggregated_prefill_kv_transfer.md)、[垂域 SFT 入門](../05_model_training_and_fine_tuning/sft_example/一文入门垂域模型SFT微调.md)、[KV Cache 八講總綱](../10_ai_related_course/kv_cache_course/syllabus.md)；外部 T4、T7 | 作業 8：推理引擎技術 talk 大綱 + 3 張圖（01/17）                                                 |
| W10 | 01/18～01/24    | 推理經濟學與容量規劃       | 每百萬 token 成本怎麼算？客戶該買幾張卡才划算？                            | ★[Token Factory 演講提綱](../99_misc/token_factory_talk/outline.md)、★[Token Factory 圖文講解](../99_misc/token_factory_talk/talk-illustrated.md)、★[Token 工廠產能怎麼算](../99_misc/token_factory_talk/cluster-capacity-measurement.md)、★[DeepSeek 推理集群單位經濟](../09_inference_system/cost_analysis/deepseek_inference_cluster_unit_economics.md)、★[LLM API 定價分析](../09_inference_system/cost_analysis/llm_api_pricing_analysis.md)、★[HBM KV 池與併發](../09_inference_system/kv_cache/01_concepts/10_capacity_planning/01_hbm_kv_pool_concurrency.md)、★[KV Cache ROI](../09_inference_system/kv_cache/01_concepts/10_capacity_planning/02_kv_cache_roi.md)、[LMCache 總覽](../09_inference_system/kv_cache/02_systems/01_lmcache/01_lmcache_overview.md)、[Mooncake 架構](../09_inference_system/kv_cache/02_systems/04_mooncake/01_mooncake_architecture.md)、★[記憶體分層總覽](../09_inference_system/kv_cache/04_memory_tiering/01_memory-tiering-overview.md)、★[B300 部署與 KV Cache](../09_inference_system/deployment/b300-deployment-and-kv-cache.md)；外部 T6 | 作業 9：TCO／每 token 成本模型（01/24）；**模組考 III：01/23（六）**；**模擬面試 III（PMM）：01/24（日）** |

### 模組四：應用層與 GTM 整合（W11～W12）

| 週  | 日期            | 主題                         | 核心問題                                                         | 主要閱讀（repo，★ 為必讀）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 作業／考試                                                                                                                                   |
| --- | --------------- | ---------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| W11 | 01/25～01/31    | RAG、Agent 與其對 infra 的影響 | Agent 工作負載怎麼改變推理基礎設施的需求？                        | ★[RAG 方案比較](../07_rag_and_tools/rag_basics/rag_comparison.md)、★[分塊策略評估](../07_rag_and_tools/rag_basics/evaluating_chunking_strategies_summary.md)、[GraphRAG 學習指南](../07_rag_and_tools/graph_rag/graph_rag_learning_guide.md)、★[12-Factor Agents](../08_agentic_system/concepts/12-factor-agents-intro.md)、★[ReAct Agent](../08_agentic_system/agent_design/docs/react-agent.md)、★[AI Agent Infra Stack](../08_agentic_system/agent_infra/01_ai-agent-infra-stack.md)、★[Context Engineering 入門](../08_agentic_system/context/context-engineering-intro.md)、★[MCP 深度解析](../08_agentic_system/mcp/docs/01_deep_dive_into_mcp_and_the_future_of_ai_tooling.md)、★[Agent 工作負載服務](../09_inference_system/agent_serving/agent-workload-serving.md)、★[Forward Deployed Engineer](../11_ai_native_everything/fde/forward-deployed-engineer.md)、[Agent 工程現狀報告](../08_agentic_system/reports/langchain-state-of-agent-engineering.md) | 作業 10：10 分鐘 live demo 腳本 + 失敗備案（01/31）                                                                                           |
| W12 | 02/01～02/05    | GTM 整合衝刺                 | 同一個產品，你能用 30 秒、3 分鐘、30 分鐘三種長度講清楚嗎？        | 外部 G1～G6 整合；MLPerf Training／Inference 最新結果頁（讀法：系統、精度、closed／open division、每加速器口徑）；2～3 家目標公司的產品頁與 JD；repo：[AI 基礎設施閱讀地圖](../99_misc/book-recommendations.md)、[AI Infra 入門課 PPT 大綱](../10_ai_related_course/ai_infra_lecture/入门级/AI%20Infra%20课程%20PPT%20大纲.md)（演講結構範本）                                                                                                                                                                                                                                                                                                                                                                                      | **期末綜合考：02/03（三）**；**期末作品集（2 件）：02/02（二）交**；**模擬面試 panel（四職缺輪番）：02/04（四）**；投遞清單與履歷定稿：02/05（五） |

### 八週衝刺版（備選）

若需更快投遞：刪去 W7 複習週，W4 與 W6 各砍去選讀（不帶 ★）文章並合併為一週，W11 的 RAG 部分改為只讀 [RAG 方案比較](../07_rag_and_tools/rag_basics/rag_comparison.md)。每日提取測驗、週測、作業制度不變；模組考改為兩次（W4 末、W8 末）。衝刺版代價是間隔不足，記憶保持率會下降，建議投遞後持續做每日測驗至少 4 週。

## 6. 作業與考試日期總表

### 6.1 週作業（每週日 22:00 前交，放在 `00_study_plan/handouts/wNN/assignment.md`）

| 編號    | 交期  | 作業名稱                                    | 作品集對應職缺   | 規格                                                                                                              | 1 小時版 |
| ------- | ----- | ------------------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------- | --- |
| 作業 1  | 11/22 | GPU 規格表解讀 one-pager                    | TMM／PMM         | 取一張 H100 或 B200 datasheet，逐欄解釋給業務看，附 3 個常見誤區（單向雙向、with sparsity、288 vs 270/279）       | 必做：寫給客戶 IT 主管看 |
| 作業 2  | 11/29 | HGX 8-GPU 伺服器資料路徑圖解                | TMM／TAM         | Mermaid 或手繪拓撲圖，標出 CPU–PCIe switch–GPU–NVSwitch–NIC 每段頻寬口徑，附一段 200 字客戶說法                   | 必做：加一段「為什麼配 8 張 400G 網卡」的客戶說法 |
| 作業 3  | 12/06 | 競品定位一頁                                | PMM              | NVIDIA GPU vs Google TPU vs 華為 NPU：甜蜜區、短板、什麼客戶選哪個，用 G1 的五要素框架                             | 選做（W3 有模組考與模擬面試） |
| 作業 4  | 12/13 | TAM 升級案例手冊                            | TAM              | 一個 GPU 故障或效能案例：現象 → 假設 → 診斷步驟（命令與指標）→ 溝通話術 → 事後報告範本                              | 必做：改成「客戶抱怨的第一小時」（GPU-Util 100% 但很慢），以售前視角回應 |
| 作業 5  | 12/20 | IB vs Ethernet 競品比較 + 給 CIO 的建議     | PMM／TMM         | 比較表（延遲、擁塞控制、生態、成本、營運人才）+ 300 字 CIO 建議，區分訓練與推理場景                                | 必做：給客戶 CIO 的選型建議，附 3 個競品反對意見與回應 |
| 作業 6  | 12/27 | 企業 GPU 平台參考架構簡報                   | TMM              | 一頁架構圖（K8s、device plugin、HAMi／Kueue、LWS、儲存）+ 每個元件的選型理由與替代方案                             | 選做（W6 有模組考與模擬面試） |
| 作業 7  | 01/10 | 模型規格 → 硬體需求計算 one-pager           | TMM／TAM         | 權重記憶體 + KV 估算（兩行公式）+ 三個模型三種精度的 sizing 表 + 客戶話術                                           | **必做（Pre-sales 核心）**：sizing 表 + BOM 草稿 + 假設清單 |
| 作業 8  | 01/17 | 推理引擎技術 talk 大綱 + 3 張圖             | Evangelist       | 15 分鐘 talk：用 G4 的結構，三張圖分別講 KV Cache、PagedAttention、PD 分離                                          | 必做，**改題**：推理方案建議書，同一預算給客戶三種配置選項（卡型、精度、台數），說明 KV Cache 對同時使用者數的影響 |
| 作業 9  | 01/24 | TCO／每 token 成本模型                      | PMM              | 試算表 + 假設清單（利用率、電價、折舊年限、Goodput）+ 敏感度分析 + 一頁結論；所有價格標日期                          | 必做，**交期改 01/31**（W10 有模組考與模擬面試）：一頁給採購與財務看的結論 |
| 作業 10 | 01/31 | 10 分鐘 live demo 腳本 + 失敗備案           | Evangelist       | RAG 或 Agent on vLLM 的 demo 流程、每一步要說的話、三種失敗情境的備案                                              | 選做 |

### 6.2 測驗與考試

| 類型         | 頻率／日期                                       | 時長    | 形式                                                                                           |
| ------------ | ------------------------------------------------ | ------- | ---------------------------------------------------------------------------------------------- |
| 每日提取測驗 | 每個上課日上午（W1～W6、W8～W11 共 50 次）         | 10 分鐘 | 6 題閉卷：昨日 2 題 + 3 天前 1 題 + 7 天前 1 題 + 14 天前或錯題本 1 題 + 口頭解釋 1 題，每題填信心 |
| 週前測       | 每週一（新模組首週）                              | 15 分鐘 | 10 題，涵蓋本週內容，**不計分**，只為校準與啟動（Make It Stick 第 4 章：先考再學）               |
| 週測         | 每週六（W1～W6、W8～W11 共 10 次）                 | 45 分鐘 | 20 題累積交錯：本週 10 題 + 前幾週 6 題 + 遷移應用 2 題 + 150 字客戶信 1 題 + 口說 1 題          |
| 間隔複習測驗 | 12/30、01/02                                     | 45 分鐘 | 模組一、二全範圍交錯，重點抽錯題本                                                              |
| 模組考       | 12/05、12/26、01/23                              | 90 分鐘 | 60 分鐘筆試（30 題 + 2 題長答）+ 30 分鐘白板講解（抽一題，錄影自評）                              |
| 模擬面試     | 12/06（TMM）、12/27（TAM）、01/24（Pre-sales，原 PMM）、02/04（panel，以 Pre-sales 為主） | 45 分鐘 | 英文為主；題庫見 `quizzes/interview_bank_*.md`；錄音後對照評分表自評或請他人評                   |
| 期末綜合考   | 02/03                                            | 120 分鐘 | 全範圍 40 題 + 3 題情境長答（各對應一種職缺）                                                  |
| 期末作品集   | 02/02 交，02/04 答辯                              | —       | 從 10 份作業中挑 2 件修到可投遞品質，另附一頁「我如何學這門課」的學習方法說明（面試可用）         |

## 7. 評分標準與規定

### 7.1 權重

| 項目                       | 權重 | 計分方式                                                                                         |
| -------------------------- | ---- | ------------------------------------------------------------------------------------------------ |
| 每日提取測驗               | 15%  | **只計完成率與校準**（信心 vs 正確的一致性），不計正確率，避免為了分數逃避難題                     |
| 週測                       | 20%  | 正確率，累積交錯題與本週題同權重                                                                 |
| 週作業（10 份）            | 25%  | 四維評分表（7.2），取最佳 8 份；**1 小時版：7 份必做取最佳 6 份**                                                                  |
| 模組考（3 次）+ 間隔複習測驗 | 25%  | 筆試 70% + 白板講解 30%                                                                          |
| 期末作品集 + 模擬面試 panel | 15%  | 作品 60% + 面試 40%                                                                              |

### 7.2 作業四維評分表（每維 1～4 分，合計 16 分，12 分為通過）

| 維度             | 4 分                                                                     | 2 分                                             |
| ---------------- | ------------------------------------------------------------------------ | ------------------------------------------------ |
| 技術正確與口徑   | 所有數字有來源與日期，廠商口徑與實測分開，無概念錯誤                     | 有數字無來源，或單向雙向、稀疏口徑混用一處以上   |
| 受眾適配         | 同一內容有 CxO 版與工程師版，用詞與深度切換自然                          | 只有一種聲音，或對 CxO 堆術語                     |
| 結構與故事       | 有「客戶情境 → 衝突 → 解法 → 證據」，開頭 30 秒能抓住人                    | 條列事實，沒有問題驅動                            |
| 視覺與可讀性     | 有一張能獨立說明機制的圖（Mermaid／手繪皆可），表格對齊，一頁內讀完       | 無圖或圖只是裝飾，超過兩頁                        |

### 7.3 規定

1. **閉卷先答**：每日測驗與週測不得先翻講義；答完、填完信心再對答案。對答案後再翻講義查錯因（Make It Stick：提取時的費力感才是記憶的來源）。
2. **信心必填**：每題填 1～5 的信心分數。「高信心但答錯」是最優先複習的題，「低信心但答對」要補精緻化（為什麼對）。
3. **錯題本 48 小時規則**：錯題在 48 小時內重測一次；連續三次（間隔 ≥ 3 天）答對才移出錯題本。模板見 [templates/error_log.md](templates/error_log.md)。
4. **每日口說**：每日測驗最後一題為口頭解釋，必須開口說出來（錄音 60 秒以上），不可只在心裡想。Evangelist 與 TAM 的核心能力是「說」。
5. **數字口徑**：講義、作業、口說中的任何數字，標註「來源 + 日期 + 廠商口徑或實測」。系統可用值與卡規格分開（288 vs 270/279 GB），單向與雙向分開，dense 與 sparsity 分開。違反者該維度最高 2 分。
6. **通過門檻與補救**：模組考 80% 為通過；未達者 48 小時後重考（由 `retrieval-quiz-builder` 從錯題與同知識點重新出題），重考成績取平均。
7. **缺席規則**：每週允許 1 個上課日跳過，但該日講義須在週六前補完，該日測驗併入週測。連續跳過兩天，下一週的新內容延後一天，不壓縮。
8. **作品真實性**：作業不得照抄 repo 原文；數字可引用，說法必須是自己對特定受眾寫的。每份作業附 50 字「我這次最不確定的一點」，當作面試的誠實練習。
9. **語言**：作業文件繁體中文；口說練習英文為主；每份作業的標題與 30 秒摘要另附英文版，直接成為 LinkedIn／履歷素材。
10. **複核提醒**：涉及價格、算力、市佔、模型發布的資料，每份作業註明「資料截至日期」，投遞前兩週（01/22 起）統一複核一次。

## 8. 學習方法的操作化（摘要）

完整規則見 [02_assessment_spec.md](02_assessment_spec.md) 與 skill 內的 `references/learning-science-rules.md`。這裡只列每份講義與測驗都要體現的八條：

| 原則（出處）                                | 本課程做法                                                                                      |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 提取練習優於重讀（L1 第 2 章）               | 每日 6 題閉卷、週測 20 題、模組考；講義結尾必有 5 題課後提取                                     |
| 間隔與交錯（L1 第 3 章）                     | 每日測驗固定抽 D-1／D-3／D-7／D-14+；週測與模組考跨週交錯；第 7 週整週複習                        |
| 生成與先考再學（L1 第 4 章）                 | 每週一前測不計分；每份講義開頭「先想再讀」3 題不給答案                                           |
| 校準，避免流暢感錯覺（L1 第 5 章）           | 每題信心分數；高信心錯題優先；每日測驗只計完成率與校準                                            |
| 背景知識先於技能（L2 第 2 章）               | 模組一、二先把硬體與系統的事實打牢，模組四才做定位與訊息；新手不被要求像專家一樣「批判性思考」    |
| 記憶是思考的殘留物，故事比事實好記（L2 第 3 章） | 每份講義從一個客戶情境與衝突開場；作業用「情境 → 衝突 → 解法 → 證據」結構                        |
| 具體先於抽象，多個例子才能抽象（L2 第 4 章）  | 每個概念先給真實規格表或命令輸出，再給定義；至少兩個不同代際或廠商的例子                          |
| 練習到自動化，分散而非集中（L2 第 5 章）      | 「30 秒／3 分鐘」口說每天練同一主題的不同受眾版本；GTM 技能從 W1 作業就開始，而不是留到 W12       |

## 9. 課程資料

- [讀書計畫門戶 README](README.md)：怎麼開始、每日流程、檔案索引
- [測驗規格](02_assessment_spec.md)：題型、組卷配方、評分表、錯題本與間隔演算法
- [職缺能力地圖](03_role_competency_map.md)：四種職缺 × 能力 × 面試題型 × 作品集對應
- [第一週題庫](quizzes/week01/README.md)：前測、每日測驗、週測與解答
- [模組一模擬面試題庫](quizzes/interview_bank_module1.md)
- [視覺化路線圖](roadmap.html)：12 週進度看板（可勾選，進度存於瀏覽器）
- 專案 skill：`.claude/skills/course-handout-builder/`、`.claude/skills/retrieval-quiz-builder/`
