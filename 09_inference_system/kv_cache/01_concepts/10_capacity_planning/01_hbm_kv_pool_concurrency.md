# L2 還有大半空著，TTFT 為什麼先崩了？L1 KV Pool 才是系統併發的上限

> 2026-09-29 | 原始碼深讀。基於 SGLang `f4de6abee6`（2026-09-28）與 vLLM `8b365ff949`（2026-09-25）靜態閱讀，行號已核對，未實際壓測。SGLang 與 vLLM 各講一半：容量怎麼記賬、准入怎麼判斷、打滿之後發生什麼，最後回到題目裡的現象。

監控面板上，L2 的曲線一直趴在底部：HiCache 的 host 記憶體（或 LMCache 的 CPU 池）大半空着，命中率看着也不差。按直覺，快取健康、容量富余，服務應該高枕無憂。但 P99 TTFT 已經從 2 秒爬到 40 秒，告警群裡吵成一團。

這類問題的排查方向常常一開始就偏了：大家盯着 L2 找問題，而瓶頸在 L1——HBM 里的 KV Pool。**推理系統的併發容量記在 L1 的賬本上，L2 只記快取的賬。** L1 打滿之後，引擎收緊准入、請求排隊、執行中的請求被整體回退重算，排隊和重算的延遲全部灌進 TTFT；這一切發生時，L2 可以依然是空的。

本文對照 SGLang 與 vLLM 的原始碼把這件事講清楚：併發能力由什麼決定（第一節）、KV Pool 的三態記賬（第二節）、看哪幾個指標確認 L1 瓶頸（第三節）、L1 與 L2 各自管什麼（第四節），最後把現象完整解釋一遍並給出診斷清單（第五節）。

## 一、併發能力由什麼決定

### 1.1 一條先行的物理公式

一個 token 的 KV 佔用在生成時就定死了。MHA/GQA 的賬目：

```text
KV per token = 2 (K 和 V) × layers × kv_heads × head_dim × dtype_bytes
```

以 Llama-3-70B 為例（80 層、GQA 8 個 KV head、head_dim 128、bf16）：2 × 80 × 8 × 128 × 2 = 320 KiB/token。80 GB HBM 扣掉權重、激活和 CUDA 圖預留後，假設 60 GiB 留給 KV Pool，約 19 萬 token；TP8 攤到 8 張卡後約 157 萬 token——32K 上下文約 48 路併發，128K 上下文只剩 12 路。上下文翻倍，併發減半（以上為估算，實際預留比例因部署而異）。

MLA 系好得多：DeepSeek-V3 每層 576 元素的壓縮 latent，61 層 bf16 約 68.6 KiB/token，一個 128K 請求約 9 GB——這也是本站 [dp-attention 篇](../../../sglang/sglang-dp-attention-dcp.md)算過的同一筆賬。

於是有了那條先行的公式：

```text
併發數 ≤ KV Pool 總 token 數 ÷ 平均序列長度（輸入 + 輸出）
```

算力不夠，請求可以慢慢跑；Pool 裝不下，請求是進不來的。KV Pool 是併發容量唯一的硬約束——而它就是 L1。

### 1.2 引擎實際怎麼准入：兩條只認 L1 的預算線

物理公式是天花板，引擎的准入是逐 token 的精細賬。

**vLLM：內聯試探。** v1 的 `schedule()` 每輪按三條線試到裝不下為止：token 預算 `max_num_batched_tokens`、併發條數 `max_num_seqs`（`vllm/v1/core/sched/scheduler.py:577-580,877-879`）、以及逐請求呼叫 `allocate_slots` 分配 block，裝不下返回 None（`scheduler.py:743-767`）。Pool 總量在啟動時由 profile 定出：profiling 算出峰值顯存佔用，剩余部分除以每 block 位元組數得到 `num_gpu_blocks`（`vllm/v1/worker/gpu_worker.py:567-659`、`vllm/v1/engine/core.py:312-337`、`vllm/v1/core/kv_cache_utils.py:1766`），block_size 預設 16（`vllm/config/cache.py:71`）。

