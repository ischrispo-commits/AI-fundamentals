# 模組一模擬面試題庫：硬體與系統（12/06 TMM 場使用，之後各場回收）

> 用法：面試官（或自己錄音）抽 4 題，每題追問兩層「為什麼」。英文提問、英文回答；下方「好答案要素」是中文備忘，不是逐字稿。評分用 [02_assessment_spec.md §7.2](../02_assessment_spec.md)。

## A. 技術深度（四職缺共用）

| #   | 問題（英文）                                                                                                                                          | 好答案要素                                                                                                                                                                  | 追問                                                                         |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| A1  | Why do we use GPUs rather than many-core CPUs for AI training? Be specific about the architecture.                                                   | 晶體管分配（運算單元 vs 控制與 cache）；SIMT／warp 讓數千 thread 共用指令流；HBM 總頻寬；一句「工作負載是幾千萬次相同的乘加」                                                   | Where does this break down? (divergence, small batch, latency-bound ops)     |
| A2  | Walk me through the memory hierarchy of a datacenter GPU and tell me which level matters most for LLM inference.                                      | register → L1/shared → L2（唯一共享、進出路徑）→ HBM；推理 decode 受 HBM 頻寬與容量限制；L2 40～50 MB 量級只能緩衝不能裝 KV                                                  | What changes if the batch size is 256 instead of 1?                          |
| A3  | HBM versus GDDR: why does every datacenter GPU pay for HBM?                                                                                           | 位寬換頻率、3D 堆疊、每 bit 功耗約一半；頻寬需求壓倒成本；舉 A100 2 TB/s vs RTX 5090 1.79 TB/s 說明「不是快一點，是量級與功耗」                                             | So why does the RTX 5090 still get close on bandwidth?                       |
| A4  | A customer reads "1.8 TB/s NVLink" on the B200 spec sheet. What do they need to understand before quoting that number?                                | 雙向總和 = 18 × 50 × 2；單向 900；與 PCIe Gen5 x16 雙向 126 比約 14×；Gbps vs GB/s；不可與 HBM 近存頻寬同尺度比                                                             | How would you explain the same thing to a CFO?                               |
| A5  | What is TF32 and why did NVIDIA introduce it?                                                                                                          | 8-bit 指數 + 10-bit 尾數 = 19 bits；範圍同 FP32、不改 code；吞吐 FP16 一半；降低訓練團隊採用 Tensor Core 的門檻                                                            | When would you tell a customer NOT to rely on TF32?                          |
| A6  | Explain MIG to me, then tell me when you would recommend against it.                                                                                   | 硬體級切分最多 7 實例、專屬 SM／顯存／L2／頻寬；多租戶推理、CI/CD；反對：需要整卡的訓練、單一實例頻寬不足的長尾工作負載                                                     | How is MIG different from MPS or time-slicing?                               |
| A7  | The B300 spec says 288 GB. Your TAM colleague's capacity plan uses 279 GB. Who is right?                                                               | 都對但口徑不同：288 卡規格、279 NVL72 可用、270 HGX 可用；系統形態少 6～9 GB 是慣例（GB200 192 vs 186）；規格表用 288、規劃用 270/279；標注「初步規格」                     | How do you keep such footnotes from making the slide unreadable?             |
| A8  | Compute the one-way bandwidth of PCIe Gen5 x16 and explain every term.                                                                                 | 32 GT/s × 0.985（128b/130b）× 16 ÷ 8 ≈ 63 GB/s；雙向 126；Gen6 換 PAM-4 + FLIT 效率 0.945                                                                                  | Why does one of our own docs say 128 GB/s bidirectional?                     |

## B. 職能情境

### TMM

| #   | 問題                                                                                                                                 | 好答案要素                                                                                                                      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| T1  | Sales wants a one-slide "H100 vs H200" comparison for a customer who runs inference. What goes on the slide and what goes in the footnotes? | 正文：顯存 80 vs 141 GB、頻寬 3.35 vs 4.8 TB/s、同一代算力與 NVLink；腳注：廠商規格、日期、「with sparsity」、形態（SXM）         |
| T2  | A benchmark claim in our whitepaper turns out to use sparse TFLOPS. The doc is already published. What do you do?                     | 立刻改並標版本與日期；內部通知業務；對外用 errata 而非悄悄改；之後建立「口徑檢查表」流程                                           |
| T3  | Build me the outline of a 2-page "how to read a GPU datasheet" guide for new SEs.                                                     | 四個口徑陷阱為骨架；每欄「它是什麼、怎麼算、常見誤讀、對客戶的意義」；一張 A100／H100／B200 對照表                                 |

### PMM

| #   | 問題                                                                                                                     | 好答案要素                                                                                                                      |
| --- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| P1  | Position HBM capacity as a buying criterion for inference customers in one sentence, then defend it.                    | 「推理能跑多大，由顯存決定，不由 TFLOPS 決定」；證據：decode 受頻寬限制、KV cache 佈 HBM；替代品比較：加卡 vs 大顯存卡          |
| P2  | A competitor's accelerator lists higher peak TFLOPS at a lower price. How do you reframe without disparaging?            | 先承認數字；轉到工作負載（推理看頻寬與容量、訓練看互連與軟體生態）；用 MLPerf 或客戶實測取代 peak；給「請用你的模型跑一次」的下一步 |

### TAM

| #   | 問題                                                                                                                                        | 好答案要素                                                                                                                                   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| M1  | A customer bought eight RTX 5090s for multi-GPU training and complains NCCL is slow. First three questions, likely root cause, and how you break the news. | 問卡型號、拓撲（`nvidia-smi topo -m`）、P2P 路徑；根因：GeForce 無 NVLink，只能走 PCIe 且 P2P 受限；溝通：先確認目標，再給兩條路（接受上限或換資料中心卡） |
| M2  | Your customer wants to run seven tenants on one A100 with MIG. What do you verify before saying yes?                                        | 每租戶顯存／SM 需求是否 ≤ 1g.10gb；是否有需要整卡的工作；監控（DCGM 對 MIG 的支援）；驅動與 K8s device plugin 版本                           |

### Evangelist

| #   | 問題                                                                                                                      | 好答案要素                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| E1  | Whiteboard a 5-minute explanation of "why GPUs" for a meetup of web developers.                                            | 從他們熟的東西出發（多執行緒 web server）→ 32 個工人一條指令 → 餵資料的頻寬 → 一個數字量級收尾；不講 warp 這個詞也能講完     |
| E2  | Design a 3-minute live demo that makes the audience "see" one-way versus bidirectional bandwidth.                         | 用 `nvbandwidth` 或 `p2pBandwidthLatencyTest` 的兩列輸出，先讓觀眾猜再揭曉；失敗備案：預錄輸出截圖                           |

## C. 自我介紹與動機（每場都問）

| #   | 問題                                                                                                   | 好答案要素                                                                                       |
| --- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| S1  | Tell me about yourself and why this role.                                                              | 現在的角色 → 看見的客戶問題 → 為什麼技術深度 + 溝通是解法 → 這 12 週怎麼補（有數據）                 |
| S2  | How do you learn a complex technical domain fast?                                                      | 提取練習、間隔、交錯；錯題本與校準分數；舉一個「高信心答錯後修正」的例子                             |
| S3  | Tell me about a time you had to say "I don't know" to a customer.                                       | STAR；重點是「我會這樣查、什麼時候回覆」；結果與學到的事                                            |
