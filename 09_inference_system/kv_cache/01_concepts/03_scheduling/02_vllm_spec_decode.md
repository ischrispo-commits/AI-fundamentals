# 投機解碼如何與 KV Cache 交互：Placeholder、回滾與草稿 KV

投機解碼（Speculative Decoding）讓 draft model 一次預測 K 個 token，target model 批次驗證後可能全部接受、部分接受、或全部拒絕。從 KV Cache 的視角看，這個"猜和驗"的過程引入了三個傳統自迴歸解碼中不存在的操作：**為尚未生成的 token 預留 KV 槽位、猜錯後回滾 `num_computed_tokens`、以及處理 draft model 和 target model 兩組不同形狀的 KV**。

本文以 vLLM V1 原始碼為基準，拆解這三個操作在 block 級 KV 管理中的實現細節及其工程代價。

> **前置閱讀**：[投機解碼圖解](../../../model_optimization/illustrated-speculative-decoding.md) — 投機解碼的完整原理、演算法家族與效能模型；[PagedAttention 原理介紹](../01_basic/02_paged_attention.md) — block table 與按需分配。

---

## 一、投機解碼的 KV 寫入：兩次 forward，兩組 KV

### 1.1 標準 decode vs 投機 decode 的 KV 增量

標準自迴歸 decode 每步只生成 1 個 token，KV Cache 追加非常規律：`num_computed_tokens` 每步 +1，block table 每 16 步（block_size=16）追加一個新 block。

投機解碼的每一步則涉及兩次 forward：

```text
Step N:
  Draft forward:  draft model 一次預測 K 個候選 token (如 K=5)
                 → 每個候選 token 都需要參與 attention 計算（讀取 base model 各層的 K 和 V）
                 → drafter 層自身的 KV 寫入獨立的 draft KV cache group（詳見 §1.2）

  Verify forward: target model 批次驗證這 K 個 token
                 → 為每個 token 寫入 target model 的 KV 到 block table
                 → 驗證結果：可能接受前 3 個，拒絕後 2 個
                 → 被拒絕的 token 的 KV 已經寫入了——怎麼處理？
```

一次投機 step 中，target model 的 forward 會產生 K+1 個 token 的 KV 寫入（K 個投機 token + 1 個 bonus token），均透過標準的 block table 路徑儲存。如果 acceptance rate = 80%、K=5，每步淨增約 4 個有效 token 的 target KV——是標準 decode 的 ~4-5 倍。Draft 側還會在獨立的 draft KV cache group 中寫入 drafter 層自身的 KV（詳見 §1.2）；Dual-Model 場景下兩組 KV 的形狀對齊問題見 §4.2。

### 1.2 Self-Speculation：draft 層有獨立的 KV cache group

vLLM 主要支持 Eagle-style self-speculation——draft 和 target 共享同一個 base model，draft head 是一個輕量級附加模組。但"共享 base model"不等於"共享 KV"：**drafter 的 attention 層在 KV cache 佈局中構成獨立的 group**。vLLM 在構建 KV cache 配置時會把 drafter attention 層聚到 `KVCacheGroupSpec.is_eagle_group=True` 的分組（欄位定義見 `vllm/v1/kv_cache_interface.py:1420`，標註邏輯見 `_annotate_eagle_groups`，`vllm/v1/core/kv_cache_utils.py:2162-2218`），它有自己的 block table 和配額。

Draft group 與 target group 的關鍵差異在**生命周期**：draft KV 服務的是"本輪猜測"。`use_eagle_block_drop`（`vllm/config/speculative.py:1942-1944`）預設開啟時，被拒絕的 draft trailing block 會被直接丟棄回收（EAGLE last-block drop，`vllm/v1/core/kv_cache_coordinator.py:105-107`），不會保留到下一輪。因此 draft group 的穩態佔用近似"一輪猜測的 K 個 token × drafter 層數"，遠小於 target 側的全模型 KV，但不是零開銷。

> 本文後續討論聚焦於 Self-Speculation 場景（target KV 即為最終有效 KV），Draft-model-based speculation（兩個獨立模型）的 KV 對齊問題僅在 §4.2 中簡要對比。

---

## 二、Placeholder：為"還沒生成的 token"預留 KV 槽位

### 2.1 問題：非同步排程下的時間差

在 vLLM V1 的非同步排程模式（async scheduling）下，排程器在 GPU 還在執行上一步時就開始準備下一步的 batch。對於投機解碼，這意味著：排程器需要在知道 draft model 會生成多少個 token **之前**，就為這些 token 預留 KV Cache 空間。

