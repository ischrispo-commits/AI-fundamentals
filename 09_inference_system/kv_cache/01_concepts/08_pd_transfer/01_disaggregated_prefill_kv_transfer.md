# PD 分離架構下的 KV Cache 傳輸：Push 還是 Pull？算完再傳還是邊算邊傳？

PD 分離（Prefill-Decode Disaggregation）把 Prefill 放到高算力 GPU 上，Decode 放到大顯存 GPU 上——兩端分開後，核心問題從"顯存放不放得下"變成了**"KV Cache 怎麼從 Prefill 節點搬到 Decode 節點"**。一個 32K token 的 prompt 產生約 10 GB KV Cache，這個搬運過程直接決定了 PD 分離架構的 TTFT 和吞吐上限。

本文從傳輸時序、发起方、傳輸內容三個維度，對比 vLLM KV Connector V1、LMCache PD Backend 和 Mooncake 三種方案在 Push/Pull、Eager/Pipelined、完整/增量上的不同選擇及其代價。

> **前置閱讀**：[KV Cache 原理簡介](../01_basic/01_kv_cache_basics.md) — Prefill 與 Decode 的計算特性差異；[Chunked Prefill 如何改變 KV Cache 管理](../03_scheduling/01_vllm_chunked_prefill.md) — PD 分離的前置概念。
>
> **配合閱讀**：本文是概念層面的方案對比。各系統的完整原始碼分析見 [LMCache PD Backend](../../02_systems/01_lmcache/08_pd_backend.md)、[Mooncake 架構](../../02_systems/04_mooncake/01_mooncake_architecture.md)、[層級流水線並行](../07_offloading/02_layerwise_pipeline.md)。

---

## 一、PD 分離的動機與 KV 傳輸的必然性

### 1.1 兩階段的硬體需求錯配

Prefill 一次性處理全部輸入 token，Attention 計算量為 $O(S^2)$，屬於 **compute-bound**——需要高算力（如 H100/H200）。Decode 每步只處理一個新 token，但需要反覆讀取完整的 KV Cache，屬於 **memory-bound**——需要大顯存頻寬。

當 Prefill 和 Decode 綁在同一張 GPU 上時，兩種需求互相妥協：算力浪費在 Decode 的空轉上，顯存被 Prefill 的 KV Cache 峰值撐滿。PD 分離將兩者解耦：Prefill 節點用高算力 GPU，快速處理 prompt 後釋放；Decode 節點用大顯存 GPU，專門承載長上下文的 KV Cache 讀取。

### 1.2 分離的代價：KV Cache 必須跨節點傳輸

解耦的必然結果是 **KV Cache 不在同一張 GPU 上了**。Prefill 節點算出的 K 和 V 必須被搬到 Decode 節點。以 LLaMA-2 70B（GQA, 8 KV heads, FP16）為例，單 token 單層 KV 約為 4 KB，80 層 × 4 KB = 320 KB/token，32K prompt 共約 **10 GB**。這個傳輸量對 PCIe 5.0（~64 GB/s）單向理論極限約 156ms，對跨機 RDMA（以 400Gbps 網卡為例，有效頻寬 ~50 GB/s）約 200ms。實際延遲還需加上接收端寫入、網路協議棧開銷、多節點競爭等因素，通常比理論值高 20-50%。注意這是全部 80 層 KV 的總和。在 Pipelined 模式下，每次只傳輸一層（約 128 MB），10 GB 的總傳輸量被分散到各層計算之間，避免一次性阻塞。

**KV 傳輸的延遲直接加在 TTFT 之上**。如果等 Prefill 全部完成再傳，TTFT = Prefill 計算時間 + KV 傳輸時間 + 首個 Decode 時間。這是 PD 分離架構設計空間的核心約束。

---

## 二、KV 傳輸的三個設計維度

KV Cache 從 Prefill 節點搬到 Decode 節點，不是一個單純的"複製"操作。它涉及三個需要獨立決策的維度：

### 2.1 誰發起傳輸？Push vs Pull

