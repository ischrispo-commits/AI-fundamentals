# vLLM Chunked Prefill 如何改變 KV Cache 管理

> 本文以 vLLM V1 排程器原始碼為基準。SGLang 的 Chunked Prefill 在排程策略（Prefill 優先、chunk 連續執行）和 Prefix Caching 交互（stash 機制支援跨 chunk 命中）上做出了不同選擇，詳見 [SGLang Chunked Prefill 原理與實現](../../../sglang/chunked_prefill.md)。

Prefill 是一次性把整個 prompt 的 KV 全算完，還是切成小塊逐步算？這看起來只是計算排程的問題，但 vLLM 的 Chunked Prefill 實際上深刻改變了 KV Cache 的分配時序、與 Prefix Caching 的交互方式，以及 Preemption 的觸發視窗。

這篇文章從 KV Cache 管理的視角拆解 vLLM 的 Chunked Prefill 實現——它如何把"一次性申請全部 block"變成"逐步申請逐批增長"，以及這個看似簡單的變化在工程上引出的三個約束：prefix cache 只在第一個 chunk 查找、chunk 大小必須對齊 block_size、以及 chunk 之間的 Preemption 風險。

> **前置閱讀**：[PagedAttention 原理介紹](../01_basic/02_paged_attention.md) — block table 與按需分配；[Prefix Caching 原理分析](../02_prefix_caching/02_prefix_caching.md) — hash chaining 與 block 級複用。

---

## 一、一次算完的代價

### 1.1 Prefill 的算力特性

Prefill 需要處理全部輸入 token——序列長度 $S$ 的 prompt，每層 Attention 的計算量是 $O(S^2)$，全部層的總 FLOPs 與 $S^2$ 成正比。一個 32K token 的 prompt，Prefill 的算力開銷約為 4K token 的 64 倍。

更重要的是，Prefill 是 **compute-bound**——GPU 的計算單元被佔滿，但顯存頻寬並未飽和。而 Decode 是 **memory-bound**——每步只算一個新 token，瓶頸在讀 KV Cache 的頻寬。

### 1.2 傳統 Prefill 對 KV Cache 的雙重衝擊

一次性 Prefill 意味著一次性為整個 prompt 的 **所有 token** 分配 KV Cache block：

```text
傳統 Prefill（無 Chunked）：
  請求到達（32K token prompt）
    ↓
  一次性分配所有 block：32K ÷ 16 = 2000 blocks
    ↓
  GPU 持續 O(S²) 計算，Decode 被阻塞
    ↓
  全部 Prefill 完成后，才開始第一個 token 的生成
```

兩個問題同時出現：

- **Block 分配峰值高**：2000 個 block 瞬間被佔用。如果此時 GPU 上還有其他請求正在 Decode，可能導致 block 池耗盡，觸發 Preemption。
- **Decode 被阻塞**：使用者感知的 TTFT（Time To First Token）等於整個 Prefill 的耗時。32K token 的 Prefill 可能需要數秒——使用者盯著空白螢幕等第一個字。

### 1.3 Chunked Prefill 的核心思路

既然 Prefill 算得慢又占得多，那就不等它全算完——切成小塊，每步只算一部分 token，與 Decode 交替執行。vLLM V1 用統一的 token budget 排程所有請求，chunk 之間的間隙自然被其他請求的 Decode 步驟填充。[^1]

```text
Chunked Prefill（max_num_scheduled_tokens=2048）：
  請求到達（32K token prompt）
    ↓
  Step 1: Prefill chunk 0-2047    → 分配 128 blocks → 計算 → 留在 running 佇列
  Step 2: Decode 其他請求          → 生成 token
  Step 3: Prefill chunk 2048-4095  → 分配 128 blocks → 計算 → 留在 running 佇列
  Step 4: Decode 其他請求          → 生成 token
  ...
  Step N: Prefill 最後一個 chunk   → 分配 128 blocks → 計算
  全部 Prefill 完成后，num_computed_tokens >= num_tokens，切換到 Decode（`num_computed_tokens` 詳見 §2.1）
```

