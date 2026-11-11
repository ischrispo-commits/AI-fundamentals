# 每週五日切分與每日來源文章

路徑相對 repo 根目錄。每日「主要來源」是講義取材的起點，必要時再讀同目錄的 README。第 7 週為複習週，不產生講義。W12 的 D4、D5 是考試與面試日，不產生講義。

## W1（11/16～11/22）GPU 本體：讀懂一張卡

| 日  | 主題                                           | 主要來源                                                                                                                                                                                      |
| --- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | GPU vs CPU、SIMT／warp／SM、kernel 與 block     | `01_hardware_architecture/nvidia/understand_gpu_architecture/01_gpu_characteristics.md`                                                                                                        |
| D2  | 記憶體層級、HBM vs GDDR、HBM 代際與公式         | `01_hardware_architecture/nvidia/understand_gpu_architecture/02_gpu_memory.md`、`01_hardware_architecture/performance/01_hbm_evolution.md`                                                    |
| D3  | A100 → H100 → B200/B300 代際、Tensor Core 精度、MIG、稀疏 | `01_hardware_architecture/nvidia/understand_gpu_architecture/07_a100_architecture.md`、`01_hardware_architecture/performance/05_pcie_nvlink_speed_reference.md`（§3）、`01_hardware_architecture/superchips/nvidia_gb300.md`（§1） |
| D4  | 規格表素養：Gbps vs GB/s、單向雙向、dense／sparsity、卡規格／系統可用、公式 | `01_hardware_architecture/nvlink/nvlink_intro.md`（§2.2、§5）、`01_hardware_architecture/performance/05_pcie_nvlink_speed_reference.md`（§1、§2、§6、§7）                         |
| D5  | 情境整合：訓練 vs 推理選卡、MIG 多租戶、消費卡限制；延遲金字塔 Level 1～2 | `01_hardware_architecture/performance/ai_latency_pyramid.md`（§3、§4）、`01_hardware_architecture/nvlink/nvlink_intro.md`（§5.3）、`10_ai_related_course/kv_cache_course/01-kv-cache-basics/syllabus.md`（重點難點表） |

## W2（11/23～11/29）節點內互連與資料路徑

| 日  | 主題                                                   | 主要來源                                                                                                                                                       |
| --- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | PCIe 基礎：代際、lane、編碼、Root Complex／Switch／Endpoint | `01_hardware_architecture/pcie/01_pcie_comprehensive_guide.md`                                                                                            |
| D2  | PCIe 拓撲層級、Switch vs Bridge、PCIe 域與 NUMA         | `01_hardware_architecture/pcie/06_pcie_topology_hierarchy.md`、`01_hardware_architecture/pcie/07_pcie_switch_vs_bridge.md`、`01_hardware_architecture/performance/04_pcie_domain_numa.md` |
| D3  | NVLink／NVSwitch／SHARP、NVLink-C2C                     | `01_hardware_architecture/nvlink/nvlink_intro.md`（§3、§4）、`01_hardware_architecture/superchips/nvlink_c2c.md`                                               |
| D4  | GPUDirect P2P／RDMA／Storage、DMA engine                | `01_hardware_architecture/gpudirect/01_gpudirect_technology.md`、`01_hardware_architecture/gpudirect/02_gpudirect_p2p.md`、`01_hardware_architecture/dma/01_dma_engine.md` |
| D5  | 整合：HGX 8-GPU 資料路徑走讀、單 GPU 拓撲分析、CXL 一瞥   | `01_hardware_architecture/performance/02_single_gpu_topology_analysis.md`、`01_hardware_architecture/pcie/03_pcie_topology_visualization.md`、`01_hardware_architecture/pcie/08_cxl_interconnect_overview.md` |

## W3（11/30～12/06）機架級系統與競品地圖

