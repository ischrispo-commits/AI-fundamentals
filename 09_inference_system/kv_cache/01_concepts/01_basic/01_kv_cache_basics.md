# KV Cache 原理簡介

## 1. 背景：大模型推理的挑戰

在大語言模型（LLM）的推理過程中，尤其是文字生成任務中，模型通常採用自迴歸（Autoregressive）的方式逐個生成 Token。這種生成機制如果不加以最佳化，會面臨嚴重的計算效率問題，理解這一基礎模式是後續探索效能最佳化手段的前提。

### 1.1 自迴歸生成模式

在自迴歸生成中，模型根據之前的上下文（Context）預測下一個 Token。例如，給定輸入 "Hello"，模型預測 "World"；接著給定 "Hello World"，模型預測 "!"。在沒有快取時，模型必須將 "Hello" 等歷史上下文重複編碼。這意味著每生成一個新的 Token，模型都需要回顧並重新計算之前所有的 Token。

![自迴歸生成模式](img/fig-1.png)

### 1.2 重複計算問題

如果不使用快取機制，每生成一個新的 Token，模型都需要將之前所有 Token 重新輸入模型，並重新計算它們的 Key (K) 和 Value (V) 矩陣。隨著序列長度的增加，這種重複計算若僅看單步前向，無快取時注意力計算量為 $O(N^2)$，其中 $N$ 為當前序列長度。若考慮從第 1 個 Token 生成到第 $L_{gen}$ 個 Token 的完整過程，累積計算量約為 $O(L_{gen}^3)$，延遲將隨生成長度急劇惡化。

![重複計算問題](img/fig-2.png)

---

## 2. KV Cache 核心原理

為了解決自迴歸生成中的重複計算問題，KV Cache 技術透過“空間換時間”的策略，將已計算過的中間結果儲存起來，從而避免了大量冗餘的矩陣運算，直接降低了單步推理的計算複雜度。

> **深入計算過程**：本文聚焦 KV Cache 的工作機制和顯存分析。如果想從矩陣形狀和計算量層面理解 Prefill 為什麼是 compute-bound、Decode 為什麼是 memory-bound、以及這些差異如何推匯出所有 KV Cache 最佳化方向，見姊妹篇 [為什麼 GPU 生成每個 token 時利用率不到 5%？——Prefill 與 Decode 深度拆解](../../../prefill_decode/prefill_decode_qkv_calculation.md)。

### 2.1 什麼是 KV Cache？

KV Cache 本質上是一種快取機制，用於儲存 Transformer 模型中 Attention 層的 Key 和 Value 矩陣。在推理過程中，模型只需要計算**當前新生成 Token** 的 Query (Q)、Key (K) 和 Value (V)，然後將新的 K 和 V 追加到快取中。最后，利用當前的 Q 與**完整的快取**（历史 K/V + 當前 K/V）進行注意力計算。

> **為什麼只快取 K/V，不快取 Q？** Q 是「一次性查詢」——每個 token 的 Q 只在使用它的那一刻有意義，後續 token 不會再訪問。K/V 是被反覆檢索的「答案庫」。詳見 [KV Cache 為什麼叫 KV Cache？——Q 去哪了](04_why_only_kv.md)。

**有無 KV Cache 的對比：**
![KV Cache 對比](img/fig-5.png)

### 2.2 工作流程詳解

KV Cache 的工作流程可以分為兩個階段：

1. **Prefill 階段（首 Token 生成）**：
   - 模型接收完整的 Prompt 輸入。
   - 計算所有輸入 Token 的 K 和 V，並將它們存入 Cache。
   - 生成第一個輸出 Token。
     ![Prefill 階段](img/fig-3.png)

2. **Decode 階段（後續 Token 生成）**：
   - 模型僅接收上一步生成的 Token。
   - 計算該 Token 的 Q、K、V。
   - 將新計算的 K、V 追加（Append）到 Cache 中。
   - 利用完整的 Cache (历史 K/V + 當前 K/V) 計算 Attention。
   - 生成下一個 Token，迴圈上述過程。
     ![Decode 階段](img/fig-4.png)

### 2.3 虛擬碼示例

以下是 KV Cache 更新邏輯的簡化虛擬碼表示：

