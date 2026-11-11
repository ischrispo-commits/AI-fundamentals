# 大模型 API 定價策略定量分析框架

本文基於 OpenRouter 聚合平台的動態定價資料，提供一套針對主流大模型（如 OpenAI、Anthropic、Google、DeepSeek 等）API 的定量成本測算與商業分析框架。

## 快速使用：執行測算指令碼

本文提供了一個配套的 Python 指令碼 `fetch_pricing.py`，用於動態獲取並計算最新價格。該指令碼無需安裝任何第三方依賴（僅使用 Python 3 標準庫）。

```bash
# 在終端中執行指令碼，使用預設參數
python fetch_pricing.py

# 調整匯率。指令碼僅提供 --exchange-rate 與 --no-cache 兩個命令列參數；
# 快取命中率與輸入/輸出 token 數為指令碼內建的場景參數（場景 A/B/C），如需調整需修改指令碼原始碼
python fetch_pricing.py --exchange-rate 7.25

# 強制忽略本地快取，從伺服器拉取最新資料
python fetch_pricing.py --no-cache
```

---

## 1. 核心模型分類與資料採集機制

透過標準化分類矩陣對市場主流模型進行分級，結合聚合平台提供的實時 API 接口，構建動態、可靠的價格獲取鏈路。此結構直接對映 `fetch_pricing.py` 中的 `CATEGORIES` 配置，確保文件分析與程式碼邏輯一致。

### 1.1 主流大模型分級矩陣

大語言模型市場（以 2026-04 快照為觀察時點）呈現明顯的梯隊化分佈。基於模型能力與目標場景，可劃分為旗艦、經濟、推理等核心層級，涵蓋國際與國內頭部廠商。

- **OpenAI 體系**：涵蓋 `gpt_flagship` (GPT 旗艦)、`gpt_mini` (GPT 經濟型)，以及專注於深度邏輯的 `o_series` (高階推理) 和 `o_mini` (輕量推理)。
- **Anthropic 體系**：包含 `claude_opus` (頂級旗艦)、`claude_sonnet` (均衡旗艦) 與 `claude_haiku` (經濟型)，滿足不同響應速度與成本要求。
- **Google 體系**：由 `gemini_pro` (專業旗艦)、`gemini_flash` (均衡速度) 及 `gemini_flash_lite` (極致輕量) 構成多模態生態。
- **國核心心梯隊**：以 `deepseek_chat` (常規互動) 和 `deepseek_reasoner` (R1 邏輯推理) 為代表的低成本高智商模型，以及阿里的 `qwen_max` (通義旗艦) 和 `qwen_plus` (通義均衡)。
- **開源旗艦生態**：Meta 发布的 `llama_70b`，為私有化部署及高併發場景提供極具價效比的基準。

### 1.2 定價資料動態採集方案

傳統依賴手動查閱各廠商官網定價頁面的方式難以應對頻繁的價格調整。本框架採用基於 OpenRouter 統一介面的動態拉取策略。

- **資料來源**：聚合接口 `https://openrouter.ai/api/v1/models` 提供全量模型最新報價。
- **版本發現引擎**：配套指令碼使用正規表示式 `\d+\.\d+|\d+` 動態提取版本號元組，並結合 `include`/`exclude` 規則過濾出指定分類的最新穩定或可用預覽版本，無需人工干預即可抵禦版本更迭（如 GPT-4.1 至 GPT-5.4）。
- **匯率轉換機制**：指令碼內建示例固定匯率常數（如取 USD to CNY = 6.9，實際使用中應根據當前真實匯率動態調整），自動將美元計價放大轉換為“元/百萬 Token”。

---

## 2. 使用者視角：API 呼叫成本定量分析

構建業務場景下的實際開銷評估模型，將抽象的 Token 單價轉化為具象的單次互動成本與月度預算。

### 2.1 主流大模型 API 定價與計費維度

下表展示了 2026-04-15 OpenRouter 快照時點主流模型的基準定價，為歷史口徑。資料由配套指令碼 `fetch_pricing.py` 動態生成，模型版本和價格隨廠商策略實時波動，請以指令碼最新輸出與各官方 pricing 頁為準。

> **口徑說明**：表 1 與表 2 的價格截至 2026-04-15（OpenRouter 快照），為歷史口徑；2026-11 現價已有變化（Claude 4.8 / Sonnet 5.5、GPT-5.5、DeepSeek V4.1），請以各官方 pricing 頁為準。

**表 1：API 基礎定價表**：