**SGLang：預算公式。** 准入走 `PrefillBudget`，核心一行：

```python
# python/sglang/srt/mem_cache/prefill_budget.py:75-84
def _available_and_evictable(self):
    evictable = (self.tree_cache.full_evictable_size() ...)
    return self.allocator.available_size() + evictable

@property
def remaining_total(self):
    return self._available_and_evictable() - self.total_offset
```

`total_offset` 裡每准入一個請求就 `reserve()` 一筆：`reserved = extend_input_len + max_new_tokens + page_size`（`prefill_budget.py:37`）——**給「這個請求將來還要生成多少」預留預算**。預留多少由 `new_token_ratio` 估計：從 0.7 × schedule_conservativeness 起步，隨 decode 步數線性衰減到下限（`managers/scheduler_components/new_token_ratio_tracker.py:22-31`）。起步保守、逐步放寬，发生 retract 時立刻調回高值重新保守。

兩個引擎的准入邏輯完全不同，但有一個共同點：**兩條預算線讀的都是 L1 的計數器**。`allocate_slots` 比的是 `get_num_free_blocks`，`remaining_total` 算的是 `available_size + evictable_size`——L2 有多少空間，在准入公式裡一次都不出現。

## 二、KV Pool 的三態：used、evictable、available

把 Pool 想成一個停車場：**used** 是被執行中請求鎖住的車位；**evictable** 停著已快取的字首，隨時可清走讓位；**available** 是空位。三態之間的遷移，就是兩個引擎記賬的全部內容。

### 2.1 SGLang：樹上的三態

SGLang 用 radix tree 管字首快取，三態在樹上遷移。請求持有一個字首時，路徑上每個節點的 `lock_ref` 加一，加鎖瞬間完成三態遷移：

```python
# python/sglang/srt/mem_cache/radix_cache.py:583-596
def inc_lock_ref(self, node: TreeNode) -> IncLockRefResult:
    ...
    if node.lock_ref == 0:
        self.evictable_size_ -= len(node.key)
        self.protected_size_ += len(node.key)
```

`protected_size` 就是三態裡的 used。賬目合成在 `pool_stats_observer.py:220-230`：

```python
available_size = self.token_to_kv_pool_allocator.available_size()
evictable_size = self.tree_cache.evictable_size()
num_used = self.max_total_num_tokens - (available_size + evictable_size)
token_usage = num_used / self.max_total_num_tokens
```

即 `total = protected + evictable + available`，三項各有一個計數器，直接可查。

逐出是按需的：分配缺口出現時，`evict_to_free_tokens` 算出 `shortfall = 需求 − available`，從 eviction heap 逐葉子節點，正好逐出 shortfall（`mem_cache/allocator/base.py:135-149`、`mem_cache/common.py:188-210`）。**沒有「水位到 90% 開始逐出」的固定水線參數——缺多少，逐多少。**

### 2.2 vLLM：塊上的三態

vLLM 沒有顯式的 evictable 計數器，三態藏在 block 的兩個欄位裡：`ref_cnt`（是否被請求持有）和 `block_hash`（是否已註冊進字首快取雜湊表）。`ref_cnt == 0 ∧ block_hash 非空` 就是 evictable——釋放後進了 `free_block_queue`，但雜湊還在，隨時可以按字首命中複用，也可以在需要時被逐出（`vllm/v1/core/block_pool.py:793-805`）。

釋放路徑上有個巧思：塊**在被持有期間**滿塊時就註冊雜湊（`cache_full_blocks`，`block_pool.py:225-298`），釋放時零操作自動變成 evictable。SGLang 是釋放時才在兩套計數間遷移，vLLM 是提前掛好牌。

free 佇列一個佇列、兩種排序：有雜湊的塊（可逐出的快取）排隊尾，按 FIFO 實現近似 LRU 逐出；無雜湊的塊插隊頭優先複用，照顧 GPU 訪問區域性性（`block_pool.py:793-805`）。

