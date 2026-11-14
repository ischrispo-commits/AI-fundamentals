# PagedAttention：當 KV Cache 遇到作業系統分頁

你還記得作業系統課上一個經典的場景嗎：一塊 4 GB 的實體記憶體，同時跑著瀏覽器、IDE、終端十幾個行程，每個行程都以為自己獨佔全部地址空間。這個"幻覺"靠的是**虛擬記憶體分頁**——實體記憶體切成 4 KB 的頁框，行程看到的是連續的虛擬地址，背後由頁表偷偷翻譯成散落在實體記憶體各處的真實地址。

現在把鏡頭從 CPU 記憶體切到 GPU 顯存。一塊 H100 有 80 GB HBM，上面跑著推理服務，同時處理幾十個併發請求，每個請求都在往 KV Cache 裡追加資料。**同樣的問題出現了**：連續預分配引發大量碎片，有效利用率只有 20-40%。

PagedAttention 的思路直截了當：**既然作業系統用分頁解決了記憶體碎片，GPU 顯存為什麼不能？** 把 KV Cache 切成固定大小的 block，每個請求維護一張 block table，按需分配、動態對映——有效利用率從 20-40% 提升到接近 100%。

> **互動視覺化**：[PagedAttention — 傳統預分配 vs 分頁管理](02_paged_attention_visual.html) — 6 步並排對比，鍵盤 ← → 翻頁。

---

## 一、KV Cache 讓推理成為可能，但也製造了一個新瓶頸

### 1.1 為什麼需要 KV Cache

自迴歸生成中，每產生一個新 token，模型都需要與歷史上所有 token 做注意力計算。如果每步都重新算一遍所有历史 token 的 K 和 V，單步注意力計算量是 $O(N^2)$——當前序列長度 $N$ 越大，每步的矩陣乘法越重，不可接受。

KV Cache 的做法很自然：**把已經算好的 K 和 V 快取起來，新 token 只算自己的 Q、K、V，然後從快取中讀取歷史的 K 和 V**。Decode 單步的計算量從 $O(N^2)$ 降到了 $O(N)$。代價是**每生成一個 token，快取就大一圈**。

### 1.2 這個"大一圈"究竟有多大

以 Llama-2 70B（GQA, num_kv_heads=8, head_dim=128, 80 layers, FP16）為例，每個 token 每層的 KV Cache 是 4 KB。乘上 80 層，每個 token 的完整 KV Cache 約 320 KB。再乘上序列長度：

| 序列長度 | 單請求 KV Cache | batch=8 | batch=32 |
| :------: | :-------------: | :-----: | :------: |
|  2,048   |     0.6 GB      |  5 GB   |  20 GB   |
|  8,192   |     2.5 GB      |  20 GB  |  80 GB   |
|  32,768  |      10 GB      |  80 GB  |  320 GB  |

模型權重本身約 140 GB（FP16）。當 batch=8, seq_len=8192 時，KV Cache（20 GB）還是可控的附加開銷。但 push 到 batch=32, seq_len=32768——**KV Cache 膨脹到 320 GB，是模型權重的 2.3 倍**。

這意味著推理服務的顯存瓶頸不再是模型權重，而是那個動態增長的 KV Cache。**你不僅需要存它，還需要高效地管理它。**

---

## 二、預分配：最直覺的方案，最嚴重的浪費

### 2.1 一個看似合理的做法

KV Cache 需要存在 GPU 顯存裡。面對"一塊 tensor 要不斷往尾部追加資料"這個需求，最直接的方案是：在推理開始時，給每個請求預分配一塊連續顯存，大小為 `max_model_len × per_token_bytes`。

這很自然。GPU 上的 tensor 不就是連續記憶體嗎？`cudaMalloc` 返回的不就是連續地址嗎？一次分配比反覆分配+複製簡單得多。

### 2.2 但這個方案有兩個制度性缺陷

**預留浪費（reservation waste）**[^1]：預分配的是**最大可能長度**，但實際生成的 token 數通常遠小於上限。`max_model_len=32768`，而使用者 prompt 只有 2,000 token——那 30,768 token 的空間被白白鎖定。vLLM 論文將這種"為未來預留但從未使用"的空間定義為 reservation waste。即使系統知道精確輸出長度，這種浪費也不可避免。

