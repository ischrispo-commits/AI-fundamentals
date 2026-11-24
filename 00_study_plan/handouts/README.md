# 講義與作業存放處

由 `course-handout-builder` skill 產生並維護索引。每週一個目錄：

```text
handouts/
└── w01/
    ├── d01_gpu_vs_cpu.md        # 講義（含先想再讀、情境、概念、數字口徑、誤區、Pre-sales 口徑、課後提取、K 點）
    ├── d02_gpu_memory_hbm.md
    ├── …
    ├── assignment.md            # 週作業（規格見 01_syllabus.md §6.1）
    ├── review.md                # 週反思（複製 templates/weekly_review.md）
    └── audio/                   # 每日口說錄音（不進 git，見 .gitignore）
```

## 索引

| 週  | 日  | 講義 | 主題 | 產生日期 |
| --- | --- | ---- | ---- | -------- |
| 1   | 1   | [d01_gpu_vs_cpu.md](w01/d01_gpu_vs_cpu.md) | GPU vs CPU、SIMT／warp／SM | 2026-11-10 |
| 1   | 2   | [d02_gpu_memory_hbm.md](w01/d02_gpu_memory_hbm.md) | GPU 記憶體層級、HBM vs GDDR、頻寬公式、顯存 sizing | 2026-11-12 |
| 1   | 3   | [d03_gpu_generations_precision.md](w01/d03_gpu_generations_precision.md) | A100 → H100 → B300 代際、Tensor Core 精度、2:4 稀疏、MIG、卡規格 vs 系統可用 | 2026-11-24 |
| 1   | 4   | [d04_spec_sheet_literacy.md](w01/d04_spec_sheet_literacy.md) | 規格表素養：Gbps vs GB/s、單向 vs 雙向、PCIe 編碼、dense vs sparsity | 2026-11-24 |
| 1   | 5   | [d05_workload_card_selection.md](w01/d05_workload_card_selection.md) | 情境整合：延遲金字塔、訓練 vs 推理選卡、何時要 NVLink、MIG、消費卡限制 | 2026-11-24 |
| 2   | 1   | [d01_pcie_basics.md](w02/d01_pcie_basics.md) | PCIe 基礎：lane、代際與編碼、樹狀拓撲、鏈路訓練與掉速 | 2026-11-24 |
| 2   | 2   | [d02_pcie_topology_numa.md](w02/d02_pcie_topology_numa.md) | PCIe 拓撲層級、Switch vs Bridge、P2P 路徑、雙路 CPU 與 NUMA | 2026-11-24 |
| 2   | 3   | [d03_nvlink_nvswitch_c2c.md](w02/d03_nvlink_nvswitch_c2c.md) | NVLink 物理層與記憶體語義、NVSwitch、SHARP、NVLink-C2C | 2026-11-24 |
| 2   | 4   | [d04_gpudirect_dma.md](w02/d04_gpudirect_dma.md) | DMA 委託模型、GPUDirect P2P／RDMA／Storage、GDS 前提與「兩倍」口徑 | 2026-11-24 |
