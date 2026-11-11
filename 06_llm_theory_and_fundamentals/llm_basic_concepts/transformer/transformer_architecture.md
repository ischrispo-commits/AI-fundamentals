# Transformer 架構詳解——從自注意力到完整解碼器

2017 年之前，處理序列資料的主流架構是 RNN 和 LSTM。它們在機器翻譯、語音識別等任務上統治了近十年，但有一個結構性的硬傷：**第 t 個 token 必須等第 t-1 個算完才能開始**。這個序列依賴帶來了兩個無法繞過的問題——序列越長訓練越慢（GPU 的並行能力被浪費），以及跨長距離的資訊會隨著梯度傳播逐步衰減甚至消失。

同年，Vaswani 等人的《Attention Is All You Need》用**自注意力（Self-Attention）**一次性解決了這兩個問題：每個 token 直接關注序列中所有其他 token，沒有先後順序，只有相關度權重。這個簡單的想法催生了 Transformer 架構，進而演化為今天所有大語言模型（GPT、LLaMA、Qwen、DeepSeek、Claude）的共同基礎。

但切換到全並行架構並非沒有代價。去掉序列順序意味著位置資訊丟失——要讓模型區分「我打你」和「你打我」，靠權重表是不夠的。同時，全注意力在長序列上的計算量是 O(n²)，當上下文從 2K 擴展到 128K 時，這個代價變得不可忽視。

本文從零拆解 Transformer 的核心元件。閱讀目標是：**讀完能看懂一份 `modeling_llama.py` 級別的原始碼**，並理解每個元件解決了什麼問題、又帶來了什麼新問題。

---

## 一、問題：RNN 的序列瓶頸

RNN/LSTM 處理序列的方式是逐步迭代——隱藏狀態 $h_t$ 由 $h_{t-1}$ 和當前輸入 $x_t$ 共同決定。

```text
RNN:  token1 → token2 → token3 → ... → tokenN  （串行，O(n) 步）
```

這個設計有兩個致命缺陷：

- **無法並行訓練**：計算 token_N 必須先算完前面 N-1 步。序列越長，一輪前向/反向傳播的時間線性增長。
- **長距離依賴衰減**：梯度和資訊在反向傳播時穿過幾十個時間步後，會因連乘效應指數級衰減（梯度消失）或放大（梯度爆炸）。

這兩個問題在 2014-2016 年間催生了大量的變體方案——LSTM 的門控機制、注意力作為 RNN 的輔助模組——但本質上仍在序列框架內打補丁。

## 二、方案：自注意力——讓每個 token 同時看見所有 token

Transformer 的答案是放棄序列假設：**不再透過隱藏狀態逐步傳遞資訊，而是讓每個 token 直接查詢序列中的每個 token。**

```text
Transformer: 每個 token ⇄ 所有 token（並行，O(1) 步）
```

這個「直接查詢」機制就是自注意力。

### 2.1 Q / K / V：資訊檢索的類比

自注意力可以用一個資訊檢索的類比來理解：

```text
Q (Query)  = x · W_Q    —— "我在找什麼？"
K (Key)    = x · W_K    —— "我能提供什麼？"
V (Value)  = x · W_V    —— "如果被選中，我給出什麼資訊？"
```

每個 token 的 Embedding 向量透過三個不同的線性變換，分別投影為查詢向量 Q、鍵向量 K、值向量 V。$W_Q$、$W_K$、$W_V$ 是可學習的權重矩陣，維度為 $d_{\text{model}} \times d_k$（通常 $d_k = d_{\text{model}} / n_{\text{heads}}$）。

這個三元組設計來自資訊檢索：Query 代表使用者的搜尋意圖，Key 代表文件的索引標籤，Value 代表文件的實際內容。把每個 token 既當作「提問者」又當作「被檢索的文件」，就得到了自注意力。

### 2.2 注意力分數：四步計算

$$
\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{Q \cdot K^\top}{\sqrt{d_k}}\right) \cdot V
$$

步驟拆解：

1. $Q \cdot K^\top$ → 得分矩陣 S（token i 對 token j 的原始相關度）
2. $S / \sqrt{d_k}$ → 縮放，防止大點積值導致 softmax 梯度消失
3. $\text{softmax}$ → 歸一化為機率分佈（每個 token 對所有 token 的注意力權重之和 = 1）
4. $\times V$ → 加權求和，得到每個 token 的「上下文感知」表示

