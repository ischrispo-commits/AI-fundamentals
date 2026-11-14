# 開課前能力診斷（2026-11-11）

> 來源：「閱讀前測驗」對話。這份是**課程規格以外的一次性診斷**，用選擇題快速掃過全棧；課程內的測驗依 [02_assessment_spec.md](../../02_assessment_spec.md) 不出選擇題。作答規則：不會填 `?`，不猜。結果彙整在 [progress/log.md](../../progress/log.md)。

## 結果：7／16

| #   | 領域（對應週）            | 題目摘要                              | 作答   | 正解 | 判定         |
| --- | ------------------------- | ------------------------------------- | ------ | ---- | ------------ |
| 1   | LLM 理論（W8）            | self-attention 對序列長度 n 的複雜度   | ?      | C    | 不會         |
| 2   | 硬體（W1）                | GPU 適合深度學習的主因                 | D      | D    | ✅           |
| 3   | RAG（W11）                | RAG 解決什麼問題                       | A      | A    | ✅           |
| 4   | Agent（W11）              | MCP 是什麼                             | C      | C    | ✅           |
| 5   | CUDA（W1）                | 一個 warp 幾個 thread                  | C（猜） | B    | ❌ 猜錯       |
| 6   | CUDA（W1）                | shared memory 的可見範圍               | ?      | D    | 不會         |
| 7   | 推理（W9）                | KV Cache 的作用                        | C      | C    | ✅           |
| 8   | 推理（W9）                | Prefill／Decode 各受什麼限制           | C      | C    | ✅           |
| 9   | Sizing（W8、作業 7）      | 7B 模型 FP16 權重顯存                  | ?      | B    | 不會         |
| 10  | 微調（W8）                | LoRA 核心做法                          | A      | A    | ✅           |
| 11  | 雲原生（W6）              | Pod 申請 GPU 靠哪個機制                | ?      | D    | 不會         |
| 12  | 互連（W2）                | GPUDirect RDMA 的好處                  | C      | C    | ✅           |
| 13  | 叢集通訊（W5）            | Ring AllReduce 每卡送出量              | ?      | D    | 不會         |
| 14  | 推理系統（W9）            | PagedAttention 解決什麼                | ?      | B    | 不會         |
| 15  | MoE（W8）                 | Expert Parallelism 的通信模式          | ?      | A    | 不會         |
| 16  | GPU 運維（W4）            | `nvidia-smi` GPU-Util 100% 的意義      | ?      | B    | 不會         |

## 正解要點

1. O(n²)：每個 token 都要和所有 token 算注意力。
5. 32：見 K 點 `W01D01-K2`。
6. 同一個 thread block 內的 thread：見 K 點 `W01D02-K1`。
9. 約 14 GB：7B 參數 × 2 bytes（FP16）。
11. Device Plugin：把 GPU 註冊成 K8s 可排程的資源。
13. 2(N−1)/N · S：reduce-scatter 與 all-gather 各送 (N−1)/N · S。
14. 把 KV Cache 切成固定大小的區塊管理，減少碎片與浪費。
15. All-to-All：token 送到不同卡上的 expert，算完再送回。
16. 取樣期間內「有 kernel 在跑」的時間比例，不代表 SM 滿載。
