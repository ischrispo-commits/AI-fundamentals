# 第 1 週可測知識點（K 點）清單

> 格式：`編號 | 難度 | 可檢驗的陳述 | 來源 file:line | 適合受眾`。難度：1 事實、2 機制、3 應用、4 遷移。所有第 1 週測驗只能從這裡出題；`course-handout-builder` 產生第 1 週講義時，結尾的 K 點清單須與本表一致（可增不可改）。來源行號以 2026-11-10 的 repo 狀態為準。

## D1（11/16）GPU vs CPU、SIMT、warp、SM

```text
W01D01-K1 | 1 | GPU 的晶體管分配偏向大量運算單元與高總記憶體頻寬；CPU 偏向複雜指令處理、高時脈與大 cache | 01_hardware_architecture/nvidia/understand_gpu_architecture/01_gpu_characteristics.md:9-37 | CxO、工程師
W01D01-K2 | 2 | 一個 warp 是 32 個連續索引的 thread；原因是 NVIDIA 硬體把 CUDA cores 固定分成 32 一組，且 cache line 為 32 × 4 B = 128 B | 01_gpu_characteristics.md:191-200；02_gpu_memory.md:25-27 | 工程師
W01D01-K3 | 2 | SIMT 比 SIMD 多了「可停用個別 thread」，因此能處理分支；但 if/else 兩路會串行執行，非活動 thread 閒置（warp divergence） | 01_gpu_characteristics.md:145-160 | 工程師
W01D01-K4 | 2 | SM 是 CUDA cores 的硬體家；一個 thread block 不能跨 SM，block 多於 SM 時多個 block 共用一個 SM；Volta 每 SM 有 4 個 warp 排程器 | 01_gpu_characteristics.md:237-252 | 工程師
W01D01-K5 | 1 | SM 數量：V100 80、Quadro RTX 5000 48、A100 108 | 01_gpu_characteristics.md:239；07_a100_architecture.md:9-13 | 工程師
W01D01-K6 | 2 | CUDA cores 總數 = SM 數 × 每 SM cores：V100 80 × 64 = 5120；A100 108 × 64 = 6912 | 07_a100_architecture.md:11-14 | 工程師
W01D01-K7 | 3 | GPU 為「可高度平行化」的工作負載而生：圖中每一排運算單元只配一個控制單元；這是「為什麼不用多核 CPU 跑 AI」的答案核心 | 01_gpu_characteristics.md:33-37 | CxO
```

## D2（11/17）記憶體層級、HBM vs GDDR、HBM 代際

```text
W01D02-K1 | 1 | GPU 記憶體由近到遠：register file → L1／shared memory（同一塊物理記憶體）→ L2（唯一被所有 SM 共享的 cache）→ global memory（HBM 或 GDDR）；local、texture、constant 是 global 的特殊區域 | 02_gpu_memory.md:36-75 | 工程師
W01D02-K2 | 2 | L2 cache 位於資料經 PCIe／NVLink 進出 device 的路徑上，進來的資料先經 L2 再到 global memory | 02_gpu_memory.md:29-31,64 | 工程師
W01D02-K3 | 2 | HBM 位寬優先：單堆疊 1024-bit、1.2～3.2 GHz、3D 堆疊 + Si interposer、約 3.5 pJ/bit；GDDR 頻率優先：32-bit 介面、14～28 GHz、PCB 平面排布、約 7 pJ/bit；消費卡用 GDDR 是成本考量 | 01_hardware_architecture/performance/01_hbm_evolution.md:21-35 | CxO、工程師
W01D02-K4 | 1 | HBM 代際與代表 GPU：V100 HBM2 4 堆疊 900 GB/s；A100 HBM2e 5 堆疊 5120-bit 2039 GB/s；H100 HBM3 6 堆疊 3.35 TB/s；H200 HBM3e 8 堆疊 4.8 TB/s；B200 HBM3e 8 堆疊 8.0 TB/s | 01_hbm_evolution.md:38-47 | 工程師
W01D02-K5 | 3 | 總頻寬 = 堆疊數 × 每堆疊頻寬；A100：5 × 1024 bits × 1.593 GHz × 2（DDR）÷ 8 = 2039 GB/s | 01_hbm_evolution.md:50-56 | 工程師
W01D02-K6 | 2 | A100 對 V100：位寬 +25%（4 → 5 堆疊）、每 pin 數據率 +81%（1.76 → 3.19 Gbps/pin），相乘得 2.3× 頻寬；設計邏輯是「減少每鏈路信號線、增加鏈路數」，與 NVLink 3.0 一脈相承 | 01_hbm_evolution.md:58-70 | 工程師、CxO
W01D02-K7 | 1 | V100 每個 SM 有 65536 個 4-byte 暫存器；register file 分 32 個 bank 對應 warp 的 32 個 thread | 02_gpu_memory.md:9-11,48 | 工程師
W01D02-K8 | 2 | 權重記憶體 ≈ 參數量 × 每參數 bytes（FP16／BF16 2、INT8 1、INT4 0.5，未含量化 metadata）；70B FP16 ≈ 140 GB，80 GB 單卡放不下，141 GB 單卡被權重塞滿、沒有 KV Cache 空間 | 09_inference_system/memory_calc/memory_analysis.md:24-38；01_hbm_evolution.md:42-46 | 客戶工程師、CxO
```

