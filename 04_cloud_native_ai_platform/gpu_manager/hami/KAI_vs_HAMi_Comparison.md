# Nvidia KAI Scheduler 功能架構解析

本文件深入解析了 NVIDIA KAI Scheduler 的核心架構與關鍵特性，並將其與異構計算虛擬化中介軟體 HAMi 進行多維度對比。透過分析兩者在系統定位（排程器 vs 中介軟體）、資源隔離（軟隔離 vs 硬隔離）及適用場景（大規模訓練 vs 線上推理）上的差異，為構建高效、可靠的 AI 基礎設施提供技術選型依據。

> 版本口徑：本文基於 KAI Scheduler v0.10.0（2025-10 发布）與 HAMi v2.11.0（2026-11-04 发布）撰寫，信息截至 2026-11-05。

---

## 1. KAI Scheduler 架構與功能解析

KAI Scheduler 是一款專為大規模 AI 與機器學習工作負載定製的 Kubernetes 排程器。它構建於 **kube-batch** 架構體系之上，而非基於 Kubernetes 上游的 **Scheduling Framework** (即 kube-scheduler 的外掛化架構)。這種架構選擇使其能夠採用 **Session (會話)** 模式與 **Action (動作)** 驅動機制，從而在全域性檢視下進行復雜的資源預留和回填（Backfill）。

KAI Scheduler 旨在突破原生 Kubernetes 排程器在高效能運算（HPC）場景下的瓶頸，重點解決了 **Gang Scheduling**（全量排程）、**細粒度資源共享**以及**多租戶公平性策略**等關鍵問題。相比於關注單個 Pod 排程的原生框架，它更契合**批處理**（Batch）場景對全域性最優解的需求。

### 1.1 架構淵源與元件互動

KAI Scheduler 的技術根基源於 **kube-batch** —— Kubernetes 社群早期的批處理排程孵化專案。理解 KAI 的架構，首先需要理解它在 Kubernetes 生態中的位置及其與核心元件的互動關係。

#### 1.1.1 kube-batch 的遺產與繼承

`kube-batch` 是 Kubernetes 生態中首個引入 **PodGroup (任務組)** 概念的排程器，旨在解決 AI/HPC 場景下 "All-or-Nothing" 的排程需求。KAI Scheduler 繼承併發揚了 `kube-batch` 的核心設計理念：

- **領域模型複用**: 沿用了 `Queue` (佇列)、`PodGroup` (任務組) 等批處理原語，支援多租戶環境下的資源配額管理。
- **架構擴展**: 在保留 kube-batch 優秀的外掛化介面 (`Session-Plugin-Action`) 基礎上，KAI 深度擴展了對異構硬體（GPU/NPU）的感知能力、拓撲感知排程 (TAS) 以及更復雜的搶佔與公平性演算法，使其從一個通用的批處理排程器進化為專用的 AI 算力排程引擎。

#### 1.1.2 核心元件互動邏輯

在執行態，KAI Scheduler 與 Kubernetes 叢集元件保持著緊密而高效的互動：

1. **資料攝入 (Ingestion)**: KAI Scheduler 透過 Kubernetes 原生的 `List-Watch` 機制，實時監聽 `Pod`、`Node`、`PodGroup`、`Queue` 等資源物件的變更事件。
2. **本地快取 (Local Cache)**: 不同於直接查詢 API Server，KAI 維護了一個高度最佳化的本地記憶體檢視。所有監聽到的事件首先更新本地快取。這種設計大幅降低了 API Server 的負載，並允許排程器在微秒級完成成千上萬次模擬排程計算。
3. **決策輸出 (Binding)**: 一旦排程週期完成併產出決策，KAI Scheduler 會透過非同步客戶端向 API Server 发送 `Bind` 請求，將 Pod 繫結到選定的 Node，完成排程閉環。

### 1.2 核心排程流程

不同於原生 Kubernetes 排程器的事件驅動模型，KAI Scheduler 采用了周期性（Cycle-based）排程模型，透過快照機制確保了排程決策的全域性一致性。其核心排程流程在一個閉環週期內完成，主要包含四個階段：

