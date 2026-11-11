# Kueue + HAMi：Kubernetes 原生的 AI 工作負載管理與 GPU 虛擬化解決方案

## 1. 概述與核心價值

`Kueue` 是一個專為 `Kubernetes` 設計的雲原生作業佇列系統，專門用於管理批處理、高效能運算（`HPC`）、人工智能/機器學習（`AI`/`ML`）以及類似應用的工作負載。作為 `Kubernetes SIG Scheduling` 的官方專案，`Kueue` 提供了一套完整的 `API` 和控制器，用於實現作業級別的佇列管理和資源排程。

### 1.1 核心價值與定位

`Kueue` 的設計理念是構建一個多租戶的批處理服務，透過配額管理和層次化的資源共享機制，幫助組織內的不同團隊高效共享計算資源。基於可用配額，`Kueue` 能夠智慧決策作業的等待時機以及執行的時間和位置。

重要的是，`Kueue` 與標準的 `kube-scheduler`、`cluster-autoscaler` 以及整個 `Kubernetes` 生態系統協同工作。這種設計使得 `Kueue` 既可以在本地環境中執行，也可以在雲環境中部署，支援異構、可替代和動態配置的資源。

### 1.2 生產就緒狀態

`Kueue` 已經達到生產就緒狀態，具備以下特徵：

- ✅ **API 版本**：`v1beta1`，遵循 `Kubernetes` 棄用策略
- ✅ **完整文件**：提供詳盡的使用文件和最佳實踐
- ✅ **全面測試覆蓋**：
  - 單元測試、整合測試、端到端測試
  - 支持 `Kubernetes 1.29`或更新版本
  - 效能測試驗證可擴展性
- ✅ **安全性**：基於 `RBAC` 的訪問控制
- ✅ **穩定釋出週期**：2-3 個月的規律釋出
- ✅ **生產採用者**：已有多個組織在生產環境中使用 `Kueue`

---

## 2. 核心概念與架構

### 2.0 核心資源物件關係圖

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                Kueue 核心架構                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│      ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│      │   Namespace A   │    │   Namespace B   │    │   Namespace C   │          │
│      │                 │    │                 │    │                 │          │
│      │ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │          │
│      │ │ LocalQueue  │ │    │ │ LocalQueue  │ │    │ │ LocalQueue  │ │          │
│      │ │   (team-a)  │ │    │ │   (team-b)  │ │    │ │   (team-c)  │ │          │
│      │ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │          │
│      │        │        │    │        │        │    │        │        │          │
│      │ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │          │
│      │ │    Jobs     │ │    │ │    Jobs     │ │    │ │    Jobs     │ │          │
│      │ │ (使用者提交)   │ │    │ │ (使用者提交)    │ │    │ │ (使用者提交)   │ │          │
│      │ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │          │
│      └─────────────────┘    └─────────────────┘    └─────────────────┘          │
│               │                       │                       │                 │
│               └───────────────────────┼───────────────────────┘                 │
│                                   │                                             │
│                                   ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                          Workload 抽象層                                 │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │    │
│  │  │  Workload   │  │  Workload   │  │  Workload   │  │  Workload   │     │    │
│  │  │   (Job-1)   │  │   (Job-2)   │  │   (Job-3)   │  │   (Job-N)   │     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                   │                                             │
│                                   ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        ClusterQueue 排程層                               │    │
│  │                                                                         │    │
│  │      ┌─────────────────┐              ┌─────────────────┐               │    │
│  │      │  ClusterQueue   │              │  ClusterQueue   │               │    │
│  │      │   (gpu-queue)   │◄────────────►│  (cpu-queue)    │               │    │
│  │      │                 │   Cohort     │                 │               │    │
│  │      │ • 資源配額       │   資源共享     │ • 資源配額       │               │    │
│  │      │ • 排程策略       │               │ • 排程策略       │               │    │
│  │      │ • 搶佔機制       │               │ • 搶佔機制       │               │    │
│  │      └─────────────────┘              └─────────────────┘               │    │
│  │               │                                │                        │    │
│  │               ▼                                ▼                        │    │
│  │      ┌─────────────────┐              ┌─────────────────┐               │    │
│  │      │ ResourceFlavor  │              │ ResourceFlavor  │               │    │
│  │      │   (gpu-v100)    │              │   (cpu-intel)   │               │    │
│  │      │                 │              │                 │               │    │
│  │      │ • 節點標籤       │              │ • 節點標籤        │               │    │
│  │      │ • 汙點容忍       │              │ • 汙點容忍        │               │    │
│  │      │ • 資源特徵       │              │ • 資源特徵        │               │    │
│  │      └─────────────────┘              └─────────────────┘               │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                   │                                             │
│                                   ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        Kubernetes 排程層                                 │    │
│  │                                                                         │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │    │
│  │  │    Node     │  │    Node     │  │    Node     │  │    Node     │     │    │
│  │  │  (GPU節點)   │  │  (GPU節點)  │  │  (CPU節點)   │  │  (CPU節點)   │     │    │
│  │  │             │  │             │  │             │  │             │     │    │
│  │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │     │    │
│  │  │ │   Pod   │ │  │ │   Pod   │ │  │ │   Pod   │ │  │ │   Pod   │ │     │    │
│  │  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

關係說明：

- `LocalQueue`：名稱空間級別的作業提交入口，實現多租戶隔離
- `Workload`：作業的抽象表示，包含資源需求和排程資訊
- `ClusterQueue`：叢集級別的資源配額和排程策略管理
- `ResourceFlavor`：定義具有特定特徵的資源類型（如GPU型號、CPU架構），用於匹配節點資源
- `Cohort`：多個`ClusterQueue`組成的資源共享組，支援動態資源借用
- 排程流程：`Job` → `LocalQueue` → `Workload` → `ClusterQueue` → `ResourceFlavor` → `Node`

### 2.1 核心資源物件

#### 2.1.1 ClusterQueue（叢集佇列）

`ClusterQueue` 是 `Kueue` 的核心資源物件，定義了叢集級別的資源配額和排程策略。它是整個佇列系統的基礎，負責管理和分配叢集中的計算資源。主要特性包括：

- **資源組管理**：透過 `ResourceGroups` 定義不同類型資源的配額，如 CPU、記憶體、GPU 等，支援細粒度的資源控制
- **佇列策略**：支持 `StrictFIFO`（嚴格先進先出）和 `BestEffortFIFO`（盡力而為先進先出）兩種排隊策略，滿足不同場景的排程需求
- **名稱空間選擇器**：透過標籤選擇器控制哪些名稱空間可以向該佇列提交工作負載，實現多租戶隔離
- **搶佔策略**：支援多種搶佔機制以最佳化資源利用率，包括同佇列內搶佔和跨佇列搶佔
- **資源借用**：允許佇列在資源空閒時借用其他佇列的配額，提高整體資源利用率
- **公平共享**：透過 Cohort 機制實現多個佇列之間的公平資源共享

#### 2.1.2 LocalQueue（本地佇列）

`LocalQueue` 是名稱空間級別的佇列，作為使用者提交作業的入口點，與特定的 `ClusterQueue` 關聯。它在 `Kueue` 架構中起到了關鍵的橋樑作用：

**主要作用：**

- **作業提交入口**：使用者透過在 `Job`、`CronJob` 等工作負載中指定 `kueue.x-k8s.io/queue-name` 標籤來將作業提交到 `LocalQueue`
- **名稱空間隔離**：每個 `LocalQueue` 只能在特定名稱空間中建立和使用，實現了天然的多租戶隔離
- **佇列對映**：將名稱空間級別的作業請求對映到叢集級別的 `ClusterQueue`，實現資源的統一管理
- **許可權控制**：透過 `RBAC` 機制，可以精確控制不同使用者或團隊對特定 `LocalQueue` 的訪問許可權

**工作流程：**

1. 使用者在特定名稱空間中建立 `LocalQueue`，並關聯到相應的 `ClusterQueue`
2. 使用者提交作業時指定 `LocalQueue` 名稱
3. `Kueue` 控制器將作業轉換為 `Workload` 物件，並根據 `LocalQueue` 的配置進行排程
4. 作業在 `ClusterQueue` 中排隊等待資源分配

#### 2.1.3 Workload（工作負載）

`Workload` 是 `Kueue` 中作業的抽象表示，是系統內部用於排程管理的核心物件。它包含了作業的完整排程資訊：

**主要組成：**

- **資源需求**：詳細描述作業所需的 `CPU`、`記憶體`、`GPU` 等資源規格
- **優先順序資訊**：基於 `Kubernetes PriorityClass` 的優先順序設定
- **排程約束**：包括節點選擇器、親和性、反親和性、容忍度等排程限制
- **佇列資訊**：關聯的 `LocalQueue` 和 `ClusterQueue` 信息
- **狀態管理**：跟蹤作業的排程狀態，如 `Pending`、`Admitted`、`Running`、`Finished` 等

**生命周期：**

1. **建立階段**：當使用者提交 `Job`、`CronJob` 等工作負載時，`Kueue` 自動建立對應的 `Workload` 物件
2. **排隊階段**：`Workload` 在 `ClusterQueue` 中排隊等待資源分配
3. **准入階段**：當資源可用時，`Workload` 被標記為 `Admitted`，原始作業開始執行
4. **完成階段**：作業執行完成後，`Workload` 狀態更新為 `Finished`，釋放佔用的資源

**狀態轉換詳細說明：**

`Workload` 在其生命週期中會經歷多個狀態，每個狀態轉換都有特定的觸發條件和對應的 `WorkloadCondition`：

- **Pending（等待）**：`Workload` 建立後的初始狀態，等待 `ClusterQueue` 中的資源配額。此時 `Workload` 在佇列中排隊，等待資源預留成功。

- **QuotaReserved（配額預留）**：當 `ClusterQueue` 有足夠資源時，系統為 `Workload` 預留資源配額，對應 `WorkloadQuotaReserved` 條件為 `True`。此階段 `Workload` 等待透過所有準入檢查。

- **Admitted（已准入）**：`Workload` 透過所有 `AdmissionCheck` 後進入此狀態，對應 `WorkloadAdmitted` 條件為 `True`。此時 `Kubernetes` 開始排程和啟動相關的 `Pod`。

- **Running（執行中）**：當所有 `Pod` 成功啟動並準備就緒時，`WorkloadPodsReady` 條件變為 `True`，`Workload` 進入執行狀態。

