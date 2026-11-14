# 云原生 AI 平台

## 1. 概述

從單機跟得上 AI 工作負載到一個讓上百個任務排隊、彈性擴縮、多人共用的叢集，中間缺的那一層就是雲原生 AI 平台。這一章要回答的問題是：當 Kubernetes 這套排程體系撞上 GPU 這種異構、昂貴、具備獨佔性的硬體時，需要解決哪些問題。

LLM 時代讓這個問題變得更尖銳：模型可能一次要吃掉一整個機櫃的 GPU，推理流量可能在幾秒鐘內翻十倍，而傳統靜態叢集管理方式在資源排程、彈性伸縮和故障恢復上都已經跟不上了。云原生 AI 平台透過宣告式 API、自動化控制器和不可變基礎設施，為 AI 工作負載提供一個標準化的執行環境和智慧化的管理能力。

從架構上看，整個平台一般分四層來構建，每一層解決的問題都不一樣：

1. **基礎設施層 (Infrastructure)**：物理算力、網路和儲存的底座。GPU/NPU/TPU 提供異構算力，InfiniBand/RoCE 支撐高速互聯，分散式儲存負責資料吞吐。
2. **容器編排層 (Orchestration)**：把異構硬體抽象成統一的資源池。主體是 Kubernetes，配合 Device Plugin 完成裝置上報，Operators（如 MPIOperator、PyTorchJob）接管任務的全生命週期。
3. **資源排程與管理層 (Scheduling & Management)**：針對 AI 負載的“大並行 + 貴顯存”特點做最佳化。Volcano / Kueue 處理批作業排程和 Gang Scheduling；HAMi / vGPU 做 GPU 細粒度切分與顯存隔離。
4. **AI 平台服務層 (Platform Services)**：最靠近開發者的一層，包括 Notebook 開發環境、分散式訓練框架適配、模型推理服務，以及 Kubeflow / Argo 這類 MLOps 流水線。（當前目錄尚未覆蓋，規劃中。）

四層各管一段，合起來才構成一個能承接真實 AI 工作負載的平台。

> **概念先行，實現跟進**：本目錄聚焦雲原生側的工程實現。如果對 GPU 排程背後的概念層——為什麼需要 Gang Scheduling、NVLink 拓撲對排程意味著什麼、MIG/MPS/Time-slicing 的區別——感興趣，先看 [GPU 排程為什麼比 CPU 排程難](../03_ai_cluster_ops/04_gpu_scheduling/01_gpu_scheduling_problem.md) 和 [GPU 共享排程](../03_ai_cluster_ops/04_gpu_scheduling/04_gpu_sharing_scheduling.md)。

---

## 2. 目錄結構

整套內容圍繞三個支柱展開：**計算編排**、**資源管理**、**儲存加速**。前者解決“GPU 如何被 Kubernetes 納管”，中間解決“一張卡如何被多個任務安全共用”，後者解決“海量資料和模型檢查點如何不成為短板”。

### 2.1 Kubernetes AI 基礎設施

Kubernetes 是云原生 AI 平台的作業系統。這一塊解析 K8s 在 AI 場景下的關鍵元件與擴展機制，從底層的容器執行時 GPU 支持，一路講到上層的分散式作業排程。

- [Kubernetes GPU 管理與 AI 工作負載](k8s/README.md)：云原生 AI 基礎設施建設指南與技術導圖。
- [NVIDIA Container Toolkit 原理](k8s/01_nvidia_container_toolkit_analysis.md)：容器使用 GPU 的底層機制解析。
- [Device Plugin 原理](k8s/02_nvidia_k8s_device_plugin_analysis.md)：Kubernetes 裝置外掛機制原始碼分析。
- [Kueue + HAMi 排程方案](k8s/03_kueue_hami_integration.md)：雲原生作業佇列與細粒度 GPU 共享機制。
- [vLLM + LWS：Kubernetes 上的多機多卡推理方案](k8s/04_lws_intro.md)：Kubernetes 原生的大模型推理排程抽象。
- [分布式推理框架](k8s/05_llm_d_intro.md)：基於 Kubernetes 的 LLM 推理架構設計。
- [Containerd 日志分析](k8s/06_containerd_log_analysis.md)：雲原生容器執行時的日誌排查與分析。