| 模式     | 发起方       | 流程                                                                         |
| -------- | ------------ | ---------------------------------------------------------------------------- |
| **Push** | Prefill 節點 | Prefill 完成後主動推送到 Decode 節點；Decode 節點被動接收並寫入本地 KV Cache |
| **Pull** | Decode 節點  | Decode 節點在需要時從 Prefill 節點（或共享儲存）拉取；類似缺頁中斷，按需載入 |

Push 的優勢是 Decode 可以立即開始——KV 已經在本地了。代價是 Prefill 節點需要知道推給誰（需要外部編排），且如果 Decode 節點還沒準備好接收，資料無處存放。

Pull 的優勢是實現簡單——Decode 節點自己管理拉取時機，不需要外部協調。代價是首個 Decode 步驟被 KV 載入延遲阻塞，TTFT 中包含拉取時間。Pull 的拉取目標（從哪個 Prefill 節點或儲存層拉）可以由外部排程器決定——Mooncake 的 Conductor 正是扮演了這個角色：維護全域性快取索引，指導 Decode 節點從最優位置拉取，而非盲目向所有 Prefill 節點發起請求。

**LMCache PD Backend 選擇了 Push**：Sender（Prefill 節點）主動申請 Receiver 端記憶體、推送資料、通知完成。**Mooncake 選擇了 Pull-with-cache**：Conductor 排程器根據全域性快取位置決定從哪個節點的哪個儲存層拉取，Decode 節點按需透過 RDMA 批量拉取。**vLLM KV Connector V1 沒有預設方向**——它提供了 Push（`save_kv_layer`）和 Pull（`start_load_kv`）兩套 API，由外部編排器決定用哪個。

### 2.2 什麼時候傳？Eager vs Pipelined vs Lazy

| 策略          | 傳輸時機                                                         |        TTFT 影響         | 實現複雜度 |
| ------------- | ---------------------------------------------------------------- | :----------------------: | :--------: |
| **Eager**     | 全部 Prefill 完成后，一次性傳輸所有 KV                           | 傳輸時間完全加在 TTFT 上 |     低     |
| **Pipelined** | 每算完一層，立即開始傳輸該層的 KV（與後續層的 Prefill 計算重疊） |  傳輸時間部分被計算隱藏  |     中     |
| **Lazy**      | 只在 Decode 實際需要某層 KV 時才載入該層                         |     逐層攤薄傳輸延遲     |     高     |

Pipelined（層級流水線）是最常用的折中：當 GPU 計算 Layer 3 的 Attention 時，Layer 2 的 KV 正在透過 RDMA 傳輸——計算和 I/O 重疊，TTFT 中額外增加的只有最後幾層的傳輸延遲。

vLLM KV Connector V1 的 `start_load_kv` + `wait_for_layer_load(layer_name)` API 正是為 Pipelined 設計的——worker 在 forward 開始前觸發非同步載入，每層計算前等待該層資料就緒。LMCache PD Backend 和 Mooncake CPP 同樣採用了層級流水線。

### 2.3 傳什麼？完整 KV vs 增量傳輸

| 策略         | 傳輸內容                                                   |   頻寬需求   |
| ------------ | ---------------------------------------------------------- | :----------: |
| **完整 KV**  | 所有的 K 和 V，FP16/BF16 原始精度                          |     最高     |
| **增量傳輸** | 只傳 prefix cache 未命中的部分（命中部分 Decode 節點已有） | 取決於命中率 |

> 量化傳輸（FP8/INT8）是另一個正交維度——它減小每個 token 的體量，但不改變傳輸策略本身。本文聚焦在完整/增量的策略選擇，壓縮技術的討論見 [KV Cache 壓縮技術詳解](../06_compression/01_kv_cache_compression.md)。

三種方案都支援某種形式的增量傳輸：

- vLLM KV Connector V1 透過 `get_num_new_matched_tokens()` 讓 Decode 節點的 scheduler 知道哪些 token 的 KV 已經存在於遠端快取中，只傳輸增量。
- LMCache PD Backend 的 `AllocRequest` 包含 `already_sent_indexes`——Receiver 回覆 Sender 哪些 key 已經有了，避免重複傳輸。
- Mooncake 的 Conductor 維護全域性 KV Cache 位置索引，排程 Decode 請求到已快取字首的節點上，減少跨節點傳輸。