- **Finished（已完成）**：作業執行完成（成功或失敗）后，`WorkloadFinished` 條件被設定，原因可能是 `Succeeded`、`Failed` 或 `OutOfSync`。

- **Evicted（被驅逐）**：`Workload` 可能因多種原因被驅逐，包括：
  - 資源不足或佇列停止（`ClusterQueueStopped`、`LocalQueueStopped`）
  - 准入檢查失敗（`AdmissionCheckFailed`）
  - 執行超時（`PodsReadyTimeout`、`MaximumExecutionTimeExceeded`）
  - 節點故障（`NodeFailures`）
  對應 `WorkloadEvicted` 條件會被設定為 `True`，幷包含具體的驅逐原因。

- **Preempted（被搶佔）**：當高優先順序 `Workload` 需要資源時，低優先順序的 `Workload` 可能被搶佔。搶佔可能發生在佇列內部（`InClusterQueueReason`）或 `Cohort` 級別的資源回收中。

- **Requeued（重新排隊）**：被搶佔或驅逐的 `Workload` 可以重新進入佇列等待排程，對應 `WorkloadRequeued` 條件。系統會根據退避策略和重試限制決定是否允許重新排隊。

**狀態轉換觸發條件：**

- **資源可用性**：`ClusterQueue` 中的資源配額狀況直接影響 `Pending` 到 `QuotaReserved` 的轉換
- **准入檢查**：所有配置的 `AdmissionCheck` 必須透過才能從 `QuotaReserved` 轉換到 `Admitted`
- **Pod 排程**：`Kubernetes` 排程器的成功排程觸發從 `Admitted` 到 `Running` 的轉換
- **優先順序搶佔**：高優先順序 `Workload` 的資源需求可能觸發低優先順序 `Workload` 的搶佔
- **超時機制**：`maximumExecutionTimeSeconds` 等超時設定可能導致 `Workload` 被驅逐
- **外部事件**：節點故障、佇列停止等外部事件可能導致狀態轉換

這種狀態機制確保了 `Workload` 在複雜的叢集環境中能夠正確處理各種排程場景和異常情況，同時為使用者提供了清晰的作業狀態可見性。

#### 2.1.4 ResourceFlavor（資源風味）

`ResourceFlavor` 定義了具有特定特徵的資源類型，是 `Kueue` 實現異構資源管理的關鍵機制。它允許叢集管理員對不同類型的計算資源進行精細化管理：

**核心功能：**

- **節點標籤匹配**：透過 `nodeLabels` 欄位指定資源所在節點的標籤，如 `GPU` 型號、`CPU` 架構等
- **汙點容忍**：透過 `tolerations` 欄位定義對特定節點汙點的容忍度，確保作業能夠排程到專用節點
- **資源替代性**：在 `ClusterQueue` 中可以定義多個 `ResourceFlavor`，實現資源的可替代性和靈活排程

**典型應用場景：**

- **GPU 類型管理**：為不同型號的 `GPU`（如 `V100`、`A100`、`T4`）建立不同的 `ResourceFlavor`
- **節點分組**：為不同可用區、不同硬體配置的節點建立專門的 `ResourceFlavor`
- **專用資源池**：為特定團隊或專案建立專用的資源池，透過汙點和容忍度實現隔離

### 2.2 高階特性

#### 2.2.1 Cohort（佇列組）

`Cohort` 是 `Kueue` 中實現資源池化和動態共享的重要機制，允許多個 `ClusterQueue` 組成一個資源共享組：

**核心價值：**

- **資源池化**：將多個佇列的資源配額匯聚成一個更大的資源池，提高整體資源利用率
- **動態借用**：當某個佇列資源不足時，可以從同一 `Cohort` 內其他空閒佇列借用資源
- **彈性擴展**：支援佇列根據實際需求動態調整資源使用量，避免資源浪費

**工作機制：**

1. **資源聚合**：`Cohort` 內所有佇列的資源配額被聚合為一個總的資源池
2. **優先順序保障**：每個佇列仍保持其基礎資源配額的優先使用權
3. **借用機制**：當佇列需要超出其配額的資源時，可以從 `Cohort` 的共享池中借用
4. **歸還機制**：當資源所有者佇列需要資源時，借用的資源會被自動歸還

#### 2.2.2 Fair Sharing（公平共享）

在 `Cohort` 內部，`Kueue` 實現了基於權重的公平共享機制，確保各佇列在資源競爭時獲得合理的資源分配：

**公平性算法（定性描述）：**

- **權重分配**：每個 `ClusterQueue`/`Cohort` 可以設定權重值，權重越高在資源競爭中越佔優
- **加權份額（weighted share）判據**：`Kueue` 為每個佇列計算基於名義配額（nominal quota）、借用量與實際用量的 dominant resource share；准入時偏好份額低的佇列，搶佔時優先挑選份額高的佇列作為候選
- **借用與歸還**：佇列在借用狀態下的准入會推高自身份額，歸還（搶佔別人）則降低份額；官方文件證明了搶佔不會形成迴圈（若 A 能搶佔 B，則 B 之後無法反過來搶佔 A）

Kueue 官方沒有給出「佇列資源份額 = 權重比例 × 總資源」這類線性公式，份額由 dominant resource share 在多資源維度上計算得出，這裡不做過度簡化。

**應用場景：**

- **多團隊環境**：不同團隊根據重要性或規模獲得不同的資源權重
- **業務優先順序**：生產環境佇列獲得更高權重，開發測試佇列權重較低
- **時間段調整**：根據業務高峰期動態調整不同佇列的權重

#### 2.2.3 Preemption（搶佔）

`Kueue` 的搶佔機制是一個多層次、智慧化的資源回收系統，支援多種搶佔策略以提高資源利用率：

**搶佔類型：**

- **同佇列內搶佔**：高優先順序作業可以搶佔同一佇列內低優先順序作業的資源
- **跨佇列搶佔**：高優先順序佇列可以搶佔低優先順序佇列的借用資源
- **Cohort 內搶佔**：在 `Cohort` 內部，資源所有者可以搶佔借用者的資源

**搶佔策略：**

- **LowerPriority**：只搶佔優先順序更低的工作負載
- **LowerOrNewerEqualPriority**：搶佔優先順序更低或同等優先順序但更新的工作負載
- **Any**：可以搶佔任何工作負載（需謹慎使用）

**搶佔流程：**

1. **資源需求評估**：系統評估新作業的資源需求
2. **候選者識別**：根據搶佔策略識別可被搶佔的工作負載
3. **影響最小化**：選擇搶佔影響最小的工作負載組合
4. **優雅終止**：被搶佔的作業會收到終止訊號，有機會進行清理工作
5. **重新排隊**：被搶佔的作業自動重新進入佇列等待排程

**搶佔保護與策略配置（ClusterQueue 的 `preemption` 字段）：**

- **同佇列內搶佔**：`withinClusterQueue`，取值 `Never`（預設）/`LowerPriority`/`LowerOrNewerEqualPriority`，控制是否可搶佔本佇列內低優先順序（或新提交的同優先順序）工作負載
- **跨佇列回收配額**：`reclaimWithinCohort`，取值 `Never`/`LowerPriority`/`LowerOrNewerEqualPriority`/`Any`，控制佇列是否可從同 Cohort 內借用了自己配額的佇列手中回收資源
- **借用時搶佔**：`borrowWithinCohort.maxPriorityThreshold`，限制借用狀態下可被搶佔者的優先順序上限
- **候選排序**：候選被搶佔者按「借用佇列優先、優先順序最低優先、最近准入優先」排序，天然抑制了頻繁搶佔剛啟動作業的行為

Kueue 沒有「搶佔冷卻期」「最小執行時間」這類配置項；搶佔行為完全由上述策略欄位和候選排序規則決定。

### 2.3 詳細排程流程

`Kueue` 的排程流程是一個多階段、多層次的複雜過程，涉及作業提交、資源評估、佇列管理、准入控制等多個環節。以下詳細描述了從作業提交到最終排程到節點的完整流程：

#### 2.3.1 作業提交階段

**1. 使用者作業提交**：

使用者透過標準的 `Kubernetes API` 提交作業（`Job`、`CronJob`、`TFJob` 等），並在作業規範中指定目標佇列：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: sample-job
  labels:
    kueue.x-k8s.io/queue-name: user-queue  # 指定目標 LocalQueue
spec:
  template:
    spec:
      containers:
      - name: main
        image: busybox
        resources:
          requests:
            cpu: "1"
            memory: "1Gi"
```

**2. Workload 物件建立**：

`Kueue` 控制器監聽到新的作業後，會自動建立對應的 `Workload` 物件，該物件包含：

- **資源需求規範**：從原始作業中提取的 `CPU`、`記憶體`、`GPU` 等資源需求
- **排程約束**：節點選擇器、親和性、反親和性、容忍度等
- **佇列關聯資訊**：關聯的 `LocalQueue` 和對應的 `ClusterQueue`
- **優先順序資訊**：基於 `PriorityClass` 的優先順序設定

#### 2.3.2 佇列路由階段

**1. LocalQueue 驗證**：

系統首先驗證指定的 `LocalQueue` 是否存在且使用者有許可權訪問：

- **名稱空間檢查**：確認 `LocalQueue` 在正確的名稱空間中
- **RBAC 驗證**：檢查使用者是否有向該佇列提交作業的許可權
- **佇列狀態檢查**：確認佇列處於活躍狀態

**2. ClusterQueue 映射**：

`LocalQueue` 將作業路由到關聯的 `ClusterQueue`：

```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: LocalQueue
metadata:
  name: user-queue
  namespace: team-a
spec:
  clusterQueue: gpu-cluster-queue  # 對映到叢集佇列
```

#### 2.3.3 資源評估與匹配階段

**1. 資源需求分析**：

`Kueue` 分析 `Workload` 的資源需求，並將其轉換為內部資源表示：

- **資源規範化**：將不同類型的資源需求統一為標準格式
- **資源聚合**：計算作業的總資源需求（考慮並行度）
- **特殊資源處理**：處理 `GPU`、`儲存` 等特殊資源類型

**2. ResourceFlavor 匹配**:

`ClusterQueue` 中定義的 `ResourceFlavor` 用於匹配合適的資源：

```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: gpu-cluster-queue
spec:
  resourceGroups:
  - coveredResources: ["nvidia.com/gpu", "cpu", "memory"]
    flavors:
    - name: gpu-v100
      resources:
      - name: "nvidia.com/gpu"
        nominalQuota: 8
      - name: "cpu"
        nominalQuota: 32
      - name: "memory"
        nominalQuota: 128Gi
