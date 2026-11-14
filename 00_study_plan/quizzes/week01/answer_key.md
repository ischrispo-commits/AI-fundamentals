# 第 1 週解答（含 K 點、來源、常見錯因、精緻化提問）

> 對答案順序：先填完信心，再看這裡。每題標 K 點（見 [k_points.md](k_points.md)）。數字口徑以 repo 2026-11-10 狀態為準；涉及廠商宣傳口徑者已註明。

## D1 週前測

| #   | K 點      | 參考答案                                                                                                                                                         | 來源                                              |
| --- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| P1  | W01D01-K1 | GPU：更多運算單元（ALU／FPU）、更高總記憶體頻寬、較少 cache 與簡單控制；CPU：複雜指令處理、高時脈、大 cache。                                                     | 01_gpu_characteristics.md:9-37                    |
| P2  | W01D01-K2 | 32。CUDA cores 在硬體上固定 32 個一組（類比 CPU 的向量單元）；cache line 128 B = 32 × 4 B 剛好餵一個 warp。                                                       | 01_gpu_characteristics.md:191-200；02_gpu_memory.md:25-27 |
| P3  | W01D01-K3 | SIMD 一條指令對所有資料做完全相同的事；SIMT 可以停用個別 thread，所以能走分支。代價：if/else 兩路串行，非活動 thread 閒置。                                       | 01_gpu_characteristics.md:145-160                 |
| P4  | W01D02-K4 | V100 HBM2 900 GB/s；A100 HBM2e 2.0 TB/s（2039）；H100 HBM3 3.35 TB/s；H200 HBM3e 4.8 TB/s；B200 HBM3e 8.0 TB/s。                                                 | 01_hbm_evolution.md:38-47                         |
| P5  | W01D02-K3 | 錯。GDDR 是頻率優先、HBM 是位寬優先；HBM 總頻寬更高（A100 2 TB/s vs RTX 5090 1.79 TB/s，且 HBM 更省電 ~3.5 vs ~7 pJ/bit）。消費卡用 GDDR 是成本考量。             | 01_hbm_evolution.md:21-35                         |
| P6  | W01D03-K2 | TF32 = FP32 的 8-bit 指數 + FP16 的 10-bit 尾數（19 bits），範圍同 FP32、尾數截斷。吸引力：不改 code 就能用 Tensor Core 加速 FP32 訓練（A100 上 TF32 156 TFLOPS）。 | 07_a100_architecture.md:57-63                     |
| P7  | W01D03-K4 | 最多 7 個，每個有專屬 SM、顯存、L2、頻寬。用：多租戶推理、小模型訓練、CI/CD 隔離。不用：需要整卡算力的訓練。                                                      | 07_a100_architecture.md:136-150                   |
| P8  | W01D04-K2 | 1.8 TB/s，**雙向總和** = 18 links × 50 GB/s（單向）× 2。                                                                                                        | nvlink_intro.md:192-199                           |
| P9  | W01D04-K4 | 單向 ≈ 32 GT/s × 0.985（128b/130b）× 16 ÷ 8 ≈ 63 GB/s；雙向 ≈ 126 GB/s。                                                                                       | 05_pcie_nvlink_speed_reference.md:106-122         |
| P10 | W01D03-K6 | 錯。288 GB 是卡規格；系統可用值為 HGX B300 270 GB、GB300 NVL72 279 GB（NVIDIA MIG 產品頁，標為初步規格）。容量規劃用 270／279。                                   | 05_pcie_nvlink_speed_reference.md:66-68；nvidia_gb300.md:33-39 |

## D2

