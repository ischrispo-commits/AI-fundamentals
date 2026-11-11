# 約束解碼的效能賬單：vLLM 與 SGLang 的結構化輸出實現拆解

> Agent 的每一次工具呼叫都要求模型輸出合法 JSON。結構化輸出（structured output）用「schema 編譯成 FSM，每步取樣前遮蔽非法 token」保證這一點，xgrammar 論文把它做到「near-zero overhead」。本文不討論原理本身，只回答一個工程問題：這套機制在 vLLM 和 SGLang 裡怎麼落地，開銷發生在哪幾步，哪些坑在生產裡會撞上。
>
> 2026-09 | 基於 vLLM（`43d691ec6b`，2026-08-07）與 SGLang（`f7101b0ae6`，2026-08-18）原始碼驗證
>
> **性質說明**：機制與行為均經原始碼驗證；涉及耗時/位元組數的數字為量級示意，實測項見文末（擬基於 [InferenceX](https://github.com/SemiAnalysisAI/InferenceX) 壓測方法執行）。

---

## 一、從可選到必選

Chat 時代，結構化輸出是個錦上添花的功能：輸出格式歪了，人看得懂就行。Agent 時代它變成硬約束：一次工具呼叫要過 JSON 解析器，輸出缺個引號，工具執行失敗，Agent 重試，流量翻倍。AgentSysBench 的測量顯示工具定義與系統指令最高占上下文視窗的 84.3%（見 [Agent 負載一篇](agent-workload-serving.md)），與之對應，輸出側的合法性靠的就是本文的主角：約束解碼（constrained decoding）。

兩引擎的預設後端都是 xgrammar（SGLang 的 `grammar_backend` 缺省 None，`_handle_grammar_backend` 將其解析為 `"xgrammar"`；vLLM 的 V1 結構化輸出以 xgrammar 為首選後端，另備 outlines/guidance/lm_format_enforcer）。下文所有機制均以 xgrammar 後端為準，版本號見文首。

## 二、三筆賬單

### 2.1 編譯賬（落在 TTFT 上）

請求到達時，引擎要把 JSON schema（或正則、EBNF）編譯成可執行的語法物件。編譯發生在請求生命週期內：vLLM 在 `grammar_init`（`v1/structured_output/__init__.py:114`）觸發 `backend.compile_grammar`（`backend_xgrammar.py:78`）；SGLang 在 `GrammarManager.process_req_with_grammar`（`constrained/grammar_manager.py:131`）里初始化。

編譯不是免費的。schema 越大越複雜，編譯耗時越長（大 schema 數十到數百毫秒，量級示意）。冷啟動的服務收到第一批請求時，這層延遲直接加在 TTFT 上。兩引擎都用「編譯快取」緩解：同樣的 schema 第二次請求直接命中。快取鍵就是 SGLang 的 grammar key 與 vLLM 的 `structured_output_key`（`request.py:82`，請求類型 + 語法規格）。對 Agent 場景這是個好訊息：工具 schema 在部署期基本不變，編譯快取命中率高。

### 2.2 每步賬（落在吞吐上）

decode 的每一步，引擎要為當前 batch 生成 token bitmask，形狀約 `[max_num_seqs, vocab_size/32]` 的 int32。以 Qwen2.5 的 15 萬級詞表算，每個序列約 19KB，batch 64 時一步約 1.2MB（量級示意）。開銷分四段：分配、CPU 填充、H2D 複製、logits 屏蔽。

兩引擎都做了短路：vLLM 排程器用 `has_structured_output_requests` 標誌跳過無約束 batch 的整段邏輯（`v1/core/sched/scheduler.py:1347`），且 prefill chunk 不參與（`not request.is_prefill_chunk`）；SGLang 只對帶 grammar 的請求填充。真正要留意的是混合場景：batch 裡只要有一個約束請求，那一步就要走完整的分配-填充-複製鏈路。

### 2.3 互動賬（組合稅）

約束解碼不單獨存在，和三個熱門特性疊加時各有故事：投機解碼要在驗證後回滾 FSM 狀態（SGLang 的 `rollback(k)`，`xgrammar_backend.py:107`）；reasoning 模型要先自由思考、到輸出段才施加約束（vLLM 的 `trim_reasoning_for_advance`，`__init__.py:462`；SGLang 有 `ReasonerGrammarBackend` 和 thinking budget 聯動，`grammar_manager.py:124`）；PD/PP 分離下編譯狀態要跨行程同步（SGLang 的 `_drain_pp_sync_work`，`grammar_manager.py:72`）。

## 三、雙引擎實現

### 3.1 vLLM：單例管理器 + 請求狀態機

vLLM V1 的結構化輸出由 `StructuredOutputManager`（`__init__.py:35`）單例驅動，每個請求掛一個 `StructuredOutputRequest`（`request.py:22`）狀態機。流程：

1. 請求進入時 `grammar_init` 觸發編譯，狀態機用 `is_grammar_ready`（`request.py:62`）暴露就緒位，編譯快取鍵 `structured_output_key` 命中時立即可用；
2. decode 迴圈中排程器呼叫 `get_grammar_bitmask`（`scheduler.py:1655`），Manager 的 `grammar_bitmask`（`__init__.py:212`）彙總各請求的 mask；
3. 填充是非同步的：`_async_submit_fill_bitmask`（:207）把 CPU 側填充提交出去，與 GPU 前向重疊；
4. `should_fill_bitmask`（:361）與 `should_advance`（:381）分別門控「這步要不要遮蔽」「FSM 要不要推進」。

reasoning 整合的位置很講究：`_find_reasoning_end_index`（:442）先定位思考段結束點，`</think>` 之前的 token 不進 FSM，思考結束後約束才接管。

### 3.2 SGLang：語法佇列 + 跳出重分詞

SGLang 把這套邏輯做成顯式的 `GrammarManager`（`grammar_manager.py:26`），最大的特點是**把「編譯未完成」當作排程層的頭等狀態**：

- 語法沒就緒的請求進 waiting grammars 佇列（`has_waiting_grammars`，:69），不進 batch，避免讓已排隊的請求空等；
- 編譯走 future 模式（`get_cached_or_future_value`，經 `process_req_with_grammar` :153 使用）：首次提交非同步編譯，第二次同 schema 請求直接命中快取；編譯失敗的 schema 也會被快取（:164），防止反覆撞牆；
- 會話結束後 `set_cache`（:286）把語法回寫快取。

跳出最佳化（jump-forward）是 SGLang 的獨門：`try_jump_forward`（`xgrammar_backend.py:164`）探測 FSM 當前狀態下的確定性字串段，`jump_and_retokenize`（:174）把這整段一次生成、按原文重分詞後同步 FSM，跳過逐 token 的 mask 與步進。outlines 後端有對應的 `outlines_jump_forward.py`。vLLM 側只有一處註釋提到 `find_jump_forward_string` 的文件連結（`backend_xgrammar.py:141`），實現未見。

### 3.3 逐項對照

| 維度           | vLLM                                                | SGLang                                                        |
| -------------- | --------------------------------------------------- | ------------------------------------------------------------- |
| 后端集合       | xgrammar / outlines / guidance / lm_format_enforcer | xgrammar / outlines / llguidance / none                       |
| 預設           | xgrammar 優先                                       | None → xgrammar（`server_args.py` `_handle_grammar_backend`） |
| 編譯快取鍵     | `structured_output_key`（request 級）               | grammar key（manager 級，含無效快取）                         |
| 未就緒處理     | 請求狀態位門控（`is_grammar_ready`）                | 顯式 waiting 佇列，不進 batch                                 |
| bitmask 填充   | 非同步提交（`_async_submit_fill_bitmask`）            | 按請求填充                                                    |
| 跳出重分詞     | 無實現（僅註釋）                                    | `try_jump_forward` + `jump_and_retokenize`                    |
| 投機解碼       | 經 `should_advance` 狀態推進                        | `rollback(k)` 顯式回滾                                        |
| reasoning 集成 | `trim_reasoning_for_advance`                        | `ReasonerGrammarBackend` + thinking budget                    |
| PP/PD 同步     | —                                                   | `_drain_pp_sync_work`                                         |

## 四、三個權衡

**編譯等待 vs 排隊**。編譯期間請求怎麼辦？SGLang 選擇顯式排隊，代價是隊頭編譯慢時後面整隊等待，好處是 batch 裡永遠不會有一個「語法沒準備好」的請求白白佔位。vLLM 的狀態位門控粒度更細，但應用側要自己面對「首 token 到底什麼時候來」的方差。兩者沒有對錯，監控指標不同：前者看佇列深度，后者看 ready 位翻轉時間。

**跳出重分詞的收益與風險**。JSON 輸出裡有大量確定性片段（鍵名、引號、括號），jump-forward 把它們一次吐出，省掉的是逐 token 的 mask 計算和 FSM 步進。代價是重分詞：跳出的字串要按分詞器重新切，切分邊界若與 FSM 期望不一致，需要回退處理。這正是 XGrammar 論文（arXiv:2411.15100）里 adaptive token mask 思想的工程延續，SGLang 把它接進了排程迴圈。

**全量 vs 惰性**。mask 的開銷與 batch 大小成正比，兩引擎都選擇「只對約束請求填充」，但短路粒度不同：vLLM 在排程器入口用 `has_structured_output_requests` 一次短路整個 batch，SGLang 按請求逐個判斷。對全無約束的純 Chat 流量，兩者開銷都趨近於零；對全約束的 Agent 流量，這層最佳化幫不了你，賬單得照付。

## 五、待實測項與生產建議

實測（擬基於 [InferenceX](https://github.com/SemiAnalysisAI/InferenceX) 開源壓測方法執行，跑完補數）：

1. 冷/熱編譯快取的首 token 延遲差（同一大 schema，服務重啟 vs 連續請求）；
2. 約束開/關的吞吐差（Qwen2.5-7B，同一 trace）；
3. 混布半徑：batch 64 中僅 1 個約束請求時，其余 63 個請求的 TPOT 損失。

生產建議（原始碼現狀推論，未經實測）：

- **schema 複用優先**：工具 schema 部署期固定，編譯快取命中率天然高；避免在執行期拼接動態 schema（比如把使用者 ID 拼進 enum），那會打穿快取；
- **監控編譯佇列**：SGLang 看 waiting grammars 深度，vLLM 看 ready 位翻轉時長；佇列堆積說明 schema 太複雜或併發太高；
- **大 schema 拆解**：列舉值越全、嵌套越深，編譯越慢；把不穩定部分移到輸出後校驗，比硬塞進 schema 便宜。

值得一提的是，XGrammar 團隊已經把「Agentic 場景的動態結構化生成」做成了獨立方向（XGrammar-2，ACM 2026）——約束解碼正在從「一個功能」長成「一個子系統」，值得持續觀察。

---

## 源文件索引

| 文件                                                | 關鍵符號                                                                                                                 | 引用點                              |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| `vllm/v1/structured_output/__init__.py`             | `StructuredOutputManager`、`grammar_init`、`grammar_bitmask`、`_async_submit_fill_bitmask`、`trim_reasoning_for_advance` | :35、:114、:212、:207、:462         |
| `vllm/v1/structured_output/request.py`              | `StructuredOutputRequest`、`is_grammar_ready`、`structured_output_key`                                                   | :22、:62、:82                       |
| `vllm/v1/structured_output/backend_xgrammar.py`     | `compile_grammar`、`allocate_token_bitmask`                                                                              | :78、:128（jump-forward 註釋 :141） |
| `vllm/sampling_params.py`                           | `StructuredOutputsParams`                                                                                                | :72                                 |
| `vllm/v1/core/sched/scheduler.py`                   | `get_grammar_bitmask`、`has_structured_output_requests`                                                                  | :1655、:1347                        |
| `python/sglang/srt/constrained/grammar_manager.py`  | `GrammarManager`、`has_waiting_grammars`、`process_req_with_grammar`、`set_cache`                                        | :26、:69、:131、:286                |
| `python/sglang/srt/constrained/xgrammar_backend.py` | `XGrammarGrammarBackend`、`try_jump_forward`、`jump_and_retokenize`、`rollback`                                          | :208、:164、:174、:107              |
| `python/sglang/srt/server_args.py`                  | `GRAMMAR_BACKEND_CHOICES`、`grammar_backend`、`_handle_grammar_backend`                                                  | :245、:1734                         |

_版本：vLLM `43d691ec6b`（2026-08-07）、SGLang `f7101b0ae6`（2026-08-18）。bitmask 位元組數與編譯耗時為量級示意。_

## 參考資料

- [XGrammar: Flexible and Efficient Structured Generation Engine for Large Language Models](https://arxiv.org/abs/2411.15100), arXiv:2411.15100——本文預設後端的原理出處
- [XGrammar-2: Dynamic and Efficient Structured Generation Engine for Agentic LLMs](https://dl.acm.org/doi/10.1145/3786335.3813124), ACM 2026——面向 Agent 動態 schema 的後續工作
- [mlc-ai/xgrammar](https://github.com/mlc-ai/xgrammar)——開源實現
