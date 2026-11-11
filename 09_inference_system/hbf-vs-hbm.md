# HBF 是 HBM 的替代嗎？單位儲存便宜了，Token 成本卻可能更高

**說明**：本文基於 Hot Chips 2026 Tutorial 1《HBF in AI Compute – A System Architect's View》，Anurag Agrawal（OXMIQ Labs，系統架構）與 Radhakrishna Giduthuri（PRAXMATI，軟體架構）主講，2026 年 8 月 23 日。

> **時效性提醒**：截至寫作時 HBF 沒有量產產品，OCP 規範版本為 v0.7.0。文中模擬結果、$ 數字與價格均為特定時點口徑，會隨產品落地變化，引用前請複核。

## 一、記憶體荒裡的一個便宜承諾

2026 年 2 月，TrendForce 把 1Q26 的常規 DRAM 合約價漲幅上修到 +90%–95%，NAND 上修到 +55%–60%，並稱各類產品季增幅度將創歷史新高。到第二季度，NAND 環比 +70%–75%，在本輪週期裡第一次漲得比 DRAM 還快；SK hynix 稱 2026 全年 HBM 產能已售罄，Kioxia 的 NAND 產能同樣售罄。

漲價的原因不在快閃記憶體本身。先進製程產能被伺服器 DRAM 和 HBM 抽走，廠商把產線從 NAND 挪向 DRAM，企業級 SSD 反而變成最大的 NAND 需求方。需求側同時在膨脹：萬億參數 MoE 把專家權重推到 TB 量級，1M 上下文把 KV Cache 推到几十 GB 每條請求。

HBF（High-Bandwidth Flash，高頻寬快閃記憶體）就是在這樣的背景下被反覆提起的。它把 3D NAND 按 HBM 的方式垂直堆疊、和計算 die 同封裝、用 UCIe 互連，宣傳口徑是 8 到 16 倍於 HBM 的容量、成本几乎持平。對於模型參數越來越大的推理場景，這個數字很難不讓人心動。

這個概念的提出時間是 2025 年 2 月，SanDisk 從西部資料分拆後的第一次投資者日，主講人 Alper Ilkbahar 現在已升任 SanDisk CTO。之後節奏不慢：2025 年 8 月 SanDisk 與 SK hynix 籤諒解備忘錄，2026 年 2 月 OCP 的 HBF workstream 成立，六個月後的 2026 年 8 月 3 日，首份 HBF 技術規範透過 OCP 发布，Google 與 Tenstorrent 以成員身份加入。規範的正式名稱是《High Bandwidth Flash (HBF) High-Level Base Die Specification》v0.7.0，正文 130 頁；報告引用時簡寫成 OCP HBF Architecture Specification v0.7.0。本文下面凡標「規範」處，都指這份文件。

Hot Chips 2026 的這場 tutorial，是這份承諾第一次被系統架構師拆開算賬。它的結論寫在第 4 頁幻燈片上：

> HBF is a capacity point (low α, low β) — not a cheaper HBM
> （α 低、β 也低，HBF 是冲着容量去的，不能當便宜的 HBM 用。）

## 二、座標系：容量便宜，頻寬昂貴

要理解這句話，先得有個能把各種儲存介質放在一起比較的座標系。報告借用的是 arXiv:2601.05047 里的 (β, α) 地景：

- **β（橫軸）** 是單位容量成本，$/GB，以 HBF = 1 為基準的對數軸
- **α（縱軸）** 是單位容量頻寬，即每 GB 能分到多少吞吐，也是對數軸

![(β, α) 記憶體地景](assets/hbf-beta-alpha-landscape.png)

把各家放上去，位置分佈得相當開。SRAM-only 方案（Cerebras、Groq）在右上角遠處，β 比 HBF 貴五個數量級，換來的 α 高約六個數量級；HBM3E / HBM4 / HBM4E 擠在中右部，β 約 10–30 倍，α 約 100–300；LPDDR5X 落在 1× 與 10× 之間；NAND SSD 在最左下，β 只有 HBF 的 0.1 倍，但 α 低到 0.001；HBF 的 G1/G2/G3 三個等級落在左下角一小片區域，β = 1，α 在 1 到 10 之間。

圖上有一處標註是整頁的核心：HBM 對 HBF-G2 的 α 高出 25 倍（對 G3 約 13 倍）。換成直白的話，同樣 1 GB 容量，HBM 能分到的頻寬是 HBF 的 25 倍；HBF 用容量換來的便宜，代價是頻寬低了一個多數量級。