```python
# KV Caching 虛擬碼示例
# 采用 HuggingFace 常見的 shape 布局:
# [batch_size, seq_len, num_heads, head_dim]
class KVCache:
    def __init__(self):
        # 初始化空的快取
        self.cache = {"key": None, "value": None}

    def update(self, key, value):
        """
        更新快取：將新的 Key 和 Value 追加到現有快取中
        """
        if self.cache["key"] is None:
            # 如果快取為空，直接儲存
            self.cache["key"] = key
            self.cache["value"] = value
        else:
            # 否則，在 seq_len 維度上進行拼接（該 shape 下 dim=1）
            # 注意：具體維度索引取決於不同框架的實現佈局
            self.cache["key"] = torch.cat([self.cache["key"], key], dim=1)
            self.cache["value"] = torch.cat([self.cache["value"], value], dim=1)

    def get_cache(self):
        return self.cache
```

以上維度僅為示意。若實現採用 `[batch_size, num_heads, seq_len, head_dim]` 等其他布局，應將拼接維度相應調整。

## 3. 顯存佔用分析

雖然 KV Cache 極大地提升了推理速度，但這種“空間換時間”的做法也帶來了顯著的顯存開銷。隨著併發請求數（Batch Size）和上下文序列長度的增加，動態增長的快取資料會佔用大量 GPU 顯存，成為制約系統吞吐量的核心瓶頸。

> **如何高效管理 KV Cache？** 上述分析解決了“KV Cache 佔多少顯存”的問題，但另一個同樣關鍵的問題是“怎麼存、怎麼回收”。傳統預分配方案的記憶體利用率僅 20-40%——大部分顯存被碎片浪費。PagedAttention 透過將 KV Cache 切分為固定大小的 block，按需分配、動態對映，將碎片率降到 4% 以下，同等顯存可服務 2-4 倍併發。詳見 [PagedAttention 原理介紹](02_paged_attention.md)。

詳細請參考[LLM 模型推理顯存佔用深度的分析](../../../memory_calc/memory_analysis.md)。

### 3.1 顯存佔用的主要構成

在 LLM 推理中，顯存主要被以下三部分佔用：

1. **模型權重 (Model Weights)**：靜態佔用，取決於模型參數量和精度。
2. **KV Cache**：動態佔用，隨著序列長度和 Batch Size 線性增長。
3. **中間激活 (Intermediate Activations)**：推理時的臨時計算緩衝區。

![KV Cache 顯存構成](img/fig-6.png)

### 3.2 KV Cache 顯存計算公式

KV Cache 的顯存佔用可以透過以下公式估算：

![KV Cache 顯存計算公式](img/fig-7.png)

$$
\text{Memory}_{KV} \approx 2 \times b_{kv} \times L \times B \times S \times H \times \frac{N_{kv}}{N_{attn}}
$$

其中：

- $2$：同時快取 Key 和 Value 矩陣。
- $b_{kv}$：資料精度（Bytes），如 FP16 為 2。
- $L$：模型層數 (Layers)。
- $B$：併發請求數 (Batch Size)。
- $S$：每個請求的平均序列長度（Prompt + 已生成 Token）。
- $H$：隱藏層維度 (Hidden Size)。
- $N_{kv}$：KV Head 的數量（GQA/MQA 中的分組數）。
- $N_{attn}$：Query Head 的數量（總注意力頭數）。當使用 MHA 時 $N_{kv} = N_{attn}$，係數為 1。

### 3.3 Batch Size 對 KV Cache 的影響

上面 $B$ 這個參數經常被初學者忽略——"我先算好 per-token 的 KV Cache，乘以序列長度，就得到顯存佔用了"。這個演算法在 batch=1 時是對的，但在真實推理服務中，**多個請求是併發處理的**，每個請求都需要自己獨立的 KV Cache。

**逐級展開公式：**

$$
\begin{aligned}
\mathrm{per token} &= 2 \times b_{kv} \times L \times \frac{H \times N_{kv}}{N_{attn}} \\[4pt]
\mathrm{per sequence} &= \mathrm{per token} \times S \quad \text{(序列長度)} \\[4pt]
\text{total} &= \mathrm{per sequence} \times B \quad \text{(併發請求數)}
\end{aligned}
$$

以 **Qwen2.5-7B**（L=28, H_kv=4, head_dim=128, FP16）為例：

$$
\mathrm{per token} = 2 \times 2 \times 28 \times 4 \times 128 = 57{,}344\ \text{bytes} \approx 56\ \text{KB}
$$

> 口徑說明：本節容量數值統一按 GiB（1024 進位制，即 bytes ÷ 2³⁰）計算；模型權重量級同理（Qwen2.5-7B BF16 權重約 14 GiB ≈ 15 GB）。

