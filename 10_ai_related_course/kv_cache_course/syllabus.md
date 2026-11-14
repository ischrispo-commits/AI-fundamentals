# KV Cache 八講 — 課程總綱

## 基本信息

| 專案        | 內容                                                                                         |
| ----------- | -------------------------------------------------------------------------------------------- |
| 課程名稱    | KV Cache 八講：從 token 賬本到生產引擎                                                       |
| 課時        | 8 講 × 120 分钟                                                                              |
| 授課物件    | 有 Python / PyTorch 基礎、了解 Transformer 基本結構的工程師                                  |
| 先修        | 矩陣乘法、注意力機制、PyTorch 基礎；建議先完成 `ai-infra-course` 模組 5/6；不要求 CUDA / K8s |
| 第 4 講前置 | 了解 vLLM 的基本請求流程和 PagedAttention 概念；沒有用過 vLLM 也能聽，但需要課前補模組 5     |
| 主線        | token 賬 → page/slot 口徑 → request/state 賬 → 引擎與容量                                    |

## 教學目標

- **知識目標**：掌握 KV Cache 的形狀、分頁、複用、分層與混合注意力下的狀態分類。
- **能力目標**：能讀 nano-vllm / vLLM / SGLang 的 KV 路徑，能算 token 池賬與 request state 池賬。
- **素養目標**：每個容量數字都帶“模型變體 + 精度 + 統計範圍”，不把不同代際、不同並行方式的數字混在一起。

## 課程邊界

| 內容                                      | 放在哪里                                           |
| ----------------------------------------- | -------------------------------------------------- |
| Transformer、QKV、prefill/decode 入門     | 第 1 講快速建立；細節參考 `ai-infra-course` 模組 5 |
| vLLM 部署、benchmark、基礎 PagedAttention | 前置材料；第 4 講只讀 KV 生命週期原始碼              |
| LMCache、Mooncake、量化、安全             | 不鋪開；第 5 講解 L3 時提及 Mooncake/HF3FS，LMCache 作為課後延伸 |
| GLM-5.3-Flash / DeepSeek-V4.1-Flash       | 第 6、7 講，只讀 KV 相關程式碼與配置                 |

## 八講安排

第 1–2 講採用 **30 min 概念 + 45 min 原始碼/演示 + 35 min 實驗 + 10 min 答疑**；第 3–4 講採用 **30 min 概念 + 50 min 原始碼/演示 + 30 min 實驗 + 10 min 答疑**；第 5–8 講採用 **30 min 概念 + 40 min 原始碼/演示 + 40 min 實驗 + 10 min 答疑**，原始碼錨點要求課前預讀。各講的詳細時間表、重點難點和參考材料放在對應章節的 `syllabus.md`。

| #   | 主題                                       | 核心問題                                                                    | 章節教學大綱                                                                 |
| --- | ------------------------------------------ | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 1   | KV Cache 為什麼存在                        | decode 為什麼必須快取 K/V，一個 token 的賬怎麼算                            | [01-kv-cache-basics/syllabus.md](01-kv-cache-basics/syllabus.md)             |
| 2   | KV Cache 怎麼放                            | token slot、block、page、block table 怎麼對應                               | [02-kv-cache-layout/syllabus.md](02-kv-cache-layout/syllabus.md)             |
| 3   | KV Cache 在 nano-vllm 裡怎麼實現           | block manager、字首雜湊、ref_count、preempt/swap 怎麼串起來                 | [03-nanovllm-kv-cache/syllabus.md](03-nanovllm-kv-cache/syllabus.md)         |
| 4   | KV Cache 在 vLLM 裡怎麼排程與回收          | `KVCacheManager`、`BlockPool`、字首快取與 nano-vllm 差在哪                  | [04-vllm-kv-cache/syllabus.md](04-vllm-kv-cache/syllabus.md)                 |
| 5   | KV Cache 怎麼複用與分層                    | radix tree 怎麼命中，HiCache 什麼時候換出到 DRAM                            | [05-kv-cache-reuse/syllabus.md](05-kv-cache-reuse/syllabus.md)               |
| 6   | KV Cache 在 GLM-5.3-Flash 裡怎麼變成三本賬 | 45 層文字層裡 34 層 KDA + 11 層 full，token KV、indexer、KDA state 各怎麼存 | [06-glm53-flash-kv-cache/syllabus.md](06-glm53-flash-kv-cache/syllabus.md)   |
| 7   | KV Cache 在 DeepSeek-V4.1-Flash 裡怎麼壓縮 | 890 B/token 的 global KV 和 SWA KV 怎麼分工                                 | [07-deepseek-v41-kv-cache/syllabus.md](07-deepseek-v41-kv-cache/syllabus.md) |
| 8   | KV Cache 怎麼算容量、怎麼選引擎            | token 池賬、request state 池賬與 page/slot 口徑怎麼一起算                   | [08-kv-capacity-planning/syllabus.md](08-kv-capacity-planning/syllabus.md)   |

