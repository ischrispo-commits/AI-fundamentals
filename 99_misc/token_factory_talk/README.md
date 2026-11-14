# Token Factory 演講專案

對外演講《Token Factory: AI 推理的成本革命》（南京大學校友會）的完整素材庫。

**對外圖文講解**：[《Token Factory：AI 推理的成本革命》24 頁 PPT 逐頁配圖講解](talk-illustrated.md)——按 PPT 頁序完整還原現場內容，適合直接閱讀與轉發。

<img src="./img/cover.jpg" width="600" alt="Token Factory：AI 推理的成本革命 — 演講封面"/>

## 內容結構

| 文件                                                                                           | 說明                                                                                                                   |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| [outline.md](outline.md)                                                                       | **可排練版演講提綱**：四部分結構 + 時間分配 + 逐小節要點/資料/轉場句/觀眾收穫 + Q&A 預判 + 資料核查清單                |
| [talk-illustrated.md](talk-illustrated.md)                                                     | **對外圖文講解**：PPT 24 頁逐頁配圖（img/cover+01–23）講解——"白菜化/Token 單位化 → 產品製造商 → 兩件事 → 國產算力差距"全文口徑 |
| [cluster-capacity-measurement.md](cluster-capacity-measurement.md)                             | **對外發布文件**：《Token 工廠的產能怎麼算？》——Goodput 框架 + AIPerf 落地（概念公開、內部資料脫敏）                  |
| [references/01-wechat-token-factory-model.md](references/01-wechat-token-factory-model.md)     | 兩年砍柴《Token工廠財務運營測算工具》微信原文（8 張 Sheet 模型全拆解，含下載方法）                                     |
| [references/02-ai-factory-ecosystem.md](references/02-ai-factory-ecosystem.md)                 | AI Factory 定義/黃仁勳敘事/分類框架/全球格局                                                                           |
| [references/03-business-model-and-finance.md](references/03-business-model-and-finance.md)     | 商業模式變革、財務測算結果、**電力佔比口徑矛盾辨析**、倉庫成本錨點                                                     |
| [references/04-cost-technology.md](references/04-cost-technology.md)                           | **物理三維框架（算/存/傳 + 能量統一）**、模型架構稀疏化（MoE/MoD/MLA/DSA）、KV Cache、硬體代際、價格歷史               |
| [references/05-jevons-demand-future.md](references/05-jevons-demand-future.md)                 | 傑文斯悖論、需求爆發資料、政策落地、未來方向                                                                           |
| [references/06-listed-companies.md](references/06-listed-companies.md)                         | **上市公司財報證據**：矽基流動招股書（毛利率 −24%）、CoreWeave 季報（66% 毛利仍淨虧）、一級市場同行資料                |
| [references/07-tokenfactory-whitepaper-2026.md](references/07-tokenfactory-whitepaper-2026.md) | **TokenFactory 白皮書 2026**（九章雲極 × InfoQ）結構化全文：八章核心內容、成本結構、產業鏈三層、九章雲極實踐、趨勢風險 |
| [references/08-hf-open-models-summer-2026.md](references/08-hf-open-models-summer-2026.md) | HF《State of Open Models: Summer 2026 Observations》報告摘要：模型能力與供給豐富度訊號（萬億參數開源競賽、開源追平閉源、296 萬個模型）與 Agent 流量 |
| [references/09-model-price-performance.md](references/09-model-price-performance.md) | **模型價效比躍遷**：GLM-5.3-Flash 與 Qwen3.8-Flash 同日雙發（2026-08-26）——性能/價格/架構資料、演講用法、口徑注 |
| [references/10-cluster-capacity-assessment.md](references/10-cluster-capacity-assessment.md) | **叢集產能評估框架**（內部倉庫引入）：SLO Goodput、單卡產能/叢集日上限/日產值四數、品質承諾 P99 體系——"利用率是第一槓杆"的運營量化版 |
| [references/11-parameter-vs-throughput.md](references/11-parameter-vs-throughput.md) | **模型選型對產能的影響**：V4 Pro/Flash 實測——單卡產能 ~2×、同卡數端到端 3.8×、通訊稅（拓撲 NVLink/IB 決定稅率） |
| [references/12-silicon-data-token-index.md](references/12-silicon-data-token-index.md) | **Silicon Data LLM Token 支出指數**：全市場平均支付價跌破 $1/百萬（历史新低、較峰值腰斬）——市場級價格錨點 |

## 注意

所有市場資料均為 2026 年 8 月搜索所得，引用前請複核。