### 2.3 為什麼要除以 √d_k？

自注意力有一個容易被忽視的數學細節。當 $d_k$ 較大時，$Q \cdot K$ 的點積結果的方差會增大（約等於 $d_k$）。大的輸入值讓 softmax 進入飽和區——輸出幾乎變成 one-hot 向量，梯度趨近於零。除以 $\sqrt{d_k}$ 將方差壓回 1，讓梯度在訓練中保持健康。

```python
# PyTorch 實現骨架
def self_attention(Q, K, V, mask=None):
    d_k = Q.size(-1)
    scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(mask == 0, -1e9)
    attn_weights = F.softmax(scores, dim=-1)
    return torch.matmul(attn_weights, V)
```

這個簡單的縮放操作解決了梯度健康問題，但它不解決自注意力的另一個根本限制——一組 Q/K/V 只能表達一種「相關性的定義」。

---

## 三、方案延伸：多頭注意力——從單視角到多視角

單組 Q/K/V 只能捕捉一種關係模式。比如在處理「蘋果很好吃」時，一組注意力可能關注「蘋果→好」的語義關聯，但它無法同時關注「蘋果→名詞主語」的語法角色和「蘋果→吃」的動作搭配。

多頭注意力（Multi-Head Attention）的解法是**並行執行多個獨立的注意力頭**，每個頭有自己的 W_Q、W_K、W_V，在各自的低維子空間中計算：

$$
\begin{aligned}
\text{MultiHead}(Q, K, V) &= \text{Concat}(\text{head}_1, \ldots, \text{head}_h) \cdot W_O \\
\text{head}_i &= \text{Attention}(Q \cdot W_{Qi}, K \cdot W_{Ki}, V \cdot W_{Vi})
\end{aligned}
$$

- 每個 head 的維度為 d_k = d_model / h（如 512 / 8 = 64）
- 所有 head 的輸出拼接後經 W_O 投影回 d_model
- 總計算量與等效的單頭注意力相同（並行度換表達力）

**代價**：多頭增加了模型的理解能力，但也讓注意力的可解釋性變得更困難——面對 32 個頭、每層一張注意力熱力圖，人類幾乎無法直觀理解模型究竟在「關注」什麼。此外，多頭之間的資訊完全獨立，直到拼接步驟才交匯——這意味著每個頭可能學習到冗餘或退化的注意力模式。

---

## 四、前饋網路：注意力之后的逐 token 變換

自注意力讓 token 之間交換資訊，但交換完後，每個 token 的表示還需要一次獨立的非線性變換。這個任務由前饋網路（FFN）承擔：

$$
\text{FFN}(x) = W_2 \cdot \sigma(W_1 \cdot x) \qquad\text{（現代 LLM 通常去掉偏置項 ）}
$$

- 先將 d_model 維投影到 d_ff 維（通常 d_ff = 4 × d_model），再投影回 d_model
- FFN 是 Transformer block 中參數量最大的部分，約佔 2/3
- σ 是激活函式：原始論文用 ReLU，現代 LLM 幾乎全部換為 SwiGLU

### 4.1 SwiGLU：門控機制的引入

從 ReLU 到 GELU 再到 SwiGLU 的演進，反映了 LLM 架構中的一個核心發現：**讓網路自己學會「哪些資訊該透過、哪些該抑制」，比用一個固定的激活函式更有效。**

$$
\begin{aligned}
\text{SwiGLU}(x) &= (x \cdot W_{\text{gate}} \odot \text{SiLU}(x \cdot W_1)) \cdot W_2 \\
\text{SiLU}(x) &= x \cdot \sigma(x)
\end{aligned}
$$

SwiGLU 引入了一個可學習的「門」——`x · W_gate`。這個門與經 SiLU 激活的主通路做逐元素乘法，讓網路在每個 token、每個維度上獨立決定資訊透過量。代價是參數量增加約 33%（多了一個 W_gate 矩陣），但訓練穩定性和收斂速度的提升足以抵消這個開銷。