Chunked Prefill 把算力開銷和 block 分配分散到多步中，讓**其他請求的 Decode** 有機會在本請求的 chunk 之間執行——請求自身仍需完成所有 chunk 後才能進入 Decode，但它不再需要等排在它前面的長請求全部 Prefill 完。TTFT 的改善來自"不被其他請求長時間阻塞"，而非"自己的第一個 chunk 就能解碼"。

---

## 二、Chunked Prefill 對 KV Cache 的三個改變

### 2.1 Block 分配：從一次性到增量式

這是最核心的變化。無 Chunked Prefill 時，`allocate_slots()` 一次性為整個 prompt 分配全部 block。Chunked Prefill 下，每次只分配當前 chunk 所需的 block：

```text
32K token prompt, block_size=16, chunk_size=2048:

傳統 Prefill:
  allocate_slots(request, num_new_tokens=32768)
  → 一次性分配 2048 個 block

Chunked Prefill:
  Step 1: allocate_slots(request, num_new_tokens=2048)  → 128 blocks
  Step 2: allocate_slots(request, num_new_tokens=2048)  → 128 blocks  (追加)
  ...
  Step 16: allocate_slots(request, num_new_tokens=2048) → 128 blocks  (追加)
```

從 KV Cache 管理的角度看，這有三個直接影響：

**記憶體峰值降低**。如果請求之間有交錯——Decode 在此請求的 chunk 之間處理其他請求——單個請求不會在任意時刻獨佔所有 block。當然，如果只有這一個請求，總 block 數不變，但峰值的時間分佈更平滑。

**Preemption 視窗期拉長**。傳統 Prefill 下，Preemption 只能在 Prefill 開始前或完成後發生。Chunked Prefill 在兩個 chunk 之間也會檢查 block 可用性：如果 Step 3 的 `allocate_slots()` 返回 `None`，排程器可以選擇 Preempt 優先順序更低的請求，或者將當前請求暫時擱置。

**`num_computed_tokens` 成為狀態指標**。在 vLLM V1 排程器中，一個請求是"正在 Prefill"還是"正在 Decode"，由 `num_computed_tokens` 與總 token 數的關係決定：`is_prefill_chunk = num_computed_tokens < num_tokens`。每完成一個 chunk，`num_computed_tokens` 向前推進——它既是"已計算了多少 token"的計數器，也是"下一次從哪開始 Prefill"的指標。請求在 `num_computed_tokens >= num_tokens` 之前，`is_prefill_chunk` 條件為真，每個排程步均走 Prefill 處理路徑——直到全部 token 計算完畢後才切換到 Decode。

### 2.2 Prefix Caching：只在第一個 chunk 查找

這裡 vLLM 有一個當前版本的重要約束：**Prefix Caching 的命中檢查只在請求首次被排程時進行**[^1]。

```python
# vLLM V1 scheduler: 字首快取查詢的入口條件
if request.num_computed_tokens == 0:
    # 首次排程：查找 prefix cache
    new_computed_blocks, num_new_local_computed_tokens = \
        self.kv_cache_manager.get_computed_blocks(request)
    # ...基於命中結果決定跳過多少 token
else:
    # 後續 chunk：跳過 prefix cache 查找，直接從上一次中斷處繼續
    # num_computed_tokens 已經記錄了進度
```

這意味著：如果請求 A 和請求 B 共享同一個長 System Prompt，但 A 先被排程，已經佔用了前 2048 個 token 的 block，B 在第一個 chunk（`num_computed_tokens==0`）可以命中 A 的快取。但 A 的第二個 chunk（`num_computed_tokens > 0`）不會去查 B 可能已經算好的後續 block——無論快取是否存在，A 的後續 chunk 都會自己重新 Prefill。

這更像一個主動的工程權衡，而非設計缺陷。跨 chunk 做 prefix cache 查詢的障礙不僅在於程式碼複雜度——還包括更實質的工程問題：快取命中後需要判斷命中的 block 是否與當前請求已分配的物理頁衝突、部分命中時需要重組 block table 映射、以及處理"快取的 block 已被其他請求淘汰"的競態。當前版本選擇了一條狀態機更可控的路徑：只在 `num_computed_tokens == 0` 時做一次快取匹配，後續 chunk 沿着已建立的 block table 繼續追加。

