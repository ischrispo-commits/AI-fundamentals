# Ascend 950 微架構速查：來自 FlashMLA 算子報告的硬體資訊整理

> 2026-09-30 | 信息整理。全部數值來自單一來源：deepseek-ai/FlashMLA 倉庫官方文件《Ascend Sparse Attention Forward 演算法與最佳化技術簡析》（深度求索著，MIT License；本站存檔為 [《Ascend950 稀疏注意力 Forward 算子與最佳化技術簡析》](Ascend950_稀疏注意力Forward算子与优化技术简析.md)，存檔檔名用「算子」，下稱「源文件」），逐條標註出處章節。口徑是**算子視角的微架構**，不是官方 data sheet；效能數字為廠商自報，無第三方復現。另有三處補充：DeepGEMM-Ascend 與 DeepEP-Ascend 倉庫 README（縮放因子格式、卡級型號），以及 2026-09-30 對 FlashMLA 倉庫的程式碼深讀（B_TOPK 最終取值、MTE2 在飛數、VLOOP 檢出情況，隨條標註 file:line）。

## 一、AI Core：1 Cube + 2 Vector

| 項                        | 數值                                                                                            | 源文件出處                                                              |
| ------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| AI Core 構成              | **1 CUBE Core + 2 VECTOR Core**（本算子實際採用 1C2V，1C1V 被三個瓶頸否決，見第四節）           | 〈能否用 1C1V〉                                                         |
| CUBE Core 吞吐            | **4096 FMA/cycle**（打滿口徑）；關閉 HF32 mode 時降至 256 FMA/cycle                             | 〈每個 AI Core 負責多少個 q head〉〈FA 的 output accumulator 在哪里做〉 |
| MMAD 特性                 | M 維取 64 即可打滿 CUBE 吞吐                                                                    | 〈每個 AI Core 負責多少個 q head〉                                      |
| L0C 容量                  | 約 **256 KB**（128×512 float32 即佔滿；只能被 FixPipe 搬出或被 CUBE 用作累加器，無法原地乘標量） | 〈FA 的 output accumulator 在哪里做〉                                   |
| 核數 / 頻率（該分析場景） | 32 個 AI Core，主頻 1.65 GHz                                                                    | 〈每個 AI Core 負責多少個 q head〉的存算比指令碼                          |

## 二、儲存層次：L1 雙 bank、L2 5 TB/s

| 層級   | 數值 / 特性                                                                                           | 源文件出處                         |
| ------ | ----------------------------------------------------------------------------------------------------- | ---------------------------------- |
| L1     | **512 KB，分兩個 bank**（0–256K / 256K–512K 兩段地址空間）；Tensor 切兩份配平擺放可打滿雙 bank 頻寬   | 〈L1 bank 配平〉                   |
| L2     | 總頻寬 **5 TB/s**（32 核分攤，注意是片上 L2，不是 HBM）                                              | 〈每個 AI Core 負責多少個 q head〉 |
| UB     | 有 bank conflict 問題（NZ buffer 額外 pad 一行規避）；讀寫頻寬可被單個 SIMD VF 打滿                   | 〈高速 ND2NZ〉                     |
| icache | CUBE **32 KB** / VECTOR **16 KB** / SIMD VF **8 KB**——程式碼體積需控制（報告建議用 `VLOOP` 硬體迴圈、慎用內聯；程式碼深讀未在原始碼檢出該符號） | 〈icache miss 問題〉               |

## 三、搬運與流水約束

- **MTE2 在飛請求上限 16 個**（單 VECTOR Core 的 Issue Queue 深度）：稀疏 gather 逐 token 發請求會爆佇列，催生 gather2 技巧（`burst_count=2`、`src_stride` 設兩 token 地址差，一次拷兩個 token）。（〈gather2〉〈能否用 1C1V〉）
- **FixPipe 向外搬運 128 Byte/cycle/AI Core**（1C1V 被否的三個瓶頸之一，由這一口徑推出 `B_TOPK > 73.14`）。最終 1C2V 程式碼實際取 **`B_TOPK = 64`**（`config.h:55`），每 AIV 32 token、gather2 折半后恰好 **16 個在飛 MTE2 請求**，與 16 的佇列深度持平。（〈能否用 1C1V〉；程式碼深讀 `kernel_body.h:1041`）
- **BIU 訪存合併條件**：源和目標**都連續**才合併。「源連續、目的不連續」無法合併，L2 頻寬利用率低——KV 的 ND2NZ 被迫繞行 UB 用 SIMD VF 完成，而不是走 GM→L1 隨路轉換。（〈KV 的 ND2NZ Layout 轉換何時進行〉）
- **硬件 PIPE 順序發射、順序執行**：`PIPE_V` 前一條不發射會阻塞整條管線；跨核訊號用 SS buffer + cross core flag（能讀寫 SS buffer 的只有 scalar core）。（〈如何進行 skip-scale 的同步〉〈流水線〉）