---

## 三、三種實現的選擇矩陣

### 3.1 vLLM KV Connector V1

vLLM V1 的 KV Connector API（PR #15960，2025 年 4 月合入 v0.8.5）定義了一套**抽象接口**，而非一種具體傳輸方案。它的核心設計選擇是**不替使用者做決定**：

```text
KVConnectorBase_V1:
  Scheduler 側：
    get_num_new_matched_tokens()  → 遠端快取命中多少？
    update_state_after_alloc()    → 分配本地 buffer
    build_connector_meta()        → 構建傳輸指令

  Worker 側：
    start_load_kv()               → 開始非同步載入（Pull）
    wait_for_layer_load(layer)    → 等待某層就緒
    save_kv_layer(layer, kv)      → 開始非同步儲存（Push）
    wait_for_save()               → 等待全部保存完成
```

- **Push/Pull**：可插拔。`save_kv_layer` 在 Prefill 節點每層 KV 計算完成後觸發推送（Push），`start_load_kv` / `wait_for_layer_load` 在 Decode 節點觸發非同步預取和逐層同步。這套 API 的設計以 **Push + Pipelined** 為主流用法——Prefill 側推送、Decode 側配合接收；Connector 實現者也可以基於它們構建純 Pull 模式（此時無需 Prefill 側 `save_kv_layer`），但當前生產部署以 Push 路徑為主。
- **時序**：支持 Pipelined（`wait_for_layer_load` 在每層計算前同步）和 Eager（全部 load 完再開始 forward）。vLLM 本身不做傳輸——它給 connector 一個在每層計算前後插入 I/O 操作的"掛鉤點"。
- **傳輸內容**：增量傳輸。`get_num_new_matched_tokens` 計算出遠端已快取的 token 數，排程器只為增量部分分配 block。

> **與 Chunked Prefill 的交互**：vLLM V1 的 PD 分離基於 Chunked Prefill 和 Prefix Caching 語義實現——PD 分離被視為"遠端 prefix cache"。這意味著 Chunked Prefill 中的 block 增量分配、只在第一個 chunk 查找 prefix cache 等約束，同樣適用於 PD 分離場景下的 KV 傳輸：Decode 節點首次排程時透過 `get_num_new_matched_tokens` 查詢遠端快取命中數，後續 chunk 不再重複查詢。詳見 [vLLM Chunked Prefill 與 KV Cache](../03_scheduling/01_vllm_chunked_prefill.md)。

### 3.2 LMCache PD Backend

LMCache 的 PD Backend 是一個**具體的 Push 模式實現**，不做抽象——它直接規定了傳輸方向和協議[^1]：

- **Push**：明確的 Sender/Receiver 角色。Prefill 節點作為 Sender，主動向 Receiver 申請記憶體（`AllocRequest`），推送資料（RDMA/NIXL），通知完成。
- **時序**：支持 Pipelined。可以在 Prefill 逐層計算時同步推送——每層 Attention 完成後立即觸發該層 KV 的傳輸。
- **傳輸內容**：支持增量。`AllocResponse` 返回 `already_sent_indexes`，Receiver 告訴 Sender 哪些 key 已經有了。

LMCache PD Backend 的獨特之處在於它取代了 `LocalCPUBackend` 充當記憶體分配器——Receiver 端的 KV Cache 接收緩衝由 PDBackend 直接管理 Host 記憶體，而非走傳統的 vLLM block table 分配路徑。這意味著 KV 傳輸的記憶體管理被從 vLLM 的核心分配邏輯中抽離出來，交由 PD Backend 獨立控制。

### 3.3 Mooncake

Mooncake 的 KV 傳輸是**全域性排程 + 多層儲存池**的副產品[^2]：

- **Pull-with-cache**：Conductor 維護全域性 KV Cache 位置索引。Decode 請求被排程到已快取所需字首的節點上（減少傳輸）。如果需要跨節點 KV，Decode 節點透過 RDMA 從目標節點的 GPU/CPU/SSD 儲存層拉取。
- **時序**：Pipelined。分塊管道並行（CPP）將 Prefill 按層和塊切分，KV 在計算過程中透過 RDMA 非同步流水線傳輸。
- **傳輸內容**：完整 KV + 增量。有全域性快取索引的節點不走傳輸；無快取的節點從最近的副本拉取完整資料。