這裡要分清量和價。α 說的是量，**單位頻寬的成本**是 β/α。翻到第 7 頁那組同成本配置可以直接算：HBM-only 是 288 GB / 22.0 TB/s，All-HBF 是 4,096 GB / 12.8 TB/s。同成本下 HBF 每 GB 便宜 14 倍（4,096/288），頻寬卻只有 0.58 倍（12.8/22.0）。兩者相除，**HBF 每買 1 TB/s 頻寬，成本是 HBM 的 1.72 倍**。α 低得比 β 少得更多（25 倍 vs 14 倍），折算到頻寬單價上就翻了盤。所以「頻寬更低」和「頻寬更貴」說的是同一件事的兩面：前者是量，後者是價，中間隔著 β/α 這一步除法。

右下角還有一行小字：compute-in-memory（IMC / PIM / d-Matrix 一類）不在這張平面上，因為它搬運的是結果而不是位元組。

報告全篇的對照口徑是 HBM4/4e ↔ HBF-G2、HBM5 ↔ HBF-G3，按產品排期對齊。也就是說，HBF 要競爭的是 2026–2027 這一代的 HBM4，而不是當期的 HBM3E。

## 三、$/token：一個被 max() 決定的公式

座標系解釋了 HBF 站在哪里，但沒有回答該不該買。報告第 6 頁把這個問題寫成一行公式：

$$
\$_{\mathrm{mem}} = \beta \cdot \max\left(C,\ \frac{\text{BW demand}}{\alpha}\right), \qquad \text{BW demand} = I \cdot b
$$

其中 $C$ 是必須佔用的物理容量（GB to HOLD，裝下模型和上下文的那部分），$I$ 是使用者感知的互動速度（tok/s/user），$b$ 是單步解碼需要搬運的位元組量，$I \cdot b$ 是頻寬需求，再除以 $\alpha$ 得到折算成容量的頻寬需求（GB to FEED）。

決定賬單的是那個 `max()`。最終成本由兩項裡更大的那個決定：

- **容量瓶頸區**：$C$ 佔上風。此時 β 極低的 HBF 便宜得離譜。
- **頻寬受害區**：$I \cdot b / \alpha$ 反超。為了補齊缺的頻寬，你得買遠超實際儲存需求的顆粒，多出來的容量變成沒有產出的殭屍容量。每 token 的真實成本反而上去。

報告給這一頁配的註解是：你不是在用錢買 GB，你買的是這個方程的結果。第 21 頁把評價函式進一步簡化成一個品質因數 $(β/α) \cdot b$，介質的 β/α 乘以工作負載的單步位元組數，兩個因子都得看。

這就是標題那句話的機制來源：

> The cheapest $/GB can be the most expensive $/token.
> （最便宜的每 GB 單價，可能會變成最貴的每 Token 成本。）

## 四、優勢區在哪裡：MoE 的低併發容量子相位

$b$ 不是一個固定值，它取決於模型結構和一個執行參數。報告第 5 頁把它寫開：

$$
b = \left[1 - \left(1 - \frac{k}{N}\right)^B\right] W + W_0 + B \cdot K
$$

$N$ 是專家總數，$k$ 是每個 token 激活的專家數，$B$ 是 batch（等於併發使用者數），$W$ 是所有路由專家的權重總量，$W_0$ 是固定權重（共享專家加 dense 部分），$K$ 是單使用者的 KV 位元組數。

第一項決定了回扣曲線的形狀。batch 很小時，$1 - (1 - k/N)^B$ 約等於 $B \cdot k / N$，每步讀入的專家權重大致正比於 $B$ 且係數極小：模型全量必須駐留在介質裡，但每步只碰其中很窄的一條。batch 漲上來之後這一項快速飽和，權重讀取變成全量，頻寬需求被拉滿。

![MoE 與 Dense 的吞吐-互動度分割槽](assets/hbf-moe-vs-dense.png)

用 Kimi-K2（MoE）和 Llama-3.1-70B（dense）在 B200 NVL72 上跑 OxSOL 仿真，三條分界線很清楚：

| 區段                 | 特徵                                                        | 誰在跑         |
|----------------------|-------------------------------------------------------------|----------------|
| ① Experts-Sparse     | 頻寬隨 B 增長但極緩，吞吐 T 基本持平，交互度 I 接近持平     | MoE 小併發     |
| ② Experts-All        | 權重讀取已被攤平，T 隨 B 線性增長                           | 兩側通吃       |
| ③ Saturated          | 算力打滿，T 不再隨 B 漲                                     | 高併發         |

