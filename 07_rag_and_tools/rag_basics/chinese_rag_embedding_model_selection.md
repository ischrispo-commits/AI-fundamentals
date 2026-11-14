# 中文 RAG 系統 Embedding 模型選型技術文件

## 文件資訊

| 專案     | 內容                           |
| -------- | ------------------------------ |
| 文件版本 | v3.0                           |
| 建立日期 | 2025-06-10                     |
| 更新日期 | 2025-11-01                     |
| 適用場景 | 中文檢索增強生成（RAG）系統    |
| 技術領域 | 資訊檢索、表示學習、向量資料庫 |

---

## 1. 選型背景

### 1.1 核心問題

在 RAG 流水線中，**Embedding 決定了召回的上限**：文件向量化時丟失的語義資訊，後續的 rerank、prompt engineering 都無法補救。選型的失誤會體現為——使用者查詢命中不了相關 chunk、相關 chunk 排在十名開外、長文件被截斷導致關鍵段落丟失。

### 1.2 關鍵權衡

中文場景的選型本質是在三個維度上做妥協：

- **品質**：在真實業務語料上的 `ndcg@10` / `recall@k` 表現
- **成本**：單次推理延遲、顯存佔用、TCO
- **覆蓋**：最大序列長度、跨語言能力、跨領域泛化

沒有一個模型能同時最優——BGE-M3 品質好但 568M 參數推理慢，text2vec-base-chinese 輕但最大 512 token，閉源 API 開箱即用但資料出境且長期價格不可控。

### 1.3 選型目標

產出一套**可落地的決策依據**：給定業務規模、預算、品質要求，能明確指向一個候選模型；並給出後續調優（微調、rerank、混合檢索）的升級路徑。

---

## 2. 評估維度

### 2.1 指標體系與權重

| 維度             | 權重 | 評估口徑                                        |
| ---------------- | ---- | ----------------------------------------------- |
| **中文適配性**   | 30%  | C-MTEB 綜合得分、領域資料覆蓋、tokenizer 友好度 |
| **語義表達能力** | 30%  | 向量維度、長文字處理、查詢-文件非對稱性         |
| **開源可控性**   | 10%  | 許可協議、是否支持本地化、社群活躍度            |
| **推理性能**     | 15%  | 單卡 QPS、P99 延遲、顯存佔用                    |
| **部署成本**     | 10%  | 硬體門檻、運維複雜度、是否可量化/蒸餾           |
| **生態成熟度**   | 5%   | 推理框架支持、向量庫適配、微調工具鏈            |

> 權重按業務調整：強合規場景可把開源可控性提至 20%；API 驅動的原型階段可把部署成本降至 5%。

### 2.2 C-MTEB 基準解讀