| 模型系列         | FFN 激活 | d_ff 比例     |
| ---------------- | -------- | ------------- |
| 原始 Transformer | ReLU     | 4×            |
| GPT-2/3          | GELU     | 4×            |
| LLaMA 1/2/3      | SwiGLU   | 8/3× (≈2.67×) |
| Qwen 2           | SwiGLU   | 8/3×          |

---

## 五、位置編碼：解決注意力「看不到順序」的問題

自注意力有一個根本性的盲區：**它對 token 的位置完全不敏感。** 打亂整個輸入序列，計算出的注意力分數不變。

但語言是有嚴格順序的。「我打你」和「你打我」共享完全相同的 token 集合，含義卻相反。RNN 透過序列計算自然地捕獲了順序——Transformer 的並行注意力犧牲了這一點。因此必須透過額外的機制向模型注入位置資訊。

### 5.1 兩種注入策略

**加到輸入端**：將位置編碼 p_i 直接加到 token embedding x_i 上——input_i = x_i + p_i。原始 Transformer 使用固定的正弦/餘弦函式生成 p_i，GPT-2/3 則用可學習的 Embedding 表。

**融入注意力計算**：不修改 token 表示本身，而是根據位置對 Q 和 K 施加旋轉變換。RoPE（旋轉位置編碼）是這一策略的代表——它將位置資訊編碼為 Q·K 點積中的相對位置項，天然支援比訓練時更長的上下文。

> 詳見本目錄的 [位置編碼：從 Sinusoidal 到 RoPE](../positional_encoding/positional_encoding.md) 對 RoPE 數學原理與 NTK/YaRN 外推技術的完整推導。

---

## 六、層歸一化與殘差連線：讓深網路能訓練

自注意力和 FFN 解決了資訊交換和變換的問題，但直接堆疊幾十層會導致訓練崩潰——早期的 Transformer 訓練到 6 層以上就開始不穩定。

### 6.1 問題：內部協變數漂移

深度網路訓練中，每層參數的更新會改變該層輸出的分佈。這種漂移逐層累積，使得底層接收到的梯度訊號變得極其不穩定。層歸一化（LayerNorm）是解決這一問題的標準手段：

$$
\text{LayerNorm}(x) = \gamma \cdot \frac{x - \mu}{\sqrt{\sigma^2 + \varepsilon}} + \beta
$$

其中 $\gamma$ 和 $\beta$ 是可學習的參數，$\varepsilon$ 防止除零。

### 6.2 歸一化位置的演化：Post-LN → Pre-LN → RMSNorm

| 變體    | 歸一化位置                     | 使用情況              | 原因                       |
| ------- | ------------------------------ | --------------------- | -------------------------- |
| Post-LN | 殘差連線之後                   | 原始 Transformer      | 訓練不穩定，梯度在深層衰減 |
| Pre-LN  | 殘差連線之前（先歸一化再計算） | GPT-2/3               | 訓練更穩定，梯度流更通暢   |
| RMSNorm | 同 Pre-LN，但只做縮放          | LLaMA、Qwen、DeepSeek | 速度更快，精度無明顯損失   |

RMSNorm 去掉了均值居中（μ），僅保留均方根縮放。實驗證明去掉居中操作對精度影響微乎其微，但省去了一次歸約計算——在大規模訓練中，這個微觀最佳化累積為可觀的加速：

$$
\text{RMSNorm}(x) = \gamma \cdot \frac{x}{\sqrt{\text{mean}(x^2) + \varepsilon}}
$$

### 6.3 殘差連線：讓梯度繞過子層

有了歸一化還不夠。堆疊 32 層以上的網路時，梯度在反向傳播中經過每一層都會衰減。殘差連線提供了一個「快捷通道」——將子層的輸入直接加到輸出上，讓梯度可以繞過子層的反向傳播直達輸入：

$$
\text{output} = x + \text{Sublayer}(\text{LayerNorm}(x)) \qquad\text{（Pre-LN：先歸一化再進子層，現代 LLM 的標準做法）}
$$

梯度可以直接透過「+」操作跳過 Sublayer 的反向傳播——這相當於給每一層都提供了一條直達輸入的梯度高速公路。沒有殘差連線，32 層以上的 Transformer 幾乎無法訓練。

---

## 七、完整資料流：一個 Decoder Block 的標準配方