| #   | K 點           | 參考答案                                                                                                                                                                                   | 來源                              | 常見錯因                                   |
| --- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------- | ------------------------------------------ |
| Q1  | W01D01-K1, K7  | 同 P1；對 AI 的意義：矩陣運算可高度平行（要很多 ALU）、模型與資料大（要高頻寬）、控制流簡單（不需要複雜分支預測）。                                                                        | 01_gpu_characteristics.md:9-37    | 只列差異沒連到工作負載                     |
| Q2  | W01D01-K2      | （1）硬體把 CUDA cores 固定分成 32 一組，像 CPU 的向量單元；（2）cache line 128 B = 32 × 4 B，一次剛好供一個 warp 的 32 個 4-byte 操作數。                                                   | 01_gpu_characteristics.md:191-200；02_gpu_memory.md:25-27 | 答「歷史慣例」                 |
| Q3  | W01D01-K4      | 不能，block 不可跨 SM。block 多於 SM 時，多個 block 排到同一個 SM 上執行。                                                                                                                 | 01_gpu_characteristics.md:243-247 | 把 block 與 warp 搞混                      |
| Q4  | W01D01-K5, K6  | A100：108 × 64 = 6912；V100：80 × 64 = 5120。                                                                                                                                             | 07_a100_architecture.md:11-14     | 用了 INT32 cores 算成 128                   |
| Q5  | W01D01-K3      | 錯。同一 warp 內 if 路與 else 路**串行**執行，另一路的 thread 閒置等待，這就是 divergence 成本。                                                                                           | 01_gpu_characteristics.md:151-160 | 以為硬體會把兩路排到不同 core              |
| Q6  | W01D01-K7      | 要素：CPU 核心少而「聰明」、GPU 核心多而「簡單」；AI 訓練是幾千萬個一樣的乘加，重點是吞吐與餵資料的頻寬；用「一位主管帶 32 個工人做同一件事」的比喻；結尾給數字量級（CUDA cores 數千 vs CPU 數十核）。 | 01_gpu_characteristics.md:33-37   | 對 CFO 講 warp、SIMT                       |

精緻化提問：為什麼 warp 大小一直維持 32、而 SM 數量每代都在變？（提示：哪一個是編程模型的契約，哪一個是製程與面積的函數）

## D3

| #   | K 點           | 參考答案                                                                                                                                                                 | 來源                           | 常見錯因                         |
| --- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------ | -------------------------------- |
| Q1  | W01D02-K1      | register file → L1／shared memory（同一塊物理記憶體，應用可調分界）→ L2（唯一全 SM 共享）→ global（HBM／GDDR；含 local、texture、constant 特殊區）。                      | 02_gpu_memory.md:36-75         | 把 shared memory 放在 L2 之後    |
| Q2  | W01D02-K3      | HBM 用「寬」換「頻率」（1024-bit／堆疊、1.2～3.2 GHz、3D 堆疊）；GDDR 用「高頻」換「窄」（32-bit、14～28 GHz）。資料中心付 HBM 成本是因為頻寬需求壓倒成本，且每 bit 功耗約一半。 | 01_hbm_evolution.md:21-35      | 忘了功耗這一項                   |
| Q3  | W01D02-K5      | 5 × 1024 bits = 5120 bits；× 1.593 GHz × 2（DDR）= 16.31 Tbit/s；÷ 8 = 2039 GB/s。口徑：A100-SXM4-80GB、HBM2e、廠商規格。                                                 | 01_hbm_evolution.md:50-56      | 忘 ×2 或忘 ÷8                    |
| Q4  | W01D02-K4      | V100 4、A100 5、H100 6、H200 8。                                                                                                                                         | 01_hbm_evolution.md:38-47      | A100 與 H100 對調                |
| Q5  | W01D01-K2；W01D02-K7 | register file 分 32 個 bank，一個 warp 的 32 個 thread 各用一個 bank；一行 32 × 4 B = 128 B，所以 cache line 128 B 一次餵滿一個 warp。                                  | 02_gpu_memory.md:25-27,48      | 沒把 bank、warp、cache line 連起來 |
| Q6  | W01D02-K2      | 要素：GPU 只有一個 L2 且被所有 SM 共享（CPU 每核有私有 L1／L2 加共享 L3）；L2 還位於 PCIe／NVLink 資料進出 device 的路徑上；A100 把 L2 從 6 MB 擴到 40 MB 是為了少跑 HBM。 | 02_gpu_memory.md:29-31,64；07_a100_architecture.md:9-27 | 只講「比較小」           |