## D3（11/18）A100 → H100 → B200/B300 代際、Tensor Core 精度、MIG

```text
W01D03-K1 | 1 | A100 對 V100：SM 108 vs 80、L2 40 MB vs 6 MB、80 GB HBM2e 2039 GB/s、NVLink 12 × 25 = 600 GB/s、PCIe Gen4、TSMC 7nm、新增 MIG 與 2:4 結構化稀疏 | 07_a100_architecture.md:9-27 | 工程師
W01D03-K2 | 2 | TF32 = FP32 的 8-bit 指數 + FP16 的 10-bit 尾數 = 19 bits；數值範圍同 FP32、尾數截斷；訓練不必改 code；Tensor Core 吞吐為 FP16 的一半（156 vs 312 TFLOPS） | 07_a100_architecture.md:57-63 | 工程師、TAM
W01D03-K3 | 2 | A100 精度矩陣（相對 FP32 19.5 TFLOPS）：TF32 8×、FP16/BF16 16×、INT8 32×、INT4 64×、FP64 0.5×；帶 2:4 稀疏時 Tensor Core 各精度再翻倍 | 07_a100_architecture.md:75-88 | 工程師、PMM
W01D03-K4 | 3 | MIG 把一張 A100 切成最多 7 個實例，每個有專屬 SM、顯存、L2 與頻寬（如 7 × 1g.10gb、3 × 2g.20gb、1 × 7g.80gb）；適用多租戶推理與 CI/CD 隔離，訓練通常不用 | 07_a100_architecture.md:136-150 | TAM、CxO
W01D03-K5 | 1 | 主流資料中心 GPU 規格：H100 80 GB HBM3 3.35 TB/s、PCIe Gen5、NVLink 4.0 900 GB/s；H200 141 GB HBM3e 4.8 TB/s；B200 192 GB HBM3e 8.0 TB/s、NVLink 5.0 1.8 TB/s；B300（HGX）270 GB 可用、PCIe Gen6 | 01_hardware_architecture/performance/05_pcie_nvlink_speed_reference.md:48-62 | 工程師、PMM
W01D03-K6 | 3 | B300 顯存有三個數：卡規格 288 GB（官方博客口徑）、HGX B300 系統可用 270 GB、GB300 NVL72 系統可用 279 GB；讀規格表用 288，做容量規劃用 270／279，不可混用 | 05_pcie_nvlink_speed_reference.md:66-68；01_hardware_architecture/superchips/nvidia_gb300.md:33-39 | TMM、TAM
W01D03-K7 | 1 | GB300 對 GB200：FP4 算力 15 vs 9 PFLOPS（+66%）、每 GPU 網路 800 vs 400 Gb/s（CX-8 vs CX-7）、CPU-GPU NVLink-C2C 同為 900 GB/s | nvidia_gb300.md:25-31 | PMM
W01D03-K8 | 1 | 消費級 GeForce RTX 不支援 NVLink（40 系起全面移除）；只有資料中心 GPU 提供 | 05_pcie_nvlink_speed_reference.md:64 | TAM、業務
```

## D4（11/19）規格表素養：單位、口徑、公式