| batch | seq_len | total_tokens | KV Cache   | 與模型權重（約 14 GiB）對比 |
| :---: | :-----: | :----------: | :--------: | :-------------------------: |
|   1   |  2,048  |    2,048     | ≈0.11 GiB  |            < 1%             |
|   1   |  8,192  |    8,192     | ≈0.44 GiB  |             3%              |
|   1   | 32,768  |    32,768    |  1.75 GiB  |            ≈13%             |
|   8   |  2,048  |    16,384    | ≈0.88 GiB  |             6%              |
|   8   |  8,192  |    65,536    |  3.5 GiB   |             25%             |
|   8   | 32,768  |   262,144    |  14 GiB    |      **≈ 模型權重**         |
|  32   |  2,048  |    65,536    |  3.5 GiB   |             25%             |
|  32   |  8,192  |   262,144    |  14 GiB    |      **≈ 模型權重**         |
|  32   | 32,768  |  1,048,576   | **56 GiB** |     **4× 模型權重**         |

**batch=32, seq_len=32768 時，KV Cache（56 GiB）約為模型權重（14 GiB）的 4 倍。** 這意味著即使 GPU 能裝下模型，也可能因為併發請求的 KV Cache 撐爆顯存。

再看 **Qwen2.5-72B**（L=80, H_kv=8, head_dim=128, FP16，模型權重 ~144 GB）：

$$
\mathrm{per token} = 2 \times 2 \times 80 \times 8 \times 128 = 327{,}680\ \text{bytes} = 320\ \text{KB}
$$

| batch | seq_len |                 KV Cache                 |
| :---: | :-----: | :--------------------------------------: |
|   1   | 32,768  |                 10 GiB                   |
|   4   | 32,768  |                 40 GiB                   |
|   8   | 32,768  | **80 GiB** ← 一張 H100 僅 KV Cache 就滿了 |
|  16   | 32,768  |    **160 GiB** ← KV Cache 超過模型權重    |

**核心結論：**

1. **Batch Size 不是"免費"的**：b=1 時 KV Cache 占比很小，但 b=32 時長上下文場景 KV Cache 遠超模型權重，成為顯存的真正瓶頸。
2. **長上下文 + 大 batch = KV Cache 爆炸**：兩者是乘法關係（$S \times B$），任何一項增大都會等比例放大顯存壓力。
3. **最佳化方向由此展開**：減少 per-token（量化、GQA/MLA）、減少併發 Cache（Offloading）、減少重複 Cache（Prefix Caching）——所有 KV Cache 最佳化策略都是為了在有限的 GPU 顯存中容納更多的 $S \times B$。

> **動手驗證**：本文所有數值可由 [`kv_cache_calc.py`](01_kv_cache_calc.py) 復現。修改 `--seq-len` 和 `--batch` 參數，觀察不同配置下的顯存佔用變化。

---

## 4. 優缺點對比與權衡

引入 KV Cache 從根本上改變了模型推理的效能特徵。在實際應用中，系統架構師需要在計算速度的顯著提升與顯存資源的急劇消耗之間尋找最佳平衡點，不同的業務場景對這種權衡有著完全不同的偏好。

### 4.1 速度與顯存的 Trade-off

在評估是否引入快取機制時，需要清晰地認識到計算效率與記憶體消耗之間的反向關係，以下表格直觀展示了兩者在不同維度的核心差異。

| 特性           | 標準推理 (Standard Inference)     | KV Caching                      |
| :------------- | :-------------------------------- | :------------------------------ |
| **單步計算量** | 隨序列長度平方級增長 ($O(N^2)$)   | 隨序列長度線性增長 ($O(N)$)     |
| **顯存佔用**   | 較低，主要取決於模型權重          | 較高，隨序列長度線性增加        |
| **推理速度**   | 隨生成長度增加顯著變慢 (計算瓶頸) | 速度快且相對穩定 (顯存頻寬瓶頸) |
| **適用場景**   | 短文本、顯存極其受限的場景        | 長文字生成、高吞吐服務          |

說明：上表中的“單步計算量”指標針對的是 Decode 階段生成單個 Token 的場景。若估算生成 $L_{gen}$ 個 Token 的累計複雜度，無 KV Cache 近似為 $O(L_{gen}^3)$；有 KV Cache 時通常近似為 $O(P^2 + P \cdot L_{gen} + L_{gen}^2)$（其中 $P$ 為 Prompt 長度，$P^2$ 來自 Prefill）。

### 4.2 為什麼 KV Cache 是必須的？