精緻化提問：如果 L2 是進出 device 的必經路徑，那 GPUDirect RDMA 從網卡直寫 GPU 顯存時，資料有沒有經過 L2？（第 2 週會回答，先猜）

## D4

| #   | K 點           | 參考答案                                                                                                                                                                                       | 來源                                   | 常見錯因                           |
| --- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ---------------------------------- |
| Q1  | W01D03-K1      | 任五項：SM 80 → 108；L2 6 → 40 MB；HBM2 900 → HBM2e 2039 GB/s；NVLink 300 → 600 GB/s（12 × 25）；PCIe Gen3 → Gen4；12 nm → 7 nm；新增 MIG（7 實例）與 2:4 稀疏；Tensor Core 精度擴到 TF32／BF16／INT8／INT4。 | 07_a100_architecture.md:9-27           | 數字張冠李戴（如 NVLink 寫 900）    |
| Q2  | W01D03-K2      | 8-bit 指數（同 FP32）+ 10-bit 尾數（同 FP16）= 19 bits。成立原因：輸入保持 FP32，cuBLAS 在 CC ≥ 8.0 預設就走 TF32（框架有自己的開關）。代價：尾數精度截斷，吞吐為 FP16 一半。                   | 07_a100_architecture.md:57-73          | 以為要改成 FP16                     |
| Q3  | W01D03-K4      | 錯。MIG 每個實例有**專屬**的 SM、顯存、L2 與記憶體頻寬，隔離是硬體級的；這正是 MIG 相對時間切片／MPS 的價值。                                                                                   | 07_a100_architecture.md:136-150        | 把 MIG 當成軟體時間切片            |
| Q4  | W01D03-K6      | 288 = 卡規格（官方博客）；270 = HGX B300 系統可用；279 = GB300 NVL72 系統可用（MIG 產品頁，初步規格）。KV cache 容量問題用 270 或 279，依客戶形態。                                                | 05_pcie_nvlink_speed_reference.md:66-68；nvidia_gb300.md:33-39 | 用 288 做規劃          |
| Q5  | W01D02-K3      | HBM：1024-bit、3D 堆疊 + interposer；GDDR：32-bit、~7 pJ/bit、14～28 GHz、消費卡典型。                                                                                                          | 01_hbm_evolution.md:21-35              | pJ/bit 配反                        |
| Q6  | W01D03-K8      | 三問：卡型號確認是 GeForce 還是資料中心卡？拓撲（`nvidia-smi topo -m`）走 PCIe 哪一層？NCCL 用的是 P2P 還是經主機記憶體？最可能原因：GeForce 40／50 系沒有 NVLink，多卡只能走 PCIe，且 P2P 支援受限，通訊成了瓶頸。 | 05_pcie_nvlink_speed_reference.md:64；nvlink_intro.md:217-229 | 直接答「換 H100」沒問診 |

精緻化提問：MIG 的硬體隔離要付什麼代價？（提示：切成 7 份後單一實例的 SM 數與頻寬是多少，長尾工作負載會怎樣）

## D5

