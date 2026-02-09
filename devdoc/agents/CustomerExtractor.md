# CustomerExtractor Agent

## 概述

CustomerExtractor 是客户信息提取 Agent，负责：
- 从邮件中自动提取客户和联系人信息
- 利用 EmailSummarizer 的分析结果（公司名、国家等）作为上下文
- 查重：匹配邮箱域名 + 公司名模糊匹配已有客户
- 创建 CustomerSuggestion 待审批记录
- 启动 Temporal 审批工作流

支持两种场景：
1. **新客户 + 新联系人**（`new_customer`）
2. **已有客户的新联系人**（`new_contact`）

## 基本信息

| 属性 | 值 |
|------|-----|
| name | customer_extractor |
| display_name | 客户信息提取器 |
| description | 从邮件中提取客户和联系人信息，创建待审批的客户建议 |
| prompt_name | customer_extractor |
| tools | 无 |
| max_iterations | 1 |

## 执行流程

```
输入（邮件内容 + EmailSummarizer 分析结果）
    ↓
[preprocess] 预处理
    ├─ 提取邮箱域名
    ├─ 检查是否跳过（免费邮箱 / 非客户类型）
    │      → 跳过 → [output] → END
    ├─ 查询已有客户列表（上下文）
    ├─ 查询 pending 建议列表（避免重复）
    └─ 渲染 Prompt
    ↓
[think] 调用 LLM 分析
    ↓
[output] 解析 JSON 结果
    ↓
[后处理] run() 覆盖
    ├─ 如果 is_new_customer → 创建 CustomerSuggestion（new_customer）
    ├─ 如果 matched_existing_customer → 创建 CustomerSuggestion（new_contact）
    └─ 启动 Temporal 审批工作流
    ↓
返回结构化结果
```

## 输入格式

通过 `input_data` 传递邮件信息：

```python
{
    "email_id": "邮件 ID",
    "sender": "发件人邮箱",
    "sender_name": "发件人显示名",
    "subject": "邮件主题",
    "content": "已清洗的邮件内容",
    "email_analysis": {  # EmailSummarizer 分析结果（可选，用于复用）
        "sender_company": "ABC Company",
        "sender_country": "USA",
        "sender_type": "customer",
        "is_new_contact": True,
        "intent": "inquiry",
        "products": [{"name": "..."}],
    },
    "_session": AsyncSession,  # 数据库会话（可选）
    "org_id": "组织 ID",
}
```

## 输出格式

```json
{
    "is_new_customer": true,
    "matched_existing_customer": null,
    "confidence": 0.85,
    "reasoning": "该域名和公司名在现有客户库中无匹配记录",
    "sender_type": "customer",
    "company": {
        "name": "ABC International Trading Co.",
        "short_name": "ABC",
        "country": "USA",
        "region": "North America",
        "industry": "Electronics",
        "website": "https://abc-intl.com"
    },
    "contact": {
        "name": "John Doe",
        "email": "john@abc-intl.com",
        "title": "Procurement Manager",
        "phone": "+1-555-0123",
        "department": "Purchasing"
    },
    "suggested_tags": ["electronics", "north-america"],
    "email_id": "xxx",
    "email_domain": "abc-intl.com",
    "llm_model": "claude-sonnet-4-20250514",
    "suggestion_id": "uuid-xxx"
}
```

## 跳过提取的场景

预处理节点会检查以下条件，符合时直接跳过 LLM 调用：

| 条件 | 说明 |
|------|------|
| 免费邮箱域名 | gmail.com、yahoo.com、qq.com 等（共 19 个域名） |
| 非客户类型 | sender_type 不是 customer / other / null |

跳过时返回：

```json
{
    "email_id": "xxx",
    "skip_extraction": true,
    "skip_reason": "免费邮箱域名: gmail.com",
    "is_new_customer": false
}
```

## 核心方法

### analyze()

```python
async def analyze(
    self,
    email_id: str,
    sender: str,
    sender_name: Optional[str],
    subject: str,
    content: str,
    email_analysis: Optional[dict] = None,
    session: Optional[AsyncSession] = None,
) -> dict:
    """提取客户信息（便捷方法）"""
```

### create_suggestion_if_needed()

```python
async def create_suggestion_if_needed(
    self,
    result: dict,
    email_id: str,
    trigger_content: str,
    session: Optional[AsyncSession] = None,
    org_id: str = None,
) -> Optional[str]:
    """如果分析结果需要创建客户建议，创建 CustomerSuggestion + Temporal 审批流"""
```

## 查重机制

创建建议前会进行去重：
1. 查询同邮箱域名是否已有 `pending` 状态的建议
2. 如果有，跳过创建（返回 `None`）
3. Prompt 上下文中包含已有客户列表和待审批建议列表，辅助 LLM 判断

## Prompt 配置

| Prompt Key | 用途 | 文件 |
|------------|------|------|
| `customer_extractor_system` | 系统提示 | `backend/app/llm/prompts/defaults.py` |
| `customer_extractor` | 用户提示模板 | `backend/app/llm/prompts/defaults.py` |

用户提示模板支持以下变量：
- `{{sender}}` - 发件人邮箱
- `{{sender_name}}` - 发件人显示名
- `{{subject}}` - 邮件主题
- `{{content}}` - 邮件内容（截取前 5000 字符）
- `{{email_analysis_context}}` - EmailSummarizer 分析结果上下文
- `{{existing_customers}}` - 已有客户列表
- `{{pending_suggestions}}` - 待审批建议列表

## 相关文件

- Agent: `backend/app/agents/customer_extractor.py`
- 客户建议模型: `backend/app/models/customer_suggestion.py`
- Prompt 默认值: `backend/app/llm/prompts/defaults.py`
- Dispatcher 集成: `backend/app/messaging/dispatcher.py`
- Temporal 审批流: `backend/app/temporal/`

## 使用示例

```python
from app.agents.customer_extractor import customer_extractor

result = await customer_extractor.analyze(
    email_id="123",
    sender="john@abc-intl.com",
    sender_name="John Doe",
    subject="Inquiry about LED products",
    content="Dear Sir, I'm interested in your LED products...",
    email_analysis={
        "sender_company": "ABC International",
        "sender_country": "USA",
        "sender_type": "customer",
        "is_new_contact": True,
    },
    session=db_session,
)

if result.get("is_new_customer"):
    print(f"新客户: {result['company']['name']}")
    print(f"建议 ID: {result.get('suggestion_id')}")
elif result.get("skip_extraction"):
    print(f"跳过: {result['skip_reason']}")
```
