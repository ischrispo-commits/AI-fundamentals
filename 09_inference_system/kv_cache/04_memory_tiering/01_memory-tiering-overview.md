# 當 KV 裝不進顯存：四篇論文的四種記憶體賬，與一個「統一名稱空間 + 成本旋鈕」的設想

> **元信息**：本文是「KV Cache 記憶體層級」系列總綱。系列含四篇單篇精讀：[DirectKV](02_directkv.md)（OSDI '26，零複製去搬運）· [NEO](03_neo.md)（MLSys 2025，計算下移）· [eLLM](04_ellm.md)（DAC 2026，抽象虛擬化）· [Strata](05_strata.md)（OSDI '26，分層排程），每篇都附逐條頁碼核對的精讀報告（`references/`），論文原文 PDF 在 `references/papers/`。本文只做橫向組織與口徑提示，機制細節與數字以單篇為準。整理日期 2026-10-12。

兩個數字放在一起，能看出這個交叉點的分裂。DirectKV 的圖 2(a)：同一個 10240 方陣乘法，用 200 MB 顯存緩衝把 CPU 記憶體裡的資料換進來（swap），PCIe 上 65 ms；換成零複製、讓 GPU 直接讀 CPU 記憶體，1122 ms，慢 17 倍（p.42）。而 NEO 在 T4 上把 decoding attention 連同 KV 一起卸給 CPU，吞吐反而最高漲 7.5 倍（合成負載掃描峰值，§5.4，pp.8–9）。

同一個總前提——KV 裝不下顯存——一邊是「別碰這套搬運」，一邊是「搬出去反而贏」。兩個答案都只在特定條件下成立：DirectKV 的小前提是 NVLink-C2C，NEO 的小前提是小顯存 GPU 加上大容量本地 CPU。把四篇論文並排看，看的不是誰更好，而是每種賬本各自記在什麼條件下。這些條件裡，哪些是物理的（頻寬與容量的台階），哪些只是接口的（訪問方式差異、成本不可見），決定了這四筆賬接下來會怎麼走。§五 把這條線展開。

## 一、同一個問題，四個拆法

KV cache 按序列長度線性增長，HBM 裝不下之後，每一層外部記憶體都在拿三樣東西做交換：頻寬（搬得動嗎）、延遲（藏得住嗎）、容量與利用率（放著划算嗎）。四篇論文在四個不同位置動手：

- **DirectKV 動的是搬運這個動作本身**：既然最貴的是「先搬進 HBM 再算」，就把 staging buffer 刪掉，讓 attention kernel 直接讀 CPU 側 KV；
- **NEO 動的是被搬的物件**：KV 之所以要搬回 GPU，是因為計算在 GPU 上；那就把 decoding attention 的計算一起挪到 CPU，KV 乾脆不回來；
- **eLLM 動的是賬本的邊界**：activation 和 KV cache 分屬兩套記憶體抽象、兩個池子，一邊爆滿一邊閒置；把物理層併成一本賬，互相借；
- **Strata 動的是搬運的路徑與排程**：搬運保留，但把 I/O 從 DMA 引擎換到 GPU 數千執行緒手裡、把布局解耦、再把搬運藏進 cache-aware 排程。

| 論文（單位）                    | 場景定位                                | 核心矛盾                                    | 招式                                            | 代表賬本                                       |
| ------------------------------- | --------------------------------------- | ------------------------------------------- | ----------------------------------------------- | ---------------------------------------------- |
| DirectKV（弗吉尼亞大學）        | 節點內長上下文 · GH200/GB200 高頻寬互聯 | staging buffer 雙程搬運、大緩衝蓋延遲       | 零複製直讀 + tiling / warp 流水 / kernel fusion | 傳輸量最高 -50% · 顯存 -43% · 端到端 1.2×      |
| NEO（UC Berkeley + Harvard）    | 小顯存 GPU + 線上服務                   | decode attention 的 KV 卡死 batch、CPU 空轉 | decoding attention 下移 CPU + 非對稱流水線      | T4 合成峰值 7.5× · 線上最高 +563%              |
| eLLM（上海交大 + 期智研究院等） | vLLM 單機 · activation 與 KV 互擠       | 兩套記憶體抽象互不借賬（空間內部碎片）        | eTensor 統一池 + inflation / deflation          | 解碼吞吐 2.32× · goodput 2.5×                  |
| Strata（Stanford + NVIDIA）     | SGLang 系分層快取 · agent/長上下文負載  | 小頁喂不飽互聯、排程看不見搬運              | GPU-assisted I/O + cache-aware 三件套           | 同 TTFT 峰值 5× · GH200 頻寬 40.3 → 150.5 GB/s |

