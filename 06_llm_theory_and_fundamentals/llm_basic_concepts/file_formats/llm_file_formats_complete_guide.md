# 大模型文件格式完整指南

大語言模型（LLM）部署中涉及多種模型檔案格式，格式的選擇直接影響模型的載入速度、推理性能、記憶體佔用與跨平台相容性。理解各類格式的技術特性與適用場景，有助於構建高效、可擴展、安全的部署方案。

---

## 一、原生訓練框架格式

### 1.1 PyTorch 系列格式

#### `.pt` / `.pth`

* **格式類型**：基於 Python `pickle` 協議的序列化格式，支持完整的 Python 物件圖序列化。
* **內容結構**：通常包含 `state_dict`（模型權重）、最佳化器狀態、訓練超參數、模型配置等。
* **載入方式**：需結合模型定義程式碼使用 `torch.load()` 載入，支持 `map_location` 參數進行裝置對映。
* **安全風險**：由於使用 `pickle`，載入時會執行任意 Python 程式碼，存在程式碼注入風險。
* **典型用途**：研究實驗、模型斷點恢復、本地訓練存檔、完整訓練狀態儲存。

#### `.bin`

* **實質說明**：Hugging Face 生態中的 `.bin` 文件（如 `pytorch_model.bin`）本質上是 `.pt` 格式的重命名版本，內容格式完全相同。
* **生態整合**：透過 Transformers 庫的 `from_pretrained()` 方法自動識別和載入，支援自動分片載入。
* **命名約定**：遵循 `pytorch_model.bin`、`training_args.bin` 等標準命名規範。

### 1.2 TensorFlow 系列格式

#### `.ckpt`

* **組成結構**：
  * `.ckpt.index`：張量名稱與資料檔案分片的對映索引表。
  * `.ckpt.data-*`：儲存模型權重的二進位制資料檔案（可能多個分片）。
  * `.ckpt.meta`（TF 1.x）：計算圖的 Protocol Buffer 定義。
* **版本差異**：TF 1.x 和 2.x 在檢查點格式上存在相容性差異。
* **載入方式**：需配合模型構圖程式碼或透過 `tf.train.Checkpoint` API 載入。

#### `.pb`（SavedModel 格式）

* **格式特性**：TensorFlow 的標準部署格式，包含完整的計算圖結構與變數值。
* **目錄結構**：
  
  ```text
  saved_model/
  ├── saved_model.pb        # 圖定義
  ├── variables/           # 權重目錄
  │   ├── variables.index
  │   └── variables.data-*
  └── assets/             # 附加資源（可選）
  ```

* **推理獨立性**：無需模型原始碼，可直接在 TensorFlow Serving、TensorFlow Lite 中使用。
* **簽名機制**：支援多個 `serving_default` 簽名，用於版本管理與介面繫結。

---

## 二、安全與現代格式

### `.safetensors`

* **設計初衷**：解決傳統 pickle 格式的安全風險與載入效能問題，提供確定性的模型儲存方案。
* **技術特點**：
  * **零複製載入**：支援記憶體對映（mmap），大模型可實現秒級載入，避免完整解序列化。
  * **純資料格式**：不包含任何可執行程式碼，從根本上消除程式碼注入風險。
  * **確定性儲存**：相同模型始終產生相同的檔案雜湊值，便於完整性驗證和快取。
  * **跨語言支援**：提供 Python、Rust、JavaScript、C++ 等多語言繫結。
* **檔案結構**：Header（JSON 後設資料）+ 對齊的張量資料塊。
* **生態應用**：已成為 Hugging Face 的預設推薦格式，正逐步取代 `.bin` 格式。
* **效能優勢**：載入速度比 pickle 格式提升 10-100 倍，特別適合大模型部署。

---

## 三、跨框架與中間表示格式

### `.onnx`（Open Neural Network Exchange）