1. **Cache Sync (快取同步)**：實時同步 Kubernetes API Server 的資源狀態至排程器內部快取。
2. **Snapshot (快照)**：在每個排程週期伊始捕獲叢集狀態快照。該機制有效隔離了併發修改，消除了排程計算過程中的競態條件。
3. **Session (會話)**：基於快照構建獨立的排程會話上下文，所有排程指令均在此上下文中封裝執行。
4. **Actions (排程動作)**：透過外掛化架構按序執行排程動作，核心動作包括：
   - `Allocate`: 執行核心資源分配邏輯。
   - `Preempt`: 觸發高優先順序任務對低優先順序資源的搶佔。
   - `Reclaim`: 基於公平性策略回收超額佔用的資源。
   - `Backfill`: 利用碎片資源對小任務進行回填排程。

```go
// 排程主迴圈邏輯 (基於 pkg/scheduler/scheduler.go 簡化)
func (s *Scheduler) Run(stopCh <-chan struct{}) {
    // 1. 啟動快取並等待同步完成
    s.cache.Run(stopCh)
    s.cache.WaitForCacheSync(stopCh)

    // 2. 週期性執行排程邏輯
    wait.Until(s.runOnce, s.schedulePeriod, stopCh)
}

func (s *Scheduler) runOnce() {
    // 3. 生成會話 ID (SessionID) 用於全鏈路追蹤
    sessionId := generateSessionID()

    // 4. 開啟會話 (Open Session): 構建快照並載入外掛
    // OpenSession 會初始化外掛並呼叫 OnSessionOpen
    ssn, err := framework.OpenSession(s.cache, s.config, sessionId)
    if err != nil {
        return
    }
    // 確保會話結束時清理資源並觸發外掛的 OnSessionClose
    defer framework.CloseSession(ssn)

    // 5. 按序執行配置的排程動作 (Actions)
    actions := conf_util.GetActionsFromConfig(s.config)
    for _, action := range actions {
        // 設定當前動作上下文 (用於日誌與監控)
        log.SetAction(action.Name())
        metrics.SetCurrentAction(action.Name())

        // 執行具體動作 (如 Allocate, Preempt, Backfill)
        action.Execute(ssn)
    }
}
```

### 1.3 關鍵特性

#### 1.3.1 Gang Scheduling (PodGroups)

針對分散式訓練任務（如 Parameter Server 架構），KAI Scheduler 引入了 `PodGroup` 資源物件以實現 "All-or-Nothing" 的排程語義。該特性確保任務的所有元件能夠同時獲得資源並啟動，從根本上解決了因資源死鎖導致的訓練停滯問題，顯著提升了叢集的作業完成率。

#### 1.3.2 多級佇列與公平性 (Hierarchical Queues & Fairness)

系統支援樹狀層級佇列管理，並基於 DRF (Dominant Resource Fairness) 演算法實現精細化的資源公平排程。這不僅透過應得配額（Deserved Quota）保障了佇列的基礎資源供給，還允許在叢集空閒時進行超額借用（Over-quota）。此外，引入的時間感知公平（Time-aware Fairness）機制透過計算歷史資源消耗的權重，防止特定租戶長期霸佔資源，從而實現了長週期維度的真正公平。

#### 1.3.3 拓撲感知排程 (Topology Aware Scheduling, TAS)

針對大模型訓練對互聯頻寬的苛刻要求，原生整合物理拓撲感知能力（如 Rack, Zone 維度）：

- **Bin-packing (裝箱策略)**: 優先將任務排程至同一拓撲域，最大化減少跨域通訊。
- **Node Ordering (節點優選)**: 在選定拓撲域內，基於親和性對節點進行排序，降低節點間通訊延遲。

#### 1.3.4 GPU 共享與動態資源分配

在資源複用方面，KAI Scheduler 支持物理 GPU 的邏輯切分，允許使用者透過註解宣告算力比例或顯存額度（Fractional Request）。其實現採用軟隔離（Soft Isolation）機制，依賴應用層的協作或配合 NVIDIA MPS 技術。同時，它全面兼容 Kubernetes DRA (Dynamic Resource Allocation) 架構，為管理第三方異構硬體資源提供了標準化的擴展介面。

---

## 2. HAMi 架構與功能解析

HAMi (Heterogeneous AI Computing Virtualization Middleware) 定位為異構 AI 計算虛擬化中介軟體。與排程器不同，HAMi 聚焦於**裝置層的虛擬化**與**異構硬體的統一管理**，旨在消除不同異構裝置之間的差異，提供統一的管理介面。

### 2.1 核心架構與隔離機制

HAMi 采用 `MutatingWebhook` + `Scheduler Extender` + `Device Plugin` 的非侵入式架構，作為原生排程器的能力增強外掛執行。其最顯著的特性是**硬隔離 (Hard Isolation)**，透過底層庫劫持（Library Interposition）等容器內虛擬化技術，實時攔截並審查 CUDA API 呼叫。這一機制強制實施了顯存配額與算力核心限制，確保了多租戶環境下的資源安全邊界，有效防止了越界使用。

