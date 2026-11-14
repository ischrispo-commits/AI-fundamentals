# 解密 LLM 中的 Tokens

在大語言模型（LLM）中，“**tokens**”（令牌）是理解和生成語言的最小單位。無論是輸入文字的處理，還是模型輸出的生成，`tokens` 都在其中扮演核心角色。本文將詳細解析 `token` 的概念、如何估算其數量，並提供具體的 `Python` 示例，幫助開發者更好地理解和呼叫大語言模型。

## 什麼是 Token？

在 LLM 中，`token` 是模型處理的基本單元。Tokens 通常不是單個字母或字元，而是更具語義的單位（如單詞、子詞或字元），具體取決於分詞方法。例如：

- **單詞**：英文中的 "`dog`" 或 "`computer`"。
- **子詞**：透過分詞方法拆分的單位，如 "`un-`" 和 "`-able`"。
- **字符**：如 "`h`", "`e`", "`l`", "`l`", "`o`"。
- **標點符號**：句號“。”、逗號“，”等也會被視作獨立 `tokens`。

這些 `tokens` 被轉換為嵌入向量，供模型理解和生成文本。

## Tokens 如何影響模型的輸入和輸出

大多數 `LLM`（如 `GPT` 系列）透過 `token`s 對文字編碼。每個 `token` 對應一個嵌入向量，模型據此預測後續內容。`Token` 數量直接影響模型的效能、計算負載及呼叫成本。

例如，`GPT-3` 的最大上下文長度為 **2,048 tokens**，若輸入超出限制則需截斷或拆分。而當前主流模型的上下文視窗已普遍達到 **128K tokens**，部分長上下文模型甚至支援 **1M tokens**，但按 token 計費與截斷的邏輯並未改變。

## 如何估算 Tokens 數量

呼叫 `LLM API` 前估算 `token` 數量至關重要，以下是常用方法：

---

### 使用 `tiktoken` 估算（適用於 OpenAI GPT 模型）

`tiktoken` 是 `OpenAI` 官方庫，專為 `GPT` 系列設計。

**安裝**：

```bash
pip install tiktoken
```

**估算示例**：

```python
import tiktoken

encoder = tiktoken.get_encoding("cl100k_base")  # 指定 cl100k_base 的分詞器
text = "What is the capital of China?"
tokens = encoder.encode(text)

print(f"Token 數量: {len(tokens)}")  # 輸出: 7
```

---

### 使用 `transformers` 估算中文 Tokens（更靈活）

`transformers` 提供多語言支援，適合中文文字。

**安裝**：

```bash
pip install transformers
```

**估算示例**：

```python
from transformers import BertTokenizer

tokenizer = BertTokenizer.from_pretrained("bert-base-chinese")  # 載入中文分詞器
text = "《哪吒之魔童鬧海》於2025年1月29日上映，講述了哪吒在成長過程中，面對重重困難，不斷挑戰自我，最終逆天改命的故事。影片融合了精彩的特效和深刻的情感，展現了哪吒的勇敢與堅韌。"
tokens = tokenizer.encode(text, add_special_tokens=False)  # 去掉特殊字符

print(f"Token 數量: {len(tokens)}")  # 輸出: 84（實測值：漢字逐字切分，
# 但數字串如 "2025"、"29" 在詞表中整體成詞，故略少於全文 88 個字元；具體計數以實測為準）
```

---

### 使用 `tiktoken` 處理中文的注意事項

儘管 `tiktoken` 主要面向英文，其基於 BPE（位元組對編碼）的演算法也可處理中文，但可能產生更多子詞 `tokens`：

```python
import tiktoken

encoder = tiktoken.get_encoding("cl100k_base")
text = "《哪吒之魔童鬧海》於2025年1月29日上映，講述了哪吒在成長過程中，面對重重困難，不斷挑戰自我，最終逆天改命的故事。影片融合了精彩的特效和深刻的情感，展現了哪吒的勇敢與堅韌。"
tokens = encoder.encode(text)

print(f"Token 數量: {len(tokens)}")  # 輸出: 115
```