**外部碎片（external fragmentation）**：不同請求的完成時間不同。短請求先結束，釋放的空間留下空洞——這些空洞可能不夠容納下一個請求，即使**總空閒空間是夠的**。

這正是作業系統在 1960 年代就遇到過的問題：連續記憶體分配下，程式來來去去，記憶體里布滿碎片。

### 2.3 作業系統在半個世紀前給出了答案

作業系統解決這個問題的方式今天已成為常識：把實體記憶體切成固定大小的**頁**（通常是 4 KB），程式看到的是連續虛擬地址，背后由**頁表**將每個虛擬頁對映到任意物理頁框。一個 100 MB 的程序，不需要找一塊 100 MB 的連續實體記憶體——只要有 25,000 個空閒頁框，散落在任何位置都行。

頁表就是翻譯器：CPU 發出虛擬地址，MMU 查頁表，找到對應的物理頁框。程式完全不知道它的資料在物理上是如何分佈的。

### 2.4 GPU 遇到了完全一樣的問題，但沒人給它做 MMU

GPU 顯存面臨同樣的碎片困境。不同的是，GPU 沒有硬體 MMU——CUDA kernel 看到的是線性地址空間，`cudaMalloc` 返回連續地址。

但"沒有硬體 MMU"並不意味著"不能做分頁"。硬件做不了的事，**軟體可以做**。這，就是 PagedAttention 的起點。

[^1]: vLLM 論文嚴格區分了三種浪費：**reservation waste**（為未來 token 預留的空間）、**internal fragmentation**（單個 block 內未填滿的 slot，PagedAttention 下最多 1 block/請求）、**external fragmentation**（不同大小塊導致的不可用空洞）。預分配方案的主要浪費來自 reservation waste，PagedAttention 消除的也是它。本文 §五.3 討論的才是論文定義的 internal fragmentation。

---

## 三、PagedAttention：在 GPU 上手工實現分頁

### 3.1 三步走——切塊、映射、按需分配

既然 CPU 記憶體的分頁機制已經解決了碎片問題，PagedAttention 的設計直接翻譯這個方案：把硬件 MMU 換成軟體實現的 block table。

**第一步：切塊。** KV Cache 不再以"整個序列"為單位分配，而是切成固定大小的 **KV block**。每個 block 儲存 `block_size` 個 token 在某層的 K 和 V。以 GQA 模型（8 KV heads, head_dim=128, block_size=16, FP16）為例：

```text
一個 block 的物理內容（單層）:
  K: (16, 8, 128) × 2 bytes = 32 KB
  V: (16, 8, 128) × 2 bytes = 32 KB
  合計: 64 KB / block / layer
```

block 是 KV Cache 管理的**最小分配單位**——就像作業系統的 4 KB 頁框。

**第二步：映射。** 每個請求維護一張 **block table**，記錄邏輯 block 到物理 block 的對應關係：

```text
請求 A 的 Block Table:
  logical_block[0] → physical_block[#42]
  logical_block[1] → physical_block[#17]
  logical_block[2] → physical_block[#89]
```

請求 A "以為"它的 KV Cache 是 `[block_0, block_1, block_2, ...]` 這樣連續的邏輯序列，但實際上這三個 block 可以散落在 GPU 顯存的任意位置。**邏輯連續，物理分散**——分頁的本質被完整保留。

**第三步：按需分配。** 請求開始時只分配第一個 block。Token 一個個生成，block 一個個追滿。追滿一個後，從空閒池中取一個新 block 掛到 block table 末尾。不再需要預測最終長度。

```text
OS 虛擬記憶體                      PagedAttention
─────────────────────────────────────────────────
物理頁框 (Page Frame)     →    KV Block
頁表 (Page Table)         →    Block Table
頁表項 (PTE)              →    block_table[i] = physical_block_id
MMU 地址翻譯              →    Attention kernel 查表 gather
按需調頁 (Demand Paging)  →    按需 block 分配
```

### 3.2 注意力計算怎麼辦——軟體 MMU 的開銷

有了 block table，每個請求的 K 和 V 就可以散落儲存。但 attention 計算怎麼辦？

OS 有 MMU 在硬體層面透明翻譯地址——CPU 執行 `mov eax, [ebx]`，MMU 自動將虛擬地址 `ebx` 翻譯為實體地址。**GPU 沒有這個。** Attention kernel 必須自己查 block table，逐個 block 做 gather：