### 2.2 異構資源管理

在資源管理層面，HAMi 提供了極細粒度的控制能力。它支持按固定大小 (`nvidia.com/gpumem`) 或百分比 (`nvidia.com/gpumem-percentage`) 分配顯存，以及按百分比分配 GPU 算力核心 (`nvidia.com/gpucores`)。

此外，HAMi 構建了統一的異構裝置抽象層，除 NVIDIA GPU 外，還廣泛支援華為 Ascend NPU、寒武紀 MLU、海光 DCU、天數智芯 CoreX、摩爾執行緒及沐曦等主流國產 AI 芯片。這種廣泛的相容性使其成為混合硬體環境下的理想管理工具。

### 2.3 排程增強

雖然作為中介軟體，HAMi 也提供了一系列排程增強能力以最佳化分配效率。這包括優先減少碎片的 Binpack 策略、實現負載均衡的 Spread 策略，以及確保 GPU 和 CPU 在同一 NUMA 節點以減少延遲的 NUMA-First 策略。它還允許使用者透過註解指定所需的 GPU 型號或具體 UUID，提供了靈活的資源繫結能力。

此外，HAMi 注重系統的易用性與配置靈活性。它提供了視覺化 WebUI (v2.4+) 以便管理員直觀監控資源狀態，並支援全域性、節點級及 Pod 級的三級配置策略，允許針對不同叢集區域靈活調整資源隔離與超賣策略。

---

## 3. KAI Scheduler 與 HAMi 對比分析

### 3.1 核心能力對比

| **特性維度**     | **KAI Scheduler**                                   | **HAMi**                                           |
| :--------------- | :-------------------------------------------------- | :------------------------------------------------- |
| **系統定位**     | 面向 AI/Batch 任務的**全量排程器** (Scheduler)      | 面向裝置虛擬化與隔離的**中介軟體** (Middleware)      |
| **架構模式**     | 獨立/替換式架構 (基於 kube-batch)                   | 插件/擴展式架構 (Extender + Webhook)               |
| **GPU 隔離級別** | **軟隔離** (Soft Isolation)，側重邏輯分配，依賴協作 | **硬隔離** (Hard Isolation)，基於 API 攔截強制限制 |
| **公平性策略**   | **作業級公平**，支援多級佇列、DRF 及 Time-aware     | **裝置級公平**，側重物理裝置切分利用率             |
| **拓撲感知**     | **原生集成** (TAS)，內建拓撲優選，路徑更短          | **擴展支援**，透過策略實現，效率略遜原生           |
| **生態相容性**   | **NVIDIA 深度最佳化**，官方維護                       | **多廠商異構**，廣泛支援國產晶片                   |
| **作業編排**     | **強**，原生支持 Gang Scheduling 及搶佔             | **中**，依賴底層排程器能力                         |
| **資源粒度**     | **粗/中粒度**，以 GPU 數量或大塊顯存為主            | **極細粒度**，支持按百分比、具體顯存大小切分       |

### 3.2 深度技術差異解析

#### 3.2.1 排程哲學與決策範圍

**KAI Scheduler** 扮演的是**全域性決策者**的角色。它接管了 Pod 的全生命周期管理，具備為了全域性最優（如 Gang Scheduling 的資源預留）而推遲部分任務排程的能力。其設計目標是最佳化整個叢集在多租戶、高併發場景下的作業吞吐量與資源公平性。相比之下，**HAMi** 扮演的是**資源增強層**的角色。它透過虛擬化技術將物理 GPU 對映為多個 vGPU，從而“欺騙”Kubernetes 原生排程器。它不改變 Kubernetes 的核心排程邏輯，而是致力於提升底層資源的分配靈活性與利用率。

#### 3.2.2 資源隔離機制的本質區別

**KAI** 的 GPU 共享機制本質上是一種**排程層面的記賬（Accounting）**。例如，當分配 `0.5` GPU 時，排程器確保同一物理卡上僅排程兩個此類 Pod。若應用發生顯存洩漏或越界使用，KAI 排程器層面無法進行執行時的強制攔截。而 **HAMi** 的核心優勢在於**執行時虛擬化**。它在容器啟動時注入特定的動態連結庫，實時攔截並審查 CUDA 記憶體申請。若申請量超過配額，API 呼叫將直接返回失敗。這種機制在不可信的多租戶環境中提供了必要的安全保障。