| 模型名稱（快照時點版本）          | API ID                                 | 輸入單價 (¥/M) | 快取讀 (¥/M) | 快取寫 (¥/M) | 輸出單價 (¥/M) | 聯網搜尋 (¥/次) |
| :-------------------------------- | :------------------------------------- | :------------- | :----------- | :----------- | :------------- | :-------------- |
| **GPT 旗艦 (v5.4)**               | `openai/gpt-5.4`                       | 17.2500        | 1.7250       | -            | 103.5000       | 0.0690          |
| **GPT 經濟型 (v5.4)**             | `openai/gpt-5.4-mini`                  | 5.1750         | 0.5175       | -            | 31.0500        | 0.0690          |
| **OpenAI O系列 高階推理 (v3)**    | `openai/o3`                            | 13.8000        | 3.4500       | -            | 55.2000        | 0.0690          |
| **OpenAI O系列 輕量推理 (v4)**    | `openai/o4-mini`                       | 7.5900         | 1.8975       | -            | 30.3600        | 0.0690          |
| **Claude Opus 頂級旗艦 (v4.6)**   | `anthropic/claude-opus-4.6`            | 34.5000        | 3.4500       | 43.1250      | 172.5000       | 0.0690          |
| **Claude Sonnet 均衡旗艦 (v4.6)** | `anthropic/claude-sonnet-4.6`          | 20.7000        | 2.0700       | 25.8750      | 103.5000       | 0.0690          |
| **Claude Haiku 經濟型 (v4.5)**    | `anthropic/claude-haiku-4.5`           | 6.9000         | 0.6900       | 8.6250       | 34.5000        | 0.0690          |
| **Gemini Pro (v3.1)**             | `google/gemini-3.1-pro-preview`        | 13.8000        | 1.3800       | 2.5875       | 82.8000        | -               |
| **Gemini Flash (v3)**             | `google/gemini-3-flash-preview`        | 3.4500         | 0.3450       | 0.5750       | 20.7000        | -               |
| **Gemini Flash-Lite (v3.1)**      | `google/gemini-3.1-flash-lite-preview` | 1.7250         | 0.1725       | 0.5750       | 10.3500        | -               |
| **DeepSeek Chat (latest)**        | `deepseek/deepseek-chat-v3.1`          | 1.0350         | -            | -            | 5.1750         | -               |
| **DeepSeek Reasoner (R1)**        | `deepseek/deepseek-r1-0528`            | 3.4500         | 2.4150       | -            | 14.8350        | -               |
| **Qwen Max 通義旗艦 (v3)**        | `qwen/qwen3-max`                       | 5.3820         | 1.0764       | -            | 26.9100        | -               |
| **Qwen Plus 通義均衡 (v3.6)**     | `qwen/qwen3.6-plus`                    | 2.2425         | -            | -            | 13.4550        | -               |
| **Llama 70B 開源旗艦 (v3.3.70)**  | `meta-llama/llama-3.3-70b-instruct`    | 0.6900         | -            | -            | 2.2080         | -               |
| **Kimi 核心模型 (v2.5)**          | `moonshotai/kimi-k2.5`                 | 2.6406         | 1.3203       | -            | 11.8680        | -               |
| **Kimi 推理模型 (v2)**            | `moonshotai/kimi-k2-thinking`          | 4.1400         | 1.0350       | -            | 17.2500        | -               |
| **GLM 旗艦 (v5.1)**               | `z-ai/glm-5.1`                         | 6.5550         | 3.2775       | -            | 21.7350        | -               |
| **GLM 經濟型（glm-4-32b）**            | `z-ai/glm-4-32b`                       | 0.6900         | -            | -            | 0.6900         | -               |
| **MiniMax 核心模型 (v2.7)**       | `minimax/minimax-m2.7`                 | 2.0700         | 0.4071       | -            | 8.2800         | -               |

**表格欄位說明（客戶視角計費邏輯）**：

- **輸入單價 (`Price_Input` / Prefill 階段)**：**“閱後即焚”的普通輸入費**。使用者提交一次性問題或指令，模型看完（進行 Prefill 預填充計算，將輸入 Token 轉化為中間狀態）並回答後即丟棄上下文。這是最基礎的計費項。
- **輸出單價 (`Price_Output` / Decoding 階段)**：**“回答生成費”**。模型根據前置的上下文，逐字自迴歸生成回覆（Decoding 解碼計算）所收取的費用。由於 Decoding 階段受限於顯存頻寬（Memory Bound），單 Token 計算成本遠高於並行的 Prefill，因此輸出單價通常顯著高於輸入費用。
- **快取讀 (`input_cache_read` / 省略 Prefill 階段)**：**“老客戶複用折扣”**。在後續的多輪對話中，若使用者的輸入命中了此前已存好的 KV Cache，模型將直接讀取這些狀態，完全免去昂貴的 Prefill 計算過程。這部分 Token 將享受大幅折扣（通常比普通輸入便宜 50%-90%）。
- **快取寫 (`input_cache_write` / 首存 Prefill 階段)**：**“首存保護費”**。當使用者首次提交需要長效保留的背景文字（如系統提示詞、超長文件庫）並開啟 Prompt Caching 時，模型必須進行完整的 Prefill 計算生成 KV Cache，並額外佔用服務端儲存資源將其持久化（留給後續對話複用）。因此，部分廠商（如 Claude）會對此類“首存”行為收取高於普通輸入的溢價。**若廠商未定義專用 Cache Write 價格，則視為未開啟 Prompt Caching 功能或等同於普通輸入價。**
- **聯網搜尋 (`web_search`)**：**“工具呼叫附加費”**。當模型判斷需要呼叫外部搜尋引擎獲取實時資訊時，每次觸發該工具所產生的固定附加費用（按次計費，與 Token 長度無關）。