**結果差異說明**  
`tiktoken` 的 BPE 演算法會將中文拆分為更細粒度的子詞（如位元組級單字或常見組合），而 `transformers` 的 `BertTokenizer`（bert-base-chinese）對中文按單字切分、粒度最細，保留的完整詞最少（僅 ASCII 數字串等會按詞表合併，如 "2025" 整體成一個 token），因此兩者計數不同。

---

## 完整程式碼

### **Dockerfile**

```Dockerfile
# 使用官方 Python 3.9 映象
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製當前目錄下的所有檔案到容器的工作目錄
COPY token_estimation.py .

RUN mkdir -p /app/models

# 使用阿里雲映象源安裝依賴（確保 URL 是有效的）
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --upgrade pip && \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ tiktoken transformers hf_transfer

# 設定環境變數
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV HF_HOME="/app/models"
#ENV HF_ENDPOINT="https://mirroring.huggingface.co"
ENV HF_HUB_ENABLE_HF_TRANSFER=1

# 執行主程式
CMD ["python", "token_estimation.py"]
```

### **token_estimation.py**

```python
import tiktoken
from transformers import BertTokenizer
import argparse

def estimate_tokens_tiktoken(text, model="cl100k_base"):  # 修改模型名稱
    """
    使用 tiktoken 估算 Tokens 數量
    """
    try:
        encoder = tiktoken.get_encoding(model)
        tokens = encoder.encode(text)
        return len(tokens)
    except Exception as e:
        print(f"Error in tiktoken estimation: {e}")
        print(f"tiktoken version: {tiktoken.__version__}")
        return None

def estimate_tokens_transformers(text):
    """
    使用 transformers 估算中文 Tokens 數量
    """
    try:
        tokenizer = BertTokenizer.from_pretrained("bert-base-chinese")
        tokens = tokenizer.encode(text, add_special_tokens=False)  # 去掉特殊字符
        return len(tokens)
    except Exception as e:
        print(f"Error in transformers estimation: {e}")
        return None

def main():
    english_text = "What is the capital of China?"
    chinese_text = "《哪吒之魔童鬧海》於2025年1月29日上映，講述了哪吒在成長過程中，面對重重困難，不斷挑戰自我，最終逆天改命的故事。影片融合了精彩的特效和深刻的情感，展現了哪吒的勇敢與堅韌。"

    print("\n--- 英文 Tokens 估算 ---")
    print(f"輸入文字: {english_text}")
    tiktoken_eng = estimate_tokens_tiktoken(english_text)
    print(f"Tokens 數量（tiktoken）: {tiktoken_eng}")

    print("\n--- 中文 Tokens 估算 ---")
    print(f"輸入文字: {chinese_text}")
    transformers_chinese = estimate_tokens_transformers(chinese_text)
    print(f"Tokens 數量（transformers）: {transformers_chinese}")
    tiktoken_chinese = estimate_tokens_tiktoken(chinese_text)
    print(f"Tokens 數量（tiktoken）: {tiktoken_chinese}")

if __name__ == "__main__":
    main()
```

### 構建及執行

```bash
docker build --network=host -t token_estimation .

docker run --rm --network=host token_estimation
None of PyTorch, TensorFlow >= 2.0, or Flax have been found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.

--- 英文 Tokens 估算 ---
輸入文字: What is the capital of China?
Tokens 數量（tiktoken）: 7

--- 中文 Tokens 估算 ---
輸入文字: 《哪吒之魔童鬧海》於2025年1月29日上映，講述了哪吒在成長過程中，面對重重困難，不斷挑戰自我，最終逆天改命的故事。影片融合了精彩的特效和深刻的情感，展現了哪吒的勇敢與堅韌。
Tokens 數量（transformers）: 84
Tokens 數量（tiktoken）: 115
```

## 總結

- `Token` 是 `LLM` 處理文字的基本單位，直接影響計算資源和成本。
- **英文文本**：推薦使用 `tiktoken`，因其與 `GPT` 系列的分詞策略一致。
- **中文文本**：`transformers` 的分詞器更貼近詞語劃分，而 `tiktoken` 可能生成更多子詞 `tokens`。
- 理解不同工具的分詞邏輯，可幫助最佳化文字輸入，避免超出模型限制。

---