* **定位**：框架無關的神經網路中間表示，用於模型標準化和跨平台部署。
* **圖結構**：基於 Protocol Buffer 的有向無環圖（DAG）表示，支援靜態計算圖。
* **兼容性控制**：
  * **Opset 版本**：透過 `opset_version` 管理算子版本與相容性（主流 runtime 已支持 opset 21+，截至 2026-11）。
  * **算子支持**：支持 200+ 標準算子，覆蓋主流深度學習操作。
* **最佳化與量化**：
  * 原生支持 INT8、FP16、BF16 等量化格式。
  * 支援動態量化和靜態量化工作流。
* **應用限制**：
  * 控制流表達能力有限（雖有 If/Loop/Scan 等控制流算子，但在圖中表達迴圈、分支等動態邏輯較繁瑣）。
  * 對自定義算子支援有限。
  * 轉換複雜模型時可能出現精度損失。
* **兼容部署平台**：ONNX Runtime、TensorRT、OpenVINO、DirectML 等主流推理引擎。

---

## 四、推理最佳化格式

### 4.1 CPU 最佳化：`.gguf`（GPT-Generated Unified Format）

* **格式演進**：由 GGML 格式演化而來，解決了元資訊表達能力不足和擴展性問題。
* **量化策略**：
  * **K-means 量化**：Q2_K、Q3_K、Q4_K、Q5_K、Q6_K（2-6 bit 非均勻量化）。
  * **傳統量化**：Q4_0、Q4_1、Q5_0、Q5_1、Q8_0（4-8 bit 均勻量化）。
  * **浮點格式**：F16（半精度）、F32（單精度）。
* **記憶體管理**：
  * 支援記憶體對映（mmap），10B+ 參數模型可在秒級時間內載入。
  * 按需載入機制，減少記憶體峰值佔用。
* **硬體適配**：針對 x86-64、ARM64、Apple Silicon 等架構的 SIMD 指令集最佳化。
* **推理引擎**：llama.cpp、Ollama、LM Studio、GPT4All 等。
* **效能特點**：在 CPU 上可達到接近 GPU 的推理速度（特別是量化模型）。

### 4.2 GPU 加速：`.trt` / `.engine`（TensorRT 格式）

* **編譯特性**：
  * 將 ONNX/TensorFlow 模型編譯為針對特定 GPU 架構最佳化的執行引擎。
  * 支持 Volta、Turing、Ampere、Hopper 等 GPU 架構。
* **精度支持**：
  * **FP32/FP16**：標準浮點精度。
  * **INT8**：需要校準資料集進行量化。
  * **INT4**：Ampere 架構及以上支援，需 TensorRT 8.5+。
* **圖最佳化技術**：
  * **層融合**：將多個算子融合為單個 kernel。
  * **記憶體最佳化**：自動最佳化記憶體佈局和重用策略。
  * **Kernel 調優**：為特定輸入尺寸選擇最優 CUDA kernel。
* **硬體繫結**：編譯後的 `.engine` 檔案與生成時的 GPU 型號、CUDA 版本、TensorRT 版本強繫結。
* **動態支援**：
  * 支援動態 batch size、序列長度（需編譯時指定 min/opt/max 範圍）。
  * 支持多 profile 以適應不同輸入尺寸。

### 4.3 移動端部署格式

#### `.tflite`（TensorFlow Lite）

* **目標平台**：Android、iOS、Raspberry Pi、Coral Edge TPU 等邊緣裝置。
* **模型最佳化**：
  * **算子融合**：自動合併相鄰算子減少計算開銷。
  * **量化支持**：動態量化、靜態量化、QAT（量化感知訓練）。
  * **稀疏化**：支援結構化和非結構化稀疏模型。
* **硬件加速**：
  * **GPU Delegate**：OpenGL ES、Vulkan 加速。
  * **NNAPI Delegate**：Android 神經網路 API。
  * **Core ML Delegate**：iOS 平台加速。
  * **Edge TPU**：Google Coral 專用加速器。
* **后端框架**：XNNPACK、Eigen、gemmlowp 等最佳化庫。

#### `.mlmodel` / `.mlpackage`（Apple Core ML）