## 學習產出與支撐章節

| 產出                                     | 支撐章節         | 驗收物                                   |
| ---------------------------------------- | ---------------- | ---------------------------------------- |
| token 池賬（每 token KV + indexer）      | 第 1、2、6、7 講 | 一張帶模型、精度、序列長度和併發的容量表 |
| request state 池賬（KDA state / SWA KV） | 第 6、7、8 講    | 按 request 或 state slot 計的容量表      |
| page/slot 對齊與碎片                     | 第 2、3、4、8 講 | 一個請求的 block table 與內部碎片計算    |
| 引擎對映與選型                           | 第 3–8 講        | nano-vllm / vLLM / SGLang 的類與參數對照 |
| Agent 長會話規劃                         | 第 8 講          | 一頁容量規劃 + 一頁選型理由              |

## 作業地圖

| 編號   | 落點    | 內容                                                         | 計入                    |
| ------ | ------- | ------------------------------------------------------------ | ----------------------- |
| 作業 1 | 第 1 講 | 通用 KV 估算器（Qwen3-0.6B / Qwen2.5-7B，MHA/GQA，FP16/FP8） | 原始碼筆記 30% 的基礎部分 |
| 作業 2 | 第 3 講 | 給 nano-vllm 加 KV 觀察點或簡單驅逐策略                      | 原始碼筆記 30% 的原始碼部分 |
| 作業 3 | 第 8 講 | Agent 長會話容量規劃與引擎選型                               | 結課作業 40%            |

## 考核建議

| 專案     | 權重 | 形式                                                       |
| -------- | ---- | ---------------------------------------------------------- |
| 課堂實驗 | 30%  | 每講一個短實驗，提交截圖、指令碼輸出或結論                   |
| 原始碼筆記 | 30%  | 作業 1 + 作業 2；選一條 KV 路徑，寫清類、池、樹節點和參數  |
| 結課作業 | 40%  | 作業 3：Agent 負載的容量規劃與引擎選型；一頁決策備忘為必做 |

## 課程資料

- [課程 README](README.md)
- [共用實驗環境](lab-environment.md)
- [術語表](glossary.md)
- [AI-fundamentals KV Cache 技術體系](../../09_inference_system/kv_cache/README.md)
- [GLM-5.3-Flash KV 布局](../../09_inference_system/sglang/glm53-flash-kv-layout.md)
- [DeepSeek-V4.1-Flash 精讀](../../09_inference_system/kv_cache/07_kv_compression/06-deepseek-v41-flash.md)
- [nano-vllm](https://github.com/ForceInjection/nano-vllm)
- [vLLM DeepSeek-V4.1-Flash](https://vllm-project.github.io/2026/10/07/deepseek-v41-flash.html)
- [SGLang GLM-5.3-Flash cookbook](https://github.com/sgl-project/sglang/blob/0bcd822377da7b5718e674eaf9c870d349424dd1/docs/cookbook/autoregressive/GLM/GLM-5.3-Flash.mdx)