dense 模型沒有區段 ①，它每生成一個 token 都要把全量權重過一遍匯流排，曲線直接從左上角的高互動度往下摔。報告在圖上把 dense 的拐點標在 B ≈ 300 附近。

所以 HBF 的生存空間來自一個具體的結構事實：MoE 在低併發時開出了一個容量子相位，模型得完整裝下，但頻寬需求極低。這個區間裡 HBF 的 α 劣勢用不上，β 優勢全發揮。

## 五、同成本下的三種方案

知道了優勢區的形狀，再看第 7 頁給的三種同成本方案：

| 方案                        | 容量         | 峰值頻寬                              |
|-----------------------------|--------------|---------------------------------------|
| HBM-only（基線）            | 288 GB       | 22.0 TB/s                             |
| (a) All-HBF（8×HBF-G2）     | 4,096 GB     | 12.8 TB/s                             |
| (b) 2×HBF + 6×HBM           | 1,240 GB     | 19.7 TB/s（跨 batch 有效值 19→4）     |

幻燈片給這三張圖的註解是：Same cost. More capacity. Less bandwidth.

> 注：All-HBF 一格按 4,096 GB ÷ 8 die 折算是 512 GB/die，而規範與 tape-out 報道口徑的單 die 容量為 256 GB——兩處讀數對不上，系幻燈片口徑差異，本文按幻燈片原數 4,096 GB 計算。

### 5.1 短上下文：贏在成本，代價是 85% 死容量

256 進 / 256 出，Kimi-K2 權重約 538–615 GB，隨 batch 從 8 漲到 128：

- HBM 方案需要 2 張卡（0.58 TB，44 TB/s），成本 2×
- 全 HBF 方案需要 1 張卡（4 TB，12.8 TB/s），成本 1×

低 batch 下 HBF 的成本地板只有 HBM 的一半，成績不差。但結論行把代價寫得很直接：85% 的容量是死的。4 TB 裡真正裝下的只有五百多 GB 的權重和少量 KV。

一旦交互速度要求上去，頻寬需求線就會撞上 12.8 TB/s 的牆；越過之後要補頻寬只能加卡，成本曲線接近垂直上翹，HBM 方案在這個區間反殺。幻燈片上還標了另一條線：如果真要把 4 TB 填滿（多模型或超長上下文），那就得堆到 14 張卡、308 TB/s，容量對齊但成本 14×。

### 5.2 長上下文：只在頻寬需求低時成立

1M 進 / 1K 出，同一個模型權重漲到 664–2,631 GB：

- HBM 方案 4 張卡（1.1 TB，88 TB/s），成本 4×
- 全 HBF 方案仍是 1 張卡（4 TB，12.8 TB/s），成本 1×

這次 HBM 的多卡換來的是實打實的頻寬，而不是閒置容量。結論行同樣直白：容量只在 $I \cdot b$ 保持低位時贏，過了那條線，HBM 是更划算的買法。

### 5.3 用 HBM 做熱專家快取：被一條曲線否掉

一個很自然的想法是分層：把最熱的專家放 HBM，冷的放 HBF。第 10 頁用一條覆蓋曲線說明為什麼行不通。多併發下實際被讀到的專家比例是：

$$
\rho_{\mathrm{eff}}(B) = 1 - \left(1 - \frac{k}{N}\right)^B
$$

注意它和 $b$ 的第一項是同一個式子。單個使用者只碰 $k/N$ 比例的專家，但 $B$ 個使用者各碰各的，取並集後迅速膨脹。按各模型實際的 $k/N$：

| 模型                 | $k/N$     | $\rho_{\mathrm{eff}}$ 達到 90% 所需的 batch     |
|----------------------|-----------|-------------------------------------------------|
| Mixtral-8x7B         | 25.0%     | ≈ 8                                             |
| Qwen3-235B-A22B      | 6.2%      | ≈ 36                                            |
| DeepSeek-V3          | 3.1%      | ≈ 73                                            |
| Kimi-K2              | 2.1%      | ≈ 109                                           |
| Kimi-K3              | 1.8%      | ≈ 127                                           |
| Llama-4-Maverick     | 0.8%      | ≈ 287                                           |