* **格式演進**：`.mlmodel`（單檔案）→ `.mlpackage`（目錄結構，支持大模型）。
* **平台最佳化**：專為 iOS/macOS/watchOS/tvOS 生態設計，深度整合系統框架。
* **硬件加速**：
  * **Neural Engine**：Apple 自研神經網路處理器。
  * **GPU 加速**：Metal 框架支持。
  * **CPU 最佳化**：針對 Apple Silicon 的向量化指令。
* **隱私特性**：所有推理在裝置本地完成，資料不上傳雲端。
* **開發整合**：與 Xcode、Swift、Objective-C 無縫對接，支援實時預覽。

---

## 五、分散式部署格式與機制

### 5.1 模型分片機制

對於超過單檔案系統限制或網路傳輸限制的大模型（通常 > 2GB），採用分片儲存機制：

* **分片命名規範**：
  
  ```text
  pytorch_model-00001-of-00005.bin
  pytorch_model-00002-of-00005.bin
  pytorch_model-00003-of-00005.bin
  pytorch_model-00004-of-00005.bin
  pytorch_model-00005-of-00005.bin
  ```

* **索引檔案結構**（`pytorch_model.bin.index.json`）：
  
  ```json
  {
    "metadata": {
      "total_size": 13231323136,
      "format": "pt"
    },
    "weight_map": {
      "model.embed_tokens.weight": "pytorch_model-00001-of-00005.bin",
      "model.layers.0.self_attn.q_proj.weight": "pytorch_model-00001-of-00005.bin",
      "model.layers.0.self_attn.k_proj.weight": "pytorch_model-00002-of-00005.bin",
      ...
    }
  }
  ```

* **Safetensors 分片**：
  
  ```json
  {
    "metadata": {"total_size": 13231323136},
    "weight_map": {
      "model.embed_tokens.weight": "model-00001-of-00005.safetensors",
      ...
    }
  }
  ```

### 5.2 分布式推理策略

* **張量並行（Tensor Parallelism, TP）**：
  * 橫向切分單層權重矩陣，分配到多個 GPU 平行計算。
  * 適用於注意力層、MLP 層的權重切分。
  * 需要裝置間高頻寬通訊（如 NVLink）。

* **流水線並行（Pipeline Parallelism, PP）**：
  * 縱向切分模型層次，不同裝置處理不同 Transformer 層。
  * 透過微批次（micro-batch）流水線減少裝置空閒時間。
  * 適合層數較多的大模型。

* **資料並行（Data Parallelism, DP）**：
  * 多個裝置分別處理不同輸入批次，透過 AllReduce 同步梯度。
  * 推理時可直接並行處理多個請求。

* **專家混合（Mixture of Experts, MoE）**：
  * 將部分專家網路分佈到不同裝置。
  * 根據輸入動態路由到相應專家，減少單次推理的計算量。

---

## 六、格式轉換工具鏈與實踐

### 6.1 主要轉換工具

#### Hugging Face 生態工具

* **基礎 API**：
  * `model.save_pretrained(path, safe_serialization=True)`：儲存為 safetensors 格式。
  * `AutoModel.from_pretrained(path, torch_dtype=torch.float16)`：自動識別格式載入。

* **轉換指令碼**：
  * `convert_tf_checkpoint_to_pytorch.py`：TensorFlow → PyTorch。
  * `convert_pytorch_checkpoint_to_tf2.py`：PyTorch → TensorFlow 2.x。
  * `convert_slow_tokenizer.py`：慢速分詞器 → 快速分詞器。

#### ONNX 工具鏈

* **匯出工具**：
  * `torch.onnx.export()`：PyTorch 模型匯出 ONNX。
  * `tf2onnx`：TensorFlow 模型轉換 ONNX。
  * `sklearn-onnx`：Scikit-learn 模型轉換。

* **最佳化工具**：
  * `onnx-simplifier`：簡化 ONNX 圖結構，去除冗余算子。
  * `onnxoptimizer`：應用圖最佳化 pass。
  * `onnx-tools`：模型驗證、視覺化、量化。

#### 量化與最佳化工具

* **GGUF 轉換**：
  * `llama.cpp/convert.py`：HF 模型 → GGUF 格式。
  * `ggml-quantize`：GGUF 模型量化工具。