| 日  | 主題                                             | 主要來源                                                                                                                                       |
| --- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | GB300 NVL72 系統規格、拓撲、C2C 實測              | `01_hardware_architecture/superchips/nvidia_gb300.md`                                                                                           |
| D2  | 延遲金字塔四層與估算公式（Ring AllReduce、TTFT）   | `01_hardware_architecture/performance/ai_latency_pyramid.md`                                                                                    |
| D3  | TPU 101：MXU／systolic array／Pod／XLA            | `01_hardware_architecture/tpu/tpu_101.md`                                                                                                       |
| D4  | GPGPU vs NPU、AMX vs Tensor Core、Ascend 950 概念  | `01_hardware_architecture/nvidia/GPGPU_vs_NPU_大模型推理训练对比.md`、`01_hardware_architecture/performance/03_amx_vs_tensorcore.md`、`01_hardware_architecture/ascend/Ascend950_微架构速查.md` |
| D5  | 資料中心基礎（電力、冷卻、PUE、SuperPOD RA）+ 模組一複習 | 外部 T3、T6；`03_ai_cluster_ops/05_datacenter/china-dc-boom-semianalysis.md`（市場脈絡）；本模組 K 點全表                                       |

## W4（12/07～12/13）GPU 運維、可觀測性與切分

| 日  | 主題                                           | 主要來源                                                                                                                                                 |
| --- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | nvidia-smi、device query、GPU 利用率迷思        | `03_ai_cluster_ops/01_gpu_ops/02_gpu_utilization_myth.md`、`03_ai_cluster_ops/01_gpu_ops/03_nvidia_smi_guide.md`、`03_ai_cluster_ops/01_gpu_ops/01_device_query.md` |
| D2  | DCGM 監控與 GPU 健康檢查                        | `03_ai_cluster_ops/01_gpu_ops/05_dcgm_monitoring.md`、`03_ai_cluster_ops/01_gpu_ops/06_gpu_health_check.md`                                               |
| D3  | 驅動排障、常見故障模式、程序管理                 | `03_ai_cluster_ops/01_gpu_ops/08_gpu_driver_troubleshooting.md`、`03_ai_cluster_ops/01_gpu_ops/07_gpu_process_management.md`、`03_ai_cluster_ops/01_gpu_ops/09_gpu_busy_check.md` |
| D4  | GPU 虛擬化與切分：MIG／MPS／時間切片／用戶態攔截  | `04_cloud_native_ai_platform/gpu_manager/01_basic_theory.md`、`04_cloud_native_ai_platform/gpu_manager/02_virtualization.md`                              |
| D5  | 資源管理與最佳化；TAM 升級案例的結構             | `04_cloud_native_ai_platform/gpu_manager/03_resource_management.md`；`00_study_plan/03_role_competency_map.md`（TAM 節）                                   |

## W5（12/14～12/20）Scale-out 網路與集合通訊

| 日  | 主題                                                 | 主要來源                                                                                                                                             |
| --- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | IB 網路架構與協定：RDMA、QP、子網管理、擁塞控制       | `03_ai_cluster_ops/02_infiniband/01_ib_network_theory.md`                                                                                            |
| D2  | NCCL 理論：ring／tree、AllReduce 成本模型             | `03_ai_cluster_ops/03_nccl/01_nccl_theory.md`、`01_hardware_architecture/performance/ai_latency_pyramid.md`（§4 公式）                                |
| D3  | NCCL 基準測試解讀與通訊路徑                           | `03_ai_cluster_ops/03_nccl/04_nccl_benchmark.md`、`03_ai_cluster_ops/03_nccl/06_nccl_path_benchmark.md`                                              |
| D4  | IB vs RoCE／Ethernet（Spectrum-X、UEC）、rail-optimized | `03_ai_cluster_ops/02_infiniband/01_ib_network_theory.md`（對比節）；外部 T3、Spectrum-X 產品頁、UEC 1.0 概述                                      |
| D5  | GPU 排程：排程問題、gang、拓撲感知                     | `03_ai_cluster_ops/04_gpu_scheduling/01_gpu_scheduling_problem.md`、`03_ai_cluster_ops/04_gpu_scheduling/02_gang_scheduling_for_training.md`、`03_ai_cluster_ops/04_gpu_scheduling/03_topology_aware_scheduling.md` |

## W6（12/21～12/27）雲原生 AI 平台與 AI 儲存