MoE 越稀疏，快取越晚才划算。只要 batch 上到几十，DeepSeek-V3 一級的模型就已經有四到五成專家被命中；到了 Kimi-K3 這個稀疏度，快取要等到上百併發才有意義。報告的結語是：專家流行度在混合查詢下會攤平，快取只在低 batch 時、或者把同類查詢湊在一起批處理時才有收益。

## 六、機架看 HBM，單機看 HBF

單卡視角的結論不足以做部署決策，幻燈片把戰場拉到 72 卡機架，條件是同 3 年 TCO（capex + opex）、同功耗預算：

| 72 卡機架          | HBM-only（TP8·DP9）     | HBF-only（TP1·DP72）     | HBF+HBM（TP2·DP36）     |
|--------------------|-------------------------|--------------------------|-------------------------|
| 單 DP 可用顯存     | 2.3 TB                  | 4.1 TB                   | 2.5 TB                  |
| 整機架容量         | 20.7 TB (1×)            | 294.9 TB (14×)           | 89.3 TB (4.3×)          |
| 整機架聚合頻寬     | 1,584 TB/s              | 922 TB/s (0.6×)          | 1,418 → 279 TB/s        |
| 單卡峰值頻寬       | 22.0 TB/s               | 12.8 TB/s                | 19.7 → 3.9 TB/s         |
| 成本 · 功耗        | 1× · 持平               | 1× · 持平                | 1× · 持平               |

仿真模型是 Kimi-K2 1T @ FP4，1M 進 / 1K 出，每 DP 的 batch 在 1–512 之間掃，decode 為主。

架構上的分化比數字更有意思。純 HBM 方案單卡裝不下萬億模型，必須 TP8 切分，一台 72 卡機櫃只能支撐 9 組服務實例；純 HBF 方案單卡 4.1 TB 裝得下整個模型，變成 TP1·DP72，72 組完全獨立的服務實例。

![機架級 $/M-token 對比](assets/hbf-rack-cost-per-token.png)

但機架級的 $/M-token 曲線給出了相反的答案。橫軸是互動速度 $I = 1000/\mathrm{TTNT}$（tok/s/user），縱軸是每百萬 token 的解碼成本，對數刻度。三條曲線的形狀：

- HBM（黑）：$I$ 從 20 升到 150 時成本從約 \$2.6 降到約 \$2.0，之後回升到約 \$2.5，服務到 72 使用者
- HBF+HBM（金）：低互動度時成本最高（約 \$5.5），$I$ 上去之後回落到約 \$2.9，服務到 288 使用者
- HBF-only（紅）：$I$ 很低時約 \$2.6，隨 $I$ 升到約 \$3.75 后走平，能服務到 576 使用者

按圖讀，HBM 方案的成本穩定在 \$2.0–2.6/M-token，全 HBF 穩定在 \$3.7–3.8。報告把 $I \geq 70$ 劃成 HBM 的地盤（圖上是陰影區），理由是那行註釋：機架的電費、折舊都攤上了，必須靠 1,584 TB/s 的總頻寬拼命噴 token，HBF 吞吐慢、單位時間產出的 token 少，每個 token 攤到的固定成本反而更貴。

> **口徑提醒**：這兩組 \$ 數字是從對數座標軸上讀的，幻燈片沒有以數字形式給出。量級可信，小數點後一位不要當精確值引用。

再把鏡頭切到單機（第 14 頁，同樣是 Kimi-K2 1T、1M/1K）：

| 單實例配置     | 顯存       | 頻寬          | 成本/功耗     | 最大使用者數     |
|----------------|------------|---------------|---------------|----------------|
| 8 張 GPU       | 2.3 TB     | 176 TB/s      | 8×            | 112            |
| 2 張 GPU       | 2.5 TB     | ~40 TB/s      | 2×            | 128            |
| 1 張 GPU       | 4.1 TB     | 12.8 TB/s     | 1×            | 232            |

在 $I < 74$ 的區間，8 卡的 HBM 方案根本服務不了，它在 112 個使用者時 OOM。而單卡 HBF 方案一直能撐到 232 個使用者，成本和功耗都是 1×。

一句話概括這套對比（報告的原文）：

> Cheaper $/GB ≠ cheaper $/token — HBM for the rack, HBF for the box: pick your scale.

## 七、要把 vLLM 改成什麼樣

報告後半程切到軟體側，第一個問題是：如果真給一張帶 HBF 的卡，記憶體該怎麼分配？第 17 頁拿 Kimi-K3（2.8T，權重合計 1.56 TB）做解剖：