```

**3. 節點相容性檢查**：

系統檢查 `ResourceFlavor` 定義的節點標籤和容忍度是否與叢集中的節點相容：

- **標籤匹配**：驗證叢集中是否存在具有所需標籤的節點
- **汙點容忍**：檢查作業是否能容忍目標節點的汙點
- **資源可用性**：確認節點上有足夠的物理資源

#### 2.3.4 佇列排程階段

**1. 佇列內排序**：

在 `ClusterQueue` 內部，`Workload` 按照配置的排隊策略進行排序：

- **StrictFIFO**：嚴格按照提交時間排序
- **BestEffortFIFO**：在 `FIFO` 基礎上考慮資源可用性
- **優先順序排序**：高優先順序作業優先排程

**2. Cohort 級別排程**：

如果 `ClusterQueue` 屬於某個 `Cohort`，還需要考慮 `Cohort` 級別的排程：

- **公平共享計算**：根據權重計算各佇列的資源份額
- **借用機制評估**：判斷是否可以從其他佇列借用資源
- **全域性優先順序**：在 `Cohort` 內部進行跨佇列的優先順序比較

#### 2.3.5 准入控制階段

`Kueue` 採用兩階段准入控制機制：

**1. 配額預留階段（Quota Reservation）**：

- **資源配額檢查**：驗證 `ClusterQueue` 是否有足夠的可用配額
- **配額預留**：為 `Workload` 預留所需的資源配額
- **借用評估**：如果本佇列配額不足，評估是否可以從 `Cohort` 借用

**2. 准入檢查階段（Admission Checks）**：

並行執行所有配置的 AdmissionChecks：

```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: gpu-cluster-queue
spec:
  admissionChecks:
  - "provisioning-check"  # 節點預配置檢查
  - "security-scan"       # 安全掃描檢查
```

每個 `AdmissionCheck` 必須返回 `Ready` 狀態，`Workload` 才能被最終准入。

#### 2.3.6 作業准入與排程階段

**1. Workload 准入**：

當所有準入條件滿足後，`Workload` 狀態變更為 `Admitted`：

- **資源分配確認**：最終確認分配給作業的具體資源
- **節點選擇器注入**：根據 `ResourceFlavor` 修改作業的節點選擇器
- **排程約束更新**：更新作業的排程約束以匹配分配的資源

**2. 原始作業恢復**：

`Kueue` 恢復原始作業的排程，使其能夠被 `Kubernetes` 排程器處理：

```yaml
# Kueue 會修改原始 Job 的 nodeSelector
apiVersion: batch/v1
kind: Job
metadata:
  name: sample-job
spec:
  template:
    spec:
      nodeSelector:
        node.kubernetes.io/instance-type: "gpu-v100"  # 由 ResourceFlavor 注入
      tolerations:
      - key: "nvidia.com/gpu"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
```

**3. Kubernetes 排程器接管**：

原始作業現在可以被標準的 `Kubernetes` 排程器排程到具體節點：

- **節點篩選**：根據更新後的節點選擇器篩選候選節點
- **資源檢查**：驗證節點上的實際資源可用性
- **最終排程**：將 `Pod` 繫結到具體的節點

#### 2.3.7 執行監控階段

**1. 作業狀態跟蹤**：

`Kueue` 持續監控作業的執行狀態：

- **Pod 狀態監控**：跟蹤作業中各個 `Pod` 的執行狀態
- **資源使用監控**：監控實際的資源使用情況
- **異常處理**：處理作業失敗、節點故障等異常情況

**2. 動態資源管理**:

- **部分准入**：支援以降低的並行度執行作業
- **動態回收**：`Pod` 完成後立即釋放對應的配額
- **彈性調整**：根據實際需求動態調整資源分配

#### 2.3.8 完成與清理階段

**1. 作業完成處理**:

當作業執行完成後：

- **狀態更新**：`Workload` 狀態更新為 `Finished`
- **配額釋放**：釋放作業佔用的所有資源配額
- **統計更新**：更新佇列和 `Cohort` 的使用統計

**2. 資源回收**:

- **配額歸還**：將借用的資源歸還給原始佇列
- **等待佇列激活**：觸發等待佇列中下一個作業的排程
- **清理操作**：清理相關的臨時資源和狀態資訊

#### 2.3.9 排程流程總結

完整的排程流程可以概括為以下關鍵路徑：

```text
使用者提交作業 → Workload建立 → LocalQueue路由 → ClusterQueue排隊 
     ↓
資源需求分析 → ResourceFlavor匹配 → 節點相容性檢查
     ↓
佇列內排序 → Cohort排程 → 配額預留 → 准入檢查
     ↓
Workload准入 → 作業恢復 → Kubernetes排程 → 節點執行
     ↓
狀態監控 → 動態管理 → 作業完成 → 資源清理
```

這個流程確保了：

- **資源的高效利用**：透過智慧的資源匹配和借用機制
- **公平的資源分配**：透過佇列權重和公平共享演算法
- **靈活的排程策略**：支援多種排隊和搶佔策略
- **強大的擴展性**：透過 `AdmissionChecks` 支援自定義准入邏輯

### 2.4 資源配額同步機制

`Kueue` 的資源配額管理採用了一種獨特的設計理念，它並不直接監控叢集中所有 `Pod` 的實際資源使用情況，而是透過標籤識別和手動配置相結合的方式來管理資源配額。這種設計在提供靈活性的同時，也對管理員提出了更高的要求。

#### 2.4.1 Kueue 管理的工作負載識別

Kueue 透過特定的標籤來識別和管理工作負載：

**管理標籤機制：**

- **標籤標識**：`Kueue` 為其管理的所有 `Pod` 添加 `kueue.x-k8s.io/managed=true` 標籤
- **資源跟蹤**：只有帶有此標籤的 `Pod` 才會被 Kueue 納入資源使用統計
- **隔離管理**：沒有此標籤的 `Pod`（如系統元件、其他排程器管理的工作負載）不會被 `Kueue` 直接感知

```yaml
# Kueue 管理的 Pod 示例
apiVersion: v1
kind: Pod
metadata:
  name: kueue-managed-pod
  labels:
    kueue.x-k8s.io/managed: "true"  # Kueue 管理標識
    kueue.x-k8s.io/queue-name: "user-queue"
spec:
  containers:
  - name: worker
    image: busybox
    resources:
      requests:
        cpu: "1"
        memory: "1Gi"
```

#### 2.4.2 nominalQuota 的設計理念

`nominalQuota` 是 `Kueue` 資源管理的核心概念，它代表了佇列可以使用的"名義配額"：

**配額定義：**

根據 `Kueue` 官方文件，`nominalQuota` 的定義明確指出：

> **"The quantity of this resource that the ClusterQueue can admit, accounting for resources consumed by system components and pods not managed by kueue."**

這意味著 `nominalQuota` 應該是：

```text
nominalQuota = 叢集總資源 - 系統元件資源 - 非Kueue管理的工作負載資源
```

**配置示例：**

```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: production-queue
spec:
  resourceGroups:
  - coveredResources: ["cpu", "memory", "nvidia.com/gpu"]
    flavors:
    - name: gpu-nodes
      resources:
      - name: "cpu"
        nominalQuota: 80    # 假設叢集有100核，預留20核給系統和其他工作負載
      - name: "memory"
        nominalQuota: 320Gi # 假設叢集有400Gi記憶體，預留80Gi
      - name: "nvidia.com/gpu"
        nominalQuota: 8     # 假設叢集有10個GPU，預留2個
```

#### 2.4.3 資源同步的侷限性

**非實時同步：**

`Kueue` 的設計存在以下重要特徵：

1. **靜態配額管理**：`nominalQuota` 需要管理員手動配置和維護
2. **有限感知能力**：`Kueue` 無法自動感知非其管理的工作負載的資源變化
3. **依賴管理員判斷**：需要管理員根據叢集實際情況合理設定配額

**其他排程器的影響：**

當叢集中存在其他排程器（如預設排程器直接排程的 `Pod`、`Volcano`、`Yunikorn` 等）時：

```yaml
# 非 Kueue 管理的 Pod（缺少 kueue.x-k8s.io/managed 標籤）
apiVersion: v1
kind: Pod
metadata:
  name: external-workload
  # 注意：沒有 kueue.x-k8s.io/managed 標籤
spec:
  containers:
  - name: worker
    image: nginx
    resources:
      requests:
        cpu: "2"      # 這2核CPU不會被Kueue感知
        memory: "4Gi"  # 這4Gi記憶體不會被Kueue感知
```

這些工作負載會消耗實際的叢集資源，但 `Kueue` 無法感知，可能導致：

- **資源超分配**：`Kueue` 可能分配超過實際可用的資源
- **排程衝突**：多個排程器可能競爭相同的資源
- **性能下降**：節點資源不足導致的效能問題

#### 2.4.4 最佳實踐建議

**統一排程管理：**

1. **集中管理**：儘可能將所有工作負載都透過 `Kueue` 進行管理
2. **標準化流程**：建立標準的作業提交流程，確保使用 `Kueue` 佇列
3. **許可權控制**：透過 `RBAC` 限制直接向叢集提交工作負載的許可權

**保守配額配置：**

```yaml
# 保守的配額配置示例
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: safe-queue
spec:
  resourceGroups:
  - coveredResources: ["cpu", "memory"]
    flavors:
    - name: standard-nodes
      resources:
      - name: "cpu"
        nominalQuota: 60    # 叢集100核，預留40核（40%緩衝）
      - name: "memory"
        nominalQuota: 240Gi # 叢集400Gi，預留160Gi（40%緩衝）
```

**監控和調整：**

1. **資源監控**：定期監控叢集實際資源使用情況
2. **配額調整**：根據監控資料定期調整 `nominalQuota`
3. **告警機制**：設定資源使用率告警，及時發現問題

```bash
# 監控叢集資源使用的示例命令
kubectl top nodes
kubectl describe nodes | grep -A 5 "Allocated resources"
```

**多排程器環境管理：**

如果必須在多排程器環境中執行：

1. **資源分割槽**：為不同排程器分配專用的節點池
2. **動態調整**：根據實際使用情況動態調整各排程器的資源配額
3. **監控整合**：整合監控系統，實時跟蹤各排程器的資源使用

#### 2.4.5 技術實現細節

**資源使用計算：**

`Kueue` 使用幾何平均數來計算資源使用情況，這些資訊儲存在 `FairSharingStatus` 中：

```yaml
# ClusterQueue 狀態示例
status:
  fairSharing:
    weightedShare: 0.5
  usage:
    cpu: "10"      # 當前使用的CPU核數
    memory: "40Gi"  # 當前使用的記憶體
  pendingWorkloads: 5  # 等待中的工作負載數量