將以上所有元件串接起來，以 LLaMA 為例——這是 2024 年主流開源 LLM 共同遵循的「標準配方」。互動視覺化版本見 [Decoder Block 資料流視覺化](transformer_block_visual.html)。

```text
輸入: token embeddings (batch, seq_len, d_model)
  │
  ├─ 1. RMSNorm ──→ 2. Self-Attention (with RoPE + Causal Mask)
  │                                          │
  │       ┌──────────────────────────────────┘
  │       ▼
  │    3. 殘差相加 (+)
  │       │
  │       ▼
  ├─ 4. RMSNorm ──→ 5. FFN (SwiGLU)
  │                    │
  │       ┌───────────┘
  │       ▼
  │    6. 殘差相加 (+)
  │       │
  │       ▼
  輸出 → 送入下一個 Block（重複 24-80 層，視模型規模而定）
```

**因果掩碼**是 Decoder 獨有的約束：生成第 t 個 token 時，模型只能看到位置 1 到 t-1，不能「偷看」未來。透過一個上三角為 -∞ 的矩陣實現：

```text
因果掩碼（seq_len=4）：
  [  0, -∞, -∞, -∞ ]
  [  0,  0, -∞, -∞ ]
  [  0,  0,  0, -∞ ]
  [  0,  0,  0,  0 ]
```

---

## 八、權衡：Transformer 得到了什麼，犧牲了什麼

```text
     得到                                    犧牲
  ──────────────────────                ──────────────────
  訓練完全並行化                       推理仍是自迴歸序列的
  O(1) 步內跨越任意距離                 每步的注意力計算是 O(n²)
  統一架構替代 RNN/CNN                 位置資訊需額外編碼（RoPE）
  易於擴展到千億參數                    注意力分數矩陣的峰值激活隨長度平方
                                         增長（FlashAttention 可消除）；
                                         KV Cache 隨序列長度線性增長
```

這些權衡驅動了 Transformer 後續 7 年的演化方向——FlashAttention 緩解了 O(n²) 的記憶體瓶頸，RoPE+YaRN 讓 4K 訓練的模型外推到 128K，MoE 在維持推理成本的同時成倍擴大參數容量。這些正是 [LLM 架構演進史](../architecture_evolution/llm_architecture_evolution.md) 所覆蓋的內容。

### 8.1 關鍵設計決策對照

| 決策       | 原始 Transformer (2017) | 現代 LLM (2023+) | 原因                                           |
| ---------- | ----------------------- | ---------------- | ---------------------------------------------- |
| 架構       | Encoder-Decoder         | Decoder-only     | 生成任務更自然，且在足夠大規模下理解與生成統一 |
| 激活函式   | ReLU                    | SwiGLU           | 門控機制提供更好的訓練動態                     |
| 歸一化位置 | Post-LN                 | Pre-LN / RMSNorm | 訓練穩定性，RMSNorm 進一步節省計算             |
| 位置編碼   | Sinusoidal              | RoPE             | 編碼相對位置，且支持上下文外推                 |
| 偏置項     | 有                      | 無               | 簡化模型，精度無明顯損失                       |
| 注意力頭數 | 8                       | 32-64            | 細粒度匹配硬體並行度                           |

---

## 九、相關資源

- [Decoder Block 資料流視覺化](transformer_block_visual.html) — 本文 §7 的互動視覺化，可點選元件檢視詳情，支持完整流/Attention/FFN 三種視角。
- [位置編碼：從 Sinusoidal 到 RoPE](../positional_encoding/positional_encoding.md) — RoPE 的數學原理與 NTK/YaRN 外推技術。
- [LLM 架構演進史](../architecture_evolution/llm_architecture_evolution.md) — Transformer 誕生後 7 年的關鍵拐點與「標準配方」的形成。
- [混合專家 (MoE)](../moe/mixture_of_experts_moe_visual_guide.zh-CN.md) — 如何用稀疏激活進一步擴展參數規模。
- 《Attention Is All You Need》(2017) — 原始論文。
- Jay Alammar, [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) — 經典圖解教程。
- Georgia Tech, [Transformer Explainer](https://poloclub.github.io/transformer-explainer/) — 互動式視覺化，可逐 token 觀察注意力計算。
- [bbycroft/llm](https://bbycroft.net/llm) — 3D 視覺化 GPT 類模型的完整推理過程。