### 2.2 GPU 資源管理與虛擬化

GPU 是整個平台上最昂貴的資源，“如何讓它不閒著、不浪費、並且能安全地被多個任務共享”是這一模組的主線。相關內容涵蓋虛擬化、切分、遠端呼叫以及池化技術。

- [GPU 管理技術深度解析](gpu_manager/README.md)：GPU 虛擬化與切分專題的子門戶，按文件、程式碼、配置三條線組織內容。

**基礎系列文件**：

- [第一部分：基礎理論篇](gpu_manager/01_basic_theory.md)：構建技術認知框架，解析傳統模式侷限性與核心技術體系。
- [第二部分：虛擬化技術篇](gpu_manager/02_virtualization.md)：深入剖析硬體級、核心態與使用者態虛擬化的核心實現機制。
- [第三部分：資源管理與最佳化篇](gpu_manager/03_resource_management.md)：探討 GPU 切分、CUDA 流及 MPS 等高效資源排程策略。
- [第四部分：實踐應用篇](gpu_manager/04_practice.md)：涵蓋環境部署、監控運維及雲平台整合的生產落地指南。

**HAMi 專題**：

- [HAMi GPU 資源管理完整指南](gpu_manager/hami/hami-gpu-resources-guide.md)：異構算力管理與隔離實戰指南。
- [HAMi-WebUI 的 Prometheus 監控指標](gpu_manager/hami/hami-prometheus-metrics.md)：構建完善的 GPU 虛擬化可觀測性體系。
- [KAI vs HAMi 對比分析](gpu_manager/hami/KAI_vs_HAMi_Comparison.md)：以 KAI Scheduler 架構解析為主，含與 HAMi 的對比。
- [GPU-Virtual-Service 與 HAMi-Core 實現對比](gpu_manager/hami/flex_ai_intro.md)：解析 CUDA 劫持機制與 LD_PRELOAD 使用者態虛擬化方案，並與 HAMi-Core 做原始碼級對比。

**程式碼實現與配置**：

- [完整實現程式碼](gpu_manager/code/)：GPU 排程器、虛擬化攔截與遠端呼叫的參考實現程式碼。
- [配置文件集合](gpu_manager/configs/)：提供適用於生產環境和多雲平台的完整部署與配置參考。

### 2.3 高效能分散式儲存

訓練一輪次要讀上億張小圖片、檢查點動輒幾十上百 GB、推理要持續命中 KV Cache——這些場景把儲存系統推到了一個很尷尬的位置：既要像本地盤一樣快，又要像物件儲存一樣能擴。JuiceFS、DeepSeek 3FS 這類雲原生分散式檔案系統正是衝著這個縫隙作答的。

- [AI 儲存：訓練 I/O 和推理 KV Cache 的資料底座](storage/README.md)：JuiceFS、DeepSeek 3FS 與 ICMS 三個子專題的門戶導航。
- [JuiceFS 分散式檔案系統](storage/juicefs/README.md)：資料與後設資料分離的架構設計，兼容 POSIX 接口。
- [檔案修改機制分析](storage/juicefs/01_juicefs_file_modification_mechanism_analysis.md)：底層資料一致性與寫入流程解析。
- [後端儲存變更手冊](storage/juicefs/02_juicefs_backend_storage_migration_guide.md)：生產環境下的儲存運維與資料遷移指南。
- [DeepSeek 3FS 設計筆記](storage/deepseek_3fs/01_deepseek_3fs_design_notes.md)：高效能儲存系統架構設計與特性分析。
- [NVIDIA ICMS 架構解析](storage/inference_context_memory_storage/01_icms_architecture.md)：面向推理的 KV Cache 儲存層架構解析（NVIDIA 已於 2026-03 更名為 CMX，本文沿用釋出時名稱）。