```

**准入懲罰機制：**

`Kueue` 在准入工作負載時會向 `FairSharingStatus` 新增條目懲罰，防止系統被惡意利用：

- **預防性計費**：在實際資源分配前就計入使用量
- **公平性保障**：確保資源分配的公平性
- **防止競爭**：避免多個工作負載同時競爭相同資源

這種設計確保了 `Kueue` 作為配額管理和排程決策系統的有效性，但也要求管理員具備足夠的叢集管理經驗來合理配置和維護資源配額。

---

## 3. 主要功能特性

`Kueue` 提供了一套完整的批處理作業管理功能，以下是其核心能力矩陣和適用場景：

### 3.1 智慧作業排程

**核心能力：**

- **優先順序佇列**：基於 `WorkloadPriorityClass` 的多級優先順序排程
- **公平排程演算法**：支援嚴格 `FIFO` 和最佳努力 `FIFO` 策略
- **搶佔機制**：`LowerPriority`、`LowerOrNewerEqualPriority` 等多種搶佔策略

**適用場景：**

- 多團隊共享叢集環境，需要優先順序保障
- 緊急任務需要搶佔低優先順序作業資源
- 大規模批處理作業的有序執行

### 3.2 靈活資源管理

**核心能力：**

- **異構資源支援**：透過 `ResourceFlavor` 管理不同類型的 `GPU`、`CPU` 架構
- **資源借用機制**：`Cohort` 實現佇列間動態資源共享
- **配額管理**：`nominalQuota` 和 `borrowingLimit` 的精細化控制

**適用場景：**

- 混合 `GPU` 型號的 `AI` 訓練叢集
- 需要資源彈性共享的多租戶環境
- 成本敏感的資源利用率最佳化

### 3.3 廣泛的工作負載整合

**原生支援的工作負載類型：**

| 類別 | 支援的工作負載 | 典型使用場景 |
|------|---------------|-------------|
| **Kubernetes 原生** | `Job`、`CronJob` | 批處理任務、定時任務 |
| **機器學習訓練** | `TFJob`、`PyTorchJob`、`XGBoostJob`、`PaddleJob`、`JAXJob` | 分散式深度學習訓練 |
| **高效能運算** | `MPIJob`（v2beta1） | 科學計算、模擬任務 |
| **分散式計算** | `RayJob`、`RayCluster` | 大資料處理、強化學習 |
| **作業編排** | `JobSet` | 複雜的多階段作業流水線 |
| **服務工作負載** | `Deployment`、`StatefulSet`、`LeaderWorkerSet` | 長期執行的服務 |
| **自定義工作負載** | `AppWrapper`、普通 `Pod` | 特殊業務需求的包裝 |

**整合優勢：**

- 無需修改現有作業定義，僅需新增佇列標籤
- 統一的資源配額和排程策略
- 與 `Kubernetes` 生態無縫整合

### 3.4 高階排程特性

**差異化功能：**

#### 3.4.1 部分准入（Partial Admission）

- **功能**：當資源不足時，允許作業以降低的並行度執行
- **場景**：大規模訓練任務的資源彈性調整

#### 3.4.2 動態資源回收

- **功能**：`Pod` 完成後立即釋放配額，供其他作業使用
- **場景**：提高資源利用率，減少資源浪費

#### 3.4.3 全有或全無排程

- **功能**：基於超時機制的 `Gang Scheduling`
- **場景**：分散式訓練任務的協調啟動

#### 3.4.4 拓撲感知排程

- **功能**：最佳化跨節點、跨機架的 `Pod` 通信
- **場景**：高頻寬要求的 `HPC` 和 `AI` 工作負載

### 3.5 企業級運維特性

#### 3.5.1 准入檢查（AdmissionChecks）

**功能：**

- 自定義准入邏輯和外部系統整合
- 與 `cluster-autoscaler` 的 `provisioningRequest` 集成
- 支援資源預配置和動態擴容

**使用場景：**

- 成本控制和預算管理
- 合規性檢查和安全策略
- 與企業 `ITSM` 系統整合

#### 3.5.2 監控與可觀測性

**功能：**

- 豐富的 `Prometheus` 指標體系
- `KueueViz` 視覺化管理介面
- 實時佇列狀態和作業監控

**監控維度：**

- 佇列長度、等待時間、資源利用率
- 作業成功率、失敗原因分析
- 多租戶資源分配和使用統計

### 3.6 多叢集資源編排

**MultiKueue 功能：**

- **跨叢集作業分發**：智慧選擇最優執行叢集
- **全域性資源檢視**：統一管理多個 `Kubernetes` 叢集
- **故障轉移**：叢集故障時自動遷移作業

**適用場景：**

- 混合雲和多雲環境的資源統一排程
- 地理分散式的計算資源管理
- 成本最佳化的跨區域作業排程

### 3.7 核心競爭優勢總結

| 特性 | `Kueue` 優勢 | 競爭對手對比 |
|------|-----------|-------------|
| **Kubernetes 原生** | 無需替換排程器，漸進式採用 | `Volcano`、`YuniKorn` 需要替換預設排程器 |
| **簡單易用** | 最小化配置，學習曲線平緩 | `Slurm` 配置複雜，運維成本高 |
| **生態整合** | 與 `K8s` 生態深度整合 | 傳統 `HPC` 排程器生態割裂 |
| **多租戶支援** | 原生多租戶設計 | 部分方案多租戶能力有限 |
| **資源效率** | 動態借用和回收機制 | 靜態資源分配效率較低 |

---

## 4. 安裝與使用

### 4.1 系統要求

**基礎環境要求：**

- **Kubernetes 版本**：1.29 或更新版本
- **節點資源**：至少 2 個工作節點，每節點 2 核 4GB 記憶體
- **網路要求**：叢集網路正常，支持 Pod 間通訊
- **許可權要求**：叢集管理員許可權，能夠建立 CRD 和 RBAC 資源

**可選元件：**

- **Prometheus**：用於監控和指標收集
- **Grafana**：用於視覺化監控面板
- **Cert-manager**：用於自動證書管理（如需 HTTPS）

### 4.2 快速安裝

**安裝最新穩定版本：**

```bash
# 安裝 Kueue v0.13.2（本文示例基於 v0.13.x 編寫；截至 2026-11-05 核對日，官方最新 release 已到 v0.20.x，
# 生產環境請到 releases 頁面取最新版並核對 CRD 兼容性）
kubectl apply --server-side -f https://github.com/kubernetes-sigs/kueue/releases/download/v0.13.2/manifests.yaml
```

**驗證安裝：**

```bash
# 檢查 Kueue 控制器狀態
kubectl get pods -n kueue-system

# 驗證 CRD 安裝
kubectl get crd | grep kueue

# 檢查控制器日誌
kubectl logs -n kueue-system deployment/kueue-controller-manager
```

控制器將在 `kueue-system` 名稱空間中執行，包含以下元件：

- **kueue-controller-manager**：核心控制器，負責佇列管理和作業排程
- **kueue-webhook**：准入控制器，負責資源驗證和預設值設定

### 4.3 基本使用示例

#### 4.3.1 建立基本佇列設定

**步驟說明：**

1. **ResourceFlavor**：定義資源類型和節點選擇策略
2. **ClusterQueue**：建立叢集級資源佇列，設定配額限制
3. **LocalQueue**：在名稱空間中建立本地佇列，連線到叢集佇列

**配置文件：**

```yaml
# ResourceFlavor：定義預設資源類型
apiVersion: kueue.x-k8s.io/v1beta1
kind: ResourceFlavor
metadata:
  name: default-flavor
spec:
  # 可選：指定節點標籤選擇器
  nodeLabels:
    node-type: "worker"
---
# ClusterQueue：定義叢集級佇列
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: cluster-queue
spec:
  # 名稱空間選擇器：匹配所有名稱空間
  namespaceSelector: {}
  # 資源組配置
  resourceGroups:
  - coveredResources: ["cpu", "memory"]
    flavors:
    - name: default-flavor
      resources:
      - name: "cpu"
        nominalQuota: 9        # 9 核 CPU 配額
      - name: "memory"
        nominalQuota: 36Gi     # 36GB 記憶體配額
  # 佇列策略：先進先出
  queueingStrategy: BestEffortFIFO
---
# LocalQueue：定義本地佇列
apiVersion: kueue.x-k8s.io/v1beta1
kind: LocalQueue
metadata:
  namespace: default
  name: user-queue
spec:
  # 連線到叢集佇列
  clusterQueue: cluster-queue
```

#### 4.3.2 提交作業示例

**作業配置說明：**

- **suspend: true**：作業初始為暫停狀態，由 Kueue 控制啟動時機
- **queue-name 標籤**：指定作業使用的佇列，必須與 LocalQueue 名稱匹配
- **資源請求**：定義作業所需的 CPU 和記憶體資源

**示例配置：**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  generateName: sample-job-
  namespace: default
  labels:
    # 關鍵配置：指定 Kueue 佇列名稱
    kueue.x-k8s.io/queue-name: user-queue
    # 可選：新增應用標籤便於管理
    app: sample-workload
spec:
  # 並行度：同時執行的 Pod 數量
  parallelism: 3
  # 完成數：需要成功完成的 Pod 數量
  completions: 3
  # 重要：作業初始為暫停狀態，由 Kueue 管理
  suspend: true
  template:
    metadata:
      labels:
        app: sample-workload
    spec:
      # 重啟策略：失敗時不重啟 Pod
      restartPolicy: Never
      containers:
      - name: dummy-job
        image: registry.k8s.io/e2e-test-images/agnhost:2.53
        command: ["/bin/sh"]
        args: ["-c", "echo 'Job started'; sleep 60; echo 'Job completed'"]
        resources:
          requests:
            cpu: "1"           # 請求 1 核 CPU
            memory: "200Mi"    # 請求 200MB 記憶體
          limits:
            cpu: "2"           # 限制最大 2 核 CPU
            memory: "400Mi"    # 限制最大 400MB 記憶體
```