**計價機制與商業策略剖析**：

透過表象的 Token 單價，各大模型廠商在快取策略、工具呼叫及推理計算上暗藏了差異化的商業意圖與計費邏輯：

- **上下文快取（Prompt Caching）**：當模型支援快取功能時，首次長文字輸入按“快取寫”計費，後續重複命中的輸入 token 按“快取讀”優惠價格計費（通常比標準輸入低 30-90%）。以 DeepSeek R1 為例，快取讀節省 30%，在長上下文重複場景中可顯著降低總成本。
- **聯網搜尋（Web Search）**：部分模型支援原生的網路搜尋功能。該功能通常按次計費。在評估智能體（Agent）或 RAG 場景時，需將此固定費用作為附加成本計入單次呼叫總成本中。
- **推理模型（Reasoning Models）隱式消耗**：如 `DeepSeek Reasoner` 及 `Kimi 推理模型`，內部會生成大量思維鏈 Token。這部分隱式消耗會被折算進輸出價格中，導致輸出單價顯著偏高，實際開發需預留 3-5 倍 Token 預算。
- **長文字同價下沉策略**：如 `GLM 經濟型（glm-4-32b）` 採用輸入輸出同價策略，旨在鼓勵開發者上傳超大上下文（如長文件、程式碼庫），以此快速進行市場滲透。

### 2.2 OpenRouter API 計費賬單（Usage）解析

在探討具體的計算公式之前，我們先來看 OpenRouter 在真實的工程執行中，每次 API 響應（如開啟了 `include_reasoning: true` 或原生支持 `usage` 追蹤時）直接返回的精確計費“電子回單”。這種結構極為清晰地展現了底層計費的維度。

