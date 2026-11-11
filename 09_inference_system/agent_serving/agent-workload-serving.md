# 當 Agent 流量成為推理系統的主要負載

> 過去推理系統服務的是「人打字」：請求短、無狀態、分鐘級會話。Agent 把這件事倒了過來：一次任務由程式連續發起 10–20 次呼叫，token 耗用是普通對話的 5–30 倍（Gartner 預測口徑）。當主要流量從人變成 Agent，推理系統賴以設計的一組隱含假設逐條失效。
>
> 2026-09 | 基於 vLLM（`43d691ec6b`，2026-08-07）與 SGLang（`f7101b0ae6`，2026-08-18）原始碼驗證；vLLM Router 部分轉引本倉庫 [router.md](../vllm/routing/router.md)（Router 倉庫未本地核驗，已標註）
>
> **性質說明**：機制與行為均經原始碼驗證；涉及成本/耗時的數字為量級示意，用於建立直覺，落地前需按自有硬體實測；外部文獻資料按原文口徑轉引。

---

## 一、負載在換人：Agent 流量長什麼樣

Chat 時代，推理系統對負載有一組很少被寫下來的隱含假設。它們如此自然，以至於散落在所有排程、快取程式碼的預設行為裡：

| 隱含假設                   | Chat 負載的現實                  | Agent 負載的現實                                                      |
| -------------------------- | -------------------------------- | --------------------------------------------------------------------- |
| 請求相互獨立、無狀態       | 每條訊息獨立到達，無跨請求約束   | 一次任務 = 有狀態的呼叫序列，每輪都要帶上全部歷史                     |
| KV 生命周期 = 請求生命週期 | 請求結束，KV 即可釋放            | 會話存活貫穿數十次呼叫，中間夾著工具執行的「空窗」                    |
| 上下文短且形態穩定         | 几百到几千 token，系統提示詞為主 | 上下文單調增長，工具結果（網頁、程式碼、日志）大量湧入                  |
| 容量按併發數規劃           | QPS × 平均時長，字首命中率穩定   | 命中率隨任務類型劇烈波動，重試與並行分支放大流量                      |
| 輸出吞吐 = 產能            | TPOT 與輸出 tok/s 就是產能口徑   | 輸入輸出比極端偏斜，decode 產出只佔處理量零頭，產能口徑要換成總處理量 |

資料側，這個趨勢已經可以量化：Agent 完成一件事要呼叫模型 10–20 次，token 耗用是普通對話的 5–30 倍（Gartner 預測，轉引自 [Token Factory 素材 05](../../99_misc/token_factory_talk/references/05-jevons-demand-future.md)）；HF Hub 的 Agent 流量監測顯示，2026 年 4 月僅 Claude Code 一類編碼 Agent 就占流量的 67.8%，7 月降至 44.4%，份額下降不是 Agent 退潮，而是十多個新客戶端湧現帶來的生態分化【素材 08】。驅動力已經從「人」切換到「機器」。

