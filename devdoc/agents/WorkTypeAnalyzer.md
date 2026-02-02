# WorkTypeAnalyzer Agent

## 概述

WorkTypeAnalyzer 是工作类型分析 Agent，负责：
- 分析邮件内容判断工作类型
- 匹配现有工作类型
- 识别并建议新的工作类型
- 触发 Temporal 审批流程

## 基本信息

| 属性 | 值 |
|------|-----|
| name | work_type_analyzer |
| description | 分析邮件内容判断工作类型，匹配现有类型或建议新类型 |
| prompt_name | work_type_analyzer |
| tools | 无 |
| max_iterations | 3 |

## 执行流程

```
输入（邮件内容）
    ↓
获取系统工作类型列表
    ↓
构建 Prompt（包含类型列表 + 邮件内容）
    ↓
调用 LLM 分析
    ↓
解析 JSON 结果
    ├─ matched_work_type: 匹配的现有类型
    └─ new_suggestion: 是否建议新类型
          ↓
    (如果 should_suggest && confidence >= 0.6)
          ↓
    创建 WorkTypeSuggestion
          ↓
    启动 Temporal 审批工作流
```

## 输入格式

通过 `input_data` 传递邮件信息：

```python
{
    "email_id": "邮件 ID",
    "sender": "发件人邮箱",
    "subject": "邮件主题",
    "content": "已清洗的邮件内容",
    "received_at": datetime,  # 可选
}
```

## 输出格式

```json
{
    "matched_work_type": {
        "code": "ORDER_NEW",
        "confidence": 0.95,
        "reason": "邮件中包含新订单确认信息"
    },
    "new_suggestion": {
        "should_suggest": false,
        "suggested_code": null,
        "suggested_name": null,
        "suggested_description": null,
        "suggested_parent_code": null,
        "suggested_keywords": [],
        "confidence": 0,
        "reasoning": null
    },
    "email_id": "xxx",
    "llm_model": "claude-3-5-sonnet",
    "suggestion_id": null
}
```

## 置信度门槛

- 建议新类型的置信度门槛：`0.6`
- 低于此值的建议会被忽略

## 与 EmailSummarizer 的关系

两个 Agent 在 Dispatcher 中**并行执行**：

```python
# dispatcher.py
results = await asyncio.gather(
    agent_registry.run("email_summarizer", ...),
    agent_registry.run("work_type_analyzer", ...),
    return_exceptions=True,
)
```

## 核心方法

### analyze()

```python
async def analyze(
    self,
    email_id: str,
    sender: str,
    subject: str,
    content: str,
    received_at: Optional[datetime] = None,
    session: Optional[AsyncSession] = None,
) -> dict:
    """分析邮件的工作类型"""
```

### create_suggestion_if_needed()

```python
async def create_suggestion_if_needed(
    self,
    result: dict,
    email_id: str,
    trigger_content: str,
    session: Optional[AsyncSession] = None,
) -> Optional[str]:
    """如果分析结果建议新类型，创建 WorkTypeSuggestion 并启动审批流"""
```

## Prompt 模板

Agent 使用的 Prompt 会：
1. 列出所有当前启用的工作类型（层级结构）
2. 包含关键词信息供 LLM 参考
3. 要求 LLM 返回结构化 JSON

## 相关文件

- Agent: `backend/app/agents/work_type_analyzer.py`
- Dispatcher 集成: `backend/app/messaging/dispatcher.py`
- 审批流程: `backend/app/temporal/workflows/work_type_suggestion.py`

## 使用示例

```python
from app.agents.work_type_analyzer import work_type_analyzer

result = await work_type_analyzer.analyze(
    email_id="123",
    sender="customer@example.com",
    subject="New Order #12345",
    content="Please confirm our new order for 1000 units...",
)

if result.get("matched_work_type"):
    print(f"匹配类型: {result['matched_work_type']['code']}")

if result.get("new_suggestion", {}).get("should_suggest"):
    print(f"建议新类型: {result['new_suggestion']['suggested_code']}")
```
