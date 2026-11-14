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