### 2.2 `num_output_placeholders` 的機制

vLLM 用一個計數器 `num_output_placeholders` 來表示"當前 step 預期會產生但尚未確認的 token 數"[^1]：

```python
# vllm/v1/core/sched/async_scheduler.py
# 每次排程投機 step 時：
cur_num_spec_tokens = len(spec_decode_tokens.get(req_id, ()))
request.num_output_placeholders += (
    self.num_sampled_tokens_per_step + cur_num_spec_tokens
)
```

`num_output_placeholders` 影響三個關鍵行為：

**Block 分配**：排程器在 `allocate_slots()` 中為 `num_output_placeholders` 預留 block 空間，確保 KV Cache 有足夠的物理頁來容納即將到來的投機 token 的 KV。

**`num_computed_tokens` 的偏移**：在計算 `is_prefill_chunk` 條件時，`num_output_placeholders` 被加到 `num_tokens` 上——排程器把 placeholder 視為"即將計算但尚未完成的 token"，避免請求被錯誤地標記為 prefill 完成狀態：

```python
# vllm/v1/core/sched/scheduler.py
is_prefill_chunk = (
    request.num_computed_tokens
    < request.num_tokens + request.num_output_placeholders
)
```

**排程跳過保護**：非同步排程下，排程器需要判斷"這個請求是否已經不用再排程"。由於 placeholder 計入 computed 計數，判定時要剔除它們——當剔除後已覆蓋全部 prompt 與最大生成長度時，直接跳過排程步，避免為一個必然完成的請求多跑一步：

```python
# vllm/v1/core/sched/scheduler.py:636-640
if (
    request.num_output_placeholders > 0
    and request.num_computed_tokens + 2 - request.num_output_placeholders
    >= request.num_prompt_tokens + request.max_tokens
):
    # 確認上一步已抵達 max_tokens，跳過多餘的排程步
    req_index += 1
    continue
```

### 2.3 Placeholder 與 block 分配的關係

Placeholder 不直接觸發 block 分配——它們是排程器在計算 block 需求時的**預期偏移量**。在 `schedule()` 階段，`num_output_placeholders` 透過影響 `num_computed_tokens` 的計算偏移（見 §2.2 的 `is_prefill_chunk` 判定），間接改變了 `get_num_new_tokens()` 的返回值，進而影響本輪排程中 `allocate_slots()` 請求的 `num_new_tokens` 數量——這是一種間接的預留機制。實際的物理塊分配仍由 `allocate_slots()` 在排程時執行。

---

## 三、回滾：猜錯了怎麼撤銷

### 3.1 回滾的本質：倒退 `num_computed_tokens`

當 target model 驗證發現只有前 A 個投機 token 正確（A < K），后 K-A 個被拒絕時，vLLM 無需"刪除"被拒絕 token 的 KV：**只需將 `num_computed_tokens` 回退到接受點**：

```python
# vllm/v1/core/sched/scheduler.py
# 投機驗證後處理被拒絕的 token：
if request.num_computed_tokens > 0:
    request.num_computed_tokens -= num_rejected  # num_rejected = K - A

# 同步回退 placeholder 計數：
if request.num_output_placeholders > 0:
    request.num_output_placeholders -= num_rejected
```

被拒絕 token 的 KV 資料**仍然物理存在於 block 中**，但 `num_computed_tokens` 的倒退意味着：下一步 decode 時，模型會從接受點繼續計算，新的 KV 會**覆蓋**被拒絕 token 在 block 中的位置。不需要顯式"刪除"——PagedAttention 透過 `num_computed_tokens` 確定哪些位置的 KV 是有效的。

### 3.2 Block 粒度下的"部分回滾"

因為 KV 儲存在 block 中（block_size=16），回滾可能跨越 block 邊界，也可能不跨越：

```text
block_size = 16

回滾前：num_computed_tokens = 1024 (block 64 的第 0 個位置)
  step: draft=5, accepted=2, rejected=3
回滾後：num_computed_tokens = 1021 (block 63 的第 13 個位置)

block 63: [token 1008-1023] — 后 3 個位置的 KV 變為"垃圾資料"
                                下次 decode 到這些位置時會被覆寫
```