vLLM 還有一個 watermark 參數，語義容易誤會：它是**准入預留**，不是逐出水線。`watermark` 預設 0.0（關閉，`vllm/config/scheduler.py:197-202`）；開啟後只在准入 waiting/preempted 請求時保留 `watermark_blocks` 個空位不分配，避免剛放進來就搶佔、搶佔完又放進的抖動（`vllm/v1/core/kv_cache_manager.py:205-208,506-513`）。舊版 v1 預設 0.01，當前 HEAD 已改為 0.0——對照舊資料時注意版本。

### 2.3 兩邊記賬對照

| 三態         | SGLang                            | vLLM                                          |
| ------------ | --------------------------------- | --------------------------------------------- |
| used（被鎖） | `protected_size_`（lock_ref > 0） | `ref_cnt > 0`，不在 free 佇列                 |
| evictable    | `evictable_size_`（樹上有、無鎖） | free 佇列中 ∧ `block_hash` 非空               |
| available    | `available_size_`（獨立計數）     | free 佇列整體（**含 evictable，無單獨計數**） |

注意最后一行：vLLM 的 free 把 evictable 含在里面，看它的空閒指標要心裡有數——「free」裡一部分是真空閒，另一部分是快取可清。SGLang 把兩者分開報。這也是第三節裡兩家指標口徑差異的根源。

![圖1：KV Pool 的三態與按需逐出](assets/kvpool-01-three-states.png)

**圖 1**｜三態與逐出：used 被執行中請求鎖住；evictable 是已快取可清的字首；available 是空位。分配缺口出現時按需逐出——缺多少逐多少，沒有固定水線。SGLang 三個計數分開報，vLLM 的 free 指標把 evictable 含在里面。

## 三、觀測 KV Pool 的幾個指標

兩個引擎的指標各成一族，按「容量賬」與「快取賬」分兩組看。

**SGLang**（Prometheus `sglang:*`，`observability/metrics_collector.py`；日誌行預設每 40 個 decode step 打一條，`arg_groups/fields/observability.py:136-139`）：

| 指標                                         | 口徑                                    | 出處                             |
| -------------------------------------------- | --------------------------------------- | -------------------------------- |
| `sglang:token_usage`                         | (total − available − evictable) / total | `pool_stats_observer.py:220-230` |
| `sglang:num_running_reqs` / `num_queue_reqs` | 執行中 / 排隊中                         | `metrics_collector.py:281-287`   |
| `sglang:cache_hit_rate`                      | 命中 token /（命中 + 新算）             | `metrics_reporter.py:786-792`    |
| `sglang:num_retracted_reqs_total`            | retract 累計數                          | `metrics_collector.py:469-486`   |

**vLLM**（Prometheus `vllm:*`，`vllm/v1/metrics/loggers.py`）：

| 指標                                                 | 口徑                                             | 出處                    |
| ---------------------------------------------------- | ------------------------------------------------ | ----------------------- |
| `vllm:kv_cache_usage_perc`                           | 1 − free/(num_gpu_blocks − 1)，分母減 null block | `block_pool.py:879-890` |
| `vllm:num_requests_running` / `num_requests_waiting` | 執行中 / 排隊中                                  | `loggers.py:509-519`    |
| `vllm:num_preemptions`                               | 搶佔累計（另有每請求直方圖）                     | `loggers.py:677,902`    |
| `vllm:prefix_cache_queries/hits`                     | 本地（L1）字首命中                               | `loggers.py:600-611`    |
| `vllm:external_prefix_cache_queries/hits`            | connector/L2 命中                                | `loggers.py:624-636`    |

兩組指標的用法不同。**容量組**（token_usage、kv_cache_usage_perc、queue、retracted/preemptions）回答「Pool 裝不裝得下」；**快取組**（cache_hit_rate、prefix_cache_hits）只回答「prefill 省了多少計算」。診斷「L2 空着 TTFT 崩」看容量組就夠了：usage 貼 1、waiting 堆積、retract/preempt 計數增長，三條同時出現就是 L1 瓶頸，不必再懷疑快取。vLLM 的 `external_prefix_cache_hits` 還順帶告訴你 L2 命中了多少——它是快取組的指標，跟 P99 長尾對不上號。