| 組成                         | 大小        | 占比     | 建議介質                      |
|------------------------------|-------------|----------|-------------------------------|
| MoE 專家權重                 | 1.45 TB     | 93%      | HBF（只寫一次、冷態讀取）     |
| attention + 其它固定權重     | 110 GB      | 7%       | HBM（計算密集、頻繁訪問）     |
| 單條 1M 序列的 KV Cache      | 30 GB       | —        | HBF（解除安裝池 + 字首快取）      |

93% 的位元組是隻寫一次、冷態讀取的專家權重，這個生命週期特徵確實和快閃記憶體對得上。剩下的 7% 計算密集、訪問頻繁，留在 HBM。（「單條 1M 序列 KV 30 GB」是幻燈片讀數；按本倉 [B300 部署篇](deployment/b300-deployment-and-kv-cache.md) §3.3 的逐層口徑，K3 的 MLA KV 為 FP8 13,824 B/token，1M 序列約 13.8 GB——兩者相差約 2 倍，幻燈片未註明其層數/精度假設，本文保留幻燈片原數。）

第 18 頁給出了改造後的 vLLM 記憶體子系統（文字還原）：HBM 側是 Model Weights (resident)、Paged KV Cache、Activations 和 Router MoE 權重；HBF 側用紅色虛線框標出，包含 Paged KV Offload Pool、Prefix KV-Cache 和 1.45 TB 的 MoE Experts Pool，框上注明 _instead of host CPU pinned-memory_；左側另有兩塊外部儲存，SSD-resident KV 與 Scale-out RDMA Remote KV Pools。

HBF 層的位置是頂替 host CPU pinned memory，也就是現在 KV Cache 解除安裝和權重換出要經過的慢速主機記憶體與 PCIe 通道。改造后，GPU 封裝內形成一個雙層儲存池：HBM 層放活躍激活值、路由網路和當前步要用的 KV；HBF 層放 1.45 TB 的 MoE 專家池和 Paged KV 解除安裝池。片內的搬運靠非同步預取掩蓋快閃記憶體延遲，不再走 PCIe。

給出的參考配置是 4×HBM + 4×HBF，單卡 2.2 TB、約 17.4 TB/s 峰值頻寬。

圖例裡有一行必須注意：**「MoE Experts Pool is not yet available in vLLM」**。vLLM 目前根本沒有 MoE 專家池這個功能，最誘人的那塊（把 1.45 TB 專家權重挪進 HBF）在引擎裡還不存在對應元件。報告自己也承認，今天 vLLM 的解除安裝路徑全部指向 CPU/LMCache，HBF 的 allocator、放置策略、非同步預取、壽命遙測都還沒有東西。

## 八、快閃記憶體的七道枷鎖

第 15 頁把 HBF 的軟體約束列成一張清單。這些都是 NAND 介質的物理性質，逐條都能在規範裡找到出處：

| 約束         | 內容                                                                                                   | 后果                                 |
|--------------|--------------------------------------------------------------------------------------------------------|--------------------------------------|
| 訪問粒度     | 協議層：讀 64 B–4 KiB（64 B 對齊、不跨 4 KiB 頁），寫 4 KiB 突发；要跑滿頻寬則需 64 KB 讀、1 MB 寫     | 不能用 64 B cacheline 精細讀寫       |
| 寫入路徑     | 4 KiB 寫必須在 NAND 塊內連續、禁止跳地址；塊擦除由裝置在收到 page-0 寫時自行觸發                       | 寫入放大不可避免                     |
| 通路         | 讀寫走 DMA，不接入 GPU cache 層級                                                                      | 必須由軟體顯式搬運                   |
| 保持期       | 85 ℃ 上電保持 24 小時（規範明確承諾）；斷電後不保證，規範稱「等同於 HBM」                              | 需要主機側週期性巡檢與重新整理           |
| 壽命         | 規範把耐久性列為 Product Specific，透過 MAXPEC / AVGPEC 暫存器交由主機監控                             | 剩餘壽命由主機推算                   |
| 管理         | HBF 與 HBM 同系統時必須分開管理                                                                        | 不是透明的更大顯存                   |
| 暫存         | 內建 scratchpad SRAM 是可選特性，64 B 粒度、掉電即失                                                   | 無法旁路 NAND 塊                     |