**block 本身不會被釋放**——只有整個 block 的所有 token 都被判定為無效時（如 Preemption）才會釋放。投機解碼的回滾只在 token 級別操作 `num_computed_tokens`，block 級別不做任何變動。

### 3.3 Preemption 與飛行中的 stale token

非同步排程引入了更復雜的情況：排程器可能在 GPU 還在執行時就發出了下一步的排程指令。如果此時請求被強制 Preemption（或 `_reset_prefix_cache()` 清空 prefix cache），已經"在飛行中"的投機 token 就變成了 stale data。vLLM 的做法是在 preemption 時直接復位請求狀態（`_preempt_request`，`vllm/v1/core/sched/scheduler.py:1570-1581`）：

```python
# vllm/v1/core/sched/scheduler.py（preemption 路徑，節選）
request.num_stale_output_tokens = request.num_in_flight_tokens  # 在飛 token 記為 stale
request.num_output_placeholders = 0    # placeholder 立即清零，不再期待它們落地
request.drop_stale_output = drop_stale_output  # reset_prefix_cache 等場景傳 True
```

後續 step 收到這批在飛輸出時（`_update_request_with_output`，`vllm/v1/core/sched/async_scheduler.py:51-68`）分三種情況處理：

- stale 輸出仍然送達（保證 spec-decode 的驗收統計不被擾動），但**不再遞減** `num_output_placeholders`——preemption 時它已被清零，再減會下溢；
- `drop_stale_output=True` 時（同 step 內 resume 的 reset 場景），整幀輸出直接丟棄（`scheduler.py:2040-2041`）；
- 只有非 stale 的輸出才走正常的 `cache_blocks()`，把確認後的 token 寫入 prefix cache。

這是 KV Cache 視角下投機解碼最微妙的角落：回滾的物件是排程層的狀態，KV 資料本身留在 block 裡等待覆寫。

---

## 四、草稿模型的 KV：存不存？怎麼存？

### 4.1 Self-Speculation：一層 draft 的短期 KV

Eagle-style self-speculation 下，draft head 是 target model 的一個輕量級附加模組（通常 1 層 decoder）。它的 KV 存放在 §1.2 介紹的獨立 draft KV cache group 中：drafter attention 層有自己的 block table，每輪猜測的 K 個 token 寫入這個 group，驗證後被拒絕的 draft trailing block 由 block-drop 機制回收。

因此 Self-Speculation 的 KV 開銷是 "target 全模型 KV + 一層 draft 的短期 KV"——draft 部分是每輪猜測的 K 個 token 的單層 KV，相對 target 側是小頭。整體 KV 增長與標準 decode 基本持平（每步淨增 A 個有效 token 而非 1 個），不會有雙份全模型儲存的壓力。

### 4.2 Dual-Model Speculation：形狀對齊問題

如果 draft model 和 target model 是獨立的兩個模型（如 LLaMA-3 70B + LLaMA-3 8B），它們的 KV 形狀可能不同：

- **head 數不同**：70B 有 64 Q heads / 8 KV heads，8B 可能只有 32 Q heads / 8 KV heads
- **head_dim 和層數不同**
- **GQA 分組比例不同**

此時 draft KV 和 target KV **不能放入同一個 block pool**——需要獨立的 `KVCacheGroupSpec` 管理（vLLM 中 EAGLE/MTP 的 drafter 層正是以獨立的 KV cache group 組織，見 §1.2）。Draft model 的 KV 通常在一個獨立的小型 block pool 中分配，驗證完成後立即釋放，不跨 step 保留——這與 target model 的 KV 長期保留形成對比。

當前 vLLM V1 的 speculative decoding 以 Self-Speculation 為主路徑：dual-model 的支援透過 Eagle 的 draft head 機制實現——draft head 複用 base model 的 hidden states，其 attention 層的 KV 存放在獨立的 draft KV cache group 中；完整的獨立 draft model（兩個全模型各自持 KV）支援仍在演進中。

---

## 五、與 Prefix Caching 的交互：跨請求命中率低

投機解碼和 Prefix Caching 在 vLLM V1 中可以同時啟用[^2]，兩者並非機制上互斥：token 一旦被確認（驗證透過），其 KV 會走正常的 `cache_blocks()` 路徑進入 prefix cache（`vllm/v1/core/sched/async_scheduler.py:66-68`）。真正的限制是**跨請求命中率低**，而非"無法快取"：