**[C-MTEB](https://github.com/FlagOpen/FlagEmbedding/tree/master/C_MTEB)** 由 BAAI 維護，覆蓋 35 箇中文資料集、6 類任務：

| 任務類型       | 資料集示例                           | 核心指標  | RAG 相關性         |
| -------------- | ------------------------------------ | --------- | ------------------ |
| Retrieval      | T2Retrieval、MMarcoRetrieval、CmedQA | ndcg@10   | ★★★★★ 直接對應 RAG |
| Reranking      | T2Reranking、MMarcoReranking         | MAP       | ★★★★☆ rerank 階段  |
| STS            | ATEC、BQ、STS-B                      | Spearman  | ★★★☆☆ 近義匹配     |
| Pair-Class.    | Cmnli、Ocnli                         | AP        | ★★☆☆☆ 蘊含判斷     |
| Clustering     | CLSClusteringS2S                     | V-measure | ★★☆☆☆ 文件聚類     |
| Classification | TNews、IFlyTek                       | Accuracy  | ★☆☆☆☆ 參考價值低   |

> **常見誤區**：直接看 C-MTEB 總榜做決策而忽略任務分佈。開放域問答應重點看 Retrieval 子榜，同義句改寫應重點看 STS。**動態榜單以 [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) 的 zh 標籤頁為準**。

### 2.3 業務場景試金石

僅看 C-MTEB 不夠，真實落地前必須在自有資料上跑三組對照：

1. **領域外術語**：行業黑話、產品代號、專有名詞——檢驗 tokenizer 是否整詞切分還是切成碎片
2. **長文件首段偏置**：截斷 512 / 1024 / 8192 token 時召回率的下降幅度
3. **查詢-文件長度非對稱**：短 query（10–30 token）對長 doc（几百 token）的匹配能力，是 RAG 的主戰場

---

## 3. 候選模型

### 3.1 主流國產 Dense 模型

#### 3.1.1 BGE 系列（BAAI）

- **開源協議**：MIT
- **程式碼倉庫**：[FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding)
- **家族譜系**：v1.5（2023-09）→ M3（2024-01）→ ICL（2024-09）→ VL（多模態）

| 模型              | 參數量 | 向量維度 | 最大長度 | 關鍵能力                                  |
| ----------------- | ------ | -------- | -------- | ----------------------------------------- |
| bge-m3            | 568M   | 1024     | 8192     | 三路輸出（dense + sparse + multi-vector） |
| bge-large-zh-v1.5 | 326M   | 1024     | 512      | 生產首選，穩定性經過廣泛驗證              |
| bge-base-zh-v1.5  | 102M   | 768      | 512      | 價效比最高                                |
| bge-small-zh-v1.5 | 24M    | 384      | 512      | CPU / 邊緣可跑                            |

**選型要點**：

- 絕大多數中文 RAG 場景下，**bge-large-zh-v1.5** 是風險最小的預設值
- 需要長文件（>512 token）或多語言——選 **bge-m3**，並啟用 sparse 分量做混合檢索
- 小模型 bge-small 適合 MVP 或嵌入式部署

#### 3.1.2 Qwen3-Embedding（阿里）

- **发布**：2025 年中
- **協議**：Apache 2.0
- **規格**：0.6B / 4B / 8B 三檔（向量維度分別 1024 / 2560 / 4096，支持 MRL）

繼承 Qwen3 基座的多語言能力，8B 版本在 MTEB 多語言榜單上一度登頂。中文任務上 0.6B 版本即可達到 BGE-large 水准，4B 起在長文字和跨語言上有明顯優勢。適合已有 Qwen 技術棧、追求 SOTA 的團隊，代價是推理成本線性增長。

#### 3.1.3 Conan-Embedding（騰訊 BAC）

- **協議**：**CC BY-NC 4.0（僅限非商業使用）**
- **來源**：騰訊業務安全與內容合規部（TencentBAC），模型卡 [`TencentBAC/Conan-embedding-v1`](https://huggingface.co/TencentBAC/Conan-embedding-v1)
- **特點**：透過 Cross-Lingual Hard Negative Mining 和迭代 hard negative 策略，在 C-MTEB Retrieval 子榜長期保持前列

> ⚠ **當前許可證為 CC BY-NC 4.0，禁止商用**。僅適合研究 / 評測 / 內部原型。商業落地應選 BGE / gte-Qwen2 / Qwen3-Embedding 等 Apache-2.0 或 MIT 模型。

#### 3.1.4 gte-Qwen2（阿里達摩院）

- **基座**：Qwen2-1.5B / 7B
- **協議**：Apache 2.0

基於通用 LLM 做對比學習適配，自然語言理解能力強，適合語義複雜的法律、醫療長文字場景。代價是推理成本顯著高於傳統 encoder-only 模型。

### 3.2 輕量級國產模型

#### 3.2.1 text2vec（shibing624）

- **協議**：MIT
- **代表**：text2vec-large-chinese（330M / 1024d / 512 token）、text2vec-base-chinese（110M / 768d / 512 token）

基於 CoSENT 訓練的 SBERT 風格模型，部署門檻低、推理快。生態以個人專案為主，企業級支援有限；Retrieval 任務上整體落後 BGE 3–5 個百分點。

#### 3.2.2 M3E（MokaAI）

- **協議**：MIT
- **特色**：multi-domain 資料混合訓練，泛化均衡

訓練語料覆蓋電商、新聞、百科、法律等多領域；自 2024 年起更新節奏放緩，被 BGE / Qwen3 趕超。**新專案不再推薦作為首選**，僅作為存量遷移對照基線。

### 3.3 閉源 API 服務

| 供應商 | 模型                   | 向量維度              | 中文品質 | 單價（每百萬 token）              |
| ------ | ---------------------- | --------------------- | -------- | --------------------------------- |
| OpenAI | text-embedding-3-large | 3072（支持 MRL 裁剪） | ★★★★☆    | $0.13                             |
| OpenAI | text-embedding-3-small | 1536（支持 MRL 裁剪） | ★★★☆☆    | $0.02                             |
| Cohere | embed-multilingual-v3  | 1024                  | ★★★★☆    | ~$0.10                            |
| Jina   | jina-embeddings-v3     | 1024（MRL）           | ★★★★☆    | ~$0.02–0.05（以官網最新報價為準） |
| NVIDIA | NV-Embed-v2            | 4096                  | ★★★☆☆    | 自託管                            |

> 閉源 API 的兩大風險：**資料出境合規**、**長期價格不可控**。企業生產環境優先考慮開源自託管；閉源 API 更適合原型驗證和跨境業務。

### 3.4 模型能力矩陣（總覽）

| 模型                   | 參數 | 維度 | 最大 token | MRL | 稀疏輸出 | 多語言 | 定位      |
| ---------------------- | ---- | ---- | ---------- | --- | -------- | ------ | --------- |
| bge-large-zh-v1.5      | 326M | 1024 | 512        | ✗   | ✗        | 弱     | 生產首選  |
| bge-m3                 | 568M | 1024 | 8192       | ✗   | ✓        | 強     | 長文字    |
| Qwen3-Embedding-4B     | 4B   | 2560 | 32K        | ✓   | ✗        | 強     | SOTA 場景 |
| gte-Qwen2-1.5B         | 1.5B | 1536 | 32K        | ✓   | ✗        | 中     | 語義複雜  |
| text2vec-base-chinese  | 110M | 768  | 512        | ✗   | ✗        | 弱     | 輕量原型  |
| m3e-base               | 110M | 768  | 512        | ✗   | ✗        | 弱     | 存量兼容  |
| text-embedding-3-large | API  | 3072 | 8191       | ✓   | ✗        | 強     | 原型驗證  |

---

## 4. 進階：從單模型到檢索系統

Embedding 選型不是終點。真正能把召回率從 80% 推到 95%+ 的，是以下四組組合拳。

### 4.1 混合檢索（Dense + Sparse）

純向量檢索對**精確術語**（產品型號、數字、專名）失效，純 BM25 對**語義改寫**失效。主流實踐是兩路並行 + RRF（Reciprocal Rank Fusion）融合：

```text
query
  ├── dense 通路：BGE 編碼 → Milvus/Qdrant ANN → top-k1
  └── sparse 通路：BM25（或 bge-m3 的 sparse 輸出）→ Elasticsearch → top-k2
        └── RRF 融合 → top-k
```

**BGE-M3 的獨特價值**：單模型同時輸出 dense / sparse / multi-vector（ColBERT 風格）三路，避免維護兩個獨立索引。

### 4.2 Matryoshka 表示學習（MRL）

MRL 訓練時對 `[d/2]`、`[d/4]`、`[d/8]` 等截斷後的向量也施加對比損失，使得**截斷後的向量仍然可用**。工程價值：

- 索引統一存 3072d，查詢時截斷到 768d 做粗排，再用完整向量精排
- 冷資料壓縮到 256d 儲存，儲存成本下降 12×
- 當前支援：text-embedding-3 系列、Jina v3、Qwen3-Embedding、gte-Qwen2

### 4.3 Embedding 與 Rerank 的分工

Embedding 是**雙塔**（bi-encoder）——編碼快但精度有限；Rerank 是**交叉編碼器**（cross-encoder）——精度高但只能對候選做精排。典型流水線：

```text
top-100 召回（bge-large，雙塔，毫秒級）
  → top-20 精排（bge-reranker-v2-m3 或 Cohere Rerank v3，交叉編碼器）
  → top-5 送入 LLM
```

常見誤區是「換更大 Embedding 模型」來提升品質，收益曲線很快飽和；**加一層 rerank 往往能帶來 5–10 個點的 ndcg 提升**，成本收益比遠高於升級基礎 Embedding。

### 4.4 領域微調

通用 Embedding 在**垂直領域黑話**（醫療術語、法條引用、金融專名）上召回率會顯著下降。微調方式按成本遞增：

- **LoRA + 硬負樣本挖掘**：少量 GPU 時，挖掘 BM25 排名 5–20 的文件作為 hard negative
- **全參數精調**：需要 10 萬量級標註對，配 InfoNCE 或 CoSENT 損失
- **檢索-生成聯合訓練**（RAG-specific）：把 LLM 的下游反饋訊號回傳到 Embedding（RAG-end2end）

### 4.5 量化與推理最佳化

| 最佳化手段         | 召回率損失 | 吞吐收益 | 實施難度   |
| ---------------- | ---------- | -------- | ---------- |
| FP16             | <0.1%      | 1.5–2×   | ★ 預設開啟 |
| INT8（動態量化） | 0.5–1.5%   | 2–3×     | ★★         |
| INT4（GPTQ/AWQ） | 2–5%       | 3–4×     | ★★★        |
| ONNX + TensorRT  | 可忽略     | 2–5×     | ★★★        |
| 蒸餾到小模型     | 3–8%       | 5–10×    | ★★★★       |

> **生產建議**：FP16 無腦開；INT8 需在自有驗證集上跑前後對比；INT4 僅在嚴格成本約束下啟用。蒸餾適合 QPS 極高的場景，需要獨立的訓練 pipeline。

---

## 5. 基準測試

### 5.1 測試條件與可復現性宣告

以下資料在 **NVIDIA A100 40GB / CUDA 12.1 / PyTorch 2.3 / batch=32 / seq_len=128 / FP16** 條件下測得。實際效能受硬體代際、批大小、序列長度分佈、併發數影響顯著，**請在目標環境重跑**。C-MTEB 分數以 [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) 的 zh 標籤頁為準。

### 5.2 效果基准（C-MTEB 中文 Retrieval 子榜）

| 模型                   | C-MTEB 綜合 | Retrieval 子榜 ndcg@10 |
| ---------------------- | ----------- | ---------------------- |
| Qwen3-Embedding-8B     | 73+         | 77+                    |
| Conan-Embedding-v1     | 72+         | 76+                    |
| bge-m3                 | 71.4        | 73.9                   |
| bge-large-zh-v1.5      | 68.6        | 71.5                   |
| bge-base-zh-v1.5       | 67.5        | 70.2                   |
| text2vec-large-chinese | 65.2        | 68.1                   |
| m3e-base               | 61.5        | 64.3                   |

> 數字隨榜單更新會變化，**相對排序比絕對數字更值得參考**。

### 5.3 推理性能基准

| 模型                  | QPS（A100，FP16） | 顯存佔用 | 單條向量儲存（float32） |
| --------------------- | ----------------- | -------- | ----------------------- |
| bge-m3                | ~800              | 3.2 GB   | 4.0 KB                  |
| bge-large-zh-v1.5     | ~1,200            | 2.1 GB   | 4.0 KB                  |
| bge-base-zh-v1.5      | ~2,800            | 0.8 GB   | 3.0 KB                  |
| text2vec-base-chinese | ~3,200            | 0.6 GB   | 3.0 KB                  |
| Qwen3-Embedding-0.6B  | ~1,500            | 1.4 GB   | 10.0 KB（2560d）        |

> 儲存成本推導：`float32 × 維度 / 1024`；啟用 INT8 量化後再縮小 4×；MRL 截斷按比例縮小。

---

## 6. 選型決策

### 6.1 決策矩陣（資料驅動）

| 模型                   | 中文品質（30%） | 語義能力（30%）   | 開源可控（10%） | 推理性能（15%） | 部署成本（10%） | 生態（5%） | 綜合   |
| ---------------------- | --------------- | ----------------- | --------------- | --------------- | --------------- | ---------- | ------ |
| bge-large-zh-v1.5      | A（68.6）       | A（1024 / 512）   | A（MIT）        | A（1200 QPS）   | B（需 GPU）     | A          | **A**  |
| bge-m3                 | A+（71.4）      | A+（8192 / 三路） | A               | B（800 QPS）    | C（高顯存）     | A          | **A**  |
| Qwen3-Embedding-4B     | A+（72+）       | A+（32K + MRL）   | A               | C（4B 參數）    | C（需高端 GPU） | B          | **A-** |
| bge-base-zh-v1.5       | B+（67.5）      | B+（768 / 512）   | A               | A+（2800 QPS）  | A（中端 GPU）   | A          | **A-** |
| text2vec-base-chinese  | B（63.8）       | B（768 / 512）    | A               | A+（3200 QPS）  | A+（CPU 可跑）  | B          | **B+** |
| text-embedding-3-large | A（API 穩定）   | A（3072 + MRL）   | D（閉源+出境）  | N/A             | B（按量付費）   | A          | **B**  |
| m3e-base               | B-（61.5）      | B（768 / 512）    | A               | A（3500 QPS）   | A+              | C          | **C+** |

> 綜合評級原則：中文品質 < 60 直接降一檔；開源性為 D 的額外扣一檔；推理 QPS < 500 扣一檔。

### 6.2 場景化選型

| 業務場景                       | 推薦模型                                      | 核心理由                           |
| ------------------------------ | --------------------------------------------- | ---------------------------------- |
| 生產級通用 RAG（預設首選）     | **bge-large-zh-v1.5**                         | 品質-成本-生態三角平衡最優         |
| 長文件 / 多語言 / 混合檢索     | **bge-m3**                                    | 8K 長度 + dense/sparse/multi-vec   |
| 追求 SOTA 品質，預算充裕       | **Qwen3-Embedding-4B / 8B**                   | 2025 年開源第一梯隊                |
| 成本敏感 / 邊緣側部署          | **bge-small-zh-v1.5 / text2vec-base-chinese** | CPU 可跑，量化后可 INT8            |
| 原型驗證 / 資料合規寬鬆        | **text-embedding-3-small**                    | 無須運維，MRL 支援降維             |
| 已有 Qwen 技術棧               | **gte-Qwen2-1.5B / Qwen3**                    | 複用 LLM 基建，推理棧共享          |
| 垂直領域（醫療 / 法律 / 金融） | bge-large + LoRA 微調                         | 通用模型 + 領域 hard-negative 微調 |

### 6.3 決策樹

```text
是否允許資料出境 / 閉源依賴?
├── 否（企業主流）
│   ├── 單次查詢 ≤ 512 token?
│   │   ├── 是
│   │   │   ├── 預算充裕 + 追求 SOTA → Qwen3-Embedding-4B
│   │   │   └── 否 → bge-large-zh-v1.5   ★ 最常見落點
│   │   └── 否（長文件 / 多語言）→ bge-m3
│   └── 需要 CPU / 邊緣部署 → text2vec-base-chinese 或 bge-small-zh-v1.5
└── 是（資料出境 OK / 跨境業務）
    └── text-embedding-3-large / Cohere v3 / Jina v3
```

---

## 7. 部署實施

### 7.1 參考架構

```text
┌─────────────────────────────────────────────────┐
│ 應用層（RAG Orchestrator / LangChain / LlamaIndex）│
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼─────────┐
│ Embedding 服務 │   │ Reranker 服務    │
│（FastAPI+TEI） │   │（bge-reranker）  │
└───────┬────────┘   └──────────────────┘
        │
┌───────▼─────────────────────────────────┐
│ 向量庫（Milvus / Qdrant / Weaviate）    │
│   ├── dense 索引（HNSW / IVF-PQ）       │
│   └── sparse 索引（BM25 / SPLADE）      │
└─────────────────────────────────────────┘
```

**推薦推理框架**：[Text Embeddings Inference (TEI)](https://github.com/huggingface/text-embeddings-inference) —— Rust 實現，支持 ONNX / FP16 / Flash Attention / 動態 batch 合併，實測相對樸素 Transformers Python 推理通常可達 **2–3× 加速**（具體倍數依賴模型大小、batch、硬件，需自行基准）。

### 7.2 硬體規劃參考

| 文件規模       | 最小配置                    | 推薦配置            |
| -------------- | --------------------------- | ------------------- |
| <100 萬        | RTX 4090 + 32 GB RAM        | A100 40GB           |
| 100 萬–1000 萬 | A100 40GB × 1 + 64 GB RAM   | A100 80GB × 2       |
| >1000 萬       | A100 80GB × N + 128 GB+ RAM | H100 × N + 10G 內網 |

> 上表針對**線上 embedding 推理**；離線構建索引可以用更低配額 + 更長時間完成。

### 7.3 關鍵監控指標

- **性能**：P95/P99 推理延遲、QPS、batch 命中率
- **品質**：召回率@k、ndcg@10、使用者點選率、「零召回率」日志
- **資源**：GPU 利用率、顯存、P99 佇列長度
- **穩定性**：錯誤率、模型版本漂移告警、向量庫一致性

### 7.4 常見效能陷阱

1. **padding 浪費**：變長序列不做 sorted-batch，長序列拖累整批——TEI 預設解決
2. **冷啟動**：首次載入模型權重 >10s，生產必須 warm-up
3. **向量庫參數失配**：HNSW 的 `efConstruction` 過小導致召回斷崖，典型值 200–400
4. **歸一化遺漏**：餘弦相似度前必須 L2-normalize；許多模型輸出已歸一化，重複歸一化無害，但忘做會造成災難
5. **版本混用**：訓練期和推理期使用不同 tokenizer 版本，向量空間漂移不可感知

---

## 8. 風險與規避

| 風險類別     | 具體表現                        | 規避策略                                 |
| ------------ | ------------------------------- | ---------------------------------------- |
| 模型漂移     | 升級新版本導致線上指標下降      | A/B 灰度 + 版本化索引 + 可回滾           |
| 領域外效果差 | 垂直術語召回率驟降              | 準備領域評測集 + LoRA 微調路徑           |
| 成本失控     | 呼叫量猛增導致 GPU 池打滿       | 自動擴縮容 + 快取熱點查詢向量 + 量化降檔 |
| 資料合規     | 使用閉源 API 導致敏感資料出境   | 本地化部署 + 敏感欄位預處理脫敏          |
| 向量庫耦合   | 維度 / 距離度量變更引發全庫重建 | 索引設計預留遷移視窗 + 雙寫過渡期        |

---

## 9. 參考資料

### 9.1 基準與榜單

- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)（動態更新）
- [C-MTEB 倉庫](https://github.com/FlagOpen/FlagEmbedding/tree/master/C_MTEB)

### 9.2 模型與論文

- [BGE 系列 / FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding)
- [BGE-M3 論文（2024）](https://arxiv.org/abs/2402.03216)
- [Qwen3 技術報告](https://github.com/QwenLM/Qwen3)
- [text2vec](https://github.com/shibing624/text2vec)
- [M3E / uniem](https://github.com/wangyuxinwhy/uniem)
- [Matryoshka Representation Learning（2022）](https://arxiv.org/abs/2205.13147)
- [MTEB: Massive Text Embedding Benchmark（2022）](https://arxiv.org/abs/2210.07316)
- [Sentence-BERT（2019）](https://arxiv.org/abs/1908.10084)

### 9.3 工程與部署

- [Text Embeddings Inference (TEI)](https://github.com/huggingface/text-embeddings-inference)
- [Milvus 向量庫](https://milvus.io/)
- [Qdrant 向量庫](https://qdrant.tech/)
- [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)

### 9.4 延伸閱讀

- [大模型 RAG 基礎：資訊檢索、文本向量化及 BGE-M3 embedding 實踐](https://arthurchiao.art/blog/rag-basis-bge-zh/)
- [智源研究院官網](https://www.baai.ac.cn/)