## 四、L1 與 L2 的關係

分層的官方定義在 HiCache 設計文件裡：L1 是 GPU 顯存（HBM），L2 是 host 記憶體（CPU DRAM），L3 是分散式儲存（`docs/docs/advanced_features/hicache_design.mdx:12`）。vLLM 側對應的機制是 KVConnector 體系裡的 offloading：`OffloadingConnector`、`SimpleCPUOffloadConnector`、`LMCacheConnectorV1`（`vllm/distributed/kv_transfer/kv_connector/v1/`）。

### 4.1 L2 幫 L1 的方式：讓逐出不丟快取

SGLang HiCache 在 write_back 策略下，逐出變成**降級（demote）**：先把該節點備份到 L2，再釋放 L1 槽位（`mem_cache/unified_cache/unified_tree_core.py:1610-1643`）。沒有 L2 時，逐出意味著快取作廢，字首再來要整段重算；有了 L2，`available` 變現回來了，快取還在 host 里躺着。`--hicache-ratio` 預設 2.0（`arg_groups/hicache_hook.py:100-103`）。

要點：**備份不佔 L1 的記賬。** L2 空間的大小不會讓 L1 的 `available_size` 變大或變小——L2 改變的只是「evictable 變現成 available 時，快取丟不丟」。

### 4.2 L2 命中回 GPU：先占 L1，才能回

兩個引擎在這一點上姿勢一致，而且都有點反直覺。

SGLang 在准入時發起 `init_load_back`，承諾的 host 命中長度必須全部提交或全部不認（`managers/schedule_policy.py:1400-1418`）；回載前先看 L1 的 available，不夠就先 `evict_for_alloc` 騰位，**還騰不出就放棄回載，寧可重算**（`mem_cache/unified_radix_cache.py:1784-1791`）。H→D 複製在 prefill 前完成，有顯式同步點。

vLLM 更直白：GPU blocks 在傳輸開始前就分配並持有（`scheduler.py:1214-1226` 的 `delay_cache_blocks` 路徑），還為在飛的 prefill 追加 `reserved_blocks` 保護（`:1199-1209`）——L2 命中的請求在等 KV 搬回來時，它占的 L1 車位是鎖著的。

所以結論要倒過來說：**L2 命中消耗 L1 容量，而不是擴容。** 「L2 擴展了 KV 容量」只在快取語義上成立（字首可備份、不丟失）；在併發語義上不成立——沒有任何一條准入路徑會去讀 L2 的計數器。

v1 還順手封死了一條歧路：v0 曾有 swap 機制（把執行中請求的 KV 換出到 CPU 騰 L1），v1 主線排程器裡沒有它的繼任者——通用的「L1 換出再換回、變相擴容准入」不存在，僅稀疏注意力 hisparse 有專用的 GPU/host 分層，屬於特性而非通用機制。SGLang 側 retract 時可以把被回退請求的 KV offload 到 host（`retract_decode` 的 `release_req` 支持），但那是請求退出後的快取備份，不是執行中的換頁。

![圖2：L1/L2 的分工與資料流](assets/kvpool-02-l1l2-flow.png)

**圖 2**｜L1/L2 分工：逐出在 write_back 下變成「備份到 L2、釋放 L1」的降級；L2 命中回 GPU 前要先占 L1 槽位，騰不出寧可重算。准入公式從頭到尾只讀 L1 的計數器——L2 決定命中率，L1 決定併發上限。

## 五、回到現象：把時間線串起來

