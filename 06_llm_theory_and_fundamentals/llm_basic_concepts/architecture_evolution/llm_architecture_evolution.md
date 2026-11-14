# LLM 架構演進史——從 GPT-1 到 DeepSeek-V3 的七個拐點

2017 年 Transformer 論文發表時，它的設計目標是機器翻譯——Encoder 讀源語言，Decoder 寫目標語言。七年后的 2024 年，几乎所有前沿 LLM（GPT-4o、Claude 4、DeepSeek-V3、LLaMA 3、Qwen 2.5）都是純 Decoder 架構，共享一套高度收斂的「標準配方」：RMSNorm + RoPE + SwiGLU + 無 bias。

中間發生了什麼？為什麼 Encoder-Decoder 被拋棄了？Billion 參數級別的模型怎麼變成了 Trillion 級別？MoE 為什麼在 2024 年集體爆發？本文梳理七個關鍵拐點，每個拐點回答一個問題：**當時的主流做法遇到了什麼瓶頸，新方案用什麼代價換來了什麼收益。**

---

## 一、拐點 1：Decoder-Only 路線勝出（2017-2018）

原始 Transformer 是完整的 Encoder-Decoder。Google 的 BERT 選擇了 Encoder-Only（雙向理解），OpenAI 的 GPT-1 選擇了 Decoder-Only（單向生成）。

雙向理解在分類、抽取、問答等判別任務上佔據絕對優勢——BERT 一度橫掃 11 項 NLP 基准。但生成任務的權重在 2019 年後急劇上升：對話、寫作、程式碼補全、翻譯——這些場景天然需要自迴歸生成。Decoder-Only 用更簡單的架構覆蓋了更廣的任務面，最終勝出。

Encoder 被拋棄的代價是喪失了深度雙向理解——判別類任務（如信息抽取）如今主要靠生成式模型用 Prompt 間接完成，專用雙向模型仍在部分抽取場景中使用。

---

## 二、拐點 2：規模效應被發現——越大越好（2019-2020）

GPT-2 (1.5B) 和 GPT-3 (175B) 的架構與 GPT-1 幾乎一樣，只是參數和資料成倍放大。但規模帶來的不僅是量變——GPT-3 證明了 **In-Context Learning**：無需微調，只需在 Prompt 中給幾個示例，模型就能完成新任務。

這個發現徹底改變了 NLP 的研究范式：從「為每個任務訓練一個模型」變成「訓練一個足夠大的模型，用 Prompt 適配所有任務」。GPT-3 的架構沒有任何創新——Pre-LN 歸一層、GELU 激活、可學習位置編碼、96 層——但 175B 的規模本身就是最大的創新。

這一階段的代價是訓練成本失控。GPT-3 的訓練約需 3.14 × 10²³ FLOPs，按 2020 年的硬體價格估算約 1200 萬美元。只有少數頭部實驗室能參與這個遊戲。

---

## 三、拐點 3：Chinchilla 修正——從「堆參數」到「堆資料」（2022）

DeepMind 用一個簡單實驗顛覆了 GPT-3 路線的底層假設：70B 的 Chinchilla（配 1.4T tokens）在几乎所有 Benchmark 上擊敗了 280B 的 Gopher。參數量小了 4 倍，資料量多了 4.7 倍——反而更強。

這個結論直接催生了以資料效率為核心的設計哲學。LLaMA 1 (2023) 徹底貫徹了這一思路：65B 參數配 1.4T tokens（token/param = 21.5），使用的全是公開可用資料，卻在 7B-65B 的規模區間全面超越 GPT-3。

> 詳見 [Scaling Laws：參數、資料、算力的三角博弈](../scaling_laws/scaling_laws.md) 對資料效率問題的完整推導。

---

## 四、拐點 4：LLaMA 的「標準配方」形成（2023）

LLaMA 1 不僅改變了資料策略，還重新定義了開源 LLM 的架構標準。它引入的三項改動後來被 Qwen、DeepSeek、Mistral 等幾乎所有開源模型沿用：

| LLaMA 的改動      | 取代的舊方案          | 收益                           |
| ----------------- | --------------------- | ------------------------------ |
| Pre-LN → RMSNorm  | LayerNorm             | 相同效果，每次歸一化省一次歸約 |
| GELU → SwiGLU     | GELU                  | 門控機制，更好的訓練收斂       |
| Sinusoidal → RoPE | 絕對位置編碼          | 相對位置 + 上下文外推能力      |
| 移除 bias 項      | W_Q/W_K/W_V 中的 bias | 簡化模型，精度無明顯損失       |

LLaMA 2 (2023.07) 的 7B/13B 架構與 LLaMA 1 一致；70B 引入了 GQA（8 個 KV 頭），上下文從 2048 擴到 4096，再加上資料翻倍 + RLHF。當 Meta 几乎不改主干、只在注意力效率、資料和對齊上發力時，說明 Decoder-Only 的架構設計已經趨於成熟。

---

## 五、拐點 5：上下文視窗的軍備競賽（2023-2024）

訓練長度的物理瓶頸被 RoPE + YaRN 突破。原本 4K 訓練的模型，透過調整 RoPE 的旋轉頻率並配合少量繼續訓練/微調，可外推到 32K-128K（Llama 3.1 用多階段繼續預訓練擴到 128K；YaRN 論文約 400 步微調）。

