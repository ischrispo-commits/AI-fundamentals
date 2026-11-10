# 職缺能力地圖：四種職缺 × 能力 × 面試題型 × 作品集

> 用途：讓每一份講義與作業都知道「這段知識在面試桌上會以什麼形式被問」。四種職缺共用同一套技術底層（本課程模組一～三），差在**對誰說、說到多深、產出什麼**。本文件中的職缺描述是外商 AI Infra／GPU／Data Center 領域的通則，應徵前請以目標公司實際 JD 為準。

## 1. 四種職缺一句話

| 職缺                                   | 一句話                                                                 | 主要受眾                   | 核心產出                                                   |
| -------------------------------------- | ---------------------------------------------------------------------- | -------------------------- | ---------------------------------------------------------- |
| Technical Marketing Manager（TMM）     | 把工程事實變成業務與客戶能用的技術證據                                 | 業務、SE、客戶架構師       | 參考架構、技術白皮書、競品 FAQ、benchmark 解讀、sizing 指南 |
| AI Evangelist／Developer Advocate      | 讓開發者與社群因為你的 talk 與 demo 想用這個平台                       | 開發者、社群、媒體         | talk、demo、部落格、workshop、開源範例                      |
| Product Marketing Manager（PMM）       | 決定產品對誰說什麼、怎麼說、憑什麼贏                                   | 市場、業務、高層、分析師   | 定位與訊息、發表計畫、競品分析、銷售賦能套件、定價輸入     |
| Technical Account Manager（TAM）       | 讓重點客戶的部署成功並持續擴大，技術與關係一起管                       | 客戶的工程與管理層         | 部署健康報告、升級處理、QBR、擴容建議、風險清單             |

## 2. 共用技術底層與各職缺的「深度刻度」

深度刻度：**1 能說名詞與定位** → **2 能講機制與數字口徑** → **3 能比較方案並給建議** → **4 能排障、算容量、做 demo**。

| 技術主題（模組）                    | TMM | Evangelist | PMM | TAM | 本課程落點 |
| ----------------------------------- | --- | ---------- | --- | --- | ---------- |
| GPU 架構、HBM、Tensor Core 精度（M1） | 3   | 3          | 2   | 3   | W1         |
| PCIe／NVLink／GPUDirect 資料路徑（M1） | 3   | 2          | 2   | 4   | W2         |
| 機架級系統、延遲金字塔、競品晶片（M1） | 3   | 2          | 3   | 2   | W3         |
| GPU 運維、可觀測性、切分（M2）        | 2   | 2          | 1   | 4   | W4         |
| IB／Ethernet、NCCL、排程（M2）        | 3   | 2          | 3   | 3   | W5         |
| K8s GPU 平台、AI 儲存（M2）           | 3   | 3          | 2   | 3   | W6         |
| LLM 基礎、量化、MoE（M3）             | 2   | 3          | 2   | 2   | W8         |
| 推理引擎、KV Cache、PD 分離（M3）     | 3   | 4          | 2   | 3   | W9         |
| Token 經濟、TCO、容量規劃（M3）       | 3   | 2          | 4   | 3   | W10        |
| RAG／Agent 與 infra 影響（M4）        | 2   | 4          | 2   | 2   | W11        |
| 定位、訊息、競品地圖、MLPerf（M4）    | 3   | 2          | 4   | 1   | W12        |

## 3. 各職缺的能力清單與本課程對應

### 3.1 TMM

| 能力                                  | 面試會怎麼問（英文題，答題用中文要點）                                                                        | 作業對應       |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------- | -------------- |
| 讀懂並解釋規格表與 benchmark          | "Walk me through this datasheet. Which numbers would you never put on a slide without a footnote?"           | 作業 1、7      |
| 寫參考架構與 sizing 指南              | "A customer wants to serve a 70B model to 2,000 concurrent users. Sketch the system and the sizing logic."   | 作業 6、7      |
| 競品技術 FAQ                          | "How would you respond when a prospect says Ethernet is good enough for training?"                            | 作業 3、5      |
| 把工程師的話翻成業務的話              | "Explain PagedAttention to a sales rep in two minutes, then to a CTO in thirty seconds."                     | 每日 OR 題     |
| 技術內容產製流程                      | "How do you validate a claim before it goes into a whitepaper?"                                               | 口徑規定、作業 9 |

### 3.2 AI Evangelist／Developer Advocate

| 能力                             | 面試會怎麼問                                                                                            | 作業對應     |
| -------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------ |
| 10～30 分鐘 talk 與 live demo    | "Give us a 10-minute talk on why inference is memory-bound. Whiteboard only."                           | 作業 8、10   |
| Demo 失敗處理                    | "Your demo cluster dies on stage. What's your plan B, C?"                                               | 作業 10      |
| 開發者同理心                     | "What's the most confusing thing about vLLM for a first-time user, and how would you fix the docs?"     | W9 講義      |
| 社群與內容節奏                   | "Pitch me a quarter of content: three blog posts, one workshop, one conference talk."                    | 期末作品集   |
| 技術誠實                         | "A benchmark makes us look bad. What do you write?"                                                     | 口徑規定     |