#### 3.2.3 公平性維度的側重

**KAI** 聚焦於**組織/租戶層面的公平性**，透過多級佇列模型解決“部門 A 與部門 B 資源爭搶”的問題，支援複雜的借用與歸還機制。**HAMi** 則聚焦於**裝置層面的切分效率**，致力於解決“如何將單張 GPU 卡高效切分給多個小任務”的問題，側重於提升單卡的利用率。

### 3.3 場景化適用性分析

#### 3.3.1 AI 訓練場景 (Training)

在模型訓練，尤其是**大規模分散式訓練**（如 LLM 預訓練、微調）場景下，**KAI Scheduler** 具有壓倒性優勢。

- **核心挑戰**: 資源死鎖、網路頻寬瓶頸、多租戶資源爭搶。
- **KAI Scheduler 優勢**:
  - **Gang Scheduling**: 原生支持 PodGroup，確保分散式任務的所有 Worker 能夠 "All-or-Nothing" 啟動，徹底根除死鎖風險。
  - **拓撲感知 (TAS)**: 對於通訊密集型訓練任務，KAI 能將 Pod 排程到同一交換機或機架下，顯著降低 AllReduce 通訊延遲，提升訓練效率。
  - **公平性保障**: 基於 DRF 的佇列管理機制，確保了不同部門或專案組在共享大叢集時的資源公平性，避免算力被單一業務獨佔。
- **HAMi 局限性**: 缺乏全域性視角的 Gang Scheduling 能力，容易導致分散式任務的部分 Pod 等待資源而部分 Pod 空轉。

#### 3.3.2 AI 推理場景 (Inference)

在**線上推理**與**開發除錯**場景下，**HAMi** 往往是更優的選擇。

- **核心挑戰**: 資源碎片化、服務間干擾、異構硬體適配。
- **HAMi 優勢**:
  - **強隔離保障 SLA**: 推理服務通常對穩定性要求極高。HAMi 的顯存硬隔離機制能防止因某個服務 OOM 而導致同一張卡上的其他推理服務崩潰，保障業務 SLA。
  - **極致資源利用率**: 推理任務通常無法佔滿整卡。HAMi 支援細粒度切分（如分配 10% 算力 + 2GB 顯存），允許在單張高效能卡（如 A100）上混部數十個小模型推理服務。
  - **異構推理卡支援**: 推理側硬體選型多樣（如 T4, A10, Ascend 310 等）。HAMi 廣泛的硬體相容性使其能統一納管各類異構推理晶片。
- **KAI Scheduler 局限性**: 軟隔離機制在不可信的多租戶推理場景下存在安全隱患；缺乏對非 NVIDIA 推理卡的深度支持。

### 3.4 選型建議與總結

在實際架構設計中，建議根據**業務核心屬性**進行分層決策：

1. **大規模訓練叢集 (Training Cluster)**:

   - **首選 KAI Scheduler**。核心訴求是算力吞吐與作業編排，需依賴其 Gang Scheduling 與 TAS 能力。
   - **可選搭配**: 若需在訓練叢集中混部少量除錯任務，可引入 HAMi 作為輔助，但需注意排程器衝突。

2. **推理與開發叢集 (Inference/Dev Cluster)**:

   - **首選 HAMi**。核心訴求是資源利用率與安全隔離。利用其硬隔離特性實現高密度混部，降低單位推理成本。

3. **混合業務叢集**:
   - 建議採用 **"KAI Scheduler (主) + HAMi (輔)"** 的聯合部署模式。
   - 利用 KAI Scheduler 處理宏觀的佇列管理與大任務編排。
   - 利用 HAMi 處理節點內的細粒度切分與隔離。
   - **注意**: 需精細配置 Resource Name（如 KAI 使用 `nvidia.com/gpu`，HAMi 使用 `nvidia.com/gpumem`），避免資源核算的衝突。

### 3.5 前沿探索：社群融合方案（已合入）