1. **流量上來，L1 爬向滿。** token_usage / kv_cache_usage_perc 逐級抬升。此刻 L2 依然空着——demote 還沒發生幾次，或者 `hicache_ratio` 給的 L1 本來就寬裕。
2. **引擎收緊准入。** SGLang 的 `remaining_total` 不足，`budget_state()` 返回 `NO_TOKEN`（`managers/schedule_policy.py:850-869`），新請求堆進 waiting；`new_token_ratio` 一路衰減，預算越算越保守。vLLM 的 waiting 請求每輪在 `schedule()` 裡試探 `allocate_slots`，裝不下就繼續等。
3. **高水位下連 decode 都裝不下。** SGLang 的 `check_decode_capacity` 先逐快取，逐完還不夠，觸發 `retract_decode`（`managers/scheduler.py:4200-4201`、`managers/schedule_batch.py:3272-3379`）：從執行批次裡挑請求、釋放其全部 KV、回 waiting 重新排隊，日志打出 `KV cache pool is full. Retract requests. #retracted_reqs: ...`。vLLM 的對應動作是搶佔：`_preempt_request` 釋放 block、`num_computed_tokens` 清零、請求插回 waiting **隊首**，從 token 0 重新 prefill（`scheduler.py:1557-1581`）。
4. **這些延遲全部落進 TTFT。** 排隊的請求在等准入；被 retract/preempt 的請求在重算 prefill——后者更冤，它可能已經開始生成，被拉回去從頭再來。P99 的長尾就是這批請求：均值被快取命中保護著，P99 被高水位的排隊與回退拖著。
5. **全程 L2 空着。** 它空着不是故障，是結構性無關：准入公式裡沒有它的變數。

![圖3：L1 打滿後的請求生命週期](assets/kvpool-03-lifecycle.png)

**圖 3**｜L1 打滿之後：新請求在 waiting 里等准入，執行中的請求被 retract/preempt、釋放全部 KV 後從頭重新 prefill——排隊與重算的時間都灌進 TTFT，P99 的長尾就是這批請求。

L2 什麼時候才派上用場：多輪對話、長 system prompt、Agent 迴圈這類共享字首比例高的負載。L2 命中省掉 prefill 計算，TTFT 均值與吞吐受益；但一批互不共享字首的新請求打進來，L1 該滿還是滿。

### 診斷清單

P99 TTFT 異常時，按序看：

1. **容量組三件套**：token_usage / kv_cache_usage_perc 是否長期貼 1；num_queue_reqs / num_requests_waiting 是否堆積；num_retracted_reqs_total / num_preemptions 是否增長。三條同時成立即 L1 瓶頸。
2. **快取組對照**：cache_hit_rate / prefix_cache_hits 高而 P99 差，坐實是併發賬問題，不是快取賬問題——排查方向轉向准入參數（`mem_fraction_static`、`max_running_requests` / `max_num_seqs`）與每 token KV 體積。
3. **處方三條**：降每 token 體積（KV 量化、壓縮、MLA、稀疏注意力）；加 L1（TP/DP/DCP 攤大池子，見本站[並行策略](../../../parallelism/parallelism_strategies.md)與 [dp-attention 篇](../../../sglang/sglang-dp-attention-dcp.md)）；或承認上限、做准入控制（限流排隊）。L2 / HiCache / LMCache 只解決命中率，別拿它救 P99。

## 說明

- 全部結論來自靜態原始碼閱讀（行號以上述 commit 為準），未實際壓測；第五節的時間線是機制推演，具體延遲量級取決於負載與硬體；
- vLLM `watermark` 預設 0.0 是 `8b365ff949` 的行為，舊版 v1 為 0.01，升級對照舊資料時注意；
- SWA/hybrid 池的 full/swa 雙側記賬、vLLM hisparse 的專用分層屬於支線，本文未展開；
- 1.1 節的併發數字為估算，實際預留比例隨部署（CUDA 圖、激活峰值）浮動；
- SGLang 逐出策略（eviction heap）支持 LRU/LFU 等多種 strategy，本文只描述「按需逐出」的觸發機制，不展開策略選擇。

## 源文件索引

SGLang（`f4de6abee6`，路徑省略 `python/sglang/srt/` 字首）：

