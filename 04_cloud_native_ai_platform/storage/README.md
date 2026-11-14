# AI 儲存——訓練 I/O 和推理 KV Cache 的資料底座

訓練一輪次要讀上億張小圖片、檢查點動輒幾十上百 GB、推理要持續命中 KV Cache——AI 工作負載把儲存推到了一個尷尬的位置：既要像本地盤一樣快，又要像物件儲存一樣能擴。

本目錄覆蓋三種思路：

| 系統 | 定位 | 核心思路 |
|------|------|---------|
| [JuiceFS](juicefs/README.md) | 通用分散式檔案系統 | 資料與後設資料分離，兼容 POSIX，對接 S3/HDFS/MinIO 等后端 |
| [DeepSeek 3FS](deepseek_3fs/01_deepseek_3fs_design_notes.md) | 訓練專用高效能儲存 | 面向大規模模型訓練的並行檔案系統架構 |
| [ICMS](inference_context_memory_storage/01_icms_architecture.md) | 推理 KV Cache 儲存 | NVIDIA 推理上下文記憶體儲存架構解析 |

## 文件

### JuiceFS

- [JuiceFS 核心架構](juicefs/README.md)
- [檔案修改機制分析](juicefs/01_juicefs_file_modification_mechanism_analysis.md)
- [後端儲存遷移指南](juicefs/02_juicefs_backend_storage_migration_guide.md)

### DeepSeek 3FS

- [DeepSeek 3FS 設計筆記](deepseek_3fs/01_deepseek_3fs_design_notes.md)

### ICMS

- [ICMS 架構解析](inference_context_memory_storage/01_icms_architecture.md) — NVIDIA Rubin 平台的推理上下文儲存層 (G3.5)；2026-03 起官方更名為 CMX Context Memory Storage

## 相關資源

- [NCCL 分散式通訊測試](../../03_ai_cluster_ops/03_nccl/README.md) — 儲存效能直接影響訓練 I/O，而 NCCL 決定了 GPU 間的通訊
- [KV Cache 技術體系](../../09_inference_system/kv_cache/README.md) — 推理 KV Cache 與 ICMS 互補