以下是一個典型的、包含上下文快取（Prompt Caching）與推理（Reasoning）明細的 JSON 賬單結構（資料規範參考自 OpenRouter 官方文件：[Usage Accounting](https://openrouter.ai/docs/guides/administration/usage-accounting)）：

```json
"usage": {
  "prompt_tokens": 10339,
  "completion_tokens": 60,
  "total_tokens": 10399,
  "prompt_tokens_details": {
    "cached_tokens": 10318,
    "cache_write_tokens": 21
  },
  "completion_tokens_details": {
    "reasoning_tokens": 0
  },
  "cost": 0.00154,
  "cost_details": {
    "upstream_inference_cost": 0.00154
  }
}
```

**賬單欄位解析**：

- `prompt_tokens`：本次請求傳入的總輸入長度。
  - `cached_tokens`：命中快取的 Token 數，享受專屬的“老客戶複用折扣”（`Price_Input_Cache_Read`）。
  - `cache_write_tokens`：未命中且被系統新寫入快取的 Token 數，需支付“首存保護費”（`Price_Input_Cache_Write`）。
  - _(隱式欄位)_ `normal_tokens`：既未命中快取，也無需寫入快取的常規尾部輸入（如每次不同的簡短提問），按普通輸入（`Price_Input`）計費。
- `completion_tokens`：總輸出 Token 數。
  - `reasoning_tokens`：大模型內部的隱式思維鏈消耗，合併計入總輸出，按輸出單價（`Price_Output`）計費。
- `cost`：即基於上述實際 Token 消耗與模型單價計算出的**單次呼叫總金額**（USD）。

在此回單結構下，OpenRouter 後端計算最終 `cost` 的精確邏輯如下：

$$
\begin{aligned}
\text{cost} &= (\mathrm{cached tokens} \times \mathrm{Price Input Cache Read}) \\
&\quad + (\mathrm{cache write tokens} \times \mathrm{Price Input Cache Write}) \\
&\quad + \big[ (\mathrm{prompt tokens} - \mathrm{cached tokens} - \mathrm{cache write tokens}) \times \mathrm{Price Input} \big] \\
&\quad + (\mathrm{completion tokens} \times \mathrm{Price Output}) \\
&\quad + (\mathrm{Web Search Count} \times \mathrm{Price Web Search})
\end{aligned}
$$

**驗證實例（以 Claude Haiku 4.5 為例）**：

假設上述 JSON 賬單是由呼叫 Claude Haiku 4.5 模型產生的（其 OpenRouter 基準定價為：輸入 `$1.0/M`、輸出 `$5.0/M`、快取寫 `$1.25/M`、快取讀 `$0.1/M`）。將賬單中的 Token 明細代入上述公式：

$$
\begin{aligned}
\text{cost} &= \left( 10318 \times \frac{0.1}{10^6} \right) + \left( 21 \times \frac{1.25}{10^6} \right) + \left( [10339 - 10318 - 21] \times \frac{1.0}{10^6} \right) + \left( 60 \times \frac{5.0}{10^6} \right) + 0 \\
&= 0.0010318 + 0.00002625 + 0 + 0.0003 \\
&= 0.00135805 \, \text{USD}
\end{aligned}
$$

上式展示了 JSON 賬單中的各微觀欄位如何加權得出最終 `cost`。需要說明的是，上方示例 JSON 取自一份真實賬單，其模型與計費單價與上文 Haiku 4.5 的假設口徑不同，因此賬單中的 `cost` 字段（0.00154 USD）與本例按假設價格復算的結果（約 0.00136 USD）相差約 13% 屬預期之內；本節意在展示欄位結構，這兩個數字不可互相代入復算。

### 2.3 成本預測公式

基於 2.2 節真實的賬單結構，我們可以構建出極其清晰的成本測算模型。在系統架構設計期，API 的總成本預測公式如下：

$$
\begin{aligned}
\text{單次呼叫總成本} &= (\text{Tokens}_{cached} \times \mathrm{Price Input Cache Read}) \\
&\quad + (\text{Tokens}_{cache write} \times \mathrm{Price Input Cache Write}) \\
&\quad + \big[ (\text{Tokens}_{prompt} - \text{Tokens}_{cached} - \text{Tokens}_{cache write}) \times \mathrm{Price Input} \big] \\
&\quad + (\text{Tokens}_{completion} \times \mathrm{Price Output}) \\
&\quad + (\mathrm{Web Search Count} \times \mathrm{Price Web Search})
\end{aligned}
$$

**宏觀測算中的合理簡化（保守高估）**：

在實際業務測算中（如評估 RAG 或 Agent 場景），我們通常無法預知每一次呼叫的精確 `cache_write` 和 `normal` 比例，而是基於宏觀的 **快取命中率（$R_{hit}$）** 進行估算。

因此，為了簡化測算並保證預算的安全性，我們（及配套指令碼）采用**保守高估策略**：

1. **命中部分**：按宏觀命中率 $R_{hit}$ 統一折算為快取讀，適用單價 $P_{hit}$。若 API 未單獨設定快取讀價格，則回退為普通輸入價。
2. **未命中部分**：由於長文字場景下未命中部分多為新寫入的超長文件，我們將其全部視作需新寫入快取的 Token，適用單價 $P_{miss}$。若 API 未單獨設定快取寫價格，則回退為普通輸入價。

基於此策略的**宏觀估算公式**如下：

$$
\begin{aligned}
\mathrm{Input Cost} &= \mathrm{Total Input Tokens} \times \big[ R_{hit} \times P_{hit} + (1 - R_{hit}) \times P_{miss} \big] \\
\text{單次呼叫總成本} &= \mathrm{Input Cost} \\
&\quad + (\mathrm{Total Output Tokens} \times \mathrm{Price Output}) \\
&\quad + (\mathrm{Web Search Count} \times \mathrm{Price Web Search})
\end{aligned}
$$

其中，輸入側動態單價的自適應回退邏輯為：

$$
P_{hit} =
\begin{cases}
\mathrm{Price Input Cache Read}, & \text{if } > 0 \\
\mathrm{Price Input}, & \text{otherwise}
\end{cases}
$$

$$
P_{miss} =
\begin{cases}
\mathrm{Price Input Cache Write}, & \text{if } > 0 \\
\mathrm{Price Input}, & \text{otherwise}
\end{cases}
$$

> [!NOTE]
> 注 1： $\mathrm{Web Search Count}$ 指 API 後台實際發起的搜尋工具呼叫次數，可能大於使用者在介面上的單次觸發請求。
> 注 2：該回退策略僅在模型支援快取功能但未單獨定價時完全適用。若模型底層完全不支援上下文快取（如 DeepSeek Chat），則 $P_{hit}$ 與 $P_{miss}$ 將自動回退為普通輸入價，即不受快取命中率 $R_{hit}$ 的影響。

### 2.4 典型業務場景下的成本測算

基於上述簡化的預測公式，我們設定了三種典型的高負載互動場景對各模型進行對標測算：

- **場景 A（知識庫檢索增強 RAG / 長文件分析）**：輸入極長，輸出較短。由於每次檢索拼入的文件片段不同，上下文變動大，快取命中率較低。**（預設：20K 入 / 1K 出 / 20% 命中）**
- **場景 B（沉浸式多輪對話 / Agent 智能體）**：上下文極長，輸出較短。由於 System Prompt 和前期歷史對話在會話期間固定不變，快取命中率極高。**（預設：30K 入 / 1K 出 / 80% 命中）**
- **場景 C（批次資料清洗 / 機器翻譯）**：輸入與輸出長度接近。由於每次處理全新的獨立文字段，完全無法利用上下文快取。**（預設：5K 入 / 5K 出 / 0% 命中）**

三種場景的 token 數與快取命中率均為指令碼 `fetch_pricing.py` 的內建參數（見原始碼場景迴圈），測算是基於表 1 同一快照（2026-04-15，OpenRouter）的價格，為歷史口徑；2026-11 現價已有變化，請以各官方 pricing 頁為準。

**表 2：典型業務場景單次呼叫成本估算 (¥)**：

| 模型名稱                          | 場景 A: RAG/長文件 (20K 入 / 1K 出 / 20% 命中) | 場景 B: 沉浸式 Agent (30K 入 / 1K 出 / 80% 命中) | 場景 C: 批次翻譯 (5K 入 / 5K 出 / 0% 命中) |
| :-------------------------------- | :--------------------------------------------- | :----------------------------------------------- | :----------------------------------------- |
| **GPT 旗艦 (v5.4)**               | 0.3864                                         | 0.2484                                           | 0.6038                                     |
| **GPT 經濟型 (v5.4)**             | 0.1159                                         | 0.0745                                           | 0.1811                                     |
| **OpenAI O系列 高階推理 (v3)**    | 0.2898                                         | 0.2208                                           | 0.3450                                     |
| **OpenAI O系列 輕量推理 (v4)**    | 0.1594                                         | 0.1214                                           | 0.1898                                     |
| **Claude Opus 頂級旗艦 (v4.6)**   | 0.8763                                         | 0.5140                                           | 1.0781                                     |
| **Claude Sonnet 均衡旗艦 (v4.6)** | 0.5258                                         | 0.3084                                           | 0.6469                                     |
| **Claude Haiku 經濟型 (v4.5)**    | 0.1753                                         | 0.1028                                           | 0.2156                                     |
| **Gemini Pro (v3.1)**             | 0.1297                                         | 0.1314                                           | 0.4269                                     |
| **Gemini Flash (v3)**             | 0.0313                                         | 0.0324                                           | 0.1064                                     |
| **Gemini Flash-Lite (v3.1)**      | 0.0202                                         | 0.0179                                           | 0.0546                                     |
| **DeepSeek Chat (latest)**        | 0.0259                                         | 0.0362                                           | 0.0311                                     |
| **DeepSeek Reasoner (R1)**        | 0.0797                                         | 0.0935                                           | 0.0914                                     |
| **Qwen Max 通義旗艦 (v3)**        | 0.1173                                         | 0.0850                                           | 0.1615                                     |
| **Qwen Plus 通義均衡 (v3.6)**     | 0.0583                                         | 0.0807                                           | 0.0785                                     |
| **Llama 70B 開源旗艦 (v3.3.70)**  | 0.0160                                         | 0.0229                                           | 0.0145                                     |
| **Kimi 核心模型 (v2.5)**          | 0.0594                                         | 0.0594                                           | 0.0725                                     |
| **Kimi K2 Thinking**              | 0.0876                                         | 0.0669                                           | 0.1070                                     |
| **GLM 旗艦 (v5.1)**               | 0.1397                                         | 0.1397                                           | 0.1414                                     |
| **GLM 經濟型（glm-4-32b）**            | 0.0145                                         | 0.0214                                           | 0.0069                                     |
| **MiniMax 核心模型 (v2.7)**       | 0.0430                                         | 0.0305                                           | 0.0517                                     |

> [!NOTE]
> 注：對於未原生支援上下文快取功能（Prompt Caching）的模型（如 DeepSeek Chat），在測算中命中部分與未命中部分將自動回退為普通輸入價，即不受快取命中率 $R_{hit}$ 的影響，測算結果依然準確有效。

**成本對標結論與業務啟示**：

1. **快取命中決定高階模型的適用性**：對比場景 A 和場景 B 可見，Claude Opus/Sonnet 在高命中率的 Agent 場景中（場景 B）呼叫成本驟降 40% 以上，這使得在多輪沉浸式對話中使用旗艦模型變得具有商業可行性；而在低命中的 RAG 場景中（場景 A），因需支付昂貴的 `Cache_Write` 首存費用，其成本極為高昂。
2. **輸出成本主導批處理任務**：在場景 C（批次翻譯/資料清洗）中，輸出 Token 數量大且無法命中快取。此時，輸出單價高昂的模型（如 GPT-5.4 和 Claude 系列）成本呈指數級膨脹，而像 Llama 3 70B 或 GLM 經濟型這種輸出價格極低（或輸入輸出同價）的模型則價效比優勢最為突出。
3. **推理模型（Reasoning）的隱式開銷**：DeepSeek R1 在三個場景中的成本均保持在相對穩定的區間，這說明其極具競爭力的基礎定價抵消了長文字和思維鏈帶來的 Token 膨脹，在中輕度複雜度的全場景中都具備極佳的泛用性。

---

## 3. 廠商視角：供給側成本與商業分析

探討算力基建的固定支出與 Token 計費模式之間的財務平衡，揭示價格戰背後的成本底線。

### 3.1 GPU 算力成本基准

以業界主流的高效能 AI 加速卡為參照系，結合公有云（如 AWS、阿里云）的公開報價與 vLLM/TensorRT-LLM 的權威基準測試，評估底層基礎設施的攤銷壓力。表內月租為 2026-04 時點的公有云公開報價區間（歷史口徑，現價以各雲廠商頁面為準）。

| GPU 型號             | 顯存 | 月租估算 (元/卡) | 單卡 FP8 吞吐參考 (Token/s)\* | 適合部署的模型與配置策略                                                 |
| :------------------- | :--- | :--------------- | :---------------------------- | :----------------------------------------------------------------------- |
| **NVIDIA H100**      | 80GB | 27,000 - 62,000  | ~4,000 (輸入) / ~2,500 (輸出) | 旗艦級模型 (如 Llama 3 70B 需 2 卡 TP，DeepSeek-V3 需 8 卡 EP)           |
| **NVIDIA H20**       | 96GB | 15,000 - 22,000  | ~1,200 (輸入) / ~1,800 (輸出) | 國產/開源大模型 (H20 顯存頻寬極高，生成價效比優於 H100，但 Prefill 較弱) |
| **華為 Ascend 910B** | 64GB | 20,000 - 30,000  | 依賴於 MindIE 框架最佳化水平    | 信創國產化替代方案 (如 Qwen-72B、GLM 等)                                 |

**\*吞吐量估算邊界條件與推導模型 (以 70B/72B 級別 FP8 稠密模型為例)**：

以上吞吐量（單卡折算值）基於以下基準條件：連續批處理（Continuous Batching）、中等上下文長度（約 2K - 8K Tokens）、高 GPU 顯存利用率（> 90%）。_注：生產環境實際吞吐量會隨最大 Batch Size、上下文長度及服務框架的排程策略發生顯著波動。_

- **1. 資料來源依據**
  - **官方性能基准**：參考 [NVIDIA NIM Llama-3.3-70b-instruct Benchmarks](https://docs.nvidia.com/nim/benchmarking/llm/1.0.0/performance.html)（8x H100 最高併發輸出吞吐約 20,000 Tokens/s）。
  - **第三方評測**：參考 [ArtificialAnalysis AI Hardware Benchmarking](https://artificialanalysis.ai/benchmarks/hardware?model=llama-3-3-instruct-70b) 對 Llama 3 70B 和 DeepSeek R1 的極限併發負載測試。
  - **硬體算力規格**：基於 NVIDIA Hopper 架構白皮書（H100 SXM5 FP8 算力 1,979 TFLOPS；H20 顯存頻寬 4.0 TB/s，FP8 算力 296 TFLOPS）。

- **2. 輸入階段 (Prefill) 吞吐推導**
  預填充階段受限於**計算力（Compute Bound）**。遵循第一性原理，處理 70B 模型 1 個 Token 需消耗計算量約 $2 \times 70 \times 10^9 = 140\,\text{GFLOP}$（1400 億次浮點運算）。
  - **H100 測算**：主流推理框架下 MFU（模型算力利用率）介於 20%~35%，取 28% 中位值估算：
    $$ \text{H100 單卡輸入吞吐} \approx \frac{1{,}979 \times 10^3 \times 28\%}{140} \approx 3{,}958\,\text{Tokens/s} \quad \text{(表內取整 ~4,000)} $$
  - **H20 測算**：算力較低更易飽和，MFU 取 55% 估算：
    $$ \text{H20 單卡輸入吞吐} \approx \frac{296 \times 10^3 \times 55\%}{140} \approx 1{,}162\,\text{Tokens/s} \quad \text{(表內取整 ~1,200)} $$

- **3. 輸出階段 (Decode) 吞吐推導**
  大模型生成受限於**顯存頻寬（Memory Bound）**，需逐個 Token 自迴歸生成。
  - **H100 測算**：8x H100 節點部署 70B (TP=4/8)，滿載併發輸出極限約 20,000 Tokens/s，折算單卡為 **~2,500 Tokens/s**。
  - **H20 測算**：顯存頻寬（4.0 TB/s）雖高於 H100，但在大 Batch 下受算力天花板拖累。經驗資料表明其高併發輸出約為 H100 的 70%-75%，折算為 **~1,800 Tokens/s**。

- **4. 併發與顯存限制（KV Cache 牆）**
  **最大併發請求數**極度受限於單請求 KV Cache 的顯存佔用。
  - **佔用預估**：以 70B 模型（8K 上下文）為例，單請求理論佔用上限約 **1.25GB**（1/8 GQA 比例 + FP8 精度）至 **5.0GB**（1/4 GQA 比例 + BF16 精度）顯存（_實際部署中透過引入 Token 剪枝、低比特量化、跨層共享及系統級解除安裝等四維 KV Cache 壓縮技術，實測顯存佔用通常遠低於此理論估算_）。
  - **併發瓶頸**：若在單張 80GB H100 上極限部署 70B（權重佔用約 70GB），剩余 10GB 理論僅能支撐 **4-8 路併發**。併發過低將導致算力閒置，無法充分攤薄計算開銷。
  - **緩解策略 (KV Cache Offloading)**：為突破 GPU 顯存牆限制，現代推理系統（如 vLLM、NVIDIA LMCache）支援將非活躍的 KV Cache 解除安裝（Offload）至 CPU 主存甚至高速外部儲存（如 NVMe SSD，利用 GPUDirect Storage 等技術）中。這一機制用空間換取了更高的併發度，但由於跨匯流排（PCIe）傳輸頻寬遠低於 GPU HBM 顯存，頻繁換頁排程會引入額外的 I/O 延遲。

### 3.2 每百萬 Token 硬體處理成本模型

從硬體折舊到實際 Token 吞吐量的轉化測算，明確盈虧的物理邊界。本模型基於分離計算模式進行推導：

**1. 基礎折舊與有效工時假設**：

- **月度折舊成本 ($C_{month}$)**：取 H100 預留實例的折中值，假設為 **¥45,000/卡/月**。
- **月度有效執行秒數 ($T_{effective}$)**：實際業務請求存在明顯的高峰（如白天 70% 利用率）與低谷（夜間 20% 利用率）。此處取綜合利用率中位數 55%（_注：此測算為理想線性擴展下限，未計入 Prefill-Decode 干涉導致的排隊損耗及顯存碎片導致的 Batch 填充不足損耗_）：
  $$ T\_{effective} = 30\,\text{天} \times 24\,\text{小時} \times 3600\,\text{秒} \times 55\% \approx 1{,}425{,}600\,\text{秒} $$

**2. 輸入階段 (Prefill) 成本測算**：

- **單卡輸入吞吐 ($V_{in}$)**：基於 3.1 節推導，取 **4,000 Tokens/s**。
- **月度總輸入產能 ($N_{in}$)**：
  $$ N_{in} = T_{effective} \times V\_{in} = 1{,}425{,}600 \times 4{,}000 = 5{,}702{,}400{,}000\,\text{Tokens} $$
- **每百萬 Token 輸入硬體成本 ($Price_{in hw}$)**：
  $$ Price_{\mathrm{in hw}} = \left( \frac{C_{\text{month}}}{N\_{in}} \right) \times 10^6 = \left( \frac{45{,}000}{5{,}702{,}400{,}000} \right) \times 10^6 \approx 7.89\,\text{¥/M} $$
  > [!NOTE]
  > 注：此處推匯出的 7.89 ¥/M 為**理想峰值吞吐下的邊際成本極限**。在實際生產環境中，隨著上下文長度（Context Length）的增加，Prefill 階段的計算量呈平方級增長，吞吐量可能急劇下降（如 8K 上下文下吞吐可能跌至 1,500 Tokens/s 以下），導致實際硬體成本通常是該理論下限的 2-3 倍。

**3. 輸出階段 (Decode) 成本測算**：

- **單卡輸出吞吐 ($V_{out}$)**：基於 3.1 節推導，取 **2,500 Tokens/s**。
- **月度總輸出產能 ($N_{out}$)**：
  $$ N_{out} = T_{effective} \times V\_{out} = 1{,}425{,}600 \times 2{,}500 = 3{,}564{,}000{,}000\,\text{Tokens} $$
- **每百萬 Token 輸出硬體成本 ($Price_{out hw}$)**：
  $$ Price_{\mathrm{out hw}} = \left( \frac{C_{\text{month}}}{N\_{out}} \right) \times 10^6 = \left( \frac{45{,}000}{3{,}564{,}000{,}000} \right) \times 10^6 \approx 12.63\,\text{¥/M} $$

### 3.3 商業定價與系統級 TCO 對標分析

將物理硬體成本與市場 API 定價進行橫向對標，揭示各大廠商的利潤空間與技術壁壘。

- **高毛利與品牌溢價**：如 GPT-5.4、Claude 4.6 旗艦等（輸出單價均超 100 ¥/M），其 API 標價高達純稠密模型硬體成本（12.63 ¥/M）的 8-10 倍。需要指出的是，GPT-5.4 等極有可能採用 MoE 架構，實際推理激活參數遠小於 70B，其真實底層計算成本會大幅低於稠密模型基線，這意味著閉源頭部廠商維持著遠高於稠密基線的毛利空間與品牌溢價。與之形成鮮明對比的是 Llama 3 70B 開源模型（輸出約 2.20 ¥/M），其定價已極度貼近甚至擊穿純硬體折舊成本。
- **底層架構降本（MoE 的隱性壁壘）**：DeepSeek-V3 的價格定位（輸入 `1.0350 ¥/M`，輸出 `5.1750 ¥/M`）遠低於上述 H100 硬體成本基線估算。需先註明口徑：這一報價取自 OpenRouter 平台上 `deepseek-chat-v3.1` 的供給價（約 $0.15/M 輸入、$0.75/M 輸出），屬於 OpenRouter 第三方供給價，並非 DeepSeek 官方標價；作為對照，DeepSeek 官方 V4.1 Flash 的現行 API 定價為快取命中輸入 $0.003/M、快取未命中輸入 $0.15/M、輸出 $0.60/M（峰時段價格翻倍）。這得益於 MoE 架構天然的稀疏激活優勢（每次僅激活約 37B 參數，將基礎計算量砍半），結合叢集通訊與 FP8 核心算子的極致工程最佳化。但需注意，MoE 強依賴於**叢集通訊頻寬的極致利用**（昂貴的 All-to-All 集合通信）。若無高速互聯（如 NVLink/InfiniBand）攤薄通訊開銷，其實際物理成本將回升至稠密模型水平，這構成了極強的自建叢集技術壁壘。
- **系統級 TCO（總體擁有成本）修正**：上述程式碼模型僅涵蓋 GPU 硬體折舊。在實際 IDC 環境中，電力（PUE）、機架、網路裝置、儲存以及叢集排程閒置損耗均構成額外開銷。行業通用的 TCO 修正係數通常介於 **1.3 至 2.0** 之間。若取 1.5 倍中值係數，H100 輸出階段硬體成本將抬升至約 **18.95 ¥/M**。這意味著部分“看似微利”的模型，其定價仍需覆蓋極高的綜合運營門檻。

### 3.4 延伸探討：API 計費與內建 RAG 檢索

分析大模型原生 API 與 Web 端產品在知識檢索與工具呼叫上的商業邊界。

當前各大廠商的 Web 端（如 ChatGPT Plus、Kimi、通義千問網頁版）普遍內建了免費的 RAG（檢索增強生成）與聯網搜尋功能。然而，在標準 API 呼叫層面（如 OpenAI Chat Completions 接口），模型本身通常**並不包含隱式的 RAG 流程**。API 提供的是純粹的“大腦推理”算力。若 API 開發者需要聯網或 RAG 能力，一般會導致隱性成本的增加：

1. **開發者自建外掛 RAG**：開發者需自行部署向量資料庫（Vector DB），將檢索到的文件片段（Context）拼接到 Prompt 中傳入 API。這會導致輸入 Token 數量劇增，雖然豐富了上下文，但也大幅拉高了 API 側的計費營收（這正是廠商鼓勵長文字輸入的核心商業動機之一）。
2. **呼叫廠商的專用工具（Tools/Search 接口）**：部分廠商（如 Perplexity，或開啟了特定 `tools` 字段的 OpenAI 接口）支援原生聯網。在此模式下，模型會在後台隱式發起搜尋，抓取的回撥網頁內容同樣會轉化為巨量的隱式輸入 Token 計入使用者的賬單；或者廠商會直接收取單次的 Tool Call 附加費（如 2.2 節表格中的 `web_search` 計費項）。

---