## 四、數值格式與 KV Cache layout

- KV Cache 支持 **FP8 / FP4**，使用時反量化為 bfloat16 送 CUBE；decoding 工況下 1C1V 時反量化頻寬追不上 CUBE（micro-benchmark），也是 2V 的理由之一。（〈能否用 1C1V〉）
- 本算子把**一個 token 的 data 與 scale 相鄰放置**（舊版 FlashMLA 是塊內 data 全在前、scale 全在后），MTE2 一次拷齊。（〈Decoding KV Cache Layout 最佳化〉）
- scale-O 在 NPU 上代價高（FixPipe 搬 L0C→UB、再 VF 累加），因此 skip-scale（rescale 閾值 `exp(6)`）在 NPU 上收益比 GPU 更大。（〈演算法回顧〉〈如何進行 skip-scale 的同步〉）
- 補充（另一來源）：DeepGEMM-Ascend README 載明昇騰側縮放因子格式為一對 **UE8M0 打包進 int16、MN-major**，與 NVIDIA 格式不同。

## 五、設計決策的硬體依據

源文件最有價值的部分，是把四個設計選擇全部還原成硬體數字：

1. **為什麼每 AI Core 64 個 q head**：存算比按 CUBE 4096 FMA/cycle、L2 5 TB/s 計算，head ≥ 64 才是 compute bound；head=128 會把 L0C 撐爆（128×512 float32 = 256 KB），且 MMAD M=64 已夠快。（存算比對照表見源文件，head×topk 從 16×512 到 128×1024 共 8 組資料）
2. **為什麼 1C2V 而非 1C1V**：三個 bound——MTE2 佇列深 16、反量化頻寬、FixPipe 128 B/cycle。
3. **為什麼 KV 經 UB 繞行做 ND2NZ**：BIU 只在源、目的都連續時合併訪存。
4. **B_TOPK 的兩個口徑**：1C1V 討論裡 FixPipe bound 要求 `> 73.14`（報告建議 96/128）；最終 1C2V 程式碼取 64，gather2 折半后每 AIV 恰好 16 個在飛 MTE2 請求，與 16 的佇列深度持平（FlashMLA `config.h:55`、`kernel_body.h:1041`）。

## 六、效能錨點與邊界

- DeepSeek V4.1 典型工況：稀疏注意力 prefill **410 TFLOPS**（硬體峰值 95%）、decode **360 TFLOPS**（83%）——廠商自報。
- **本文件沒有的**：HBM 容量與頻寬、TDP/功耗、卡間互聯、Die 面積。L2 的 5 TB/s 是片上頻寬，勿與 HBM 混淆。卡級資訊全批開源材料裡僅出現「950DT」型號名與 Atlas 850E 超節點字樣（出自 DeepEP-Ascend README），無 data sheet。

## 來源

- 源文件：[deepseek-ai/FlashMLA](https://github.com/deepseek-ai/FlashMLA) `docs/20260930-ascend-prefill-deep-dive-zh.md`（本站存檔：[Ascend950 稀疏注意力 Forward 算子與最佳化技術簡析](Ascend950_稀疏注意力Forward算子与优化技术简析.md)）
- 補充：[deepseek-ai/DeepGEMM-Ascend](https://github.com/deepseek-ai/DeepGEMM-Ascend)、[deepseek-ai/DeepEP-Ascend](https://github.com/deepseek-ai/DeepEP-Ascend) README（縮放因子格式、卡級型號）
- 程式碼深讀：2026-09-30 淺克隆核對（B_TOPK 取值、MTE2 在飛數、VLOOP 檢出情況）
- 背景報道：深度求索公眾號《DeepSeek 開源昇騰基礎元件》（2026-09-30）