```text
for each logical_block_id in range(num_blocks):
    physical_block = block_table[logical_block_id]    // 軟體查表
    k_block = load_k_from(physical_block)              // gather
    v_block = load_v_from(physical_block)

    scores = Q @ k_block.T                             // 分塊計算
    output = update_online_softmax(output, scores, v_block)
```

vLLM 為此實現了專門的 CUDA kernel——本質上是**用軟體實現了一個 GPU 版的 MMU**，翻譯的是 "logical_block_id → physical_block_addr"。

### 3.3 Block Size 的選擇——作業系統也要選頁大小

Block size 決定了碎片粒度和管理開銷的平衡點：

|  block_size   |   碎片粒度   | Block Table 大小 |    Kernel 效率     | 適用場景         |
| :-----------: | :----------: | :--------------: | :----------------: | ---------------- |
|   小 (8~16)   | 細，利用率高 | 大，VRAM 開銷多  |   launch 次數多    | 通用場景         |
| 大 (128~256)  | 粗，可能浪費 |    小，開銷低    | 單次處理更多 token | 長序列、壓縮模型 |
| **16 (預設)** |      —       |        —         |         —          | GQA/MHA 模型     |
| **256 (V4)**  |      —       |        —         |         —          | CSA/HCA 壓縮模型 |

vLLM 預設 block_size=16，單層每個 block 僅 64 KB。DeepSeek-V4 推薦 256——CSA/HCA 壓縮後單個 token 的 KV 極小（平均 ~169 B），小 block 會導致 block table 條目激增。

---

## 四、效果：不只是利用率數字的變化

### 4.1 紙面資料

分頁方案的效果有多顯著？vLLM 論文的對比給出了答案：

| 方案                        | 有效 KV Cache 利用率 | 浪費來源               | 同等顯存下的併發上限 |
| :-------------------------- | :------------------: | :--------------------- | :------------------: |
| Orca (Max)                  |        20.4%         | reservation + external |          1×          |
| Orca (Pow2)                 |        32.0%         | reservation + external |        ~1.6×         |
| Orca (Oracle, 已知輸出長度) |        38.2%         | 純 reservation waste   |        ~1.9×         |
| **vLLM (PagedAttention)**   |      **~100%**       | ≤ 1 block/請求         |       **2-4×**       |

> 資料來源：vLLM 論文 Table 1。即使系統提前知道每個請求的精確輸出長度（Orca Oracle），預留浪費仍佔 61.8%——預分配的浪費是**結構性的**，不是調參問題。PagedAttention 透過按需分配消除了 reservation waste，僅剩每個請求最後一個 block 未填滿的 internal fragmentation（≤ `block_size - 1` 個 token）。

### 4.2 換個角度看：同一塊 GPU 能多跑多少請求

假設 GPU 可分配 40 GB 用於 KV Cache，服務 Llama-2 70B：

```text
傳統預分配 (max_len=8192):
  每請求預分配 = 8192 × 4 KB × 80 = ~2.5 GB
  最多併發 = 40 / 2.5 ≈ 16 個請求
  但實際平均長度只有 3000 → 實際佔用僅 37%
  40 GB 中有 25 GB 白白浪費

PagedAttention:
  16 個請求實際佔用 = 16 × 3000 × 4 KB × 80 ≈ 15 GB
  剩余 25 GB 還能服務更多請求
  按動態增長持續分配，最多可支持 ~40 個併發

  吞吐提升: 2.5×
```

**同樣的硬體，同樣的模型，吞吐翻了 2.5 倍。** 沒有 GPU 升級，沒有量化壓縮，沒有模型修改——僅僅改變了"怎麼存"。

### 4.3 Block 抽象之上自然生長的能力

分頁帶來的不只是碎片消除。**寫時複製（Copy-on-Write）**、**共享記憶體**、**按需調頁**——這些 OS 特性都是在分頁抽象上自然生長的。PagedAttention 也一樣。

**Prefix Caching**：相同 prompt 字首的 block 可以在多請求間共享——多個 block table 指向相同物理 block。vLLM 的 Automatic Prefix Caching (APC) 不需要額外架構，只是 block manager 分配時多做一次 hash 比對。

**靈活的記憶體分層**：Block 粒度讓 offloading 不需要搬動整個序列。按 block 級別做 CPU/NVMe 換入換出，比搬動 GB 級連續 tensor 靈活得多。

---

## 五、權衡：軟體 MMU 不是免費的

