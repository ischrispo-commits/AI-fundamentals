# 12-Factor Agents - 構建可靠 LLM 應用的原則

> 專案地址：<https://github.com/humanlayer/12-factor-agents/>

## 問題/需求：為什麼我們需要新的方法論？

在當前的 AI 應用開發中，我們面臨著一個普遍的問題：**大多數標榜為"AI 智能體"的產品實際上並沒有那麼智慧**。根據 Dex 的研究和與 100 多位 SaaS 構建者的交流，發現了以下典型問題：

1. **品質瓶頸**：使用現有框架可以快速達到 70-80% 的品質標準，但要超過 80% 往往需要逆向工程整個框架
2. **框架限制**：現有框架的黑盒特性限制了開發者對提示詞、控制流和上下文的精細控制
3. **生產就緒性**：大多數框架無法直接滿足生產環境的嚴格要求
4. **維護困難**：隨著需求變化，框架的抽象層反而成為阻礙

正如 Dex 所說："**我看到構建者讓客戶用上高品質 AI 軟體的最快方式是，從智能體構建中獲取小型、模組化的概念，並將它們整合到他們現有的產品中**"。

## Why 12-Factor Agents：為什麼是 12 要素方法論？

12-Factor Agents 借鑑了著名的 [12 Factor Apps](https://12factor.net/) 方法論，為構建可靠的 LLM 應用提供了一套經過驗證的原則。這套方法論的核心理念是：

> **將智能體視為由確定性程式碼和 LLM 步驟組成的軟體系統，而非黑盒框架**

### 核心優勢

1. **漸進式採用**：可以逐步引入，不需要重寫整個系統
2. **完全控制**：開發者擁有對提示詞、上下文、控制流的完全控制權
3. **生產就緒**：每個要素都考慮了生產環境的實際需求
4. **技術棧無關**：適用於任何程式語言或框架
5. **可測試性**：每個要素都可以獨立測試和驗證

## What 12-Factor Agents：12 個要素詳解

以下是基於官方文件的 12 個要素的詳細中文介紹，每個要素都包含核心思想、實現細節、最佳實踐和實際應用場景。

### 要素 1：自然語言到工具呼叫 (Natural Language to Tool Calls)

**📁 詳細文件**：[要素 1：自然語言到工具呼叫](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-01-natural-language-to-tool-calls.md)

**視覺化示例**：

![自然語言到工具呼叫](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/110-natural-language-tool-calls.png)

**核心思想**：將使用者的自然語言輸入原子化地轉換為結構化的工具呼叫，這是構建智能體的最基礎模式。

**深入解析**：

這個要素解決的是智能體如何理解使用者意圖並轉化為可執行操作的問題。關鍵在於"原子化"轉換 - 不是試圖理解整個複雜工作流，而是將單個自然語言指令精確對映到具體的 API 呼叫。

**實際案例**：

考慮一個真實的付款連結建立場景：

```text
使用者輸入："為 Jeff 建立 750 美元的付款連結，用於贊助二月的 AI 技術聚會"
↓
結構化輸出：
{
  "function": "create_payment_link",
  "parameters": {
    "amount": 75000,  // 以分為單位
    "currency": "usd",
    "customer_email": "jeff@example.com",
    "description": "二月 AI 技術聚會贊助費用",
    "metadata": {
      "event_type": "sponsorship",
      "month": "february",
      "purpose": "ai_meetup"
    }
  }
}
```

**實現模式**：

```python
# 使用 LLM 進行意圖識別和參數提取
async def determine_next_step(natural_language_input: str) -> ToolCall:
    response = await llm.create_completion(
        prompt=f"""
        將以下使用者請求轉換為結構化的工具呼叫：
        使用者說：{natural_language_input}

        可用的工具：create_payment_link, list_customers, list_products

        請輸出 JSON 格式的工具呼叫。
        """,
        response_format=ToolCall
    )
    return response

# 處理工具呼叫
async def handle_tool_call(tool_call: ToolCall):
    if tool_call.function == 'create_payment_link':
        return await stripe.payment_links.create(**tool_call.parameters)
    elif tool_call.function == 'list_customers':
        return await stripe.customers.list(**tool_call.parameters)
    # ... 其他工具處理
```

**最佳實踐**：

1. **保持原子性**：每個工具呼叫應該只執行一個具體操作
2. **明確參數**：為每個參數提供清晰的類型定義和驗證
3. **錯誤處理**：當模型無法匹配到合適工具時，提供優雅的降級方案
4. **上下文增強**：在實際呼叫前，可能需要額外的資訊收集步驟

### 要素 2：擁有自己的提示詞 (Own Your Prompts)

**📁 詳細文件**：[要素 2：擁有自己的提示詞](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-02-own-your-prompts.md)

**視覺化示例**：

![擁有自己的提示詞](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/120-own-your-prompts.png)

**核心思想**：提示詞是程式碼的一部分，應該像程式碼一樣被版本控制、測試和迭代最佳化，而不是依賴框架的黑盒提示詞。

**深入解析**：

許多框架提供"黑盒"提示詞方法，如 `Agent(role="...", goal="...")`，這在初期很方便，但會限制我們對系統的精細控制。擁有自己的提示詞意味著我們可以：

- 精確控制每個 token 的使用
- 進行 A/B 測試比較不同提示詞效果
- 針對特定用例最佳化提示詞
- 避免框架升級導致的意外行為變化

**實際對比**：

**❌ 黑盒方式**：

```python
# 框架提供的黑盒方法
agent = Agent(
    role="部署助手",
    goal="安全地部署應用到生產環境",
    personality="謹慎且專業",
    tools=[deploy_backend, deploy_frontend]
)
result = agent.run("部署最新後端到生產環境")
```

**✅ 自有提示詞方式**：

```rust
function DetermineNextStep(thread: string) ->
    DoneForNow | ListGitTags | DeployBackend | DeployFrontend | RequestMoreInformation {
  prompt #"
    {{ _.role("system") }}

    你是一個專業的部署助手，負責管理前端和後端系統的部署。
    你遵循最佳實踐，確保部署的安全性和成功率。

    部署前的檢查清單：
    - 確認部署環境（staging vs production）
    - 驗證部署標籤/版本是否正確
    - 檢查當前系統狀態
    - 高風險部署需要人工審批

    可用工具：deploy_backend, deploy_frontend, check_deployment_status
    敏感操作使用 request_approval 獲取人工驗證。

    思考步驟：
    1. 先檢查當前部署狀態
    2. 驗證部署標籤是否存在
    3. 如需要則請求審批
    4. 先部署到 staging 測試
    5. 監控部署進度

    {{ _.role("user") }}
    {{ thread }}

    下一步應該做什麼？
  "#
}
```

**提示詞工程最佳實踐**：

1. **版本控制**：將提示詞儲存在單獨的`.prompt`文件中
2. **模板化**：使用 Jinja2 或類似模板引擎管理動態內容
3. **測試覆蓋**：為提示詞編寫單元測試和整合測試
4. **效能監控**：追蹤不同提示詞的 token 使用情況和響應品質
5. **角色分離**：為不同任務類型建立專門的提示詞模板

### 要素 3：擁有自己的上下文視窗 (Own Your Context Window)

**📁 詳細文件**：[要素 3：擁有自己的上下文視窗](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-03-own-your-context-window.md)

**視覺化示例**：

![擁有自己的上下文視窗](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/130-own-your-context-building.png)

**核心思想**：完全控制如何構建和格式化傳遞給 LLM 的上下文，突破標準訊息格式的限制，最大化 token 效率和模型理解能力。

**深入解析**：

傳統的 LLM 互動使用標準的訊息格式（system/user/assistant/tool），但這可能不是最優的資訊傳遞方式。透過自定義上下文格式，我們可以：

- 最佳化資訊密度，減少不必要的 token
- 以模型最理解的格式呈現資訊
- 靈活控制哪些資訊保留、哪些資訊隱藏
- 實現更復雜的上下文管理策略

**標準格式 vs 自定義格式對比**：

**標準訊息格式**（低效）：

```yaml
[
  { "role": "system", "content": "你是一個部署助手..." },
  { "role": "user", "content": "能否部署后端？" },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [{ "name": "list_git_tags", "arguments": {} }]
  },
  {
    "role": "tool",
    "name": "list_git_tags",
    "content": '{"tags": [...長 JSON...]}'
  }
]
```

**自定義XML格式**（高效）：

```xml
<slack_message>
  來自：@alex
  頻道：#deployments
  內容：能否部署最新後端到生產環境？
</slack_message>

<list_git_tags>
  意圖：列出git標籤
</list_git_tags>

<list_git_tags_result>
標籤：
  - v1.2.3 (最新，2024-03-15)
  - v1.2.2 (穩定版，2024-03-14)
  - v1.2.1 (舊版本，2024-03-13)
</list_git_tags_result>

下一步應該做什麼？
```

**上下文工程實現**：

```python
class Thread:
    events: List[Event]

class Event:
    type: Literal["slack_message", "tool_call", "tool_result", "human_input", "error"]
    data: Union[str, ToolCall, ToolResult, HumanInput, ErrorInfo]

def event_to_prompt(event: Event) -> str:
    """將事件轉換為最佳化的提示詞格式"""
    if isinstance(event.data, str):
        return f"<{event.type}>\n{event.data}\n</{event.type}>"
    else:
        # 使用YAML格式提高可讀性
        yaml_data = yaml.dump(event.data, default_flow_style=False)
        return f"<{event.type}>\n{yaml_data}\n</{event.type}>"

def thread_to_prompt(thread: Thread) -> str:
    """將執行緒轉換為完整的提示詞"""
    return '\n\n'.join(event_to_prompt(event) for event in thread.events)
```

**高階上下文管理策略**：

1. **資訊壓縮**：對於長文字，使用摘要或關鍵資訊提取
2. **選擇性遺忘**：移除已解決錯誤的詳細資訊
3. **上下文分層**：將資訊按重要性分層，確保關鍵資訊始終保留
4. **token預算管理**：動態調整上下文長度以適應模型限制

### 要素 4：工具只是結構化輸出 (Tools Are Structured Outputs)

**📁 詳細文件**：[要素 4：工具只是結構化輸出](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-04-tools-are-structured-outputs.md)

**視覺化示例**：

![工具只是結構化輸出](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/140-tools-are-just-structured-outputs.png)

**核心思想**：工具呼叫本質上是 LLM 的結構化 JSON 輸出，不需要複雜的抽象層。透過簡單的資料類定義，就能實現強大的工具呼叫功能。

**深入解析**：

這個要素強調工具呼叫的簡潔性。我們不需要複雜的框架來處理工具呼叫，只需要：

1. 定義清晰的資料結構（Pydantic 模型、TypeScript 接口等）
2. LLM 輸出符合該結構的 JSON
3. 用簡單的 switch 語句處理不同的工具類型

**實現模式**：

```python
from typing import Literal
from pydantic import BaseModel

# 工具定義 - 簡單而清晰
class Issue(BaseModel):
    title: str
    description: str
    team_id: str
    assignee_id: str

class CreateIssue(BaseModel):
    intent: Literal["create_issue"]
    issue: Issue

class SearchIssues(BaseModel):
    intent: Literal["search_issues"]
    query: str
    what_youre_looking_for: str

# 統一的工具響應類型
ToolCall = CreateIssue | SearchIssues

# 工具處理 - 簡潔的switch模式
async def handle_tool_call(tool_call: ToolCall) -> dict:
    if tool_call.intent == "create_issue":
        return await linear_client.create_issue(tool_call.issue.dict())
    elif tool_call.intent == "search_issues":
        return await linear_client.search_issues(
            query=tool_call.query,
            description=tool_call.what_youre_looking_for
        )
```

**高階技巧**：

1. **工具組合**：透過組合簡單工具實現複雜功能
2. **工具驗證**：在 LLM 輸出後立即驗證參數
3. **工具回退**：當工具呼叫失敗時提供備用方案
4. **工具文件**：為每個工具提供清晰的描述和使用示例

### 要素 5：統一執行狀態和業務狀態 (Unify Execution State)

**📁 詳細文件**：[要素 5：統一執行狀態和業務狀態](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-05-unify-execution-state.md)

**視覺化示例**：

![統一執行狀態](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/150-unify-state.png)

**核心思想**：將執行狀態（當前步驟、等待狀態、重試計數等）和業務狀態（工具呼叫結果、對話歷史等）統一儲存在上下文視窗中，避免複雜的狀態分離。

**深入解析**：

傳統系統常常將執行狀態和業務狀態分開管理，但這會帶來複雜性。12-Factor Agents 方法論建議將兩者統一：

- **執行狀態**：只是業務狀態的後設資料
- **業務狀態**：包含所有必要的資訊來恢復執行
- **單一真相源**：整個狀態可以序列化為一個可恢復的 "執行緒"

**統一狀態的優勢**：

1. **簡化架構**：不需要複雜的狀態管理系統
2. **輕鬆序列化**：整個狀態可以序列化為 JSON
3. **斷點續傳**：可以從任何狀態點恢復執行
4. **除錯友好**：所有狀態都在一個地方，便於除錯
5. **分叉能力**：可以複製狀態建立新的執行分支

**實現示例**：

```python
class Thread:
    """統一的狀態容器"""
    events: List[Event]           # 業務狀態：所有发生的事情
    current_step: Optional[str]   # 執行狀態：從事件中推斷

    def get_execution_state(self) -> dict:
        """從業務狀態推斷執行狀態"""
        last_event = self.events[-1] if self.events else None
        return {
            "current_step": last_event.type if last_event else None,
            "waiting_for": self._infer_waiting_for(),
            "retry_count": self._count_retries()
        }

    def serialize(self) -> str:
        """序列化整個狀態用於儲存"""
        return json.dumps({
            "events": [e.dict() for e in self.events],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            }
        })
```

### 要素 6：使用簡單 API 啟動/暫停/恢復 (Launch/Pause/Resume)

**📁 詳細文件**：[要素 6：使用簡單 API 啟動/暫停/恢復](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-06-launch-pause-resume.md)

**視覺化示例**：

![簡單API啟動暫停恢復](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/160-pause-resume-with-simple-apis.png)

**核心思想**：智能體應該像普通程式一樣，支援標準的生命週期管理 API，包括啟動、查詢狀態、暫停、恢復和停止。

**深入解析**：

這個要素解決的是智能體的工程化問題。在生產環境中，我們需要：

- **簡單啟動**：透過 API 呼叫啟動智能體
- **暫停等待**：在需要人類輸入或長時間操作時暫停
- **外部觸發**：透過 webhooks 或其他事件恢復執行
- **狀態查詢**：隨時檢查智能體的執行狀態

**生命周期管理 API 設計**：

```python
class AgentAPI:
    async def launch(self, initial_input: str) -> str:
        """啟動新的智能體執行"""
        thread = Thread(initial_message=initial_input)
        thread_id = await self.store.save(thread)
        await self._process_next_step(thread_id)
        return thread_id

    async def pause(self, thread_id: str, reason: str):
        """暫停執行，等待外部輸入"""
        thread = await self.store.load(thread_id)
        thread.events.append(PauseEvent(reason=reason))
        await self.store.save(thread)

    async def resume(self, thread_id: str, external_input: dict):
        """透過外部輸入恢復執行"""
        thread = await self.store.load(thread_id)
        thread.events.append(ResumeEvent(data=external_input))
        await self._process_next_step(thread_id)

    async def get_status(self, thread_id: str) -> dict:
        """查詢當前執行狀態"""
        thread = await self.store.load(thread_id)
        return {
            "status": thread.get_status(),
            "last_activity": thread.last_activity,
            "waiting_for": thread.waiting_for
        }
```

**實際應用場景**：

1. **人工審批流程**：在關鍵操作前暫停，等待人工確認
2. **長時間任務**：處理可能需要幾分鐘或幾小時的任務
3. **外部依賴**：等待第三方系統響應或 webhook 回撥
4. **使用者互動**：在 Slack、郵件等渠道中與使用者互動

### 要素 7：透過工具呼叫聯絡人類 (Contact Humans With Tools)

**📁 詳細文件**：[要素 7：透過工具呼叫聯絡人類](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-07-contact-humans-with-tools.md)

**視覺化示例**：

![透過工具與人類聯絡](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/170-contact-humans-with-tools.png)

**核心思想**：將人類互動視為一種特殊的工具呼叫，使智能體能夠以結構化方式請求人類輸入、審批或協助。

**深入解析**：

這個要素突破了傳統人機互動的模式。不是讓智能體直接輸出文字給人類，而是：

- **結構化請求**：定義清晰的請求格式
- **多渠道支持**：支持 Slack、郵件、簡訊等多種渠道
- **非同步處理**：人類可以在任何時間響應
- **狀態追蹤**：記錄人類響應並繼續執行流程

**人類互動工具定義**：

```python
class RequestHumanInput(BaseModel):
    intent: Literal["request_human_input"]
    question: str
    context: str
    options: Options
    urgency: Literal["low", "medium", "high"]

class Options(BaseModel):
    format: Literal["free_text", "yes_no", "multiple_choice"]
    choices: List[str] = []
    timeout_hours: int = 24

# 使用示例
async def handle_human_request(request: RequestHumanInput):
    # 格式化消息
    message = format_human_message(request)

    # 透過多渠道傳送
    await send_to_slack(
        channel="#deployments",
        message=message,
        thread_ts=get_thread_id()
    )

    # 記錄等待狀態
    await save_waiting_state(
        waiting_for="human_response",
        request_id=generate_request_id()
    )
```

**實際應用示例**：

```xml
<!-- 上下文中的完整交互流程 -->
<slack_message>
  來自：@alex
  頻道：#deployments
  內容：能否部署后端 v1.2.3 到生產環境？
</slack_message>

<request_human_input>
  意圖：請求人工確認
  問題：是否確認部署 v1.2.3 到生產環境？
  上下文：這是生產環境部署，將影響線上使用者
  緊急程度：high
  選項：
    - 格式：yes_no
    - 超時：30分钟
</request_human_input>

<human_response>
  響應："是的，請繼續"
  已批准：true
  使用者：alex@company.com
  時間：2024-03-15T10:30:00Z
</human_response>

<deploy_backend>
  意圖：部署后端
  標籤：v1.2.3
  環境：production
</deploy_backend>
```

### 要素 8：擁有自己的控制流 (Own Your Control Flow)

**📁 詳細文件**：[要素 8：擁有自己的控制流](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-08-own-your-control-flow.md)

**視覺化示例**：

![擁有自己的控制流](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/180-control-flow.png)

**核心思想**：不要依賴框架的"魔法"控制流，而是顯式地設計和實現自己的控制邏輯，包括迴圈、條件判斷、重試機制等。

**深入解析**：

這個要素讓我們能夠：

- **自定義中斷點**：決定在哪些步驟暫停等待外部輸入
- **靈活的重試邏輯**：針對不同類型的失敗實施不同的重試策略
- **結果彙總**：在繼續執行前彙總和分析多個工具呼叫的結果
- **記憶體管理**：實現智慧的上下文視窗壓縮和清理

**控制流模式示例**：

```python
async def handle_next_step(thread: Thread) -> None:
    """自定義控制流處理"""

    while True:
        next_step = await determine_next_step(thread_to_prompt(thread))

        # 模式1：需要人工澄清 - 中斷並等待
        if next_step.intent == 'request_clarification':
            await handle_clarification_request(thread, next_step)
            break  # 等待人工響應

        # 模式2：簡單查詢 - 同步執行並繼續
        elif next_step.intent == 'fetch_git_tags':
            result = await git_client.list_tags()
            thread.add_event('git_tags', result)
            continue  # 直接繼續下一步

        # 模式3：高風險操作 - 需要審批
        elif next_step.intent == 'deploy_production':
            await request_approval(thread, next_step)
            break  # 等待審批

        # 模式4：批次處理 - 彙總多個結果
        elif next_step.intent == 'batch_process':
            results = await execute_batch(next_step.items)
            summary = await llm_summarize(results)
            thread.add_event('batch_summary', summary)
            continue
```

**高階控制流功能**：

1. **工具呼叫審批**：在工具執行前插入審批步驟
2. **結果驗證**：用 LLM 驗證工具輸出是否符合預期
3. **錯誤恢復**：實現智慧的錯誤處理和恢復策略
4. **效能監控**：記錄每個步驟的執行時間和成功率

### 要素 9：將錯誤壓縮到上下文視窗中 (Compact Errors)

**📁 詳細文件**：[要素 9：將錯誤壓縮到上下文視窗中](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-09-compact-errors.md)

**視覺化示例**：

![壓縮錯誤到上下文視窗](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/190-factor-9-errors-static.png)

**核心思想**：將錯誤資訊以緊湊、結構化的格式傳遞給 LLM，使智能體能夠自我修復，同時避免錯誤迴圈。

**深入解析**：

這個要素實現了智能體的"自愈"能力。關鍵在於：

- **結構化錯誤**：將錯誤轉換為 LLM 能理解的格式
- **緊湊表示**：避免冗長的堆疊跟蹤汙染上下文
- **重試限制**：防止無限重試導致的資源浪費
- **升級機制**：在重試失敗後升級到人工處理

**錯誤處理模式**：

```python
class CompactError(BaseModel):
    type: Literal["api_error", "validation_error", "timeout", "unknown"]
    tool: str
    message: str
    retryable: bool
    suggestion: Optional[str] = None

class ErrorHandler:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.consecutive_errors = defaultdict(int)

    async def handle_error(
        self,
        error: Exception,
        tool_name: str,
        thread: Thread
    ) -> str:
        """處理錯誤並決定下一步"""

        # 轉換為緊湊錯誤格式
        compact_error = self._create_compact_error(error, tool_name)

        # 記錄錯誤到上下文
        thread.add_event('error', compact_error.dict())

        # 檢查重試次數
        self.consecutive_errors[tool_name] += 1

        if (compact_error.retryable and
            self.consecutive_errors[tool_name] < self.max_retries):
            return "retry"
        elif self.consecutive_errors[tool_name] >= self.max_retries:
            return "escalate_to_human"
        else:
            return "skip_tool"

    def _create_compact_error(self, error: Exception, tool: str) -> CompactError:
        """將異常轉換為緊湊錯誤格式"""
        if isinstance(error, APIError):
            return CompactError(
                type="api_error",
                tool=tool,
                message=str(error),
                retryable=error.status_code >= 500,
                suggestion="檢查 API 金鑰和網路連線"
            )
        elif isinstance(error, ValidationError):
            return CompactError(
                type="validation_error",
                tool=tool,
                message=str(error),
                retryable=False,
                suggestion="檢查輸入參數格式"
            )
        # ... 其他錯誤類型
```

**實際應用示例**：

```python
async def execute_with_recovery(thread: Thread, tool_call: ToolCall):
    """執行工具呼叫並處理錯誤"""

    try:
        result = await execute_tool(tool_call)
        thread.add_event('success', result)
        return result

    except Exception as e:
        handler = ErrorHandler()
        action = await handler.handle_error(e, tool_call.intent, thread)

        if action == "retry":
            # LLM會看到錯誤資訊並決定如何調整
            return await execute_with_recovery(thread, tool_call)
        elif action == "escalate_to_human":
            await request_human_help(thread, e)
            return None
        else:
            # 跳過這個工具，繼續執行
            thread.add_event('skipped', {"tool": tool_call.intent})
            return None
```

### 要素 10：小型、專注的智能體 (Small, Focused Agents)

**📁 詳細文件**：[要素 10：小型、專注的智能體](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-10-small-focused-agents.md)

**視覺化示例**：

![小型專注的智能體](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/1a0-small-focused-agents.png)

**核心思想**：構建專注於特定任務的小型智能體（3-10 個步驟），而不是試圖處理所有事情的大型智能體，以保持上下文窗口的可管理性和 LLM 性能。

**深入解析**：

這個要素基於 LLM 的固有限制：隨著上下文增長，LLM 更容易迷失或失去焦點。透過限制智能體的範圍，我們可以：

- **保持高性能**：小上下文窗口意味着更好的 LLM 理解
- **明確邊界**：每個智能體有清晰的職責範圍
- **可組合性**：透過組合多個小智能體構建複雜工作流
- **易於測試**：小範圍更容易測試和驗證

**智能體規模指導原則**：

| 智能體類型 | 步驟範圍 | 示例場景                   |
| ---------- | -------- | -------------------------- |
| 原子操作   | 1-3步    | 建立付款連結、查詢使用者資訊 |
| 簡單工作流 | 3-10步   | 處理客戶退款、部署單個服務 |
| 複雜工作流 | 10-20步  | 完整的发布流程、多系統協調 |

**智能體組合模式**：

```python
class SmallAgent:
    """小型專注智能體基類"""

    def __init__(self, name: str, max_steps: int = 10):
        self.name = name
        self.max_steps = max_steps

    async def execute(self, input_data: dict) -> dict:
        """執行智能體任務"""
        thread = Thread()
        thread.add_event('start', input_data)

        for step in range(self.max_steps):
            next_action = await self.determine_next_step(thread)

            if next_action.intent == 'complete':
                return self.format_result(thread)

            result = await self.execute_action(next_action)
            thread.add_event('step_result', result)

        # 如果達到步驟限制，升級到更大的智能體
        return await self.escalate_to_larger_agent(thread)

# 實際使用：組合多個小智能體
class DeploymentOrchestrator:
    """透過組合小智能體實現複雜部署"""

    def __init__(self):
        self.agents = {
            'code_check': CodeCheckAgent(),
            'build': BuildAgent(),
            'test': TestAgent(),
            'deploy': DeployAgent()
        }

    async def deploy_application(self, config: dict):
        """協調多個小智能體完成部署"""

        # 1. 程式碼檢查
        check_result = await self.agents['code_check'].execute(config)
        if not check_result['success']:
            return check_result

        # 2. 構建
        build_result = await self.agents['build'].execute(check_result)
        if not build_result['success']:
            return build_result

        # 3. 測試
        test_result = await self.agents['test'].execute(build_result)
        if not test_result['success']:
            return test_result

        # 4. 部署
        return await self.agents['deploy'].execute(test_result)
```

**智能體演進策略**：

1. **從小開始**：先構建最小可行智能體
2. **逐步擴展**：隨著 LLM 能力提升慢慢擴大範圍
3. **品質監控**：始終監控效能指標，確保品質不下降
4. **分解重構**：當智能體變得過於複雜時，考慮分解為更小單元

### 要素 11：從任何地方觸發 (Trigger From Anywhere)

**📁 詳細文件**：[要素 11：從任何地方觸發](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)

**視覺化示例**：

![從任何地方觸發](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/1b0-trigger-from-anywhere.png)

**核心思想**：支援從任何渠道觸發智能體（Slack、郵件、短信、Webhook、定時任務等），並讓智能體能夠在相同渠道響應使用者。

**深入解析**：

這個要素解決了智能體的可用性問題。使用者不應該需要學習新的介面或工作流，智能體應該融入現有的工作環境：

- **多渠道觸發**：支援使用者習慣的溝通方式
- **上下文保持**：在不同渠道間保持對話上下文
- **響應一致性**：無論透過哪個渠道觸發，響應品質一致
- **許可權管理**：不同渠道可能有不同的許可權要求

**渠道介面卡模式**：

```python
class ChannelAdapter:
    """渠道介面卡基類"""

    async def receive_message(self, raw_message: dict) -> dict:
        """將原始訊息轉換為標準格式"""
        raise NotImplementedError

    async def send_response(self, response: dict, context: dict):
        """將響應傳送到對應渠道"""
        raise NotImplementedError

class SlackAdapter(ChannelAdapter):
    """Slack渠道介面卡"""

    async def receive_message(self, slack_event: dict) -> dict:
        return {
            "user": slack_event["user"],
            "text": slack_event["text"],
            "channel": slack_event["channel"],
            "timestamp": slack_event["ts"],
            "thread_ts": slack_event.get("thread_ts")
        }

    async def send_response(self, response: dict, context: dict):
        await slack_client.chat_postMessage(
            channel=context["channel"],
            text=response["text"],
            thread_ts=context.get("thread_ts")
        )

class EmailAdapter(ChannelAdapter):
    """郵件渠道介面卡"""

    async def receive_message(self, email_data: dict) -> dict:
        return {
            "user": email_data["from"],
            "text": email_data["body"],
            "subject": email_data["subject"],
            "message_id": email_data["message_id"]
        }

    async def send_response(self, response: dict, context: dict):
        await email_client.send_mail(
            to=context["user"],
            subject=f"Re: {context['subject']}",
            body=response["text"]
        )
```

**統一觸發器實現**：

```python
class UniversalTrigger:
    """統一觸發器管理"""

    def __init__(self):
        self.adapters = {
            'slack': SlackAdapter(),
            'email': EmailAdapter(),
            'webhook': WebhookAdapter(),
            'cron': CronAdapter()
        }

    async def handle_incoming(self, channel: str, raw_data: dict):
        """處理來自任何渠道的請求"""

        # 1. 使用對應介面卡轉換訊息
        adapter = self.adapters[channel]
        message = await adapter.receive_message(raw_data)

        # 2. 建立或恢復執行緒
        thread = await self.get_or_create_thread(
            user=message["user"],
            channel=channel
        )

        # 3. 執行智能體邏輯
        response = await self.agent.execute({
            "message": message,
            "thread": thread
        })

        # 4. 透過相同渠道響應
        await adapter.send_response(response, message)

        # 5. 儲存執行緒狀態
        await self.save_thread(thread)
```

### 要素 12：讓智能體成為無狀態歸約器 (Stateless Reducer)

**📁 詳細文件**：[要素 12：讓智能體成為無狀態歸約器](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-12-stateless-reducer.md)

**視覺化示例**：

![無狀態歸約器](https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/img/1c0-stateless-reducer.png)

**核心思想**：將智能體設計為純函式（歸約器），輸入當前狀態和事件，輸出新狀態，實現函數語言程式設計的無副作用特性。

**深入解析**：

這個要素將智能體提升到函數語言程式設計的高度。透過將智能體視為純函式：

- **可預測性**：相同的輸入總是產生相同的輸出
- **可測試性**：易於單元測試和驗證
- **可組合性**：可以像樂高積木一樣組合多個歸約器
- **併發安全**：無狀態設計天然支援併發執行

**純函式智能體模式**：

```python
from typing import List, Callable, TypeVar
from functools import reduce

T = TypeVar('T')
E = TypeVar('E')

class AgentState(BaseModel):
    """智能體狀態"""
    events: List[dict]
    current_step: Optional[str] = None
    waiting_for: Optional[str] = None

class AgentEvent(BaseModel):
    """智能體事件"""
    type: str
    data: dict
    timestamp: datetime

class StatelessReducer:
    """無狀態歸約器實現"""

    @staticmethod
    def reducer(state: AgentState, event: AgentEvent) -> AgentState:
        """純函式歸約器"""

        # 建立新狀態（不修改原狀態）
        new_state = state.copy()
        new_state.events = state.events + [event.dict()]

        # 根據事件類型更新狀態
        if event.type == "tool_call":
            new_state.current_step = event.data["tool"]
            new_state.waiting_for = "tool_result"

        elif event.type == "tool_result":
            new_state.current_step = None
            new_state.waiting_for = None

        elif event.type == "human_request":
            new_state.current_step = "waiting_for_human"
            new_state.waiting_for = "human_response"

        elif event.type == "human_response":
            new_state.current_step = "processing"
            new_state.waiting_for = None

        return new_state

    @staticmethod
    def process_events(events: List[AgentEvent]) -> AgentState:
        """處理事件序列"""
        initial_state = AgentState(events=[])
        return reduce(StatelessReducer.reducer, events, initial_state)

# 使用示例
events = [
    AgentEvent(type="start", data={"input": "deploy backend"}),
    AgentEvent(type="tool_call", data={"tool": "check_git"}),
    AgentEvent(type="tool_result", data={"tags": ["v1.2.3"]}),
    AgentEvent(type="human_request", data={"question": "deploy v1.2.3?"}),
    AgentEvent(type="human_response", data={"approved": True}),
    AgentEvent(type="tool_call", data={"tool": "deploy"}),
    AgentEvent(type="tool_result", data={"status": "success"})
]

final_state = StatelessReducer.process_events(events)
```

**函式式組合**：

```python
class AgentComposer:
    """智能體組合器"""

    @staticmethod
    def compose(*reducers: Callable) -> Callable:
        """組合多個歸約器"""
        def combined_reducer(state, event):
            for reducer in reducers:
                state = reducer(state, event)
            return state
        return combined_reducer

    @staticmethod
    def with_logging(reducer: Callable) -> Callable:
        """新增日誌功能的裝飾器"""
        def logging_reducer(state, event):
            print(f"Processing {event.type} with data: {event.data}")
            new_state = reducer(state, event)
            print(f"New state: {new_state.current_step}")
            return new_state
        return logging_reducer

# 建立帶日誌的組合歸約器
logged_reducer = AgentComposer.with_logging(
    AgentComposer.compose(
        StatelessReducer.reducer,
        ValidationReducer.reducer,
        AuditReducer.reducer
    )
)
```

**無狀態智能體的優勢**：

1. **可重現性**：相同的輸入總是產生相同的結果
2. **時間旅行除錯**：可以回放任何歷史狀態
3. **併發安全**：多個實例可以安全並行執行
4. **快取友好**：純函式結果可以安全快取
5. **測試簡單**：不需要複雜的測試設定和清理

## 總結

12-Factor Agents 不是另一個框架，而是一套經過驗證的原則和方法論。它幫助開發者構建真正可靠、可維護的 LLM 應用，而不被框架的抽象所限制。正如方法論本身所強調的：**"最好的智能體是由確定性程式碼和恰到好處的 LLM 步驟組成的軟體系統"**。

透過採用這套方法論，開發者可以：

- 保持對系統的完全控制
- 逐步改進現有系統
- 構建真正生產就緒的 LLM 應用
- 避免常見的框架陷阱
