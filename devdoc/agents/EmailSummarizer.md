# EmailSummarizer Agent

## 概述

EmailSummarizer 是邮件摘要分析 Agent，负责：
- 使用 LLM 分析邮件内容
- 提取摘要、意图、发件方信息
- 识别产品、金额、贸易条款等业务信息
- 针对外贸场景优化

## 基本信息

| 属性 | 值 |
|------|-----|
| name | email_summarizer |
| description | 邮件摘要分析，提取意图、产品、金额等业务信息 |
| prompt_name | email_summarizer |
| tools | clean_email |
| max_iterations | 3 |

## 执行流程

```
输入（邮件内容）
    ↓
调用 clean_email 工具清洗正文
    ↓
构建 Prompt（包含发件人、主题、正文）
    ↓
调用 LLM 分析
    ↓
解析 JSON 结果
    ↓
返回结构化分析结果
```

## 输入格式

通过 `input_data` 传递邮件信息：

```python
{
    "email_id": "邮件 ID",
    "sender": "发件人邮箱",
    "sender_name": "发件人名称",
    "subject": "邮件主题",
    "body_text": "邮件纯文本正文",
    "body_html": "邮件 HTML 正文（可选）",
    "received_at": datetime,
}
```

## 输出格式

```json
{
    "summary": "一句话总结（中文，不超过100字）",
    "key_points": ["关键要点1", "关键要点2"],
    "original_language": "en",
    "sender_type": "customer",
    "sender_company": "ABC Company",
    "sender_country": "USA",
    "is_new_contact": false,
    "intent": "order",
    "intent_confidence": 0.95,
    "urgency": "high",
    "sentiment": "positive",
    "products": [
        {
            "name": "产品名称",
            "specs": "规格描述",
            "quantity": 1000,
            "unit": "件",
            "target_price": 5.5
        }
    ],
    "amounts": [
        {
            "value": 5500,
            "currency": "USD",
            "context": "订单总金额"
        }
    ],
    "trade_terms": {
        "incoterm": "FOB",
        "payment_terms": "T/T 30%",
        "destination": "Los Angeles"
    },
    "deadline": "2024-03-15",
    "questions": ["交货期能提前吗？"],
    "action_required": ["确认订单", "发送 PI"],
    "suggested_reply": "建议确认订单细节并发送形式发票",
    "priority": "p1"
}
```

## 意图类型 (intent)

| 值 | 说明 |
|-----|------|
| inquiry | 询价/询盘 |
| quotation | 报价/还价 |
| order | 下单/订单确认 |
| order_change | 订单修改/取消 |
| payment | 付款/汇款通知 |
| shipment | 发货/物流跟踪 |
| sample | 样品请求 |
| complaint | 投诉/质量问题 |
| after_sales | 售后服务 |
| negotiation | 价格谈判 |
| follow_up | 跟进/催促 |
| introduction | 公司/产品介绍 |
| general | 一般沟通 |
| spam | 垃圾邮件/营销 |
| other | 其他 |

## 优先级 (priority)

| 值 | 说明 |
|-----|------|
| p0 | 立即处理 |
| p1 | 今日处理 |
| p2 | 本周处理 |
| p3 | 可延后 |

## 核心方法

### analyze()

```python
async def analyze(
    self,
    email_id: str,
    sender: str,
    sender_name: Optional[str],
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    received_at: Optional[datetime] = None,
) -> dict:
    """分析邮件，返回结构化结果"""
```

## 邮件清洗配置

```python
cleaned_content = await clean_email_content(
    body_text=body_text or "",
    body_html=body_html or "",
    max_length=10000,       # 增加到 10000 字符
    remove_signature=False,  # 保留签名
    remove_quotes=False,     # 保留引用历史
)
```

## 相关文件

- Agent: `backend/app/agents/email_summarizer.py`
- 清洗工具: `backend/app/tools/email_cleaner.py`
- Dispatcher 集成: `backend/app/messaging/dispatcher.py`

## 使用示例

```python
from app.agents.email_summarizer import email_summarizer

result = await email_summarizer.analyze(
    email_id="123",
    sender="customer@example.com",
    sender_name="John Doe",
    subject="RE: Order Inquiry",
    body_text="We would like to place an order for...",
    received_at=datetime.now(),
)

print(f"意图: {result['intent']}")
print(f"摘要: {result['summary']}")
print(f"优先级: {result['priority']}")
```