* **量化庫**：
  * **AutoGPTQ**：基於 GPTQ 算法的 4bit 量化。
  * **BitsAndBytes**：動態 4bit/8bit 量化，支持 QLoRA。
  * **Intel Neural Compressor**：英特爾 CPU 最佳化量化。
  * **NVIDIA TensorRT-LLM**：GPU 大模型推理最佳化。

### 6.2 轉換最佳實踐

#### 轉換前準備

1. **環境一致性**：確保轉換環境與目標部署環境的依賴版本一致。
2. **模型驗證**：檢查源模型的完整性和可載入性。
3. **基准建立**：記錄原始模型的推理結果作為轉換後的對比基準。

#### 轉換過程控制

1. **精度驗證**：

   ```python
   # 數值一致性檢查示例
   import torch
   import numpy as np
   
   def compare_outputs(output1, output2, rtol=1e-3, atol=1e-5):
       return np.allclose(output1.numpy(), output2.numpy(), rtol=rtol, atol=atol)
   ```

2. **效能基準測試**：
   * **吞吐量測試**：測量單位時間內處理的 token 數。
   * **延遲測試**：測量單次推理的端到端時間。
   * **記憶體佔用**：監控推理時的峰值記憶體使用。

3. **資源評估**：
   * **載入時間**：不同格式的模型載入速度對比。
   * **儲存空間**：檔案大小對比（考慮壓縮效果）。
   * **相容性測試**：在目標平台上的實際執行驗證。

#### 常見問題處理

1. **精度損失**：
   * 檢查量化配置是否過於激進。
   * 驗證轉換過程中的數值截斷問題。
   * 考慮使用校準資料集進行更精確的量化。

2. **效能不達預期**：
   * 檢查是否啟用了硬體加速（GPU、專用晶片）。
   * 驗證batch size 和序列長度設定。
   * 考慮模型結構是否適合目標平台最佳化。

3. **相容性問題**：
   * 確認目標執行時版本支援所需算子。
   * 檢查動態形狀支援情況。
   * 驗證自定義算子的轉換情況。

---

## 七、格式選擇決策框架

### 7.1 應用場景導向選擇

| 應用場景         | 首選格式                        | 備選格式                     | 關鍵考量因素                   |
| ------------ | --------------------------- | ------------------------ | ------------------------ |
| 研究與實驗        | `.pt` / `.ckpt`             | `.safetensors`           | 保留完整訓練上下文，便於除錯與繼續訓練      |
| 生產 Web 服務    | `.safetensors` / `.onnx`    | `.bin` → `.safetensors`  | 安全性、載入速度、推理引擎兼容性         |
| CPU 本地部署     | `.gguf`                     | `.onnx`                  | 記憶體效率、量化支持、跨平台兼容性         |
| GPU 高性能推理    | `.engine` / `.safetensors`  | `.onnx`                  | 推理性能、硬體最佳化、動態輸入支援         |
| 移動端/邊緣裝置    | `.tflite` / `.mlmodel`      | `.onnx`                  | 模型大小、功耗、硬件加速支持           |
| 跨平台分发        | `.onnx`                     | `.safetensors`           | 標準化程度、執行時支援廣度            |
| 模型微調         | `.pt` / `.safetensors`      | `.ckpt`                  | 梯度計算支援、最佳化器狀態儲存           |
| 模型服務化        | `.safetensors` / `.onnx`    | `.pb`                    | 服務穩定性、版本管理、API 兼容性       |

### 7.2 技術特性對比