| #   | K 點                  | 參考答案                                                                                                                                                                                  | 來源                                       | 常見錯因                          |
| --- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | --------------------------------- |
| Q1  | W01D04-K1, K5, K6, K7 | （1）Gbps vs GB/s、單向 vs 雙向；（2）with sparsity vs dense；（3）卡規格 vs 系統可用（288 vs 270/279）；（4）近存頻寬（HBM）vs 片間頻寬（PCIe／NVLink）不可直接比；加分：同一規格不同口徑（計／不計編碼效率）。 | nvlink_intro.md:183-190；05_pcie_nvlink_speed_reference.md:46,66 | 只答出單向雙向      |
| Q2  | W01D04-K2             | 18 × 50 GB/s × 2 = 1.8 TB/s，雙向總和；每 link 單向 50 GB/s = 400 Gbps（PAM-4）。                                                                                                        | nvlink_intro.md:192-199                    | 寫成單向                          |
| Q3  | W01D04-K4             | 16 × 0.985 × 16 ÷ 8 ≈ 31.5 GB/s 單向。Gen6 改 PAM-4 + FLIT（256 B flit 中 242 B 載荷）→ 242/256 ≈ 0.945。                                                                                 | 05_pcie_nvlink_speed_reference.md:7-23,106-122 | 用 0.8 的 8b/10b 效率           |
| Q4  | W01D04-K7             | 把近存頻寬（GPU 到自己的 HBM）和片間頻寬（GPU 到另一張 GPU）放在同一個尺度比。它們回答的是不同問題：前者決定單卡能多快餵 SM，後者決定多卡協作的通訊成本；且 TP 等場景的資料本來就必須跨卡。          | 05_pcie_nvlink_speed_reference.md:46；nvlink_intro.md:217-229 | 只說「不能比」沒說為什麼 |
| Q5  | W01D02-K6             | 位寬 +25%（4 → 5 堆疊）× 每 pin 數據率 +81%（1.76 → 3.19 Gbps）≈ 2.3×。共同點：都是「減每鏈路信號線、加鏈路數」，NVLink 3.0 信號對 8 → 4、鏈路 6 → 12。                                     | 01_hbm_evolution.md:58-70；nvlink_intro.md:52-61 | 只答一個因子                   |
| Q6  | W01D04-K1             | 可行方案：雙向車道比喻（標 1.8 TB/s 是兩個方向加總，單向只有 900）；或現場跑 `nvbandwidth`／`p2pBandwidthLatencyTest` 看單向與雙向兩列數字；關鍵是讓觀眾自己發現「數字差一倍」。               | nvlink_intro.md:183-199                    | 只講定義沒設計「發現」的瞬間       |

精緻化提問：為什麼網路業界習慣報單向 Gbps、總線業界習慣報雙向 GB/s？（提示：各自的典型瓶頸在哪一側）

## D6 週測