先看訪問粒度這一行，因為這裡最容易把兩個層級混掉。規範 §4.1 定的是協議層能力：讀突發 64 B 到 4 KiB、寫突發 4 KiB。而報告第 15 頁說的「64 KB 讀、1 MB 寫」是另一回事——那是要把頻寬跑滿所需要的塊大小，背后是跨 16 條主機通道的交織效率。兩個數字都對，但一個說的是最小交易單位，一個說的是達到峰值吞吐的推薦批次。

「85 ℃ 上電保持 24 小時」在規範裡是明確承諾的（Table 33：Power On Data Retention @85°C = 24 Hours）。同一張表還有半句更容易被忽略：斷電之後 HBF 不再保證資料，規範的原話是「equivalent to HBM」。用通用 NAND 資料可以交叉驗證這個量級：JEDEC 企業級斷電保持指標是 40 ℃ / 3 個月，按 Arrhenius 模型（Ea ≈ 1.0 eV）折算到 85 ℃ 大約是 21 小時，與規範給的 24 小時吻合。而 GPU 封裝的散熱環境恰好落在這個溫度附近，儲存廠商的資料指出，70 ℃ 環境溫度就足以讓盤體達到 85 ℃。對貼裝在計算 die 邊上的 HBF 來說，這是工作點。

寫入壽命那條，規範給的答案比「未定義」具體得多：耐久性一欄寫的是 **Product Specific**，同時提供兩個暫存器——MAXPEC（設計上限）與 AVGPEC（當前平均擦寫次數）——交主機去算。規範原文是「The host is responsible for determining the remaining lifespan by comparing the dynamic AVGPEC against the static MAXPEC limit」。規範不寫壽命，是因為它把壽命變成了一個執行期由主機監控的量。這與 SSD 把地址轉換、垃圾回收、磨損管理全封進控制器的做法相反，也是「HBF 不是即插即用」這句話的出處。HBF 自身沒有任何廠商公佈過 P/E 數字；業界通用的 NAND 資料是 SLC 約 5 萬–10 萬次、TLC 約 1 千–3 千次、QLC 約 100–1000 次。

這張清單裡沒有的一項是延遲。報告全篇用頻寬和容量算賬，沒有給出訪問延遲的數字，而快閃記憶體的讀延遲和 DRAM 根本不在一個量級。行業彙總口徑把 HBF 的讀延遲放在微秒級（數千納秒），HBM4 在 10–100 納秒，差一到兩個數量級。這個數字不是報告資料，列在這裡是為了對照：decode 每一步都在關鍵路徑上等資料，延遲和頻寬是兩筆賬，而報告的成本模型只算了後一筆。

最後排除一個容易混的類比。Intel Optane 是位元組可定址的，能當另一塊記憶體用，敗在每 bit 成本高、密度低；HBF 走的是反方向，靠 4 KiB 頁和塊內順序寫換取 NAND 的便宜和大容量，把複雜度轉嫁給軟體層。規劃系統時，別把它當成一塊更大的記憶體。

## 九、兩個正在開啟的視窗

第 19 頁和第 20 頁給出兩條演算法紅利，能把 HBF 從邊緣位置推進優勢區。

### 9.1 稀疏注意力：把每步讀取壓到 1–2%

長上下文推理之所以吃頻寬，是因為 full attention 每步都要把历史全刷一遍。稀疏注意力改變了這個前提。報告按第 19 頁的式子給出的判據是：

$$
\varphi = \frac{\text{top-}k}{\text{context}} \approx 1\%\text{–}2\% \quad \ll \quad \varphi^* = \frac{\alpha}{I}
$$

$\varphi$ 是每步真正讀的比例，$\varphi^*$ 是介質能承受的比例上限。當 $\varphi$ 遠小於 $\varphi^*$ 時，整份 KV 可以便宜地攤在 HBF 上，每步只把 top-k 那一兩千行撈出來。報告把這條標成「A genuine HBF fit」，但加了一個前提條件：只在稀疏注意力模型上成立，點名的是 DSA（DeepSeek Sparse Attention）、CSA（Compressed Sparse Attention）與 Kimi-Linear。

這條和我們倉庫裡已經寫過的東西正好接上。[當百萬 Token KV Cache 從 250GB 降到 5GB](kv_cache/07_kv_compression/05-post-kv-cache-era.md) 講的是演算法側把每步要讀的位元組砍掉一個數量級，[把 KV Cache 壓縮推到極限](kv_cache/07_kv_compression/06-deepseek-v41-flash.md) 講的是壓縮比再往下推。算法把 $b$ 壓下去，硬體才有空間把介質換成便宜的。所以 HBF 能不能成立，取決於模型架構願不願意繼續把稀疏度做上去。