HAMi 社群與 KAI Scheduler 社群探討了一種更深度的融合方案（Resource isolation 設計，[PR #60](https://github.com/NVIDIA/KAI-Scheduler/pull/60)），已於 2026-06-09 合入 KAI Scheduler 主干。該方案透過解耦的方式，在保留 KAI 排程決策權的同時，引入 HAMi 的底層硬隔離能力。

**方案架構核心**:

該方案不再依賴 HAMi 的 Scheduler Extender，而是將 HAMi 的核心隔離能力 (HAMi Core) 作為獨立元件執行：

1. **元件解耦**:

   - **KAI Scheduler**: 繼續負責核心排程邏輯（Gang Scheduling, TAS 等）及資源分配決策。
   - **HAMi Core**: 以 DaemonSet 形式獨立部署，僅負責節點級的動態庫分發與底層攔截。
   - **Mutating Webhook**: 負責攔截 Pod 建立請求，注入 HAMi Core 的掛載路徑。

2. **協同工作流**:
   - **Step 1 (排程)**: KAI Scheduler 完成排程決策，並將分配的顯存大小（Bytes）寫入標準環境變數（如 `GPU_MEMORY_LIMIT`）。
   - **Step 2 (注入)**: Webhook 自動掛載 HAMi Core 的動態連結庫到 Pod 容器中。
   - **Step 3 (執行時)**: 容器啟動時載入攔截庫，庫函式讀取 `GPU_MEMORY_LIMIT` 環境變數，在 CUDA API 呼叫層面強制實施顯存硬隔離。

**方案價值**:

這種模式試圖打破“二選一”的局面，實現 **“KAI 的全域性編排能力 + HAMi 的執行時硬隔離能力”** 的完美結合，且對 KAI 排程器的程式碼侵入性極低。

---

## 4. 擴展對比：KAI Scheduler vs Volcano

鑑於 **KAI Scheduler** 與 CNCF 孵化專案 **[Volcano](https://github.com/volcano-sh/volcano)** 均源自 **kube-batch** 架構體系，兩者在技術路線上存在一定的親緣性，但在演進方向與適用場景上已展現出顯著差異。

### 4.1 定位與演進方向差異

| **維度**     | **KAI Scheduler**                                                                | **Volcano**                                                                          |
| :----------- | :------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------- |
| **核心定位** | **垂直深耕的 AI 算力引擎**                                                       | **通用的雲原生批處理平台**                                                           |
| **目標場景** | 聚焦 **LLM/GenAI** 大規模分散式訓練，深度適配 NVIDIA 硬體棧 (GPU/NPU/InfiniBand) | 覆蓋 **BigData** (Spark/Flink), **AI**, **HPC**, **基因計算** 等廣泛的批處理工作負載 |
| **生態相容** | 緊密整合 NVIDIA GPU Operator, DRA, PyTorch 等 AI 生態                            | 廣泛支援 Spark Operator, Flink Operator, Argo, Kubeflow 等 CNCF/大資料生態           |

### 4.2 核心能力對比

- **拓撲感知 (Topology Awareness)**:

  - **KAI Scheduler**: 擁有 **Native TAS** 能力，針對 NVIDIA 硬體拓撲（NVLink, NVSwitch, InfiniBand 結構）進行了深度定製與最佳化，能夠感知極其細微的硬體互聯層級，以極致降低 AI 訓練的通訊延遲。
  - **Volcano**: 提供通用的拓撲感知外掛，更側重於 CPU/NUMA 或通用的網路距離，對特定 AI 晶片的私有互聯協議最佳化不如 KAI 深入。

- **公平性算法 (Fairness)**:

  - **KAI Scheduler**: 引入了 **Time-aware Fairness** (時間感知公平性)，不僅關注當前的資源配額，還追溯歷史使用時長，防止長期霸佔資源，更適合昂貴的 GPU 算力租賃場景。
  - **Volcano**: 經典的 DRF (Dominant Resource Fairness) 演算法實現，側重於多資源維度的即時分配公平。

- **作業類型支援**:
  - **KAI Scheduler**: 針對 AI 訓練任務（Training Jobs）進行了特化，對 `All-or-Nothing` 的 Gang Scheduling 做了針對大模型的死鎖最佳化。
  - **Volcano**: 對資料密集型任務（Data-Intensive）有更好的支持，如 Spark 的 Driver/Executor 模型，支援更豐富的作業外掛（Job Plugins）。

### 4.3 選型建議

- **選擇 KAI Scheduler**: 如果您的叢集是 **NVIDIA GPU 專用算力池**，且核心業務是 **LLM 預訓練/微調**，追求極致的算力利用率與訓練速度，KAI 的垂直最佳化能力將帶來更高的 ROI。
- **選擇 Volcano**: 如果您的叢集是 **混合負載叢集**（同時執行 Spark 資料處理、Flink 流計算、以及 AI 訓練），需要一個統一的批處理排程器來管理多樣化的工作負載，Volcano 是更通用且成熟的選擇。

---