| 模型                  | 上下文長度 | 關鍵方法              |
| --------------------- | ---------- | --------------------- |
| GPT-3 (2020)          | 2K         | —                     |
| GPT-4 (2023)          | 8K-128K    | 推測為稀疏注意力      |
| Claude 3 (2024)       | 200K       | 未公開                |
| Gemini 1.5 Pro (2024) | 1M-2M      | 環形注意力 / 混合架構（推測口徑） |
| LLaMA 3 (2024)        | 128K+      | RoPE scaling（社群常歸為 YaRN 類） |
| Qwen 2.5 (2024)       | 128K       | RoPE + YaRN 外推      |

長上下文擴展的代價是推理成本。上下文翻倍，自注意力的計算量翻四倍（O(n²)）。FlashAttention 把 O(n²) 的記憶體複雜度降到了 O(n)，使得 128K 上下文在實際硬體上變得可執行。

---

## 六、拐點 6：MoE 的工程勝利（2023-2024）

Mixtral 8×7B (2023.12) 證明了 MoE 可以在開源場景下工程化落地：8 個專家中每次激活 2 個，推理成本約等於 12B 模型，能力超 70B 模型。

DeepSeek-V3 (2024.12) 將 MoE 推向了極致：671B 總參數（256 個路由專家 + 1 個共享專家），每次只激活 37B（Top-8 routing）。訓練僅需 ~2.7M H800 GPU hours（廠商口徑）——不到 GPT-4 訓練成本的十分之一——能力達到 GPT-4o 水平。配合 Multi-Head Latent Attention（MLA）大幅壓縮 KV Cache，以及 Multi-Token Prediction（MTP）提升訓練效率，DeepSeek-V3 代表了 2024 年 LLM 效率工程的最高水平。

MoE 的引入帶來了新的工程挑戰：專家負載不均衡會導致部分 GPU 空閒等待、路由崩塌（token 湧向少數熱門專家）、以及跨專家通訊開銷。但這些都是可解決的工程問題，而非不可逾越的架構限制。

---

## 七、拐點 7：推理 Scaling——新的增長軸（2024-2025）

前面六個拐點都是訓練階段的創新。OpenAI o1 (2024.09) 和 DeepSeek-R1 (2025.01) 開闢了一條新路：**不改變訓練方式，改變推理方式。**

透過強化學習讓模型學會在推理時生成長 Chain-of-Thought——有時數千 token——然後從中提取最終答案。這相當於把「思考時間」當作可伸縮的計算資源：給更多時間，就得到更好的答案。這個方向不受訓練資料和參數規模的硬約束，是目前最被看好的下一代 Scaling 方向。

代價是延遲——o1 的推理延遲可達 GPT-4o 的數倍到數十倍（無公開出處，社群觀察口徑）。對於需要毫秒級響應的場景（如程式碼補全），推理 Scaling 不適用；但對於需要深度分析的場景（數學證明、法律分析、科研推理），用時間換品質是完全值得的。

---

## 八、七年演進的三條主線

```text
            2017 ────────────────────────────────── 2025

架構:    Encoder-Decoder → Decoder-Only (不可逆轉的收斂)
規模:    65M → 1.5B → 175B → 671B (MoE) → ?
效率:    Dense → MoE → MoE + MLA + MTP → 推理 Scaling
范式:    為每個任務微調 → Few-shot → Zero-shot → Agent
上下文:  512 → 2K → 4K → 128K → 1M+
```

三條主線的交匯點是：**架構在收斂，效率在分化，推理在成為新的增長軸。** 架構層面的創新空間越來越集中在注意力機制的變體（如 MLA）和 MoE 的路由策略上；效率提升則從訓練端（Chinchilla、MoE、MTP）向推理端（o1/R1）轉移。

> **後記（2026-11）**：本文「到 DeepSeek-V3」的收束是 2024-2025 年的快照。2025-2026 起旗艦模型開始在 Decoder-only 內部引入線性注意力/稀疏/壓縮混合層（Kimi K3、GLM-5.3、Qwen3.8-Flash-Next），見本目錄 attention 演進三篇：[從 GPT-2 到 Kimi K3](from_gpt2_to_kimi_k3_attention_evolution.md)、[Attention 演進與 KV Cache 之變](attention_evolution_kv_cache.md)、[圖解注意力算力賬](attention_compute_fifteen_charts.md)。

---

## 九、相關資源

- [Transformer 架構詳解](../transformer/transformer_architecture.md) — 標準配方的逐元件拆解。
- [位置編碼：從 Sinusoidal 到 RoPE](../positional_encoding/positional_encoding.md) — 上下文擴展的數學基礎。
- [Scaling Laws](../scaling_laws/scaling_laws.md) — 拐點 2、3、6 背後的資料效率邏輯。
- [混合專家 (MoE)](../moe/mixture_of_experts_moe_visual_guide.zh-CN.md) — MoE 的架構細節與負載均衡。
- LLaMA: Open and Efficient Foundation Language Models (2023)
- DeepSeek-V3 Technical Report (2024)