口徑說明：數字均為論文自測，對照基線各不相同，引用前先過 §六「數字怎麼讀」。

![同一個問題，四個拆法：四篇論文的四個動手位置](../../assets/mtier-panorama-four-takes.svg)

## 二、四條路線

### 2.1 去搬運：DirectKV（OSDI '26）

既有 offload 方案的共同假設是「KV 必須先到 HBM」（p.39）。這條假設帶來三筆代價：預留大塊 GPU 緩衝蓋延遲、swap 讓互聯流量翻倍、`cudaMemcpyAsync` 的動態地址讓 CUDA Graph 無法原樣重放（p.41）。DirectKV 押注的是硬體變化：GH200/GB200 的 NVLink-C2C 有 900 GB/s（"7× higher than PCIe Gen5"，p.39），零複製的細粒度訪問在這條通道上能湊出 MB 級聚合流量，決定效能的從單次延遲變成持續頻寬。

機制三招：**CPU-aware tiling** 把矩陣乘裡"駐留"的運算元從 CPU 側換成 HBM 側（B tile 只取一次，流量 O(n³) 降到 O(n²)，換 HBM 流量約 2×，p.42–43）；**warp 級流水**用 producer/consumer/storer 三個 warp group 把搬運藏進計算（HBM 吞吐 0.3 → 1.3 TB/s，p.43）；**kernel fusion** 把 QKV projection 與 attention 合成一次 launch，K/V 生成后留在 SMEM 直接被消費，不回 CPU 記憶體兜圈（延遲 85 → 57 ms，p.43）。

賬本（GH200，對 offload 系統基線）：傳輸量最高降 50%、顯存 47 GB（對照 offload 系統均值 82.7 GB，降 43%）、端到端平均 1.2×（p.48–49）。前提取自論文自己的邊界宣告：高頻寬互聯是硬條件，"on PCIe-only platforms … throughput benefits are often limited"（p.50）。

![DirectKV：刪掉 staging buffer 的零複製路徑](../../assets/mtier-directkv-zerocopy.svg)

### 2.2 挪計算：NEO（MLSys 2025）

NEO 的起點是一句反向的前提檢查：decoding attention 在 GPU 和 CPU 上都是 memory-bandwidth-bound，而兩類硬體的頻寬差距遠小於算力差距：A10G 的 600 GB/s 對現代 x86 伺服器的約 200 GB/s，只差約 3 倍，算力差約 100 倍（§2.2，p.3）。既然瓶頸是頻寬，把這段計算搬去 CPU 的損失就有限；而騰出來的顯存能換更大的 batch。

機制是 **asymmetric pipelining**（partial offloading + prefill 併入 batch-0 + layer-wise swapping + asymmetric batch division，§3.1，p.5）加**負載感知排程**（每迭代六步、始終保留退回 GPU-only 的選項，§3.2，p.6）。論文先用兩個 strawman 劃掉錯誤答案：全量解除安裝讓 CPU 線上性層階段空轉；均分的對稱流水線既閒置 GPU 記憶體又製造 bubble（§3.1，p.4–5）。

賬本分兩組口徑：合成負載掃描對 GPU-only 基線，T4/A10G/H100 最高 +750% / +26% / +14%（§5.4，pp.8–9）；真實線上對 vLLM、固定時延點，是 14.3% / 6.40% / 563%（§5.2，p.7）。CPU 容量敏感性顯示增益由**頻寬而非核數**決定（§5.5，p.9）。前提：大容量本地 CPU 記憶體（"NEO relies on large CPU memory"，p.10）、權重全部駐留 GPU。

![NEO：decoding attention 下移與非對稱流水線](../../assets/mtier-neo-cpu-attention.svg)

### 2.3 並賬本：eLLM（DAC 2026）

論文把「activation 預留按最壞情況、使用按典型情況」的錯位量化了：MTP-30B 的上下文從 2K 調到 200K 時，為激活預留的顯存佔比從 0.3% 漲到 30.8%，而 decoding 階段激活利用率約 1%（p.2）。兩塊記憶體分屬兩套抽象（activation 走靜態張量分配、KV 走頁表虛擬化），誰也不認識對方的賬本，論文稱之為 **space-wise internal fragmentation**，「leading to suboptimal utilization and 20% throughput degradation」（p.1）。