**提交和監控作業：**

```bash
# 提交作業
kubectl apply -f sample-job.yaml

# 檢視作業狀態
kubectl get jobs -w

# 檢視佇列狀態
kubectl get localqueue user-queue -o yaml

# 查看 Workload 物件
kubectl get workloads

# 檢視作業日誌
kubectl logs job/sample-job-xxxxx
```

---

## 5. 與業界其他批處理排程器的對比

在 Kubernetes 批處理排程領域，Kueue 面臨著來自多個成熟解決方案的競爭。本章將從技術架構、功能特性、易用性、生態整合等維度，對主要競爭對手進行客觀分析，幫助使用者根據實際需求做出合適的技術選型。

**對比維度說明：**

- **技術架構**：排程器設計、與 Kubernetes 的集成方式
- **功能特性**：支援的排程演算法、資源管理能力、高階特性
- **易用性**：學習曲線、配置複雜度、運維成本
- **生態整合**：與現有工具鏈的相容性、社群支援

### 5.1 Apache YuniKorn

**專案概述：**

Apache YuniKorn 是一個通用資源排程器，旨在為 Kubernetes 和 Apache Hadoop YARN 提供統一的排程語義。該專案由 Cloudera 主導開發，現已成為 Apache 頂級專案。

**技術架構：**

- **排程器替換**：完全替換 Kubernetes 預設排程器
- **雙環境支援**：同時支援 Kubernetes 和 YARN 叢集管理
- **分層佇列**：提供層次化的佇列管理和資源分配
- **外掛化設計**：支援自定義排程策略和資源管理外掛

**核心優勢：**

- **統一排程語義**：為混合雲環境提供一致的排程體驗
- **自動資源預留**：智慧預留資源，減少作業等待時間
- **強大的公平性保證**：支援多種公平性演算法，確保資源公平分配
- **成熟的多租戶支援**：完善的租戶隔離和配額管理

**主要限制：**

- **部署複雜度高**：需要替換預設排程器，對叢集侵入性強
- **學習曲線陡峭**：配置複雜，需要深入理解排程原理
- **生態整合度低**：與 Kubernetes 原生工具鏈相容性有限
- **運維成本高**：需要專門的運維團隊維護排程器

### 5.2 Volcano

**專案概述：**

Volcano 是華為開源的 Kubernetes 批處理排程器，專為高效能運算（HPC）和 AI/ML 工作負載設計。該專案是 CNCF 的孵化專案，在深度學習和科學計算領域有較好的應用實踐。

**技術架構：**

- **自定義排程器**：替換 Kubernetes 預設排程器，提供專門的批處理排程能力
- **Gang 排程**：支持多 Pod 同時排程，確保分散式作業的完整性
- **作業依賴管理**：支援複雜的作業依賴關係和工作流排程
- **多種排程演算法**：提供公平共享、優先順序、回填等多種排程策略

**核心優勢：**

- **先進的排程演算法**：針對 HPC 和 AI 工作負載最佳化，支援複雜排程需求
- **Gang 排程支援**：確保分散式訓練任務的所有 Pod 同時啟動
- **作業依賴管理**：支持 DAG 工作流，適合複雜的科學計算場景
- **AI/ML 社群認可**：在深度學習領域有較多成功案例

**主要限制：**

- **排程器替換**：需要替換預設排程器，對叢集侵入性強
- **配置複雜度高**：排程策略配置複雜，需要專業知識
- **通用性不足**：主要針對 HPC 和 AI 場景，通用批處理支援有限
- **運維成本高**：需要深入了解 HPC 排程原理進行運維

### 5.3 Slurm

**專案概述：**

Slurm（Simple Linux Utility for Resource Management）是傳統 HPC 領域最廣泛使用的叢集管理和作業排程系統。該專案由勞倫斯利弗莫爾國家實驗室開發，在全球超過一半的 Top 500 超級計算機中使用，擁有超過 20 年的发展历史。

**技術架構：**

- **獨立叢集管理**：提供完整的叢集資源管理解決方案
- **分散式架構**：支援大規模叢集的分散式管理
- **確定性排程**：提供精確的資源控制和排程保證
- **傳統 HPC 模型**：基於作業提交和佇列管理的經典模式

**核心優勢：**

- **成熟穩定**：在 HPC 領域有超過 20 年的發展歷史和豐富實踐
- **強大的批處理能力**：支援複雜的作業依賴、資源預留和回收機制
- **原生 MPI 集成**：與科學計算框架深度整合，適合傳統 HPC 應用
- **大規模支援**：能夠管理數萬節點的超大規模叢集

**主要限制：**

- **云原生不兼容**：與 Kubernetes 生態完全割裂，無法利用雲原生優勢
- **使用者體驗傳統**：缺乏現代化介面和 API，學習曲線陡峭
- **容器化支持弱**：主要面向傳統 HPC 應用，容器化支持有限
- **現代化程度低**：缺乏雲原生特性和現代運維工具支援

### 5.4 商業解決方案

**NVIDIA Run:ai：**

- **定位**：企業級 AI 工作負載和 GPU 編排平台，專注於 AI/ML 場景
- **優勢**：動態資源分配、AI 原生排程、混合云支持、企業級功能
- **限制**：商業許可成本高、主要針對 GPU 工作負載

**IBM Spectrum LSF：**

- **定位**：企業級工作負載管理平台，提供全面的作業排程和資源管理
- **優勢**：高階排程演算法、企業級支援、豐富的管理功能
- **限制**：成本高昂、與雲原生生態整合度低

**Altair PBS Professional：**

- **定位**：高效能運算工作負載管理器，專注於科學計算和研究場景
- **優勢**：複雜排程策略支援、在學術界廣泛應用、穩定可靠
- **限制**：商業許可成本、云原生支持不足

### 5.5 Kueue 的競爭優勢

基於以上對比分析，Kueue 在 Kubernetes 批處理排程領域具有以下核心競爭優勢：

**1. Kubernetes 原生設計**:

- **"作業優先，Pod 原生"設計理念**：透過 `spec.suspend` 欄位管理作業生命週期，讓預設排程器處理 Pod 排程
- **最小化侵入性**：無需替換現有排程器，對叢集架構影響最小
- **漸進式採用路徑**：支援逐步遷移，降低技術風險和運維成本
- **深度生態整合**：與 Kubernetes 原生 API 和工具鏈無縫協作

**2. 簡單易用的運維體驗**:

- **零排程器替換**：保持現有叢集架構不變，降低部署風險
- **標準 Kubernetes API**：使用熟悉的 kubectl 和 YAML 配置方式
- **平緩學習曲線**：基於 Kubernetes 基礎知識，無需額外的專業技能
- **低運維成本**：減少專門的排程器運維工作，降低人力成本

**3. 靈活的資源管理能力**:

- **多維度資源支援**：CPU、記憶體、GPU、自定義資源的統一管理
- **層次化佇列設計**：支援複雜的組織架構和資源分配策略
- **智能公平共享**：基於權重的公平性演算法，確保資源合理分配
- **搶佔機制**：支援優先順序搶佔，提高資源利用效率

**4. 企業級生產就緒**:

- **官方專案保障**：由 Kubernetes SIG Scheduling 維護，品質和穩定性有保障
- **活躍社群支援**：Google、Red Hat、CERN 等知名機構的生產實踐
- **持續演進發展**：緊跟 Kubernetes 發展趨勢，功能持續完善
- **廣泛工具整合**：與 Argo Workflows、Kubeflow、Ray 等主流工具良好集成

### 5.6 技術選型建議

基於不同的業務需求和技術環境，以下是各種批處理排程解決方案的適用場景建議：

#### 5.6.1 選擇 Kueue 的場景

**核心適用場景：**

- **雲原生環境**：已有 Kubernetes 叢集，需要原生的批處理作業管理
- **漸進式遷移**：希望最小化對現有叢集架構的影響
- **運維簡化**：重視簡單性和易維護性，團隊 Kubernetes 經驗豐富
- **生態整合**：需要與 Kubernetes 生態工具深度整合
- **多租戶管理**：需要靈活的佇列管理和資源配額控制

**典型使用者畫像：**

- 雲原生技術團隊
- 中小型 AI/ML 團隊
- 需要批處理能力的微服務架構
- 重視技術債務控制的企業

#### 5.6.2 選擇競爭對手的場景

**Apache YuniKorn：**

- **混合環境管理**：需要統一管理 Kubernetes 和 YARN 環境
- **大資料場景**：Spark、Hadoop 等大資料工作負載為主
- **複雜排程需求**：需要高階排程演算法和資源最佳化

**Volcano：**

- **HPC 工作負載**：複雜的科學計算和高效能運算場景
- **Gang 排程需求**：分散式訓練任務需要同時啟動多個 Pod
- **作業依賴管理**：複雜的工作流和作業依賴關係

**Slurm：**

- **傳統 HPC 環境**：現有 Slurm 基礎設施，需要與科學計算工具整合
- **超大規模叢集**：數萬節點的超算中心
- **確定性排程**：對排程精確性有極高要求

**商業解決方案：**

- **企業級支援**：需要 7x24 技術支援和 SLA 保障
- **預算充足**：有足夠的軟體許可預算
- **合規要求**：需要商業軟體的合規性保障

### 5.7 典型應用場景

以下是 Kueue 在實際生產環境中的幾個典型應用場景：

#### 5.7.1 機器學習模型訓練平台

**場景描述：**

某 AI 公司需要為多個研發團隊提供統一的機器學習訓練平台，支持 `PyTorch`、`TensorFlow` 等多種框架的分散式訓練任務。

**傳統痛點：**

- GPU資源爭搶激烈，缺乏公平的分配機制
- 任務排隊無序，重要專案可能被阻塞
- 資源利用率低，GPU空閒時無法被其他團隊使用
- 缺乏多租戶隔離，資源配額難以管理
- 任務失敗後重啟困難，影響訓練效率

**Kueue 解決方案與好處：**

- **公平資源分配**：透過 ClusterQueue 為不同團隊設定GPU配額，確保資源公平分配
- **智慧排隊排程**：基於優先順序和公平性演算法，確保重要任務優先執行
- **資源借用機制**：空閒資源可被其他佇列借用，提高整體利用率
- **多租戶隔離**：LocalQueue 提供專案級別的資源管理和隔離
- **自動重試機制**：任務失敗後自動重新排隊，提高訓練成功率

**配置示例：**

