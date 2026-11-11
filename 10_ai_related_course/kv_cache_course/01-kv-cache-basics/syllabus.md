# 第 1 講：KV Cache 為什麼存在 — 教學大綱

## 基本信息

| 專案     | 內容                                                        |
| -------- | ----------------------------------------------------------- |
| 課時     | 120 分钟                                                    |
| 授課物件 | 有 Python / PyTorch 基礎的工程師；不要求 Transformer 注意力細節 |
| 先修     | 矩陣乘法、PyTorch 基礎；不要求 Transformer 注意力細節        |
| 本講定位 | 建立 token 級 KV 成本模型，為分頁、複用和容量規劃打底       |

## 教學目標

- **知識目標**：理解自迴歸生成中 K/V 的複用條件，掌握每 token 與總 KV 的兩行公式，以及注意力變體的影響。
- **能力目標**：給定模型 config、精度、序列長度和併發，算出 KV 顯存，判斷權重和 KV 誰先成為瓶頸。
- **素養目標**：報容量數字時同時說明模型、精度、序列長度和 batch。

本講使用兩行公式：

`per_token_bytes = 2 × b_kv × L × H_kv × D`

`total_bytes = per_token_bytes × T × batch`

| 符號    | 含義           | 說明                              |
| ------- | -------------- | --------------------------------- |
| `L`     | 層數           | 每層各有一份 K/V                  |
| `H_kv`  | KV head 數     | 不是 Q head 數；GQA/MQA 改這一項  |
| `D`     | head 維度      | 不是 hidden size / H_q            |
| `b_kv`  | 每元素位元組     | FP16/BF16=2，FP8/INT8=1，INT4=0.5 |
| `T`     | 每請求序列長度 | 包含 prompt 和已生成 token        |
| `batch` | 併發請求數     | 統一寫 `batch`，不用單字母 `B`    |

`T` 是本講的“當前總序列長度”；講 prefill 時如果只想說 prompt 長度，寫 `T_prompt`，不要和這個 `T` 混用。

模型陣容：Qwen3-0.6B（`L=28`、`H_q=16`、`H_kv=8`、`D=128`）+ Qwen2.5-7B（`L=28`、`H_q=28`、`H_kv=4`、`D=128`）+ Qwen2.5-72B（`L=80`、`H_q=64`、`H_kv=8`、`D=128`）。Qwen3 沒有 7B / 72B；Qwen3-0.6B 的 `head_dim` 是 128，不是 64。

## 時間安排

| 時間   | 環節       | 內容                                                                                                                                                                            |
| ------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 30 min | 概念       | 自迴歸迴圈；Q/K/V 的作用；因果掩碼下歷史 K/V 為什麼不變；prefill 與 decode 的直覺差異；用 3-token 玩具例子手算一行注意力                                                         |
| 45 min | 公式與演示 | KV 兩行公式與符號表；對照 Qwen3-0.6B 與 Qwen2.5 的 config 逐項代入；精度表；MHA / GQA / MQA / MLA；TTFT / TPOT / 吞吐；現場執行 `code/kv_estimator.py` 演示 batch、序列長度、精度的變化 |
| 35 min | 實驗       | 5 min 安裝與自檢 + 30 min 填表：用 `code/kv_estimator.py` 算 Qwen3-0.6B / Qwen2.5-7B / Qwen2.5-72B 的每 token KV 與總量；72B 單獨做 GPU 預算判斷                                   |
| 10 min | 答疑       | 回答公式參數、GQA/MLA、TTFT/TPOT 口徑問題；預告第 2 講                                                                                                                          |

## 重點與難點

| 類型 | 內容                             | 處理方式                                                                                                                    |
| ---- | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 重點 | KV 顯存公式                      | 逐參數拆解，代入真實 config 手算；強調 `H_kv` 不是 Q head 數                                                                |
| 重點 | prefill 與 decode 的差異         | 對比矩陣形狀和 arithmetic intensity；decode 說“典型小 batch、長上下文下頻寬受限”，大 batch 可能 compute-bound               |
| 難點 | MLA 為什麼不是簡單的 `H_kv` 變小 | 先講 latent 壓縮 + 共享 RoPE key，公式 `b_kv × L × (kv_lora_rank + qk_rope_head_dim)`，不乘 2；第 6 講落到 GLM 的 11 層 MLA |
| 難點 | 容量數字的口徑                   | 每個數字標註模型變體、精度、序列長度、batch；權重與 KV 分開記賬                                                             |
| 難點 | 72B 的預算判斷                   | 單卡 40 GiB 只算每 token KV，說明權重先爆；併發要用 8×80 GiB 或明確 TP                                                      |

## 本講產出

一頁 KV 成本模型，至少包含：

- 模型與 config 來源；
- 精度與每元素位元組；
- 每 token KV 位元組；
- 給定序列長度和併發下的總 KV；
- 權重（按 FP16 參數估算）；
- 與 GPU 預算的對比，以及“KV 與權重誰更大 / 是否超預算”。

## 參考材料

- [第 1 講實驗指令碼](code/kv_estimator.py)
- [AI-fundamentals KV Cache 技術體系](../../../09_inference_system/kv_cache/README.md)
- [KV Cache 基本概念](../../../09_inference_system/kv_cache/01_concepts/01_basic/)
- `~/Project/study/ai-infra-course/06-kvcache-optimization/code/calculate_qwen3_memory.py`
- `~/Project/study/ai-infra-course/06-kvcache-optimization/visuals/kv-cache-formula.html`

參考計算器的 Qwen3-0.6B 預設預設把 `head_dim` 當成 64，會算出 56 KiB；本講以 `head_dim=128`、112 KiB 為準，對答案時先核對 `num_key_value_heads`、`head_dim` 和精度。