| 日  | 主題                                         | 主要來源                                                                                                                                                       |
| --- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Container Toolkit 與 Device Plugin 原理        | `04_cloud_native_ai_platform/k8s/01_nvidia_container_toolkit_analysis.md`、`04_cloud_native_ai_platform/k8s/02_nvidia_k8s_device_plugin_analysis.md`           |
| D2  | Kueue + HAMi、GPU 共享排程、KAI                | `04_cloud_native_ai_platform/k8s/03_kueue_hami_integration.md`、`04_cloud_native_ai_platform/gpu_manager/hami/hami-gpu-resources-guide.md`、`03_ai_cluster_ops/04_gpu_scheduling/04_gpu_sharing_scheduling.md`、`04_cloud_native_ai_platform/gpu_manager/hami/KAI_vs_HAMi_Comparison.md` |
| D3  | LWS 與 llm-d：K8s 上的多機推理                 | `04_cloud_native_ai_platform/k8s/04_lws_intro.md`、`04_cloud_native_ai_platform/k8s/05_llm_d_intro.md`                                                         |
| D4  | AI 儲存：JuiceFS、3FS、ICMS、GDS               | `04_cloud_native_ai_platform/storage/README.md`、`04_cloud_native_ai_platform/storage/deepseek_3fs/01_deepseek_3fs_design_notes.md`、`04_cloud_native_ai_platform/storage/inference_context_memory_storage/01_icms_architecture.md`、`01_hardware_architecture/gpudirect/03_gds_basics.md` |
| D5  | 參考架構整合 + 模組二複習                       | `04_cloud_native_ai_platform/README.md`；本模組 K 點全表                                                                                                      |

## W7（12/28～01/03）間隔複習週：不產生講義

D1 模組一錯題重測；D2 模組二錯題重測；D3（12/30）累積測驗 1；D4 讀 G1 + 自錄 talk；D5（1/1）Capstone 提案；1/2（六）累積測驗 2。

## W8（01/04～01/10）LLM 基礎與模型架構演進

| 日  | 主題                                                  | 主要來源                                                                                                                                                                 |
| --- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | Transformer 與 attention、token／tokenizer              | `06_llm_theory_and_fundamentals/llm_basic_concepts/transformer/transformer_architecture.md`、`06_llm_theory_and_fundamentals/llm_basic_concepts/token/llm_token_intro.md` |
| D2  | Embedding、位置編碼與 RoPE 概念                         | `06_llm_theory_and_fundamentals/llm_basic_concepts/embedding/embedding.md`、`06_llm_theory_and_fundamentals/llm_basic_concepts/positional_encoding/positional_encoding.md` |
| D3  | Scaling laws、test-time scaling、架構演進（GPT-2 → MoE → MLA） | `06_llm_theory_and_fundamentals/llm_basic_concepts/scaling_laws/scaling_laws.md`、`.../scaling_laws/test_time_scaling.md`、`.../architecture_evolution/llm_architecture_evolution.md` |
| D4  | MoE 與量化（FP16／BF16／FP8／INT4／FP4）               | `06_llm_theory_and_fundamentals/llm_basic_concepts/moe/mixture_of_experts_moe_visual_guide.zh-CN.md`、`.../quantization/visual_guide_to_quantization.md`                 |
| D5  | 模型檔案格式、評測與幻覺；權重記憶體估算                 | `.../file_formats/llm_file_formats_complete_guide.md`、`.../evaluation/llm_evaluation.md`、`.../hallucination/llm_hallucination_and_mitigation.md`                       |

## W9（01/11～01/17）訓練並行與推理引擎核心

| 日  | 主題                                                 | 主要來源                                                                                                                                                              |
| --- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | 訓練並行 DP／TP／PP／EP 與互連需求；SFT／RL 概念        | 外部 T4；`01_hardware_architecture/nvlink/nvlink_intro.md`（§5.3）；`05_model_training_and_fine_tuning/sft_example/一文入门垂域模型SFT微调.md`；`05_model_training_and_fine_tuning/rl_training/miles-train-rollout-alignment.md` |
| D2  | KV Cache 基礎、兩行公式、為什麼只緩存 KV               | `09_inference_system/kv_cache/01_concepts/01_basic/01_kv_cache_basics.md`、`.../01_basic/04_why_only_kv.md`、`06_llm_theory_and_fundamentals/llm_basic_concepts/architecture_evolution/kv_cache_seven_charts.md`、`10_ai_related_course/kv_cache_course/01-kv-cache-basics/syllabus.md` |
| D3  | PagedAttention 與 prefix caching                      | `09_inference_system/kv_cache/01_concepts/01_basic/02_paged_attention.md`、`.../02_prefix_caching/02_prefix_caching.md`、`.../02_prefix_caching/01_radix_attention.md`  |
| D4  | Chunked prefill、speculative decoding、CUDA graph      | `.../03_scheduling/01_vllm_chunked_prefill.md`、`.../03_scheduling/02_vllm_spec_decode.md`、`.../04_execution/01_vllm_cuda_graph.md`                                    |
| D5  | PD 分離與 KV 傳輸                                     | `.../08_pd_transfer/01_disaggregated_prefill_kv_transfer.md`、`.../08_pd_transfer/02_pd_state_handoff_optimization_map.md`                                              |