> **對比 SGLang**：SGLang 採取了不同的設計——透過 `stash_chunked_request()` 將每個 chunk 的部分 KV 寫回 Radix Tree，後續 chunk 呼叫 `init_next_round_input()` 重建 `fill_ids` 後重新匹配字首，使得跨 chunk 的 HiCache 命中成為可能。兩種設計體現了同一個權衡的不同選擇：vLLM 選擇了排程邏輯的簡單性，SGLang 選擇了快取利用率的完整性。詳見 [SGLang Chunked Prefill 原理與實現](../../../sglang/chunked_prefill.md)。

### 2.3 Block 對齊：chunk 大小必須是 block_size 的整數倍

Chunked Prefill 與 Prefix Caching 同時啟用時，vLLM 要求 `max_num_batched_tokens`（即 chunk size）必須能被 `block_size` 整除[^2]。

```python
# vllm/v1/core/sched/scheduler.py: chunked prefill + prefix caching 的約束
# 如果 token budget 無法完整容納剩餘 token：
# 只排程 (budget // block_size) * block_size 個 token
num_new_tokens = (budget // block_size) * block_size
```

原因在於 Prefix Caching 需要**完整的 block** 做 hash 匹配。如果一個 chunk 在 block 中間結束（比如 block_size=16，chunk 只處理了 20 個 token，恰好卡在第二個 block 的第 4 個 token），這第二個 block 處於"半滿"狀態——它的 hash 無法用於快取查詢，因為它還缺 12 個 token 才能形成一個完整 block。

這個約束有一個實際影響：token budget 可能無法被充分利用。例如 `block_size=16, budget=133`，只能排程 `(133//16)*16 = 112` 個 token——浪費了 21 個 token 的預算額度。PR #7753 的作者註明了這是一個"臨時約束"，理論上可以透過支援 partial block hashing 來解除，但截至當前版本仍然有效。

---

## 三、三個派生問題

### 3.1 第一個 chunk 的 hit 與後續 chunk 的 miss 並存

結合 §2.2 和 §2.3，同一個雙請求場景的收益取決於 B 首次排程的時間點：

```text
請求 A: System Prompt (4096 token) + User Query (256 token)
請求 B: System Prompt (4096 token) + User Query (512 token)

Chunk size = 2048, block_size = 16 (128 blocks/chunk)

請求 A 先到達：
  Chunk 1 (token 0-2047): 首次排程 → 查 prefix cache → 無命中 → 分配 128 blocks，計算
  Chunk 2 (token 2048-4095): num_computed_tokens=2048 > 0 → 跳過查詢 → 分配 128 blocks，計算
  Chunk 3 (token 4096-4352): User Query → 分配 16 blocks，計算（同樣不會觸發 prefix cache 查找）
  Prefill 完成，開始 Decode；確認後的 block 逐 chunk 寫入 prefix cache

場景一：B 在 A 全部 Prefill 完成後才到達
  B Chunk 1: 首次排程 → get_computed_blocks 對 B 的完整序列做哈希匹配
             （首次排程會從頭走一遍 B 的所有 block 的雜湊鏈，scheduler.py:932）
    → System Prompt 的 4096 token（256 個 block）全部命中 → 直接跳過
  B 從 User Query 開始 Prefill，零重複計算

場景二：B 在 A 的 chunk 1 剛入快取、chunk 2 尚未計算時到達
  B Chunk 1 (token 0-2047): 首次排程 → 查 prefix cache → 命中 A 的 chunk 1 的 128 個 block → 複用
  B Chunk 2 (token 2048-4095): num_computed_tokens=2048 > 0 → 跳過查詢
    → 即使 A 的 chunk 2 稍後入快取，B 也不會再查 → 自己重新 Prefill 這 2048 個 token
```