```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: ml-training-queue
spec:
  cohort: ml-cohort
  preemption:
    withinClusterQueue: LowerPriority
  resourceGroups:
  - coveredResources: ["nvidia.com/gpu", "cpu", "memory"]
    flavors:
    - name: gpu-a100
      resources:
      - name: "nvidia.com/gpu"
        nominalQuota: 32
        borrowingLimit: 16  # 允許借用額外資源
      - name: "cpu"
        nominalQuota: 256
      - name: "memory"
        nominalQuota: 2048Gi
```

#### 5.7.2 科學計算批處理系統

**場景描述：**

某研究機構需要處理大量的科學計算任務，包括基因測序、氣候模擬、物理仿真等，這些任務具有不同的資源需求和優先順序。

**傳統痛點：**

- 計算任務資源需求差異巨大，難以統一排程
- 多節點並行任務啟動不同步，導致資源浪費
- 長時間執行任務佔用資源，影響其他任務執行
- 缺乏有效的資源共享機制，部門間資源孤島嚴重
- 任務監控困難，無法及時發現和處理異常

**Kueue 解決方案與好處：**

- **靈活資源管理**：Cohort 機制實現多個研究組間的動態資源共享
- **Gang Scheduling**：確保多節點並行任務同時啟動，避免部分節點等待
- **智慧搶佔策略**：低優先順序長任務可被高優先順序任務搶佔，提高響應速度
- **資源借用最佳化**：空閒計算資源自動分配給有需求的研究組
- **完整監控體系**：集成 Prometheus 監控，實時跟蹤任務狀態和資源使用

**關鍵特性：**

- 支援長時間執行的計算任務
- 自動處理節點故障和任務重啟
- 與 HPC 排程器（如 Slurm）的遷移相容性

#### 5.7.3 CI/CD 構建農場

**場景描述：**

大型軟體公司需要為數百個專案提供持續整合和部署服務，每天處理數千個構建任務，需要高效的資源排程和隔離。

**傳統痛點：**

- 構建任務排隊時間長，影響開發效率
- 資源分配不均，熱門專案搶佔大量資源
- 緊急修復無法快速構建，影響生產釋出
- 構建資源利用率低，夜間和週末資源閒置
- 缺乏構建任務的視覺化管理和監控

**Kueue 解決方案與好處：**

- **動態資源分配**：根據專案活躍度和提交頻率自動調整資源配額
- **優先順序管理**：生產修復和釋出任務獲得最高優先順序，確保快速執行
- **彈性擴縮容**：構建高峰期自動擴展資源，低峰期回收節約成本
- **多專案隔離**：不同專案和分支使用獨立佇列，避免相互影響
- **智慧排程**：基於歷史資料預測構建時間，最佳化任務排序

**技術實現：**

- 為不同專案組建立隔離的佇列
- 使用資源配額限制每個專案的資源使用
- 配置動態擴縮容，根據構建負載自動調整叢集規模
- 集成 Tekton 或 Argo Workflows 實現完整的 CI/CD 流水線

#### 5.7.4 多租戶資料處理平台

**場景描述：**

雲服務提供商需要為客戶提供資料處理服務，支持 Spark、Flink 等大資料框架，同時確保租戶間的資源隔離和公平性。

**傳統痛點：**

- 租戶間資源爭搶，服務品質難以保證
- 缺乏有效的資源隔離機制，存在安全風險
- 資源使用統計不準確，計費困難
- 無法根據租戶等級提供差異化服務
- 資源超售風險高，可能導致服務中斷

**Kueue 解決方案與好處：**

- **嚴格租戶隔離**：基於 Namespace 和 LocalQueue 實現完全的資源和許可權隔離
- **分級服務保障**：不同等級租戶享受不同的資源配額和優先順序
- **精確計費統計**：詳細記錄每個租戶的資源使用情況，支援精確計費
- **彈性資源管理**：支援資源超售和動態調整，提高平台收益
- **SLA 保障**：透過優先順序和搶佔機制確保高階租戶的服務品質

**技術實現：**

```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: tenant-a-queue
spec:
  namespaceSelector:
    matchLabels:
      tenant: "tenant-a"
  admissionChecks:
  - billing-check
  - quota-validation
  resourceGroups:
  - coveredResources: ["cpu", "memory"]
    flavors:
    - name: standard-nodes
      resources:
      - name: "cpu"
        nominalQuota: 100
        borrowingLimit: 50
```

#### 5.7.5 邊緣計算任務排程

**場景描述：**

物聯網公司需要在邊緣節點上執行資料處理和 AI 推理任務，這些節點資源有限且網路不穩定。

**傳統痛點：**

- 邊緣節點資源有限且異構，排程複雜度高
- 網路不穩定，任務執行可靠性差
- 資料傳輸成本高，缺乏本地性最佳化
- 節點故障頻繁，任務容錯能力不足
- 缺乏統一的邊緣資源管理和監控

**Kueue 解決方案與好處：**

- **異構資源統一管理**：支持 CPU、GPU、FPGA 等多種計算資源的統一排程
- **地理位置感知排程**：基於節點標籤實現就近排程，減少資料傳輸延遲
- **智慧容錯機制**：任務失敗自動遷移到其他可用節點，提高執行成功率
- **混合負載最佳化**：離線批處理和線上服務任務合理混部，提高資源利用率
- **邊緣叢集聯邦**：多個邊緣叢集統一管理，實現全域性資源最佳化

**特殊考慮：**

- 網路頻寬限制和延遲最佳化的排程策略
- 裝置功耗管理和節點可靠性評估
- 資料本地性最佳化，減少跨節點資料傳輸
- 離線模式支援和斷網續傳機制

---

## 6. Kueue + HAMi 集成方案

### 6.1 架構概述

在現代 `AI` 基礎設施中，`Kueue` 與 `HAMi`（`Heterogeneous AI Computing Virtualization Middleware`）的結合為企業提供了一套完整的 `AI` 工作負載管理解決方案。這種組合實現了從資源虛擬化到作業排程的全棧管理能力，為 `Kubernetes` 環境下的 `AI` 工作負載提供了強大的排程和資源管理能力。

#### 6.1.1 應用場景

`Kueue` 與 `HAMi` 的整合特別適用於以下 `AI` 工作負載場景：

**機器學習訓練場景：**

- 大規模深度學習模型訓練
- 分散式訓練任務的資源協調
- GPU 資源的高效利用和共享
- 多租戶環境下的資源隔離

**AI 推理服務場景：**

- 高併發推理任務的批處理
- GPU 算力的精細化分配
- 推理服務的彈性擴縮容
- 實時和離線推理的混合排程

**科研計算場景：**

- 科學計算和模擬任務
- 多使用者共享 GPU 叢集
- 長時間執行任務的資源管理
- 實驗任務的優先順序排程

#### 6.1.2 分層架構設計

**整體架構：**

```text
┌─────────────────────────────────────────────────────────┐
│                   AI 應用層                              │
│  (PyTorch, TensorFlow, Jupyter Notebook, MLflow)        │
├─────────────────────────────────────────────────────────┤
│                  Kueue 佇列管理層                         │
│  • 作業佇列管理    • 資源配額控制    • 公平排程              │
│  • 多租戶隔離      • 優先順序管理      • 搶佔策略              │
├─────────────────────────────────────────────────────────┤
│                  HAMi 排程與虛擬化層                      │
│  • GPU 智慧排程    • GPU 虛擬化      • 算力隔離            │
│  • 算力分片        • 裝置共享        • 資源監控             │
├─────────────────────────────────────────────────────────┤
│                Kubernetes 排程層                         │
│  • 節點選擇        • 親和性排程      • 資源約束             │
└─────────────────────────────────────────────────────────┘
```

#### 6.1.3 HAMi 元件架構

`HAMi` 作為異構 `AI` 計算虛擬化中介軟體，由以下核心專案組成：

**核心元件：**

- **HAMi 主專案**：包含 `Scheduler Extender`（智慧排程器）和 `Mutating Webhook`（准入控制器）
- **HAMi-WebUI**：提供 `GPU` 資源管理和可觀測性的 `Web` 界面
- **HAMi-core**：負責容器內 `GPU` 算力切分和資源隔離的核心庫
- **裝置外掛專案**：針對不同 `GPU` 廠商的 `Device Plugin` 實現，如 `ascend-device-plugin` 等

**元件職責：**

- **排程層**：`HAMi Scheduler Extender` 負責 `GPU` 資源的智慧分配和最佳化
- **准入層**：`HAMi` Webhook 負責 Pod 建立時的資源轉換和配置注入
- **執行時層**：`HAMi-core` 負責容器內的 `GPU` 資源隔離和監控
- **管理層**：`HAMi-WebUI` 提供視覺化的資源管理和監控介面

#### 6.1.4 協作架構模式

Kueue 與 HAMi 的結合專門針對 AI 批處理工作負載的管理與排程需求，形成了分層協作的架構模式：

**分層職責：**

- **Kueue 層**：負責作業佇列管理、資源配額控制和多租戶隔離
- **HAMi 層**：負責 GPU 資源虛擬化、智慧排程和裝置共享
- **協作機制**：透過資源抽象對映和排程策略協調，實現高效的 AI 批處理負載管理

**協作優勢：**

- **資源利用率提升**：HAMi 的 GPU 虛擬化技術提高硬體利用率
- **排程效率最佳化**：Kueue 的佇列管理確保任務有序執行
- **多租戶支援**：完善的資源隔離和配額管理機制
- **運維簡化**：統一的管理介面和監控體系

```text
┌─────────────────────────────────────────────────────────┐
│                    HAMi 架構圖                           │
├─────────────────┬───────────────────┬───────────────────┤
│  HAMi Webhook   │  HAMi Scheduler   │   HAMi-WebUI      │
│   (准入控制)     │   (智慧排程)       │ (GPU資源監控介面)    │
├─────────────────┼───────────────────┼───────────────────┤
│              HAMi Device Plugin   HAMi-core             │
│                (裝置管理)           (算力切分)             │
├─────────────────────────────────────────────────────────┤
│                GPU Driver & Runtime                     │
│              (NVIDIA, AMD, 昇騰等硬體驅動)                │
└─────────────────────────────────────────────────────────┘
```

### 6.2 核心工作機制

#### 6.2.1 資源抽象與對映

Kueue 與 HAMi 的整合透過資源抽象層實現了邏輯資源配額與物理 GPU 資源的對映關係。

**HAMi 物理資源定義：**