順帶一提，稀疏注意力的讀取模式和 HBF 的偏好是冲突的。top-k 是散讀，而快閃記憶體喜歡順序大塊。這個矛盾在我們的 [稀疏注意力 × KV Cache Offloading](kv_cache/01_concepts/07_offloading/04_sparse_attention_driven_offloading_problems.md) 裡已經從解除安裝角度列舉過八類問題，換成 HBF 只會更尖銳。

### 9.2 EP × HBF：用容量買回通訊

第二條更直接。大規模 MoE 分散式推理最頭疼的是 EP（專家並行）的跨卡通信：單卡裝不下，專家被撒到多台伺服器，每一層解碼都要 all-to-all。

HBF 的單卡容量改變了這個約束的起點：每個節點本地冗餘部署全量專家，2 個節點就能裝下，几乎不需要 all-to-all。報告的原文是「Cheap HBF capacity → fewer EP shards → less all-to-all comm」。

## 十、這份報告沒有回答的部分

前面九節都建立在報告的模擬結論上。到這一步必須交代它的邊界，否則很容易讀成一份推薦採購書。

第一，全部結論來自模擬。仿真器是 OXMIQ 自己的 OxSOL，模型是 Kimi-K2 / Kimi-K3，沒有一片 HBF 矽片參與測試。

第二，HBF 目前沒有產品。截至本文寫作（2026-09-14）：首顆 HBF 記憶體 die 在 2026 年 8 月 13 日完成 tape-out，樣品指引是 2027 年，公司沒有給出任何量產年份；SanDisk 自己的 FY2028–2030 財務模型裡不含 HBF 收入。StorageReview 的評論說得準確：「a tapeout is also several steps short of a product」。規範版本是 v0.7.0 而不是 1.0，這個數字本身也說明它還沒定稿。

第三，把 HBF 當作「更快的 SSD」來用，反而會變慢。北大與復旦的一篇全棧表徵工作（arXiv:2608.11668, 2026-08-25）把 HBF 換進 SSD 式的 KV 解除安裝棧實測，結論是 H100/B200 上端到端延遲上升 2–5.5 倍，最大 SLO goodput 下降 1.1–2.7 倍。原因很具體：KV 流量的寫比讀多（實測寫讀比 1.14×–4.90×），寫密集流量觸發熱降頻；而 HBF 層的壽命只有它所替代的 SSD 池的 0.56 倍。論文的結論一句話：_「HBF is not the problem, using it as a faster SSD for transient KV is.」_

第四，拿到收益的軟體代價還沒有被證明比替代方案更低。Chips and Cheese 在報道這份報告時給出的判斷是：為一套為 DRAM 設計的記憶體管理邏輯做塊對齊、DMA 驅動的改造，工作量不比直接從 SSD 流式載入模型權重更少，而后者反而省事：作業系統的頁快取天然把塊對齊的坑填掉了大半，只要不碰 O_DIRECT 這類繞過快取的介面。

這三份材料並不互相矛盾。OXMIQ 論證的是 HBF 在低頻寬需求的容量場景裡划算，那篇論文測的是 HBF 在寫密集的瞬態資料場景裡不划算，Chips and Cheese 質疑的是改造引擎的價效比。三條合起來，HBF 能不能用取決於你把什麼放進去，以及你願意為它改多少程式碼：專家權重（只寫一次、冷讀）和瞬態 KV（反覆寫、熱讀）是兩種完全不同的負載。

## 十一、回到那一行公式

把報告的四條收尾（第 21 頁）按順序讀一遍，會發現它就是對標題的回答：

1. 用品質因數判斷介質。$\$_{\mathrm{mem}} = \beta \cdot \max(C, I \cdot b / \alpha)$，評價指標是 $(β/\alpha) \cdot b$，介質和負載的乘積，缺一個都算不對賬。
2. HBF 只贏在一個區間。低頻寬需求（$I \cdot b$ 小）的場景，即小 batch / 低交互度的 MoE，以及稀疏注意力支撐下的長上下文 KV。
3. 要擴大這個區間：讀取頻寬得漲（α↑），與 HBM 的 $/GB 差距得保持住（β↓），寫入壽命與寫入頻寬、延遲得解決。
4. 軟體得先到位。allocator、放置策略、非同步預取、壽命遙測，今天 vLLM 的路徑全部指向 CPU/LMCache，不指向 HBF。