- `mem_cache/prefill_budget.py` — 准入預算：`_available_and_evictable`（:75）、`remaining_total`（:84）、reserved 公式（:37）
- `mem_cache/radix_cache.py` — `inc_lock_ref`/`dec_lock_ref` 三態遷移（:583-616）
- `mem_cache/allocator/base.py`、`mem_cache/common.py` — 按需逐出 `evict_to_free_tokens`（:135-149）、`_evict_until_allocatable`（:188-210）
- `managers/scheduler_components/pool_stats_observer.py` — 三態合成與 token_usage 公式（:220-230）
- `managers/scheduler_components/new_token_ratio_tracker.py` — 預估係數起步與衰減（:22-31）
- `managers/scheduler.py`、`managers/schedule_batch.py` — retract 觸發（:4200-4201）、`retract_decode`/`release_req`（:3272-3379）
- `managers/schedule_policy.py` — `budget_state`（:850-869）、`init_load_back` 准入回載（:1400-1418）
- `mem_cache/unified_radix_cache.py`、`mem_cache/unified_cache/unified_tree_core.py` — demote（:1610-1643）、回載放行判據（:1784-1791）
- `observability/metrics_collector.py`、`managers/scheduler_components/metrics_reporter.py` — 指標定義與日誌行
- `arg_groups/hicache_hook.py` — hicache_ratio 預設值（:100-103）
- `docs/docs/advanced_features/hicache_design.mdx` — L1/L2/L3 官方定義（:12）

vLLM（`8b365ff949`）：

- `vllm/v1/core/kv_cache_utils.py` — block 數推導（:1766）、`KVCacheBlock` 字段（:177-193）
- `vllm/v1/core/block_pool.py` — free 佇列與雜湊表（:174-180）、cache_full_blocks（:225-298）、雙端複用（:793-805）、usage 公式（:879-890）
- `vllm/v1/core/kv_cache_manager.py` — watermark 計算（:205-208）與准入應用（:506-570）
- `vllm/v1/core/sched/scheduler.py` — 三條准入線（:577-580,877-879）、`allocate_slots`（:743）、搶佔（:1557-1581）、L2 回載預佔（:1199-1226）
- `vllm/config/cache.py`、`vllm/config/scheduler.py` — block_size 預設 16（:71）、watermark 預設 0.0（:197-202）
- `vllm/v1/metrics/loggers.py` — 全部 Prometheus 指標定義
- `vllm/v1/worker/gpu_worker.py`、`vllm/v1/engine/core.py` — profile 推導 num_gpu_blocks（:567-659、:312-337）
- `vllm/distributed/kv_transfer/kv_connector/v1/` — `offloading_connector.py`、`simple_cpu_offload_connector.py`、`lmcache_connector.py`

## 參考資料

- [SGLang](https://github.com/sgl-project/sglang) 倉庫，commit `f4de6abee6`（2026-09-28）
- [vLLM](https://github.com/vllm-project/vllm) 倉庫，commit `8b365ff949`（2026-09-25）
- 本站 [SGLang KV Pool 管理：物理儲存、Radix Tree 索引與請求檢視](../../../sglang/sglang-kv-pool-management.md)——本文第二節的展開版：物理儲存、lock_ref、分配器與 page
- 本站 [七池與八池：HiCache 支持 DeepSeek V4 與 V4.1 的不同接法](../../../kv_cache/07_kv_compression/07-multilevel-cache.md)——HiCache 池形態與讀寫的進一步拆解
- 本站 [GLM-5 模型 KV Cache 容量規劃報告](03_glm5_kv_cache_capacity_planning.md)、[KV Cache ROI](02_kv_cache_roi.md)——容量測算的業務側方法
- 本站 [MoE 與百萬上下文：請求怎麼分卡，長文怎麼切](../../../sglang/sglang-dp-attention-dcp.md)——「加 L1」路線裡 DCP 的機制篇
- 本站 [PagedAttention](../01_basic/02_paged_attention.md)、[KV Cache 基礎](../01_basic/01_kv_cache_basics.md)——block 化與 KV 基礎概念