對於現代 LLM 應用（如 RAG、長文件摘要），上下文長度往往達到 32k 甚至 128k。如果不使用 KV Cache，生成延遲將變得難以接受。因此，KV Cache 已成為所有主流推理框架（如 vLLM, HuggingFace Transformers）的標準配置。

---

## 5. 進階：降低 KV Cache 開銷——從注意力機制入手

KV Cache 的顯存佔用與注意力頭數成正比。標準 MHA 下每個 Q head 都有獨立的 K/V head，KV Cache 需要儲存全部 K/V。如果在注意力層面讓多個 Q head 共享一組 K/V——在不改變模型總參數量的前提下減少需要快取的 K/V 數量——KV Cache 就會成倍縮小。這就是 MQA 和 GQA 的核心思路：**它們首先是注意力機制的架構設計，KV Cache 減小是其對推理最直接的收益。**

![降低 KV Cache 開銷](img/fig-9.png)

### 5.1 Multi-Query Attention (MQA)

MQA 讓所有的 Attention Head 共享同一組 Key 和 Value 矩陣，從而將 KV Cache 的大小壓縮到原來的 $1/N_{attn}$。這極大地降低了顯存佔用，但可能會輕微影響模型效能。

### 5.2 Grouped-Query Attention (GQA)

GQA 是 MQA 和標準 MHA (Multi-Head Attention) 的折中方案。它將 Query Head 分組，每組共享一對 K/V Head。例如，Llama-2-70B 就使用了 GQA，顯著提升了推理吞吐量，同時保持了較好的模型效果。

![MHA vs GQA vs MQA Comparison](img/fig-10.png)

不同注意力機制的 Head 對應關係如下：

- **MHA (左)**: 每個 Query Head 都有對應的 Key/Value Head。
- **GQA (中)**: 多個 Query Head 共享一組 Key/Value Head (分組共享)。
- **MQA (右)**: 所有 Query Head 共享同一組 Key/Value Head。

---

## 6. 推薦閱讀與工程實踐

將 KV Cache 技術真正落地到高併發的生產環境中，需要面對記憶體碎片化、首字延遲（TTFT）與吞吐量的綜合博弈。業界已經發展出一系列成熟的系統級最佳化方案，幫助推理引擎在有限硬體下壓榨出極限效能。

### 6.1 工程實踐要點

在真實推理服務中，KV Cache 的最佳化目標通常不是單一指標，而是綜合平衡首字延遲、單 Token 延遲、吞吐與顯存成本。以下是最常見的實踐方向：

1. **TTFT / TPOT 指標分拆最佳化**：
   - TTFT (Time To First Token) 主要受 Prefill 影響，最佳化重點是批處理策略、算子融合與高效排程。
   - TPOT (Time Per Output Token) 主要受 Decode 影響，最佳化重點是 KV 訪存效率與頻寬利用率。

2. **Paged KV Cache（分頁快取）**：
   - 將連續大塊 KV 記憶體切分為頁，按需分配與回收，減少記憶體碎片。
   - 支援更高併發與更靈活的請求排程，是高吞吐推理框架中的常見方案。

3. **KV Cache 量化（如 FP8 / INT8）**：
   - 透過降低 KV 精度顯著減少顯存佔用與頻寬壓力。
   - 需要在速度、顯存收益與精度損失之間做任務級評估。

4. **淘汰與視窗策略（Eviction / Sliding Window）**：
   - 對超長上下文可採用滑動視窗、分段摘要或優先順序淘汰策略。
   - 核心目標是在有限顯存下維持可接受的生成品質與系統穩定性。

### 6.2 推薦閱讀與資源

- **姊妹篇**: [為什麼 GPU 生成每個 token 時利用率不到 5%？——Prefill 與 Decode 深度拆解](../../../prefill_decode/prefill_decode_qkv_calculation.md)（[互動視覺化](../../../prefill_decode/prefill_decode_visual.html) · [校驗指令碼](../../../prefill_decode/prefill_decode_validate.py)） — 從矩陣形狀和計算量層面推導 KV Cache 的數學必然性，以及 compute-bound vs memory-bound 的根因分析。
- **文章**: [KV Caching Explained (Hugging Face)](https://huggingface.co/blog/not-lain/kv-caching) - 本文的主要參考來源。
- **視覺化**: [KV Caching in LLMs, explained visually](https://www.dailydoseofds.com/p/kv-caching-in-llms-explained-visually/) - 包含生動的動畫演示。
- **論文**: [GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints](https://arxiv.org/abs/2305.13245) - GQA 的原始論文。