```text
W01D04-K1 | 2 | 網路視角用 Gbps 且常指單向（400G NIC = 單向 400 Gbps = 50 GB/s）；系統總線視角用 GB/s 且常指雙向總和 | 01_hardware_architecture/nvlink/nvlink_intro.md:183-190 | 全部
W01D04-K2 | 3 | B200 標稱 1.8 TB/s 是單 GPU 雙向總頻寬 = 18 links × 50 GB/s 單向 × 2 | nvlink_intro.md:192-199 | 工程師、TMM
W01D04-K3 | 1 | NVLink 代際：1.0 P100 4 × 20 = 160 GB/s；2.0 V100 6 × 25 = 300；3.0 A100 12 × 25 = 600；4.0 H100 18 × 25 = 900；5.0 B200 18 × 50 = 1.8 TB/s；6.0 Rubin 3.6 TB/s（GTC 2025 口徑；官網 2026-11 為 3.0 TB/s） | 05_pcie_nvlink_speed_reference.md:25-42 | 工程師
W01D04-K4 | 3 | PCIe 單向頻寬 = GT/s × 編碼效率 × lane 數 ÷ 8；Gen3～5 用 128b/130b（≈0.985），Gen6／7 用 PAM-4 + FLIT（≈0.945）；Gen5 x16 單向 ≈ 63 GB/s、雙向 ≈ 126 GB/s | 05_pcie_nvlink_speed_reference.md:7-23,106-122 | 工程師、TAM
W01D04-K5 | 4 | 同一個 PCIe 5.0 x16 雙向，速查表寫 ~126 GB/s（計編碼效率）、NVLink 文寫 128 GB/s（未計）；差異來自口徑，不是誰錯，引用時要標明 | 05_pcie_nvlink_speed_reference.md:17；nvlink_intro.md:66 | TMM
W01D04-K6 | 2 | 規格表上的 Tensor Core 算力常標「with sparsity」（2:4 結構化稀疏），dense 口徑要除以 2 | 07_a100_architecture.md:75-77,161-173 | TMM、PMM
W01D04-K7 | 2 | HBM 頻寬是「近存頻寬」（near-memory），PCIe／NVLink 是「片間頻寬」，兩者量級不同、不可直接比較 | 05_pcie_nvlink_speed_reference.md:46 | 工程師
W01D04-K8 | 3 | 任何數字標來源與日期；同一規格可能有宣傳口徑與官網口徑之差（NVLink 6.0 3.6 vs 3.0 TB/s、NVL72 域 260 vs 216 TB/s） | 05_pcie_nvlink_speed_reference.md:40-42 | TMM、PMM
```

## D5（11/20）情境整合與延遲金字塔

```text
W01D05-K1 | 1 | 延遲量級：Math < 1 ns；SRAM／L1 15～30 ns；DRAM／HBM 250～350 ns；GPU-GPU NVLink 80～250 ns；Host-Device PCIe 1～3 µs；kernel launch 5～15 µs | 01_hardware_architecture/performance/ai_latency_pyramid.md:116-130 | 工程師
W01D05-K2 | 3 | 傳輸時間 = Latency + Size ÷ Bandwidth；小資料看延遲、大資料看頻寬 | ai_latency_pyramid.md:134-139 | 工程師、TAM
W01D05-K3 | 4 | 推理 decode 在典型小 batch、長上下文下受記憶體頻寬限制，因此 HBM 容量與頻寬（如 H200 141 GB／4.8 TB/s）常比 TFLOPS 更決定推理能跑多大；大 batch 可能轉為 compute-bound | 10_ai_related_course/kv_cache_course/01-kv-cache-basics/syllabus.md:52-53；05_pcie_nvlink_speed_reference.md:48-62 | CxO、PMM
W01D05-K4 | 3 | NVLink 必要場景：張量並行（每層 all-reduce）、MoE all-to-all、超過單卡顯存的模型；非必要：單卡推理、資料並行（瓶頸在節點間網路）、小模型 LoRA | nvlink_intro.md:217-229 | TAM、業務
W01D05-K5 | 3 | MIG 用於多租戶推理可避免多個服務競爭同一 GPU；一張 A100-80GB 可切 7 × 1g.10gb | 07_a100_architecture.md:136-150 | TAM
```