微觀形態上，AgentSysBench 對 10 個代表性 Agent 應用、6 萬餘次模型呼叫與 11 萬餘次工具呼叫的測量給出了第一份系統畫像（[From LLM Inference to Agentic Workloads](https://arxiv.org/abs/2608.15127)，2026-08）：會話中位活躍計算時間僅 20%，其餘時間「活著但空閒」；空閒期導致的 KV 重算（re-prefill）占 cache 相關 token 的 55.9%、總成本的 31.5%；工具定義與系統指令等控制面後設資料最高占上下文視窗的 84.3%；長短請求混批時，隊頭阻塞可使快請求減速 7.1–35.7 倍、小請求 TPOT 惡化至 +79.7%。這些數字把第二節要展開的四個連鎖問題，從推測變成了實測。

Agent 流量不是把 Chat 流量「放大」，而是把它變形。下面挑四個最關鍵的連鎖問題逐一拆（第五個假設「產能口徑失效」放到 §5 度量收尾），每一個都能在原始碼裡找到引擎的應對，以及應對不了的部分。

---

## 二、四個被打破的假設，四個連鎖問題

### 2.1 KV 生命週期錯配：逐出還是保留，從偶發變成常態

Agent 會話的存活時間遠長於單次請求。兩輪呼叫之間，系統要做一個 Chat 時代幾乎不存在的決定：

- **逐出**：下輪 turn 到來時重算整條軌跡。一個累積了 50K token 历史的 Agent 會話，若 KV 已被逐出，resume 時的 prefill 需要重讀全部歷史：按單卡 10–20K tok/s 的 prefill 量級估算，就是一次 2.5–5 秒的 TTFT 尖刺（量級示意，按硬體實測為準）。對一個每輪都在等待工具返回的互動式 Agent，這個尖刺出現在每一輪。這份估算還偏保守：prefill 是可並行的，開了上下文並行的部署裡純計算部分會隨並行度明顯縮短；而 miss 輪的 TTFT 由「計算 + 排隊」構成，負載越高排隊的佔比越大。尖刺的第一槓杆在排程與准入（見 3.2），堆卡幫助有限。
- **保留**：空閒會話的 KV 持續佔用顯存。併發會話數一多，「看不見的會話」吃掉的顯存比活躍請求還多，擠壓的是正在 decode 的 batch。

Agent 會話的 KV 命中率直接決定 TTFT 形態：Chat 場景下 prefix cache miss 的代價是幾百毫秒，Agent 場景下是數秒。

### 2.2 排程語義失真：佇列裡混著兩種完全不同的東西

Agent 流量進入佇列後，排程器看到的是兩類請求的混合體：

1. **活躍請求**：正在 prefill/decode，對 TTFT/TPOT 敏感；
2. **休眠會話**：工具執行中，下一輪幾秒到幾分鐘後才回來；但它的 KV 若還佔著顯存，就在持續支付「租金」。

更麻煩的是重試帶來的長 prefill 衝擊：一次 50K token 的重試 prefill，足以讓同 batch 的所有 decode 請求的 TPOT 抖動一個量級。Chat 時代靠 chunked prefill 緩解的問題，在 Agent 時代被放大，因為 Agent 的 prefill 特別長，重試又頻繁。而且這種干擾不均勻：被長 prefill 撞上的步直接落進長尾分位，p50 幾乎不動，SLO 往往先被 ITL 尾部擊穿，均值還看著正常。

### 2.3 路由的粘性需求：會話要「記住」實例

多實例部署下，Agent 會話的第 N 輪請求若被路由到一個沒見過它的實例，字首快取全部失效，2.1 的 TTFT 尖刺直接兌現。Chat 時代負載均衡追求「均勻」，Agent 時代要追求「親和」，而這兩個目標在容量緊張時互相沖突。

### 2.4 容量規劃失真：QPS 公式失效

Chat 容量公式：`併發數 = QPS × 平均請求時長`。Agent 場景下，決定顯存的不只是併發請求，還有併發會話數 × 會話 KV 增長速率 × 命中率。命中率取決於任務類型組合：一批編碼 Agent 和一批客服 Agent 的 KV 增長曲線完全不同，按平均數規劃的容量會在任務類型切換時震盪。還有兩個形態：會話佔空比（活躍請求與會話數之比）由會話的序列屬性決定，不隨規模改善；容量耗盡的表現是准入懸崖而非平滑退化，佇列打滿再疊加突發長 prefill，新會話會被直接拒絕。

---

## 三、引擎現狀：四個問題，原始碼裡已有什麼答案

以下均基於 vLLM `43d691ec6b`、SGLang `f7101b0ae6` 原始碼驗證。

### 3.1 KV 生命周期：radix tree + 分層儲存（SGLang 走得最遠）

SGLang 的 RadixCache 是會話複用的核心載體：

- `match_prefix`（`python/sglang/srt/mem_cache/radix_cache.py:376`）按字首樹匹配歷史 KV；
- `inc_lock_ref` / `dec_lock_ref`（`radix_cache.py:622`、`radix_cache.py:637`）透過引用計數把「正在使用」的子樹排除在逐出之外（`evictable_size_` 相應增減）；
- 逐出按 LRU（`last_access_time`，`radix_cache.py:248`）執行 `evict`（`radix_cache.py:592`）。

這套機制對 Agent 負載的含義：只要下一輪請求的 prompt 字首還在樹裡、沒有被逐出，resume 就是「免費」的。但 radix tree 預設只活在一個行程的顯存裡：重啟即失，多實例間不共享。

分層快取把「會話記憶」擴展到顯存之外：`--enable-hierarchical-cache`（`python/sglang/srt/server_args.py:2668`，預設關閉）啟用 HiCache 后，L1（GPU）逐出的 KV 寫回 L2（CPU）/L3（遠端儲存），下輪命中 L2 的恢復代價遠低於重算（架構細節見 [HiCache 深入詳解](../sglang/hicache_deep_dive.md)）。Agent 負載下，HiCache 應當作會話記憶層來配置，而不是可開可關的調優項。

vLLM 側：prefix caching 在 V1 已預設開啟（`vllm/config/cache.py:93`，`enable_prefix_caching: bool = True`），複用依據是塊級字首雜湊：`get_computed_blocks`（`vllm/v1/core/kv_cache_manager.py:229`）呼叫 `find_longest_cache_hit`（`kv_cache_manager.py:261`）定位最長命中，請求結束由 `free`（`kv_cache_manager.py:567`）歸還塊，同字首的後續請求仍可命中未被覆蓋的塊。但 vLLM 沒有「為某會話保留 KV」的租約/TTL 原語：命中是統計性的，顯存壓力下 Agent 會話的歷史塊隨時可能被新請求覆蓋。

### 3.2 排程：請求級優先順序已有，會話語義沒有

先糾正一個常見印象：兩個引擎都已具備請求級優先順序。

SGLang：

- 排程策略可選 `lpm / random / fcfs / dfs-weight / lof / priority / routing-key`（`server_args.py:828-846`），預設 `fcfs`；對字首複用最友好的 `lpm`（最長字首優先）需要顯式開啟；
- `--enable-priority-scheduling` 開啟後按請求 priority 欄位排程，且此時 `schedule_policy` 必須是 `fcfs` 或 `lof`（`server_args.py:9246-9249`）；
- 顯存不足時 `retract_decode`（`python/sglang/srt/managers/schedule_batch.py:2816`）逐個收回 decode 請求直至記憶體可容納，若仍不夠，則中止最後一個請求而不是讓排程器崩潰；收回順序由 `_get_decode_retraction_order`（`schedule_batch.py:2869` 起）決定，預設保留「已生成最少輸出、輸入最長」的請求，`retraction_policy=priority` 時優先保護高優先順序請求；
- `schedule_conservativeness`（`server_args.py:886`，預設 1.0）是防頻繁 retract 的調節閥，調大即更保守地准入。

vLLM V1：搶佔受害者按 `(priority, arrival_time)` 最小者選中（`vllm/v1/core/sched/scheduler.py:592-594`），被搶佔請求重新入隊等待重算。

缺的是什麼：以上所有原語都以「請求」為單位。沒有任何機制回答「這個請求屬於哪個會話」「這個會話已經花了多少預算」「這批互為分支的請求應該同進同退」。引擎外圍已出現會話語義的雛形：NVIDIA Dynamo 的 KV 路由支持 priority/latency 兩類 agentic hints，讓使用者面 turn 插隊後台任務；llm-d 的 Endpoint Picker 正在社群推進 session-affinity 路由（[issue #177](https://github.com/llm-d/llm-d-inference-payload-processor/issues/177)）。但它們都是閘道器層的「拼接」，vLLM/SGLang 核心裡仍沒有會話原語。這條裂縫有多寬，從學術界的反應可見一斑：Autellix 把 agent 程式整體作為一等公民重新排程（同等延遲下吞吐 4–15×），Helium 從資料系統視角重做 workflow-aware serving。排程層被整體重造，說明參數調優彌合不了。

### 3.3 路由：字首感知已有，會話粘性靠應用層

vLLM Router 的 `cache_aware` 策略在每個 worker 側維護近似 radix 樹追蹤已快取字首，按匹配率路由（匹配率閾值 `cache_threshold=0.5`，快取條目 30 秒周期清理；機制詳解見 [vLLM Router 架構解析](../vllm/routing/router.md)，Router 為獨立 Rust 專案，本文未對原始碼本地核驗）。

對 Agent 負載的啟示與缺口：

- `cache_aware` 解決的是**字首維度的親和**：系統提示詞、工具 schema 這類穩定字首收益最大；
- **會話維度的粘性**（同一會話的 N 輪請求儘量落同一實例）沒有內建：radix 樹追蹤的是「哪些字首在哪個節點上」，不是「哪個會話屬於哪個節點」。生產路由層的現狀是「有意識、無標準」：Dynamo 維護跨 worker 的 KV block 全局索引（Flash Indexer），llm-d 的 EPP 把 session-affinity 路由列為社群議題，但都未成為跨引擎的通用機制。實踐中仍靠應用層閘道器按 session id 做一致性哈希，或接受外置 KV 層來解耦（見 4.3）；
- 多引擎混合部署時，路由層無法感知 LMCache/Mooncake 里的 KV 分布，KV 感知路由目前停留在各自體系內（分布式 KV 層見 [LMCache 架構概覽](../kv_cache/02_systems/01_lmcache/01_lmcache_overview.md)、[Mooncake 架構詳解](../kv_cache/02_systems/04_mooncake/01_mooncake_architecture.md)）。

### 3.4 容量：把規劃公式從 QPS 換成會話三要素

容量公式的遷移：

```text
Chat：  併發請求數 ≈ QPS × 平均請求時長
Agent： 併發會話成本 ≈ Σ (活躍請求數 × 請求 KV)
        + Σ (休眠會話數 × 會話 KV × 保留概率)
        + Σ (每輪新增 token × (1 − 會話命中率) 的重算峰值)
```

方法論層面的支撐已經齊備：KV 容量推演的框架見 [GLM-5 KV Cache 容量規劃](../kv_cache/01_concepts/10_capacity_planning/03_glm5_kv_cache_capacity_planning.md)，服務產能與承諾的 Goodput 框架見 [Token 工廠的產能怎麼算？](../../99_misc/token_factory_talk/cluster-capacity-measurement.md)。新的工作是把 Goodput 的「成功」從請求級改成 turn 級：一個工具呼叫失敗重試 3 次的 turn，Goodput 該怎麼記？現有框架沒有答案。

---

## 四、三個沒有標準答案的權衡

### 4.1 粘性 vs 均衡

親和路由提升命中率，但把同類會話壓到同一實例，製造熱點與長尾。vLLM Router 用 `cache_threshold`（0.5）畫了一條線：匹配率過線才按親和路由，否則回落到負載均衡，本質上是承認親和是機率性的、均衡是兜底的。Agent 流量下這條線的位置需要按任務類型重調：編碼 Agent 的會話內字首增長率高，過線請求複用價值大；而系統提示同質化的客服 Agent，任何實例命中率都高，親和的邊際價值低。親和的緊迫性還取決於外接快取層的容量：配了足量 DRAM 層、write_through 策略的 HiCache，能把跨實例命中率託在高位，在相當大的規模區間內實質替代會話親和路由。先看外接層配了多少，再決定要不要做親和。

### 4.2 保留 vs 重算

直覺上的成本模型（量級示意）：

```text
保留成本 = 會話 KV 位元組 × 保留時長 × 單位顯存租金
重算成本 = 历史 token 數 / prefill 吞吐 × 等待時間價值
```

變數是保留時長。Agent 會話的工具間隔（秒到分钟）恰好落在「顯存租金不可忽略、重算又不便宜」的區間。新架構把天平進一步推向重算：CSA 把 KV 壓到 1/4，KDA 乾脆不產生 token 級 KV（見 [01-post-kv-cache-era.md](../kv_cache/07_kv_compression/05-post-kv-cache-era.md)），重算成本在快速通縮。今天按 H100+MHA 口徑設計的粘性/外置 KV 方案，換到新架構模型上可能突然不划算。會話基礎設施的設計要把「重算變便宜」當作一階趨勢來對沖。

### 4.3 會話狀態放哪：三層選型

| 層               | 代表                                                                                                                | 優勢                                                          | 代價                                       |
| ---------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------ |
| 引擎內 radix     | SGLang RadixCache、vLLM prefix hash                                                                                 | 零額外跳數，命中即免 prefill                                  | 與行程共生：重啟即失、多實例不共享、無 TTL |
| 外置 KV 儲存     | LMCache（L2/L3）、Mooncake                                                                                          | 跨實例/跨引擎共享，會話記憶持久；足量配置時可實質替代會話親和 | 恢復走網路/盤，多一跳運維複雜度            |
| 應用層上下文重組 | 壓縮/摘要（[Claude Code 上下文壓縮](../../08_agentic_system/context/claude-code-context-compression.md)）、狀態外化 | 把「存」的問題換給「算」，引擎零改造                          | 摘要有資訊損失，重組本身是一次 prefill     |

選型不是單選，多數生產系統是「引擎內 radix 保熱點 + 外接儲存保長尾 + 應用層壓縮控總量」的三明治。要避免的是預設態：什麼都不配，每輪 resume 都交全額重算稅。

---

## 五、怎麼度量：三個 Agent 形態指標與缺口清單

現有 benchmark（`benchmark_serving`、`sglang bench`）的流量形態是 Chat 的：獨立請求、穩定字首。Agent 負載需要自己的度量：

1. Turn-resume TTFT：同一會話上一輪結束後 T 秒（模擬工具執行）發起來輪請求，測 TTFT 分布。它同時暴露逐出策略與分層快取的實效，Chat TTFT 測不出這些。
2. 會話 KV 命中率：按會話聚合的 prefix cache 命中 token 占比，隨任務類型/會話長度分佈，而不是叢集平均值。
3. 每任務 token 成本：含重試與分支放大的、按「任務」而非「請求」聚合的 token 消耗，容量規劃與成本歸因都該以它為單位。

度量口徑本身也要換：Agent 負載 prefill 主導，decode 產出只佔處理量的零頭，拿「輸出吞吐」橫評引擎沒有意義，應以總 token 處理量 + TTFT/ITL 分位為主口徑。工具鏈層面另有一個坑：按完成事件切片匯出的利用率會系統性低估全窗負載，做 Agent 負載的全窗分析要用請求秒守恆或時間加權指標。

缺口清單（截至 2026-09，按原始碼現狀）：

- 引擎無會話原語：session id → 親和/配額/分組搶佔的對映，只能應用層拼；
- KV 無租約/TTL：「保留多久」沒有宣告式介面，逐出策略對所有流量一視同仁；
- KV 感知路由不跨引擎、不跨儲存層（Router 只見引擎、LMCache 只見自己）；
- Agent 形態 benchmark 標準化剛起步：MLCommons 已於 2026-07 啟動 [MLPerf Agentic Inference](https://mlcommons.org/2026/07/agentic-inference-for-mlperf-inference/)（多輪、上下文持續增長、閉環工作流），學術界已有 AgentSysBench 這樣的負載畫像工具，但 turn-resume TTFT、會話 KV 命中率尚不在任何標準測法中。

實測待辦（本文數字均未實測，為量級示意）：同一 20 輪工具呼叫 trace（每輪間隔 5–30 s），分別在「radix 開/關」「HiCache 開/關」下測 turn-resume TTFT 與每任務 token 成本。這一步做完，本文才能從機制分析變成容量依據。

---

## 結語

Chat 時代推理系統的一等公民是請求，Agent 時代要換成會話。請求級的機制引擎已備齊：優先順序、搶佔、字首複用、分層逐出都有原始碼級的答案；會話級的原語（粘性、租約、分組、turn 級度量）還全部空缺，應用層閘道器與 KV 儲存層因此在 2026 年擁擠起來。給基礎設施團隊的建議：把 Agent 平台接上推理叢集之前，先決定會話狀態放在三層中的哪一層。這個決定做錯，後面的排程與容量最佳化都在為它還債。

---

## 參考資料

1. **負載畫像與系統研究**
   - Chaokun Chang et al., [From LLM Inference to Agentic Workloads](https://arxiv.org/abs/2608.15127), arXiv 2608.15127, 2026-08——本文第一節量化資料來源（AgentSysBench：會話中位活躍計算時間 20%、re-prefill 占 cache 相關 token 55.9%、後設資料占上下文最高 84.3%）
   - [Autellix: An Efficient Serving Engine for LLM Agents as General Programs](https://arxiv.org/abs/2502.13965), arXiv 2502.13965, 2025（NSDI'26 发表）——程式級排程，同等延遲下吞吐 4–15×
   - [Helium: Efficient LLM Serving for Agentic Workflows — A Data Systems Perspective](https://dl.acm.org/doi/10.1145/3802046), ACM——workflow-aware serving
   - [Cost-Efficient Large Language Model Serving for Multi-turn Conversations with CachedAttention](https://www.usenix.org/conference/atc24/presentation/gao-bin-cost), USENIX ATC'24——多輪會話 KV 分層複用的先導工作（原 AttentionStore）

2. **生產系統與路由**
   - NVIDIA, [Full-Stack Optimizations for Agentic Inference with NVIDIA Dynamo](https://developer.nvidia.com/blog/full-stack-optimizations-for-agentic-inference-with-nvidia-dynamo/)——KV block 全局索引（Flash Indexer）與 agentic hints
   - llm-d, [Agentic Serving Well-Lit Path](https://llm-d.ai/docs/0.8/well-lit-paths/workloads/agentic-serving) 與 [KV Cache Management](https://llm-d.ai/docs/architecture/advanced/kv-management)；session-affinity 路由進展見 [issue #177](https://github.com/llm-d/llm-d-inference-payload-processor/issues/177)
   - Red Hat, [Master KV cache aware routing with llm-d for efficient AI inference](https://developers.redhat.com/articles/2025/10/07/master-kv-cache-aware-routing-llm-d-efficient-ai-inference), 2025-10
   - [DualMap: Enabling Both Cache Affinity and Load Balancing](https://arxiv.org/html/2602.06502v1), arXiv 2602.06502——4.1 節「粘性 vs 均衡」的學術跟進

3. **Benchmark**
   - MLCommons, [Agentic Inference for MLPerf Inference](https://mlcommons.org/2026/07/agentic-inference-for-mlperf-inference/), 2026-07——多輪、上下文持續增長、閉環工作流的基準標準化

延伸閱讀：LLM 系統演進「請求 → 會話 → 軌跡」的三段敘事，見 [LLMSys PaperList](https://github.com/AmberLJC/LLMSys-PaperList/)。

---

## 源文件索引

| 文件                                            | 關鍵符號                                                                                                               | 本文引用點                                             |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `python/sglang/srt/mem_cache/radix_cache.py`    | `match_prefix`、`inc_lock_ref`/`dec_lock_ref`、`evict`、`last_access_time`                                             | 字首匹配與引用計數保護（:376、:622、:637、:592、:248） |
| `python/sglang/srt/managers/schedule_batch.py`  | `retract_decode`、`_get_decode_retraction_order`                                                                       | 顯存不足時的收回順序與最後請求中止（:2816、:2869）     |
| `python/sglang/srt/managers/schedule_policy.py` | `PrefillAdder`、`rem_chunk_tokens`、`budget_state`                                                                     | 准入預算（:504、:512-538、:664、:834）                 |
| `python/sglang/srt/managers/scheduler.py`       | `get_next_batch_to_run`、`event_loop_normal/overlap`                                                                   | 排程主迴圈（:3015、:1719、:1754）                      |
| `python/sglang/srt/server_args.py`              | `schedule_policy`（預設 fcfs）、`enable_priority_scheduling`、`schedule_conservativeness`、`enable_hierarchical_cache` | 策略選項與預設值（:828-846、:886、:2668）              |
| `vllm/v1/core/sched/scheduler.py`               | `schedule`、搶佔受害者選擇                                                                                             | 按 (priority, arrival_time) 搶佔（:440、:592-594）     |
| `vllm/v1/core/kv_cache_manager.py`              | `get_computed_blocks`、`find_longest_cache_hit`、`free`                                                                | 字首命中與塊歸還（:229、:261、:567）                   |
| `vllm/config/cache.py`                          | `enable_prefix_caching`                                                                                                | V1 預設開啟（:93）                                     |

_版本：vLLM `43d691ec6b`（2026-08-07）、SGLang `f7101b0ae6`（2026-08-18）。文中未標註實測的耗時/成本數字均為量級示意。_