## W10（01/18～01/24）推理經濟學與容量規劃

| 日  | 主題                                                     | 主要來源                                                                                                                                                      |
| --- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Token 經濟與四層槓桿                                      | `99_misc/token_factory_talk/outline.md`、`99_misc/token_factory_talk/talk-illustrated.md`                                                                     |
| D2  | 單位經濟與 API 定價分析                                   | `09_inference_system/cost_analysis/deepseek_inference_cluster_unit_economics.md`、`09_inference_system/cost_analysis/llm_api_pricing_analysis.md`              |
| D3  | 叢集產能：Goodput 與 SLO                                  | `99_misc/token_factory_talk/cluster-capacity-measurement.md`                                                                                                  |
| D4  | KV 容量規劃與 ROI、記憶體分層、LMCache／Mooncake 概念      | `09_inference_system/kv_cache/01_concepts/10_capacity_planning/01_hbm_kv_pool_concurrency.md`、`.../10_capacity_planning/02_kv_cache_roi.md`、`09_inference_system/kv_cache/04_memory_tiering/01_memory-tiering-overview.md`、`09_inference_system/kv_cache/02_systems/01_lmcache/01_lmcache_overview.md`、`.../02_systems/04_mooncake/01_mooncake_architecture.md` |
| D5  | B300 部署與 KV、HBF vs HBM；TCO 模型組裝                   | `09_inference_system/deployment/b300-deployment-and-kv-cache.md`、`09_inference_system/hbf-vs-hbm.md`；外部 T6                                                 |

## W11（01/25～01/31）RAG、Agent 與其對 infra 的影響

| 日  | 主題                                             | 主要來源                                                                                                                                                                 |
| --- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | RAG 方案比較、分塊策略、embedding 選型            | `07_rag_and_tools/rag_basics/rag_comparison.md`、`07_rag_and_tools/rag_basics/evaluating_chunking_strategies_summary.md`、`07_rag_and_tools/rag_basics/chinese_rag_embedding_model_selection.md` |
| D2  | Agent 概念：12-factor、ReAct、agent infra stack   | `08_agentic_system/concepts/12-factor-agents-intro.md`、`08_agentic_system/agent_design/docs/react-agent.md`、`08_agentic_system/agent_infra/01_ai-agent-infra-stack.md` |
| D3  | Context engineering 與 MCP                        | `08_agentic_system/context/context-engineering-intro.md`、`08_agentic_system/mcp/docs/01_deep_dive_into_mcp_and_the_future_of_ai_tooling.md`                             |
| D4  | Agent 工作負載對推理系統的影響                     | `09_inference_system/agent_serving/agent-workload-serving.md`、`09_inference_system/agent_serving/constrained-decoding-engines.md`                                      |
| D5  | FDE 與 AI native 工程；demo 腳本結構              | `11_ai_native_everything/fde/forward-deployed-engineer.md`、`11_ai_native_everything/fde/fde-ai-landing-guide.md`                                                        |

## W12（02/01～02/05）GTM 整合衝刺

| 日  | 主題                                      | 主要來源                                                                                                       |
| --- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| D1  | 定位五要素實作（Obviously Awesome）         | 外部 G1；`00_study_plan/03_role_competency_map.md`；W3 作業 3 回顧                                              |
| D2  | 訊息架構（Made to Stick）與三種長度         | 外部 G2、G4；`10_ai_related_course/ai_infra_lecture/入门级/AI Infra 课程 PPT 大纲.md`（演講結構範本）           |
| D3  | 競品地圖與 MLPerf 讀法                      | 外部 MLPerf 結果頁；`01_hardware_architecture/tpu/tpu_101.md`（§6）；`01_hardware_architecture/nvidia/GPGPU_vs_NPU_大模型推理训练对比.md` |
| D4  | 期末綜合考（不產生講義）                    | —                                                                                                              |
| D5  | 模擬面試 panel 與投遞清單（不產生講義）       | —                                                                                                              |