報告的結語是：

> HBF: A precision instrument, not a hammer — bargain in its zone, trap outside it.

關於 HBF 的爭論大多停在「HBF 好不好」上。這份材料裡真正能拿去做決策的，是那行 `max()` 公式。它把「這個介質能不能用」變成兩個可計算的量：你的工作負載單步要搬多少位元組，以及這個介質的單位容量頻寬是多少。容量便宜不等於推理便宜，在 $/token 這個指標面前，容量和頻寬是乘法關係。

## 參考資料

- **原始素材**：Hot Chips 2026 Tutorial 1《HBF in AI Compute – A System Architect's View》，Anurag Agrawal（OXMIQ Labs）、Radhakrishna Giduthuri（PRAXMATI），2026-08-23，22 頁。會議議程：<https://hotchips.org/advance-program/>。**幻燈片未由會議方公開發布**，本文引用的頁面與三張配圖取自公眾號轉載版還原的原圖；文中規格數字均與 OCP 規範原文逐條對照，**核對日期 2026-09-14**。
- OCP《High Bandwidth Flash (HBF) High-Level Base Die Specification》v0.7.0，2026-08-03 发布，130 頁，Sandisk 與 SK hynix 為主要貢獻方。規範原文：<https://www.opencompute.org/documents/ocp-hbf-architecture-specification-v0-7-0-final-pdf>（該站會攔截自動化請求，瀏覽器可正常開啟；命令列取需完整瀏覽器 UA + HTTP/1.1）。[釋出新聞稿](https://www.sandisk.com/company/newsroom/press-releases/2026/2026-08-03-Sandisk-and-sk-hynix-advance-global-standardization-of-hbf)
- 獨立報道：[ServeTheHome](https://www.servethehome.com/oxmiq-labs-hbf-in-ai-compute-at-hot-chips-2026/)、[Chips and Cheese](https://chipsandcheese.com/p/hot-chips-2026-applying-high-bandwidth)
- 中文報道：[電子工程專輯（EET China）](https://www.eet-china.com/mp/a522097.html)、[ic.work](https://www.ic.work/article/hot-chips-2026-high-bandwidth-flash-hbf-explained)（延遲對照表與 Optane 對比出自此篇，為其行業彙總口徑，非報告資料）
- 反方實測：Zhuoran Li et al., _HBF Sucks? A Full-Stack Characterization of High-Bandwidth Flash for KV-Centric LLM Serving_, arXiv:2608.11668v3, 2026-08-25. <https://arxiv.org/html/2608.11668v3>
- 報告引用的學術工作：arXiv:2601.05047（(β, α) 地景）、arXiv:2502.05370（FineMoE）、arXiv:2508.17137（MoE-Beyond）、arXiv:2401.14361（MoE-Infinity）、arXiv:2605.03375（Tutti）
- 成熟度：[StorageReview 關於首顆 die tape-out 的報道](https://www.storagereview.com/news/sandisk-tapes-out-its-first-hbf-memory-die-targets-2027-for-inference-product-samples)
- 價格資料：TrendForce 2026-02-02 儲存器價格上修公告 <https://www.trendforce.com/presscenter/news/20260202-12911.html>

## 口徑說明

正文的數字絕大多數直接來自報告幻燈片；下面幾處的出處不同，列在這裡備查：

| 內容                            | 出處                        | 說明                                                     |
|---------------------------------|-----------------------------|----------------------------------------------------------|
| 頻寬單價 1.72 倍、α 比 25 倍    | 幻燈片 p.7 數字 + 本文推導  | 幻燈片未給這兩個比值，為本文相除所得（1.72 = 22.0/12.8） |
| 機架 $/M-token 曲線數值         | 幻燈片 p.13                 | 對數軸上的目視讀取，非幻燈片標註                         |
| 延遲對照（微秒級 vs 10–100 ns） | ic.work 行業彙總口徑        | 非報告資料，報告未給出任何延遲數字                       |
| NAND P/E 壽命區間               | 儲存廠商通用資料            | 非 HBF 專屬資料，HBF 自身 P/E 未公布                     |
| 85 ℃/24h 的量級驗證             | JEDEC 指標 + Arrhenius 折算 | 本文獨立推算，非報告內容                                 |