HAMi 在 Pod 規格中定義實際的 GPU 硬體資源需求：

```yaml
# HAMi 裝置資源（實際硬體層面）
resources:
  limits:
    nvidia.com/gpu: 2              # 請求 2 個 vGPU
    nvidia.com/gpumem: 6000         # 每個 vGPU 6GB 顯存
    nvidia.com/gpucores: 50         # GPU 算力占用 50%
```

**Kueue 邏輯配額定義：**

Kueue 在 ClusterQueue 中定義邏輯資源配額，實現資源的抽象管理：

```yaml
# Kueue 邏輯配額（在 ClusterQueue 中定義）
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: ai-training-queue
spec:
  resourceGroups:
  - coveredResources: ["nvidia.com/gpu", "nvidia.com/gpumem", "nvidia.com/gpucores"]
    flavors:
    - name: nvidia-gpu-flavor
      resources:
      - name: "nvidia.com/gpu"
        nominalQuota: 32     # GPU 卡數配額
      - name: "nvidia.com/gpumem"
        nominalQuota: 256000 # 顯存配額 (MB)
      - name: "nvidia.com/gpucores"
        nominalQuota: 1600   # GPU 算力配額 (%)
```

**資源對映關係：**

| HAMi 物理資源 | Kueue 邏輯配額 | 對映說明 |
|--------------|---------------|----------|
| nvidia.com/gpu | nvidia.com/gpu | 1:1 映射，GPU 卡數 |
| nvidia.com/gpumem | nvidia.com/gpumem | 1:1 映射，顯存大小 (MB) |
| nvidia.com/gpucores | nvidia.com/gpucores | 1:1 映射，算力百分比 |

#### 6.2.2 雙層排程流程詳解

Kueue 與 HAMi 的整合採用雙層排程架構，實現了從邏輯佇列管理到物理資源分配的完整排程鏈路。這種設計將佇列管理與裝置排程解耦，提供了更高的靈活性和擴展性。

##### 排程流程概述

**第一層：Kueue 佇列排程**:

- 負責作業佇列管理、資源配額控制和准入決策
- 實現多租戶資源隔離和公平排程策略
- 提供作業優先順序管理和搶佔機制

**第二層：HAMi 裝置排程**:

- 負責 GPU 等異構裝置的智慧分配和虛擬化
- 實現裝置級別的拓撲感知和負載均衡
- 提供細粒度的資源隔離和監控能力

##### 詳細排程階段

**階段一：作業提交與佇列管理**:

```text
使用者作業 → LocalQueue → Workload 物件 → 資源需求驗證
```

- 使用者透過 `kueue.x-k8s.io/queue-name` 標籤將作業提交到指定的 LocalQueue
- Kueue 控制器自動建立 Workload 物件，封裝作業的資源需求和排程資訊
- 系統驗證作業的資源請求格式和配額限制，確保請求的合理性

**階段二：配額准入與優先順序評估**:

```text
Workload → ClusterQueue → 配額檢查 → 優先順序排序 → 准入決策
```

- Kueue 根據 ClusterQueue 配置驗證可用資源配額，包括 GPU、記憶體、算力等維度
- 應用佇列優先順序、公平共享策略和借用機制，確定作業的排程優先順序
- 基於資源可用性和策略約束，做出准入決策（准入/排隊/拒絕）

**階段三：Kubernetes 排程與 HAMi 介入**:

```text
准入透過 → Pod 建立 → Kubernetes 排程器 → HAMi 擴展排程 → 節點選擇
```

- Kueue 准入透過後，釋放 Pod 到 Kubernetes 進行實際排程
- HAMi Scheduler Extender 作為排程器擴展介入，執行 GPU 專用的排程邏輯
- 考慮 GPU 拓撲結構、記憶體碎片化、裝置利用率等因素進行最優節點選擇
- HAMi Mutating Webhook 自動注入 GPU 配置和環境變數

**階段四：資源分配與執行時管理**:

```text
Pod 排程 → 裝置分配 → 資源隔離 → 執行時監控
```

- HAMi 裝置外掛完成具體的 GPU 裝置分配和虛擬化配置
- HAMi-core 在容器執行時實現顯存和算力的精確隔離
- HAMi-WebUI 提供實時的資源使用監控和管理介面
- Kueue 持續跟蹤作業狀態，支援動態搶佔和資源回收

#### 6.2.3 裝置外掛專案

裝置外掛專案是 HAMi 生態系統的基礎元件，負責異構計算裝置的發現、註冊和虛擬化管理。透過標準的 Kubernetes Device Plugin API，實現對不同廠商 GPU/NPU 裝置的統一管理。

##### 核心功能特性

**裝置發現與註冊**:

- 自動掃描節點上的異構計算裝置（NVIDIA GPU、華為昇騰 NPU、AMD GPU 等）
- 向 Kubelet 註冊裝置資源，使其在 Kubernetes 叢集中可見和可排程
- 支援熱插拔裝置的動態發現和註冊更新

**資源虛擬化管理**:

- 將物理裝置虛擬化為多個邏輯裝置，實現裝置共享
- 支援顯存、算力、頻寬等多維度資源的細粒度分割
- 提供靈活的虛擬化策略配置，適應不同應用場景需求

**裝置分配與隔離**:

- 響應 Pod 的裝置資源請求，執行裝置分配決策
- 生成裝置掛載配置和環境變數注入
- 確保不同容器間的裝置資源隔離和安全訪問

##### 多廠商裝置支援

**NVIDIA GPU 支持**:

```yaml
# NVIDIA GPU 資源配置示例
resources:
  nvidia.com/gpu: "1"           # GPU 裝置數量
  nvidia.com/gpumem: "8192"     # GPU 顯存 (MB)
  nvidia.com/gpucores: "50"     # GPU 算力百分比
```

**華為昇騰 NPU 支持**:

```yaml
# 昇騰 NPU 資源配置示例（HAMi charts 預設口徑，按晶片型號命名，核對日 2026-11-05）
resources:
  huawei.com/Ascend910B2: "1"            # 昇騰 NPU 數量
  huawei.com/Ascend910B2-memory: "4096"  # NPU 顯存 (MB)
  huawei.com/Ascend910B2-core: "30"      # NPU 算力百分比（hami-core/enpu 模式）
```

**AMD GPU 支持**:

```yaml
# AMD GPU 資源配置示例
resources:
  amd.com/gpu: "1"              # AMD GPU 裝置數量
  amd.com/gpumem: "16384"       # GPU 顯存 (MB)
```

#### 6.2.4 HAMi 排程器擴展

HAMi 排程器擴展是核心排程元件，透過擴展 Kubernetes 預設排程器，實現對異構計算資源的智慧感知和最佳化分配。主要提供拓撲感知排程、智能碎片整理、負載均衡最佳化等能力。與 Kueue 協作時，Kueue 負責作業佇列管理和資源配額控制，HAMi 負責 GPU 裝置的具體分配和最佳化。

#### 6.2.5 HAMi Mutating Webhook

HAMi Mutating Webhook 是 Kubernetes 准入控制器的重要組成部分，在 Pod 建立階段自動執行 GPU 資源配置的轉換和注入。主要功能包括資源請求轉換、環境變數注入（如 CUDA_VISIBLE_DEVICES）、容器配置修改等，確保使用者提交的 GPU 資源請求能夠正確轉換為 HAMi 執行時所需的配置格式。

```yaml
resources:
  limits:
    nvidia.com/gpu: "1"
    nvidia.com/gpumem: "8192"
    nvidia.com/gpucores: "50"
```

**Webhook 注入后的配置**：

```yaml
resources:
  limits:
    nvidia.com/gpu: "1"
env:
- name: CUDA_VISIBLE_DEVICES
  value: "0"
- name: CUDA_DEVICE_MEMORY_LIMIT
  value: "8192"
- name: CUDA_DEVICE_SM_LIMIT
  value: "50"
- name: LD_PRELOAD
  value: "/usr/local/hami/libvgpu.so"
volumeMounts:
- name: hami-lib
  mountPath: /usr/local/hami
- name: nvidia-dev
  mountPath: /dev/nvidia0
```

#### 6.2.6 HAMi-core - 算力切分與隔離

HAMi-core 是容器內 GPU 資源控制的核心庫，透過劫持 CUDA API 呼叫實現硬體資源的精確控制。主要功能包括顯存虛擬化、算力限制、實時監控等，確保不同容器間的 GPU 資源隔離和精確分配。

#### 6.2.7 HAMi-WebUI - 管理與監控介面

HAMi-WebUI 提供直觀的 Web 介面用於 GPU 資源的管理和監控，包括資源概覽、節點管理、GPU 管理、任務管理等功能，幫助使用者視覺化叢集資源使用情況和任務狀態。

### 6.3 配置實踐

本節將透過一個完整的AI訓練場景，展示如何配置Kueue與HAMi的整合環境。我們將構建一個支援多團隊、多GPU類型的AI訓練平台，實現資源的高效排程和管理。

#### 6.3.1 場景描述

**業務場景：**
某AI公司擁有一個混合GPU叢集，包含V100和A100兩種GPU類型，需要支援多個研發團隊進行模型訓練。要求實現：

- **資源隔離**：不同團隊擁有獨立的資源配額，互不干擾，確保資源的公平分配。
- **GPU共享**：支持GPU虛擬化，提高資源利用率，避免資源浪費。
- **優先順序排程**：生產任務優先，研發任務可被搶佔，確保生產環境的及時響應。
- **彈性擴展**：支援資源借用機制，當叢集資源不足時，允許臨時借用其他團隊的資源。

**叢集環境：**

- 節點配置：4台V100節點（每台8卡32GB），2台A100節點（每台8卡80GB）
- 團隊配置：ai-research團隊（研发）、ai-production團隊（生產）
- 資源需求：支援大模型訓練、推理服務、實驗任務

#### 6.3.2 HAMi 基礎配置

**HAMi 裝置外掛配置：**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: hami-device-plugin-config
data:
  config.yaml: |
    resourceName: "nvidia.com/gpu"
    resourceMemoryName: "nvidia.com/gpumem"
    resourceCoreName: "nvidia.com/gpucores"
    deviceSplitCount: 10
    migStrategy: "none"
```

**GPU 節點標籤配置：**

```yaml
apiVersion: v1
kind: Node
metadata:
  name: gpu-node-01
  labels:
    nvidia.com/gpu.product: "Tesla-V100-32GB"
    nvidia.com/gpu.count: "8"
    zone: "gpu-zone-a"