eLLM 的抽象叫 **eTensor**：邏輯層保留兩套定製化管理，物理層共享一個統一記憶體池（p.3）。KV 池不夠時向 activation 池 inflation：輕量 GC 回收不活躍塊、只轉所有權不搬資料、再按需對映進目標虛擬地址空間；deflation 惰性歸還（p.4）。第二級彈性把 CPU DRAM 當溢位 buffer，靠 layer-wise pipelining 把 O(N) 的 KV 傳輸藏進 O(N²) 的 prefill 計算（p.4）。排程按 SLO 分階段調整 logical buffer 的可用尺寸（p.4）。

賬本：解碼吞吐最高 2.32×（128k-4k 離線配置、Jamba-Mini、2 GPU，p.6），goodput 最高 2.5×（p.5）。代價論文自己認：CPU buffer 引入 prefill 偏好、TPOT 高於 vLLM（p.5），PCIe 頻寬是無法完全重疊的上限（p.6）。前提：單機 A100 + 大 CPU DRAM + PCIe。實現未開源（vLLM v0.5.5 上約 4000 行修改）。

![eLLM：eTensor 統一記憶體池與 inflation / deflation](../../assets/mtier-ellm-elastic-pool.svg)

### 2.4 重排排程：Strata（OSDI '26）

Strata 的起點是一組「搬運效率」的實測：8192 個 token 的 KV 從 CPU 記憶體搬回 GPU，只吃到 PCIe 5.0 理論頻寬的約 22%；換 GH200 用 NVLink，這個比例掉到 5%（p.3–4）。根因是頁太小：PagedAttention 為省顯存把 KV 切成 1–32 token 的頁，單頁幾十 KB 喂不飽互聯（p.2–4）。按 Little's Law `X = C·S/L`，要吃滿 PCIe 需要 1–2MB 的單次傳輸（p.3），但放大頁會讓命中率塌掉（頁 1→512，P90 TTFT 最高漲 2.9×，p.3）。

機制分兩條線。**搬運線**：GPU-assisted I/O，不再发 cudaMemcpyAsync 傳小塊，而是 launch kernel、數千執行緒直接讀源寫目標，128 bytes 粒度就高效（2 block × 1024 執行緒達成 48 GB/s，prefill 干擾 <5%，p.5）；同一套執行緒順帶完成 layer-first ↔ page-first 的佈局轉換，"negligible overhead"（p.6）。**排程線**：cache-aware 三件套：delay hit 規避（把撞在計算中的重複 miss 推遲到即將命中，p.7）、均衡批（load/compute 比超閾值 `loading_bound`=100 就移出，p.7）、氣泡填充（用 decoding batch 去填載入空檔，p.7）。

賬本：同 TTFT 下峰值吞吐最高 5×（對 vLLM-LMCache）/ 3.75×（對 TensorRT-LLM），對應 Llama-70B + LooGLE + H200 的最優點；多輪負載 ReviewMT 上收斂到 1.7×/2.3×（p.9）。GH200 上持續傳輸頻寬從 40.3 GB/s 提到 150.5 GB/s（p.12）。前提：單實例、大 host DRAM、SGLang 系生態；主力基線 SGLang-HiCache 是作者自實現版本（p.8）。

![Strata：GPU-assisted I/O 與 cache-aware 排程三件套](../../assets/mtier-strata-io-schedule.svg)

## 三、對號入座：你手上是什麼條件