可見"重算 chunk 2"只发生在 B 的首次快取查詢早於 A 的 chunk 2 block 入快取的時序下；只要 B 首次排程時對應的 block 已在快取中，首次匹配即可命中全部分配過的字首。這個場景揭示了當前實現的真正侷限：**快取查詢只有一次機會，且只發生在請求首次排程時**。B 的首個 chunk 命中多少，完全由"那一刻快取裡有多少"決定——共享字首跨越 chunk 邊界且對方算得比自己晚的部分，就浪費了。

### 3.2 Chunk 之間的 KV Cache 碎片

Chunked Prefill 分配 block 是增量的——每個 chunk 追加到已有的 block table 中。但如果兩個 chunk 之間，其他請求分配並釋放了中間的一些 block，這個請求的 block table 在物理顯存上是不連續的。PagedAttention 透過 block table 的虛擬→物理對映天然處理了這種不連續性，不會影響正確性。但極端的物理碎片可能降低 block table 遍歷時的快取區域性性——雖然在實際中，PagedAttention 的虛擬→物理對映對 compute kernel 完全透明，且 block_size=16 或更大時這個影響極小。

### 3.3 long_prefill_token_threshold：長 prompt 的特殊對待

vLLM 提供了一個 `long_prefill_token_threshold` 參數用於標註"長" prompt：超過此閾值的 prompt，每個排程步最多隻能處理 `long_prefill_token_threshold` 個 token，禁止一個 prompt 吃掉全部 token budget[^3]。這個參數配合 `max_long_partial_prefills`（預設 1）使用，允許短 prompt 跳過排在前面的長 prompt 優先被排程——"短 prompt 插隊"。

從 KV Cache 角度，這引入了更復雜的 block 分配交錯模式。但本文不展開討論——它更多是排程策略而非 KV Cache 機制本身的改變。

---

## 四、與 Preemption 的交互：視窗期變寬了

傳統 Prefill 下，Preemption 只有一個觸發點：`allocate_slots()` 為整個 prompt 分配 block 時，發現空閒 block 不夠。Chunked Prefill 把"一次分配"變成"多次分配"，每個 chunk 的 `allocate_slots()` 呼叫都可能觸發 Preemption。

```text
Chunked Prefill 的 Preemption 窗：
  Chunk 1: allocate_slots → 成功 → 計算 →
  Chunk 2: allocate_slots → 失敗（block 池耗盡）
           → 排程器檢查 running 佇列
           → 選擇 victim（FCFS: self.running.pop()，PRIORITY: max priority）
           → _preempt_request() → 釋放 victim 的全部 block
           → allocate_slots 重試 → 成功 → 繼續計算
```

這比傳統 Prefill 多了一個好處：**Preemption 不再需要一次性釋放足夠的 block 來容納整個 prompt**。傳統 Prefill 下，如果 prompt 需要 2000 個 block，必須 Preempt 足夠多的請求來騰出 2000 個 block。Chunked Prefill 只需要騰出當前 chunk 所需的 block（如 128 個）——門檻大幅降低。

但同時多了一個風險：**請求可能在半路被 Preempt**。同一個 `schedule()` 呼叫內，`allocate_slots()` 失敗時，victim 通常選自 `self.running` 佇列中的其他請求，而非當前正在被排程的請求本身。但如果後續排程輪次中顯存壓力持續，該請求優先順序較低，則可能在後續輪次中被選為 victim——此時已計算的 3 個 chunk（384 blocks, num_computed_tokens=6144）全部被釋放，恢復時 `num_computed_tokens` 歸零，需要從頭 Prefill。Chunked Prefill 讓請求在"半完成"狀態下暴露了更長的 Preemption 窗口——單次排程中通常不會 preempt 當前請求，但跨排程輪次的競爭中，半完成的請求仍面臨被犧牲的風險。

---

## 五、取舍

### 5.1 三個維度的變化