```

#### 6.3.3 Kueue 佇列配置

本節將配置 Kueue 的核心元件，包括 ResourceFlavor（資源類型）、ClusterQueue（叢集佇列）和 LocalQueue（本地佇列）。這些配置將實現以下功能：

1. **ResourceFlavor**：定義不同類型的 GPU 資源（V100 和 A100），指定節點標籤和容忍度
2. **ClusterQueue**：建立叢集級別的資源佇列，設定資源配額和排程策略
3. **LocalQueue**：在特定名稱空間中建立本地佇列，連線到叢集佇列

**ResourceFlavor 定義：**

```yaml
# 定義 V100 GPU 資源類型
apiVersion: kueue.x-k8s.io/v1beta1
kind: ResourceFlavor
metadata:
  name: gpu-v100-32gb
spec:
  nodeLabels:
    # 指定 GPU 產品型號，用於節點選擇
    nvidia.com/gpu.product: "Tesla-V100-32GB"
    # 指定可用區，實現資源隔離
    zone: "gpu-zone-a"
  tolerations:
  # 容忍 GPU 節點的汙點，確保 Pod 可以排程到 GPU 節點
  - key: "nvidia.com/gpu"
    operator: "Exists"
    effect: "NoSchedule"
---
# 定義 A100 GPU 資源類型
apiVersion: kueue.x-k8s.io/v1beta1
kind: ResourceFlavor
metadata:
  name: gpu-a100-80gb
spec:
  nodeLabels:
    # 指定 GPU 產品型號，A100 效能更強
    nvidia.com/gpu.product: "Tesla-A100-80GB"
    # 不同的可用區，實現負載均衡
    zone: "gpu-zone-b"
```

**ClusterQueue 配置：**

```yaml
# 建立 AI 訓練專用的叢集佇列
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: ai-training-queue
spec:
  # 名稱空間選擇器：只有打了 team 標籤（ai-research 或 ai-production）的名稱空間可以使用此佇列
  # 注意：LocalQueue 必須建在被此選擇器命中的名稱空間裡，否則建立的 LocalQueue 不會被激活
  namespaceSelector:
    matchExpressions:
    - key: team
      operator: In
      values: ["ai-research", "ai-production"]
  resourceGroups:
  # 定義資源組，包含 HAMi 提供的三種 GPU 資源類型
  - coveredResources: ["nvidia.com/gpu", "nvidia.com/gpumem", "nvidia.com/gpucores"]
    flavors:
    # V100 GPU 資源配置
    - name: gpu-v100-32gb
      resources:
      - name: "nvidia.com/gpu"
        nominalQuota: 32        # 基礎配額：32 個 GPU
        borrowingLimit: 16      # 可借用額度：16 個 GPU
      - name: "nvidia.com/gpumem"
        nominalQuota: 1024000   # 1TB 顯存配額（32GB × 32 = 1024GB）
      - name: "nvidia.com/gpucores"
        nominalQuota: 1600      # 1600% GPU 算力（50% × 32 = 1600%）
    # A100 GPU 資源配置
    - name: gpu-a100-80gb
      resources:
      - name: "nvidia.com/gpu"
        nominalQuota: 16        # 基礎配額：16 個 GPU
      - name: "nvidia.com/gpumem"
        nominalQuota: 1280000   # 1.25TB 顯存配額（80GB × 16 = 1280GB）
      # A100 不設定 gpucores 限制，允許全效能使用
  # 佇列策略：盡力而為的先進先出
  queueingStrategy: BestEffortFIFO
  # 搶佔策略配置
  preemption:
    # 在同一 cohort 內可以搶佔低優先順序任務
    reclaimWithinCohort: LowerPriority
    # 在同一佇列內可以搶佔低優先順序任務
    withinClusterQueue: LowerPriority
```

**LocalQueue 配置：**

```yaml
# 研發環境的本地佇列
apiVersion: kueue.x-k8s.io/v1beta1
kind: LocalQueue
metadata:
  name: research-queue
  namespace: ai-research    # 部署在研發名稱空間
spec:
  clusterQueue: ai-training-queue  # 連線到 AI 訓練叢集佇列
---
# 生產環境的本地佇列
apiVersion: kueue.x-k8s.io/v1beta1
kind: LocalQueue
metadata:
  name: production-queue
  namespace: ai-production  # 部署在生產名稱空間
spec:
  clusterQueue: ai-training-queue  # 共享同一個叢集佇列資源
```

#### 6.3.4 名稱空間和優先順序配置

本節配置支援多租戶環境的名稱空間和任務優先順序管理，實現以下功能：

1. **名稱空間隔離**：為不同團隊建立獨立的名稱空間，實現資源和許可權隔離
2. **優先順序管理**：定義不同優先順序類別，確保重要任務優先排程
3. **標籤管理**：透過標籤實現名稱空間與佇列的關聯

**名稱空間配置：**

```yaml
# AI 研發團隊名稱空間
apiVersion: v1
kind: Namespace
metadata:
  name: ai-research
  labels:
    # 團隊標識，用於 ClusterQueue 的 namespaceSelector
    team: "ai-research"
    # 環境標識，便於管理和監控
    environment: "development"
    # 資源類型標識
    workload-type: "research"
---
# AI 生產團隊名稱空間
apiVersion: v1
kind: Namespace
metadata:
  name: ai-production
  labels:
    # 生產團隊的正確標籤，與研發環境區分
    team: "ai-production"
    # 生產環境標識
    environment: "production"
    # 生產工作負載類型
    workload-type: "inference"
```

**優先順序類配置：**

```yaml
# 高優先順序類：用於生產環境的關鍵任務
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
# 高優先順序值，確保優先排程
value: 1000
# 不設為全域性預設，避免所有任務都使用高優先順序
globalDefault: false
description: "高優先順序任務，用於生產環境的關鍵推理服務"
---
# 普通優先順序類：用於研發環境的日常任務
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: normal-priority
# 普通優先順序值
value: 100
# 設為全域性預設，未指定優先順序的任務使用此級別
globalDefault: true
description: "普通優先順序任務，用於研發環境的訓練和實驗"
```

#### 6.3.5 完整任務示例

**大模型訓練任務（研發環境）：**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: llm-training-research
  namespace: ai-research  # 指定研發團隊的名稱空間
  labels:
    # 關鍵配置：指定Kueue佇列名稱，必須與LocalQueue名稱匹配
    kueue.x-k8s.io/queue-name: research-queue
spec:
  parallelism: 2    # 並行執行2個Pod，適合分散式訓練
  completions: 1    # 任務完成條件：1個成功的Pod即可
  template:
    metadata:
      labels:
        app: llm-training
    spec:
      restartPolicy: Never  # Job失敗時不重啟Pod
      containers:
      - name: trainer
        image: pytorch/pytorch:2.0.1-cuda11.7-cudnn8-devel
        command: ["python", "/workspace/train.py"]
        resources:
          requests:  # 資源請求：排程器保證的最小資源
            cpu: "4"
            memory: "16Gi"
          limits:    # 資源限制：容器可使用的最大資源
            cpu: "8"
            memory: "32Gi"
            # HAMi GPU資源配置 - 關鍵部分
            nvidia.com/gpu: "1"        # 申請1個物理GPU
            nvidia.com/gpumem: "16000" # 申請16GB GPU顯存（單位：MB）
            nvidia.com/gpucores: "50"  # 申請50%的GPU算力
        volumeMounts:
        - name: workspace
          mountPath: /workspace
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: training-data-pvc  # 掛載訓練資料儲存
      tolerations:  # 容忍GPU節點的汙點，允許排程到GPU節點
      - key: "nvidia.com/gpu"
        operator: "Exists"
        effect: "NoSchedule"
```

**推理服務任務（生產環境）：**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: model-inference-prod
  namespace: ai-production  # 指定生產團隊的名稱空間
  labels:
    # 關鍵配置：指定生產環境的LocalQueue
    kueue.x-k8s.io/queue-name: production-queue
  annotations:
    # 可選配置：指定優先順序類，用於Kueue排程優先順序判斷
    kueue.x-k8s.io/priority-class: "high-priority"
spec:
  parallelism: 4    # 並行4個Pod，提高推理吞吐量
  completions: 1    # 任務完成條件：1個成功的Pod即可
  template:
    metadata:
      labels:
        app: model-inference
    spec:
      restartPolicy: Never
      # 關鍵配置：Pod級別的優先順序類，影響Kubernetes排程順序
      priorityClassName: high-priority
      containers:
      - name: inference
        image: tensorflow/serving:2.13.0-gpu
        resources:
          requests:  # 推理任務通常資源需求較小
            cpu: "2"
            memory: "8Gi"
          limits:
            cpu: "4"
            memory: "16Gi"
            # HAMi GPU資源配置 - 推理最佳化配置
            nvidia.com/gpu: "1"       # 申請1個物理GPU
            nvidia.com/gpumem: "8000" # 申請8GB GPU顯存（推理需求較小）
            nvidia.com/gpucores: "30" # 申請30%的GPU算力（推理計算量較小）
        ports:
        - containerPort: 8501  # TensorFlow Serving REST API端口
        env:
        - name: MODEL_NAME
          value: "llm-model"  # 指定要載入的模型名稱
      tolerations:  # 容忍GPU節點的汙點
      - key: "nvidia.com/gpu"
        operator: "Exists"
        effect: "NoSchedule"
```

#### 6.3.6 驗證配置

**檢查資源狀態：**

```bash
# 檢查ClusterQueue狀態
kubectl get clusterqueue ai-training-queue -o yaml

# 檢查LocalQueue狀態
kubectl get localqueue -A

# 查看GPU節點資源
kubectl describe nodes -l nvidia.com/gpu.count

# 監控任務佇列
kubectl get jobs -A --watch
```

**資源使用驗證：**

```bash
# 提交測試任務
kubectl apply -f llm-training-research.yaml

# 檢視任務排程狀態
kubectl describe job llm-training-research -n ai-research

# 檢查GPU資源分配
kubectl exec -it <pod-name> -n ai-research -- nvidia-smi
```

---

## 7. 總結

Kueue + HAMi 的組合為 Kubernetes 環境下的 AI 工作負載管理提供了一套完整、高效的解決方案。這種協作模式充分發揮了兩個專案的優勢，實現了從作業佇列管理到 GPU 資源虛擬化的全棧覆蓋。

---