| 你的條件                                                              | 該看哪篇 | 先決條件與口徑提示                                                                                                     | 開源入口                                                  |
| --------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| GH200/GB200 或帶高頻寬互聯的平台，節點內長上下文                      | DirectKV | NVLink-C2C 是硬前提，純 PCIe 上只省顯存不保吞吐；「50% 傳輸降幅」對照樸素零複製，「43% 顯存降幅」對照 offload 系統均值 | [DirectKV](https://github.com/shutianluo/DirectKV)（MIT） |
| 小顯存 GPU（T4/A10G 一類）、本地 CPU 記憶體大、要線上服務               | NEO      | 前提是「隨卡白送」的本地 CPU 與大 host 記憶體；峰值倍數看合成掃描，真實收益看固定時延點（563% 對 7.5× 是兩組賬）         | [NEO](https://github.com/NEO-MLSys25/NEO)（論文承諾開源） |
| vLLM 上長上下文跑滿、activation 與 KV 互相擠                          | eLLM     | 單機 + PCIe；收益最大的形狀是長序列 + 高 activation-to-KV 比；代價是 TPOT 讓步；未開源，先學思路                       | 論文未開源                                                |
| SGLang 系 + 大 host DRAM + agent/長上下文負載，分層快取已開但搬運浪費 | Strata   | 單實例範圍；主力基線的 HiCache 是自實現版；「5×/3.75×」是 "up to" 最優點，多輪負載收斂到 1.7×/2.3×                     | 論文未提及                                                |

四條路線互不排斥：DirectKV 的零複製消除的是 eLLM 仍要付的 PCIe 賬單；NEO 的 CPU attention 與 Strata 的 CPU↔GPU 傳輸是兩個方向；eLLM 的池內彈性與 Strata 的層級排程正交。混用的邊界，四篇的「侷限與邊界」小節裡都有各自的答案。

## 四、共同的支點與邊界

先量缺口，再對數字設計。四篇的機制都能回指一組事先被測出來的數字：DirectKV 量出樸素零複製把 B 的流量放大到 33.5 GB、L2 命中率掉到 32.3%，三招各自對著這兩筆賬修；NEO 量出頻寬差約 3×、算力差約 100×，才敢把 bandwidth-bound 的 decoding attention 搬走；eLLM 量出預留佔比 30.8% 對實際利用率約 1% 的錯位，才有了互借的池；Strata 量出 22% 的頻寬利用率、最高 24% 的載入停頓與 38% 的 delay hit 撞車率，才去換 I/O 機制與排程。

第二個交叉點：把搬運藏起來的四種配對手法。四篇走的都是同一條路：把傳輸藏進另一份資源面的計算裡（DirectKV 消掉的也只是 staging 這一個動作），配對方式各不相同：kernel 內藏（DirectKV 的 warp 級流水，producer 預取下一 tile 與 consumer 的計算同 kernel 掩護）、兩側互藏（NEO 的雙 batch，CPU attention 與 GPU 線性段互為掩護，排程約束落成 `Tl0 ≥ Tca1` 這樣的不等式）、層間藏（eLLM 的 layer-wise pipelining，O(N) 的 KV 傳輸藏進 O(N²) 的 prefill）、批間藏（Strata 的氣泡填充，載入吃 PCIe、解碼吃 HBM，資源面錯開）。手法不同、約束相同：掩護視窗要蓋得下傳輸，且兩份負載不能搶同一種資源。

都建立在當代硬體的某道新縫隙上。DirectKV 賭 NVLink-C2C 把互聯和 HBM 的差距縮排一個數量級；NEO 賭 CPU 頻寬與 GPU 只差約 3 倍；eLLM 賭 GPU VMM 支援對映轉手；Strata 賭數千個 GPU 執行緒搬 KB 級資料的效率。硬體前提變了，賬就要重算。四篇論文各自的侷限章節都在談硬體，原因就在這裡。

精度賬普遍缺席。DirectKV 全文沒有 accuracy/perplexity 實驗；eLLM 是純記憶體管理、理論上不影響精度但沒報告；NEO 也沒有品質資料。記憶體層級重構在數值上"免費"到什麼程度，四篇裡沒有一篇測完。

與 FAST'26 系列的分工。那邊的五篇是「KV × 儲存的五個場景」（端側、智能體、多輪對話、分離式、冷啟動），物件是 SSD 與檔案系統；這邊四篇的物件是顯存之外的第一層：DRAM、互聯、記憶體抽象與排程。串起來讀的順序是：先把記憶體層級用對（本系列），再和儲存打交道（[FAST'26 系列](../03_fast26/01_fast26-kv-storage-five-scenarios.md)）。

## 五、未來方向：統一名稱空間與成本旋鈕

四篇有個共同處境：每個團隊都在應用層手搓一層「翻譯」：把兩種記憶體的物理成本差（頻寬 4× 到 60×、延遲、訪問方式）翻譯成顯式策略（DirectKV 的三招、NEO 的流水線平衡、eLLM 的借調規則、Strata 的排程三件套）。翻譯層之所以存在，是因為介面只提供了兩種形態：「兩個地址空間 + 顯式複製」，或「統一地址空間 + 自動遷移」（Unified Memory 式的缺頁加頁遷移；主流推理棧的 KV 熱路徑基本不用它：頁粒度遷移對 token 粒度、帶 stride 的 KV 訪問並不合身）。

如果硬體補上另外兩件東西，這層翻譯可以整體收斂成一個排程器：

- **統一名稱空間**：HBM 與 CPU 記憶體同一套指標語義，**地址段本身即層級標籤**，策略不需要額外後設資料，就能知道自己在跟誰說話；
- **成本旋鈕**：每段空間有確定、可分檔、可預測的頻寬與延遲檔位（頻寬 QoS、顯式預取、不觸發缺頁的訪問），供排程器查詢與規劃。

有這兩樣，搬運從「正確性要求」降級為「性能策略」：staging buffer、雙緩衝、`cudaMemcpyAsync` 動態地址造成的 CUDA Graph 重放問題這些管道程式碼都會消失。軟體不必再為了「能讀」而搬，只需為了「夠快」而搬。eLLM 已經給了同速層內的小樣板：activation 池與 KV 池並賬後，借調只轉所有權、不搬資料，約 20% 吞吐几乎白得。反過來看，四篇裡最重的部分恰好全是跨過成本台階的那部分，一件都省不掉。

反面教材也現成：資料庫幾十年來寧可自建 buffer pool，也不把頁快取交給虛擬記憶體的缺頁邏輯；Apple 的統一記憶體讓推理軟體變簡單，是因為它只有一層。統一在同速層內幾乎免費，跨了層就重新變成策略問題。 GH200 的統一頁表與 CXL 是最接近這組設想的硬體，而經驗事實是：GH200 上 DirectKV、Strata 依然要自建整套機制。統一名稱空間改變的是軟體的結構（少寫管道），不改變瓶頸的數學（頻寬比還在）。這也正是 vLLM KV Connector、LMCache 分層與 HiCache 預取正在走的路：把「怎麼搬」從各系統的私有實現，收斂成可替換的策略層。

![未來方向：統一名稱空間與成本旋鈕——把翻譯層收進介面](../../assets/mtier-future-unified-namespace.svg)

## 六、數字怎麼讀

- **DirectKV**：「50% 傳輸量降幅」的對照是樸素零複製，不是 Pie/Neo/FlexGen（§7.4.1，p.49）；43% 顯存降幅的基線是 Neo/Pie/FlexGen 三者均值 82.7 GB（不含 SGLang 的 92 GB）；1.2× 是跨上下文長度的平均值，優勢隨長度放大。
- **NEO**：7.5×/26%/14% 是合成負載掃描的峰值（對 GPU-only 的 SwiftLLM）；真實線上是 14.3%/6.40%/563%（對 vLLM、固定時延點）；79.3% 由 CPU 頻寬決定、論文未逐一點名實例型號；2 卡實驗的 CPU 資源被限在 1/4 NUMA 節點。
- **eLLM**：2.32× 是 128k-4k 離線最優配置（Jamba-Mini，2 GPU）；「128K batch 擴約 3×」是 Figure 7 讀圖值、正文沒有；295×/140× 的 TTFT 倍數取自 vLLM 排隊崩潰區，不是穩態對比。
- **Strata**：5×/3.75× 均為 "up to"，對應 Llama-70B + LooGLE + H200 的同 TTFT 最優點；主力基線 SGLang-HiCache 是作者自實現，與 SGLang 發行版功能的關係論文未說明；22%/5% 兩個頻寬利用率是同為「搬 KV、頁大小 32、Llama-3.1-8B」條件下的測量（p.3–4）。

## 系列篇目

- [不搬 KV 反而更快：OSDI'26 DirectKV 讓顯存少佔 43%](02_directkv.md)——去搬運（OSDI '26）
- [顯存卡死 batch 的 GPU 上：NEO 把 decoding attention 搬給了隨卡白送的 CPU](03_neo.md)——挪計算（MLSys 2025）
- [30.8% 的顯存按 200K 上下文預留，實際只用 1%：eLLM 讓 Activation 與 KV Cache 互相借記憶體](04_ellm.md)——並賬本（DAC 2026）
- [8192 個 token 的 KV 只跑出 22% PCIe 頻寬：Strata 重做分層快取的搬運與排程](05_strata.md)——重排排程（OSDI '26）
- 精讀報告（逐條頁碼核對版）：[DirectKV](references/directkv-report.md) · [NEO](references/neo-report.md) · [eLLM](references/ellm-report.md) · [Strata](references/strata-report.md)；論文原文 PDF 在 `references/papers/`（已核頁數與首末頁）

## 誠實宣告

- 四篇的數字均為論文自測，本倉未復現；本文的橫向比較跨論文、跨硬件、跨負載，除注明外**不可直接互比**。
- 本文每個數字都取自對應單篇精讀；各單篇的「誠實宣告」列出了自己的口徑限定與未核實項（如 DirectKV 的精度實驗缺席、Strata 的自實現基線、NEO 的 NUMA 限制、eLLM 的讀圖值）。
- 「未來方向」一節是展望性論述：由四篇的實測經驗與公開的硬體背景（Unified Memory、GH200 統一頁表、CXL 等）並讀推演而來，不是任一論文的主張，其中的硬體側細節未按本系列的逐條核對標準核驗。

## 延伸閱讀：本倉相關（按主題）

> 本系列只管「顯存之外的第一層」；上下游的傳輸、系統與儲存線索按主題列在這裡，完整對映見 [KV Cache 技術體系門戶](../README.md)。

解除安裝與預取（把 KV 搬到 CPU/盤，並隱藏搬運延遲）：

- [KV Offloading 架構對比](../01_concepts/07_offloading/01_kv_offloading.md) · [KV Cache 層級流水線並行](../01_concepts/07_offloading/02_layerwise_pipeline.md) · [KV Cache Prefetching：三層預取](../01_concepts/07_offloading/03_kv_cache_prefetching.md) · [稀疏注意力 × KV Cache Offloading：跨層聯動必須回答的八個問題](../01_concepts/07_offloading/04_sparse_attention_driven_offloading_problems.md)

PD 分離與跨節點傳輸（搬運走出單機之後）：

- [PD 分離架構下的 KV Cache 傳輸](../01_concepts/08_pd_transfer/01_disaggregated_prefill_kv_transfer.md) · [壓縮、重疊、複用、隔離：PD 狀態交接最佳化的四條軸](../01_concepts/08_pd_transfer/02_pd_state_handoff_optimization_map.md) · [分卡之後再跨機：DCP 與 PD 分離疊加時的 KV 傳輸](../01_concepts/08_pd_transfer/03_dcp-pd-transfer.md)

系統與容量（分層快取的工業實現與併發賬本）：

- [SGLang HiCache 深讀](../../sglang/hicache_deep_dive.md) · [LMCache 概覽](../02_systems/01_lmcache/01_lmcache_overview.md) · [L2 還有大半空著，TTFT 為什麼先崩了？L1 KV Pool 才是系統併發的上限](../01_concepts/10_capacity_planning/01_hbm_kv_pool_concurrency.md)

壓縮與淘汰（把 KV 變小的經典兩條腿）：

- [KV Cache 壓縮技術詳解](../01_concepts/06_compression/01_kv_cache_compression.md) · [KV Cache 淘汰策略：從滑動視窗到注意力引導的精確淘汰](../01_concepts/05_eviction/01_attention_sinks_and_eviction.md)

KV × 儲存的五個場景（本系列的下一層：SSD 與檔案系統）：

- [當 KV Cache 裝不進記憶體：FAST'26 五篇論文給出的五個不同答案](../03_fast26/01_fast26-kv-storage-five-scenarios.md)

## 參考資料

- Shutian Luo, Haiying Shen. _No Buffer, No Bottleneck: Efficient Zero-Copy KV Cache Offloading for Long-Context LLMs_. OSDI '26, pp. 39–54. [USENIX 論文頁](https://www.usenix.org/conference/osdi26/presentation/luo)
- Xuanlin Jiang et al. _NEO: Saving GPU Memory Crisis with CPU Offloading for Online LLM Inference_. MLSys 2025. [arXiv:2411.01142](https://arxiv.org/abs/2411.01142)
- Jiale Xu et al. _eLLM: Elastic Memory Management Framework for Efficient LLM Serving_. DAC '26. [arXiv:2506.15155](https://arxiv.org/abs/2506.15155)
- Zhiqiang Xie et al. _Strata: Hierarchical Context Caching for Long Context Language Model Serving_. OSDI '26. [USENIX 論文頁](https://www.usenix.org/conference/osdi26/presentation/xie-zhiqiang)
- 本倉相關：[FAST'26 KV × 儲存五場景](../03_fast26/01_fast26-kv-storage-five-scenarios.md) · [SGLang HiCache 深讀](../../sglang/hicache_deep_dive.md)