| 維度           |            Prefix Caching             |                 Speculative Decoding                 |
| -------------- | :-----------------------------------: | :--------------------------------------------------: |
| KV 內容確定性  | 相同 token 序列 → 相同 KV → 相同 hash |  投機階段 token 序列未定，驗證確認後才固化入快取     |
| Block 重用方式 |        基於 hash 的跨請求共享         | 確認後的 block 正常入快取，被拒絕部分被覆寫或丟棄    |
| 跨請求命中     |        Prompt 字首命中率高            |      生成段序列因草稿/取樣差異，跨請求命中很少       |

原因在於：投機解碼產生的**生成段** token 序列依賴 draft model 的猜測與取樣隨機性——同一段 prompt，兩次請求生成出的 token 序列通常不同，hash 鏈自然分叉。投機 token 對應的 block 對本請求的 decode 加速有效，但很難被下一個請求複用。而 **Prompt 字首部分（投機開始前）的 KV 照常可以被 prefix cache 複用**。

限制是 **block 級的而非 token 級的**：如果一個 block 全部由投機 token 組成，它的 hash 對跨請求複用意義不大（下次請求很可能走出不同的序列）；如果一個 block 包含部分 prompt token 和部分投機 token，只有 prompt 部分的 hash 是確定性的——當前實現不支援這種 partial block hashing，因此整個 block 都難以跨請求命中。這意味著在多輪對話等 prefix-heavy 場景下，投機解碼 + Prefix Caching 的組合仍然有價值：System Prompt 的 KV 被快取（全部由 prompt token 組成的 block），後續請求的 prompt 字首命中快取，進入 decode 階段後投機解碼加速生成——兩者各司其職。

---

## 六、取舍

### 6.1 三個額外開銷

| 開銷                 | 來源                                          |                量級                 |
| -------------------- | --------------------------------------------- | :---------------------------------: |
| **Placeholder 預留** | `num_output_placeholders` 讓 block 分配更激進 | 每步多預留 K 個 token 的 block 空間 |
| **回滾的垃圾 KV**    | 被拒絕 token 的 KV 暫時佔據 block             |  每步 K-A 個 token，被覆寫前不釋放  |
| **Preemption 復位**  | stale 在飛 token 由 `num_stale_output_tokens`/`drop_stale_output` 處理 |  僅在 Preemption / prefix cache reset 時觸發  |

### 6.2 小結

**投機解碼給 KV Cache 管理引入的核心操作是"先預留、再回滾"——`num_output_placeholders` 在排程層為尚未生成的 token 預留空間，`num_computed_tokens` 的倒退在邏輯層完成回滾，而被拒絕 token 的 KV 在 block 中物理保留直到被覆寫。** 這種"樂觀寫入 + 邏輯回滾"的模式，與標準自迴歸解碼"每步確定性地追加 1 個 token"的簡單性形成了鮮明對比。理解和處理這兩者之間的張力，是在推理引擎中正確整合投機解碼的關鍵。

---

## 相關閱讀

- [投機解碼圖解](../../../model_optimization/illustrated-speculative-decoding.md) — 投機解碼的完整原理、演算法家族與效能模型
- [PagedAttention 原理介紹](../01_basic/02_paged_attention.md) — Block table、按需分配、碎片率
- [vLLM Chunked Prefill 與 KV Cache](01_vllm_chunked_prefill.md) — `num_computed_tokens` 在 Chunked Prefill 中的作用
- [Attention Sinks 與 KV Cache 淘汰策略](../05_eviction/01_attention_sinks_and_eviction.md) — KV Cache 滿了怎麼淘汰

[^1]: vLLM V1 非同步排程器原始碼 [`vllm/v1/core/sched/async_scheduler.py`](https://github.com/vllm-project/vllm/blob/main/vllm/v1/core/sched/async_scheduler.py) — `num_output_placeholders` 在每次排程投機 step 時增加 `num_sampled_tokens_per_step + cur_num_spec_tokens`，在 reject 時減去 `num_rejected`。

[^2]: vLLM V1 排程器 [`vllm/v1/core/sched/scheduler.py`](https://github.com/vllm-project/vllm/blob/main/vllm/v1/core/sched/scheduler.py) — `num_computed_tokens -= num_rejected` 實現回滾；preemption 時 `_preempt_request` 將 `num_output_placeholders` 清零並記錄 `num_stale_output_tokens`（scheduler.py:1570-1581），stale 輸出在 `_update_request_with_output`（async_scheduler.py:51-68）中按 `drop_stale_output` 丟棄或跳過計數。