### 3.3 PMM

| 能力                              | 面試會怎麼問                                                                                                        | 作業對應   |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------- |
| 定位（Dunford 五要素）            | "Position a GPU-as-a-service offering against hyperscalers and against on-prem."                                     | 作業 3     |
| 訊息層級與受眾                    | "Same product, three audiences: CFO, VP Infra, ML engineer. Give me the one-liner for each."                          | 每日 OR 題 |
| 競品與市場地圖                    | "Map the AI infrastructure market: who competes on what axis? Where is the white space?"                              | 作業 3、5  |
| 發表與賦能                        | "Plan a launch for a new rack-scale system. What does sales need on day one?"                                        | 作業 6     |
| 定價與 TCO 敘事                   | "A customer says the competitor's accelerator is 40% cheaper. How do you reframe?"                                   | 作業 9     |

### 3.4 TAM

| 能力                              | 面試會怎麼問                                                                                                       | 作業對應     |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------ |
| 排障思路（現象 → 假設 → 診斷）     | "A customer reports 100% GPU utilization but training is 3x slower than expected. Walk me through your first hour." | 作業 4       |
| 升級溝通與期望管理                | "The fix needs a driver upgrade that requires downtime. How do you communicate this to the customer's VP?"          | 作業 4       |
| 部署健康與容量建議                | "Prepare a QBR for a customer running 256 GPUs. What metrics go in, what recommendations?"                           | 作業 6、7、9 |
| 跨團隊協調                        | "Engineering says it's not a bug; the customer says it is. What do you do?"                                           | 模擬面試 II  |
| 信任建立（Trusted Advisor）       | "How do you say no to a customer request without losing the relationship?"                                           | G5           |

## 4. 外商 JD 常見關鍵字對照

| JD 用語                                   | 它在本課程的位置                               |
| ----------------------------------------- | ---------------------------------------------- |
| technical collateral / enablement content | 作業 1、2、6、7（every one-pager）              |
| reference architecture / sizing guide     | 作業 6、7                                      |
| competitive analysis / battlecard         | 作業 3、5                                      |
| benchmark interpretation / MLPerf         | W1 D4 規格表素養、W12                           |
| TCO / unit economics / cost per token     | W10、作業 9                                    |
| positioning / messaging / launch          | W12、作業 3                                    |
| developer community / DevRel / workshops  | 作業 8、10                                     |
| escalation management / QBR               | 作業 4、模擬面試 II                             |
| cross-functional with PM/Eng/Sales        | 所有作業都要附「給誰看、他們下一步做什麼」      |
| GPU / accelerator / interconnect / fabric | 模組一、二                                     |
| inference serving / LLM deployment        | 模組三                                         |
| Kubernetes / cloud-native AI platform     | W6                                             |

## 5. 期末作品集建議組合

從 10 份作業中挑 2 件修到可投遞品質，建議依目標職缺：

| 目標職缺   | 作品 A（技術證據）         | 作品 B（溝通證據）                  |
| ---------- | -------------------------- | ----------------------------------- |
| TMM        | 作業 6 參考架構簡報        | 作業 1 或 7 的 one-pager            |
| Evangelist | 作業 8 talk（錄影 15 分鐘）| 作業 10 demo 腳本 + 錄影            |
| PMM        | 作業 3 競品定位            | 作業 9 TCO 模型 + 一頁結論          |
| TAM        | 作業 4 升級案例手冊        | 作業 7 sizing one-pager 改寫成 QBR 片段 |

另附一頁「我如何用提取練習與間隔學完這門課」：面試時被問「你怎麼快速學新東西」，這就是答案，而且是有數據（校準分數、錯題本曲線）的答案。

## 6. 自我定位問卷（第 1 週第一天做，第 12 週再做一次）

對每一條用 1～4 的深度刻度打分，第 12 週對照：

1. 我能在 30 秒內說清楚 HBM 為什麼決定推理能跑多大。
2. 我能畫出 HGX 8-GPU 伺服器的資料路徑並標每段頻寬。
3. 我能解釋 IB 與 Ethernet 在訓練場景的取捨，不只說「IB 快」。
4. 我能算一個 70B 模型在 FP8 下的權重與 KV 記憶體，並說明假設。
5. 我能用「情境 → 衝突 → 解法 → 證據」結構講一個 10 分鐘 talk。
6. 我能處理一個 GPU 效能升級案例的第一個小時。
7. 我能用定位五要素寫一頁競品定位。
8. 我能把每百萬 token 成本拆成硬體、電力、利用率、Goodput 四個因子。