| 維度                      |             傳統 Prefill              |                 Chunked Prefill                  |
| ------------------------- | :-----------------------------------: | :----------------------------------------------: |
| **Block 分配峰值**        |         高（一次性分配全部）          |             低（按 chunk 增量分配）              |
| **TTFT（首 token 延遲）** | 差（長 prompt 需等全部 Prefill 完成） |            改善（Decode 可交錯執行）             |
| **總吞吐**                |       高（無 chunk 間排程開銷）       |               略低（排程開銷增加）               |
| **Prefix Cache 利用率**   |       高（一次查找，完整命中）        |            中（僅第一個 chunk 查找）             |
| **Preemption 門檻**       |   高（需騰出整個 prompt 的 block）    |        低（只需騰出單個 chunk 的 block）         |
| **Preemption 代價**       |            重算整個 prompt            | 重算已完成的所有 chunk（如果請求自己被 Preempt） |

### 5.2 Chunk Size 的選擇困境

- **大 chunk**（如 4096）：接近傳統 Prefill 的行為——分配峰值高、Decode 等待久，但 prefix cache 利用率高（共享字首更可能完整落在一個 chunk 內）
- **小 chunk**（如 512）：分配更平滑、其他請求的 Decode 能更頻繁地被穿插執行（請求自身仍需完成全部 chunk 才能開始 Decode），但第一個 chunk 更小意味着"從位置 0 開始的快取查詢"能複用的 token 更少——共享字首可能在第一個 chunk 之後還在延續，但排程器不會再查快取
- **vLLM 預設**：`max_num_batched_tokens` 不設硬上限，由 token budget 自然約束。PR #7753 的 benchmark 顯示 chunk_size=2048 配合 block_size=16 在 Llama-2 上取得了最佳吞吐（3929.7 tok/s）

### 5.3 小結

**Chunked Prefill 把 KV Cache 的分配從"一次性大宗申請"變成了"多次小額分期"，降低了峰值壓力和 Preemption 門檻，但付出的代價是 Prefix Caching 只在第一個 chunk 生效——共享字首如果跨越 chunk 邊界，後續的快取將白白浪費。** 這個約束源自一個工程選擇：為簡單性犧牲跨 chunk 的快取查詢。如果未來 vLLM 支持 partial block hashing 或跨 chunk 快取索引，Chunked Prefill 的記憶體效率還會有成倍的提升空間。

---

## 相關閱讀

- [PagedAttention 原理介紹](../01_basic/02_paged_attention.md) — Block 級記憶體管理：block table、按需分配、碎片率
- [Prefix Caching 原理分析](../02_prefix_caching/02_prefix_caching.md) — Hash chaining 與 block 級複用機制
- [Attention Sinks 與 KV Cache 淘汰策略](../05_eviction/01_attention_sinks_and_eviction.md) — KV Cache 滿了怎麼淘汰
- [為什麼 GPU 生成每個 token 時利用率不到 5%？——Prefill 與 Decode 深度拆解](../../../prefill_decode/prefill_decode_qkv_calculation.md) — compute-bound vs memory-bound 的數學推導
- [SGLang Chunked Prefill — 原理與程式碼實現](../../../sglang/chunked_prefill.md) — SGLang 的不同設計選擇：Prefill 優先、chunk 連續執行、stash 機制支援跨 chunk 字首快取命中

[^1]: vLLM V1 排程器原始碼 [`vllm/v1/core/sched/scheduler.py`](https://github.com/vllm-project/vllm/blob/main/vllm/v1/core/sched/scheduler.py) — `if request.num_computed_tokens == 0:` 守衛條件。後續 chunk 跳過字首快取查詢，直接從上一次中斷處繼續。

[^2]: vLLM PR #7753 ["Enable chunked prefill and prefix caching together"](https://github.com/vllm-project/vllm/pull/7753) — 引入 block 對齊約束（`budget // block_size * block_size`），並要求 `max_num_batched_tokens % block_size == 0`。作者註明此為臨時約束。

[^3]: vLLM 排程器配置 [`vllm/config/scheduler.py`](https://github.com/vllm-project/vllm/blob/main/vllm/config/scheduler.py) — `long_prefill_token_threshold` 預設 0（禁用），`enable_chunked_prefill` 預設 `True`，`max_long_partial_prefills` 預設 1。