| #   | K 點                  | 參考答案                                                                                                                                                                                                   | 來源                                   |
| --- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| W1  | W01D01-K1, K7         | 同 D2 Q1。                                                                                                                                                                                                 | 01_gpu_characteristics.md:9-37         |
| W2  | W01D01-K4             | 錯。block 不可跨 SM；平行度來自多個 block 分到多個 SM。                                                                                                                                                      | 01_gpu_characteristics.md:243-247      |
| W3  | W01D02-K2             | L2 cache。含意：進出資料都經 L2，L2 容量與頻寬影響 H2D／D2H 與跨卡傳輸的行為；A100 把 L2 擴到 40 MB。                                                                                                        | 02_gpu_memory.md:29-31,64              |
| W4  | W01D02-K6             | 4 × 1024 × 1.76 ÷ 8 ≈ 901 GB/s（≈ 900，口徑：V100 32 GB HBM2 規格）。                                                                                                                                       | 01_hbm_evolution.md:58-70              |
| W5  | W01D03-K2             | TF32 吞吐是 FP16 的一半（156 vs 312 TFLOPS）；TF32 用於不改 code 的訓練，FP16 用於訓練（混合精度）與推理。                                                                                                   | 07_a100_architecture.md:57-63          |
| W6  | W01D03-K3             | TF32 8× = 156；FP16 16× = 312；INT8 32× = 624 TFLOPS（dense）；帶 2:4 稀疏各翻倍（312／624／1248）。口徑：A100-SXM4-80GB 資料表折算。                                                                       | 07_a100_architecture.md:75-88          |
| W7  | W01D04-K1             | 錯。400G = 單向 400 Gbps = 50 GB/s 單向；GB/s 與 Gbps 差 8 倍，且網路口徑是單向。                                                                                                                             | nvlink_intro.md:183-190                |
| W8  | W01D04-K3, K4         | 18 × 25 × 2 = 900 GB/s 雙向；PCIe Gen5 x16 雙向 ≈ 126 GB/s → 約 7.1×。                                                                                                                                      | 05_pcie_nvlink_speed_reference.md:25-40,124-137 |
| W9  | W01D05-K2             | Time = Latency + Size ÷ Bandwidth；小資料由 Latency 主導，大資料由 Bandwidth 主導。                                                                                                                           | ai_latency_pyramid.md:134-139          |
| W10 | W01D05-K1             | SRAM／L1 15～30 ns < NVLink 單跳 80～250 ns ≈ HBM 250～350 ns < PCIe 往返 1～3 µs < kernel launch 5～15 µs。                                                                                               | ai_latency_pyramid.md:116-130          |
| W11 | W01D02-K4             | 同 P4。                                                                                                                                                                                                    | 01_hbm_evolution.md:38-47              |
| W12 | W01D03-K4             | 7 × 1g.10gb、3 × 2g.20gb、1 × 4g.40gb（或 1 × 7g.80gb）。用：多租戶推理、CI/CD；不用：需整卡的訓練。                                                                                                         | 07_a100_architecture.md:136-150        |
| W13 | W01D03-K8             | 錯。40 系（Ada）起 GeForce 全面移除 NVLink；只有資料中心 GPU 支援。                                                                                                                                          | 05_pcie_nvlink_speed_reference.md:64   |
| W14 | W01D03-K7             | FP4 15 vs 9 PFLOPS（+66%）；網路 800 vs 400 Gb/s（CX-8 vs CX-7）；每 GPU 顯存 279 vs 192 GB（NVL72 口徑，+45%）；C2C 同 900 GB/s。                                                                            | nvidia_gb300.md:25-31                  |
| W15 | W01D04-K6             | 錯。with sparsity 假設權重 2:4 結構化稀疏，dense GEMM 要用一半的數字。                                                                                                                                      | 07_a100_architecture.md:75-77,161-173  |
| W16 | W01D01-K3             | 同一 warp 內 thread 走不同分支時，兩路串行、閒置 thread 不做有用工作；成本來自 SIMT 共用一條指令流。                                                                                                        | 01_gpu_characteristics.md:151-160      |
| W17 | W01D02-K6；W01D04-K3  | HBM2e：每堆疊位寬不變、堆疊數 +25%、每 pin 速率 +81%。NVLink 3.0：每鏈路信號對 8 → 4（每鏈路頻寬維持 25 GB/s，靠更高單對速率），鏈路數 6 → 12，所以 300 → 600 GB/s。共同邏輯：少每條線的寬度、多條數，提升總並發與可路由性。 | 01_hbm_evolution.md:58-70；nvlink_intro.md:52-61 |
| W18 | W01D02-K5；W01D05-K3  | 6 × 1.0 TB/s = 6.0 TB/s。相對 H100（3.35 TB/s）頻寬高 1.8×，若容量也更大（HBM3e 堆疊通常更大），偏向推理（decode 受頻寬限制）；但下定論缺：算力（TFLOPS）、顯存容量、互連（NVLink 代別）、功耗與價格。          | 01_hbm_evolution.md:38-56；10_ai_related_course/kv_cache_course/01-kv-cache-basics/syllabus.md:52-53 |
| W19 | W01D05-K3             | 要素：結論先講（推理服務 decode 階段受顯存容量與頻寬限制，不是算力）；數字口徑（H200 141 GB／4.8 TB/s vs H100 80 GB／3.35 TB/s，廠商規格）；意義（更大 batch 與 KV cache、更長上下文、更少卡）；下一步（給模型大小、上下文長度、併發數，我們算一張 sizing 表）。 | 05_pcie_nvlink_speed_reference.md:48-62 |
| W20 | W01D03-K6；W01D04-K8  | 評分要素：三個數字來源各自講清；為什麼系統形態少 6～9 GB 是慣例（GB200 192 vs 186）；「初步規格」的風險提示；結尾給客戶一句可用的話。                                                                        | nvidia_gb300.md:33-39；05_pcie_nvlink_speed_reference.md:66-68 |

## 本週校準計算

正確率 = 答對題數 ÷ 20（W19、W20 用評分表折算：≥ 9/12 算對）。校準分數 = 1 − |平均信心 ÷ 5 − 正確率|。填入 `handouts/w01/review.md`。