| 特性維度      | `.pt/.bin` | `.safetensors` | `.onnx` | `.gguf` | `.trt` | `.tflite` |
| --------- | ---------- | -------------- | ------- | ------- | ------ | --------- |
| 載入速度      | ⭐⭐         | ⭐⭐⭐⭐⭐          | ⭐⭐⭐     | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐⭐  | ⭐⭐⭐       |
| 推理性能      | ⭐⭐⭐        | ⭐⭐⭐⭐           | ⭐⭐⭐⭐    | ⭐⭐⭐⭐    | ⭐⭐⭐⭐⭐  | ⭐⭐⭐⭐      |
| 記憶體效率      | ⭐⭐         | ⭐⭐⭐⭐           | ⭐⭐⭐     | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐   | ⭐⭐⭐⭐⭐     |
| 跨平台兼容性    | ⭐⭐⭐        | ⭐⭐⭐⭐           | ⭐⭐⭐⭐⭐   | ⭐⭐⭐     | ⭐⭐     | ⭐⭐⭐       |
| 安全性       | ⭐          | ⭐⭐⭐⭐⭐          | ⭐⭐⭐⭐    | ⭐⭐⭐⭐    | ⭐⭐⭐⭐   | ⭐⭐⭐⭐      |
| 生態成熟度     | ⭐⭐⭐⭐⭐      | ⭐⭐⭐⭐           | ⭐⭐⭐⭐    | ⭐⭐⭐     | ⭐⭐⭐⭐   | ⭐⭐⭐⭐      |
| 開發除錯友好性   | ⭐⭐⭐⭐⭐      | ⭐⭐⭐⭐           | ⭐⭐      | ⭐⭐      | ⭐⭐     | ⭐⭐        |

### 7.3 決策流程圖

```text
開始選擇模型格式
        ↓
    是否需要訓練/微調？
    ┌─── 是 ──→ .pt/.safetensors
    └─── 否
        ↓
    目標部署平台？
    ├─── GPU伺服器 ──→ .safetensors/.engine
    ├─── CPU伺服器 ──→ .gguf/.onnx
    ├─── 移動裝置   ──→ .tflite/.mlmodel
    └─── 跨平台    ──→ .onnx
        ↓
    效能要求級別？
    ├─── 極致效能 ──→ 專用最佳化格式(.engine/.gguf)
    ├─── 平衡性能 ──→ 通用格式(.safetensors/.onnx)
    └─── 相容優先 ──→ 標準格式(.onnx)
        ↓
    確定最終格式
```

---

## 八、未來發展趨勢與展望

### 8.1 標準化趨勢

* **統一中間表示**：ONNX、MLIR、OpenXLA 等專案推動跨框架標準化。
* **安全格式普及**：safetensors 等安全格式逐漸成為預設選擇。
* **量化標準化**：INT4、FP8 等新精度格式的標準化推進。

### 8.2 效能最佳化方向

* **零複製技術**：記憶體對映、共享記憶體等技術減少資料複製開銷。
* **異構計算支援**：CPU、GPU、NPU 等多種處理器的協同最佳化。
* **動態最佳化**：執行時根據輸入特徵動態選擇最優執行策略。

### 8.3 新興技術格式

* **IREE-MLIR**：Google 開源的端到端編譯器中間表示。

### 8.4 配套推理生態（框架/庫，非格式）

以下不屬於模型檔案格式，而是圍繞模型部署的推理框架/最佳化庫，常與上述格式配合使用：

* **Apple MLX**：針對 Apple Silicon 最佳化的統一機器學習框架（模型權重多以 safetensors 儲存）。
* **FasterTransformer**：NVIDIA 針對 Transformer 架構的專用推理最佳化庫。
* **DeepSpeed-Inference**：Microsoft 的大模型推理最佳化框架。

### 8.5 行業發展預測

1. **格式收斂**：預計未來 2-3 年內，主流格式將收斂為 3-5 種核心標準。
2. **自動化工具鏈**：模型格式轉換和最佳化將更加自動化和智慧化。
3. **硬體感知最佳化**：格式選擇將更多地考慮目標硬體的特性和限制。
4. **安全性強化**：模型檔案的完整性驗證和防篡改機制將成為標配。

透過深入理解各種模型檔案格式的技術特性、適用場景和轉換策略，開發者可以在 LLM 系統的全生命週期中做出最優的技術決策，從而構建高效、安全、可擴展的大模型應用系統。建議在實際專案中建立格式選擇的標準化流程，結合自動化工具鏈實現最佳的工程實踐。

---