Mooncake 與其他方案的關鍵區別是**KV 傳輸不是獨立決策，而是全域性資源排程的一部分**。Conductor 同時考慮快取位置、GPU 負載、網路拓撲來決定"請求發給哪個 Decode 節點"和"KV 從哪個儲存層拉"。

---

## 四、取舍

### 4.1 三維對比

| 維度           |                 vLLM KV Connector V1                 |          LMCache PD Backend          |                    Mooncake                     |
| -------------- | :--------------------------------------------------: | :----------------------------------: | :---------------------------------------------: |
| **Push/Pull**  |       可插拔（API 同時提供 Push 和 Pull 掛鉤）       |       Push（Sender 主動推送）        |     Pull-with-cache（Conductor 決定從哪拉）     |
| **傳輸時序**   |     Pipelined（`wait_for_layer_load` 逐層同步）      |  Pipelined（逐層 Attention 後觸發）  |          Pipelined（CPP 分塊管道並行）          |
| **傳輸內容**   |  增量（`get_num_new_matched_tokens` 計算遠端命中）   | 增量（`already_sent_indexes` 去重）  |           完整或增量（全域性索引決定）            |
| **編排方式**   |    外部編排（connector 由外部 orchestrator 控制）    | 內建角色（Sender/Receiver 自動協商） |       全域性排程（Conductor 統籌所有節點）        |
| **實現複雜度** | 低（vLLM 側只定義 API，傳輸邏輯在 connector 實現中） |    中（固定 Push 模式，協議簡單）    | 高（需要全域性排程器 + 多層儲存池 + RDMA 傳輸層） |
| **適用規模**   |            單對單 PD 分離（vLLM 實例對）             |        單對單或小規模 PD 分離        |             大規模叢集（數十節點）              |

### 4.2 一句話總結

**PD 分離的 KV 傳輸本質上是在 Push 和 Pull、Eager 和 Pipelined、完整和增量三條軸上做排列組合。vLLM 選擇了"不做選擇"——提供 API 讓社群自由選擇組合；LMCache 選擇了最簡路徑——固定 Push + Pipelined；Mooncake 選擇了最全域性的路徑——讓排程器統籌一切。** 三個方案適用於不同的規模：vLLM KV Connector 適合需要靈活對接不同傳輸後端的場景，LMCache PD Backend 適合快速搭建單對單 PD 分離，Mooncake 適合大規模叢集下的全域性最佳化。

---

## 相關閱讀

- [KV Cache 層級流水線並行](../07_offloading/02_layerwise_pipeline.md) — 計算與 KV I/O 重疊的詳細機制
- [vLLM Chunked Prefill 與 KV Cache](../03_scheduling/01_vllm_chunked_prefill.md) — PD 分離的排程基礎
- [LMCache PD Backend 原始碼分析](../../02_systems/01_lmcache/08_pd_backend.md) — Sender/Receiver 角色與 AllocRequest 協議
- [Mooncake 架構概覽](../../02_systems/04_mooncake/01_mooncake_architecture.md) — CPP 分塊管道並行與 Conductor 全域性排程
- [NIXL 網路傳輸庫](../../02_systems/05_nixl/01_nixl_introduction.md) — RDMA、GDS 與跨節點傳輸抽象層

[^1]: LMCache PD Backend 原始碼分析見 [`pd_backend.md`](../../02_systems/01_lmcache/08_pd_backend.md)。核心設計：Push 模式，Sender 透過 AllocRequest 向 Receiver 申請遠端記憶體，資料推送後通知 Proxy 完成。

[^2]: Mooncake 架構見 [`mooncake_architecture.md`](../../02_systems/04_mooncake/01_mooncake_architecture.md)。核心設計：Conductor 全域性排程器維護 KV Cache 位置索引，RDMA-based Messenger 實現跨節點 KV 批次傳輸。