### 5.1 翻譯開銷——沒有 TLB 的分頁

OS 有硬件 MMU 和 TLB，查頁表的開銷被壓到幾乎為零。PagedAttention 每次 attention 計算都要遍歷 block table 逐個 block gather。這個"軟體 MMU"的開銷直接體現在 kernel 執行時間上。

vLLM 的緩解手段：kernel 內預載入 block table 到寄存器或 shared memory，批量 gather 減少記憶體事務，分塊 softmax 融合計算。好在 memory-bound 的 Decode 場景下，這個開銷可以被記憶體延遲部分掩蓋。

### 5.2 Block Table 自身也佔顯存

每個請求的 block table 也是一塊顯存。block_size=16, seq_len=32768 時，單請求 block table 有 `32768/16=2048` 條目 × 8 bytes = 16 KB。100 併發約 1.6 MB。block_size 減到 8 則翻倍至 3.2 MB。雖整體可控，但它是"碎片粒度 vs 管理開銷"天平上的一個砝碼。

### 5.3 Internal Fragmentation 的最后一公里

即使 block 粒度，序列長度不是 `block_size` 的整數倍時，最後一個 block 會有部分 slot 未使用——每個請求最多浪費 `block_size - 1` 個 token。block_size=16 時平均浪費 8 個 token（~32 KB），佔單請求 KV Cache 的比例隨序列增長趨近於零。量級上可接受，但不是零。

---

## 六、抽象層之上的天空

PagedAttention 的 block 抽象已成為事實標準。其他 KV Cache 最佳化都在這個基礎上疊加：

```text
        ┌─────────────────────┐
        │    Prefix Caching   │ ← block 級共享，APC
        ├─────────────────────┤
        │    KV Offloading    │ ← block 粒度的 CPU/NVMe 換入換出
        ├─────────────────────┤
        │    KV 量化 (FP8)     │ ← block 內部壓縮，kernel 反量化
        ├─────────────────────┤
        │    PagedAttention   │ ← 基礎抽象層：碎片消除 + 按需分配
        └─────────────────────┘
```

Block 是這一切的**通用組織單位**。沒有它，Prefix Caching 的共享需要額外資料結構，Offloading 需要搬動連續大塊記憶體，量化需要重新設計整個記憶體佈局。

PagedAttention 的設計者洞見到了這一點：**好的抽象不是疊加功能，而是讓功能自然生長。**

---

## 七、小結

PagedAttention 回答了一個簡單但影響深遠的問題：**KV Cache 到底該怎麼存？**

從作業系統半個世紀前的分頁方案中借來洞見，用軟體在 GPU 上實現了一個輕量級 "MMU"，把有效利用率從 20-40% 提升到接近 100%。Block 抽象成為 Prefix Caching、Offloading、量化等上層最佳化的共同基礎。

> 預分配連續記憶體 → 利用率僅 20-40%（1960 年代 OS 碎片問題的翻版）
> 引入分頁 → 利用率接近 100%（OS 的答案，在 GPU 上用軟體再做一遍）
> Block 抽象 → Prefix Caching、Offloading、量化自然疊加

工程上最優雅的解決方案，往往不是發明一個新東西，而是**把另一個領域已經驗證了半個世紀的方案，帶到一個新場景裡**。

---

## 相關閱讀

- [互動視覺化：傳統預分配 vs PagedAttention](02_paged_attention_visual.html) — 6 步並排對比，鍵盤 ← → 翻頁
- [KV Cache 原理簡介](01_kv_cache_basics.md) — 本文依賴的 KV Cache 基礎概念與顯存公式
- [不同注意力類型的 KV Cache 到底長什麼樣](05_attention_kv_cache_formats.md) — GQA/MQA/MLA/CSA-HCA 下 block 物理形狀的變化
- [Prefix Caching 原理分析](../02_prefix_caching/02_prefix_caching.md) — PagedAttention 之上的 block 級複用
- [KV Cache Offloading 分析](../07_offloading/01_kv_offloading.md) — block 粒度的儲存層次遷移
- [vLLM 論文: Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180) — 原始論文
- [vLLM v1 架構: KVCacheGroupSpec](https://github.com/vllm-project/vllm/blob/main/vllm/v1/kv_cache_interface.py) — 多注意力類型 block 池的原始碼實現（`KVCacheGroupSpec` 資料類定義在 `kv_cache_interface.py:1410` 附近）
