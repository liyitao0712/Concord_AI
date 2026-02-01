# app/llm/prompts/defaults.py
# 默认 Prompt 模板
#
# 这些是代码内置的默认值，作为 fallback 使用
# 运行时优先从数据库加载，如果数据库中不存在则使用这里的默认值
#
# Prompt 命名规范：
# - 使用下划线分隔
# - 格式：{用途}_{类型}，如 intent_classifier, email_analyzer

from typing import Optional

DEFAULT_PROMPTS = {
    # ==================== 意图分类 ====================
    "intent_classifier": {
        "display_name": "意图分类器",
        "category": "agent",
        "description": "分析用户输入的意图类型",
        "model_hint": "claude-3-haiku-20240307",
        "variables": {
            "content": "需要分析的内容（邮件/消息）",
        },
        "content": """你是一个专业的意图分类助手。请分析以下内容，判断其意图类型。

## 可能的意图类型：
- inquiry: 询价、咨询产品信息
- order: 下单、订购产品
- complaint: 投诉、问题反馈
- follow_up: 跟进之前的事务
- greeting: 问候、寒暄
- other: 其他类型

## 待分析内容：
{{content}}

## 输出格式（JSON）：
{
    "intent": "意图类型",
    "confidence": 0.95,
    "reason": "判断理由",
    "entities": {
        "product": "提到的产品（如有）",
        "quantity": "数量（如有）",
        "company": "公司名称（如有）"
    }
}

请只返回 JSON，不要包含其他文本。""",
    },

    # ==================== 邮件分析 ====================
    "email_analyzer": {
        "display_name": "邮件分析器",
        "category": "agent",
        "description": "分析邮件内容，提取关键信息",
        "model_hint": "claude-3-sonnet-20240229",
        "variables": {
            "subject": "邮件主题",
            "sender": "发件人",
            "content": "邮件正文",
        },
        "content": """你是一个专业的邮件分析助手。请分析以下邮件，提取关键信息。

## 邮件信息：
- 发件人: {{sender}}
- 主题: {{subject}}
- 正文:
{{content}}

## 请提取以下信息：
1. 邮件意图（inquiry/order/complaint/follow_up/other）
2. 紧急程度（high/medium/low）
3. 需要的操作（reply/forward/archive/escalate）
4. 关键实体（产品、数量、金额、日期等）
5. 情感倾向（positive/neutral/negative）

## 输出格式（JSON）：
{
    "intent": "inquiry",
    "urgency": "medium",
    "action": "reply",
    "entities": {
        "products": ["产品A", "产品B"],
        "quantity": 100,
        "deadline": "2024-02-01"
    },
    "sentiment": "neutral",
    "summary": "一句话总结邮件内容",
    "suggested_reply_points": ["回复要点1", "回复要点2"]
}

请只返回 JSON，不要包含其他文本。""",
    },

    # ==================== 报价生成 ====================
    "quote_agent": {
        "display_name": "报价生成器",
        "category": "agent",
        "description": "根据询价信息生成报价单内容",
        "model_hint": "claude-3-sonnet-20240229",
        "variables": {
            "customer_info": "客户信息",
            "products": "产品列表",
            "pricing_rules": "定价规则",
        },
        "content": """你是一个专业的报价生成助手。请根据以下信息生成报价单。

## 客户信息：
{{customer_info}}

## 产品列表：
{{products}}

## 定价规则：
{{pricing_rules}}

## 请生成报价单，包含：
1. 产品明细（名称、规格、数量、单价、小计）
2. 优惠说明（如有）
3. 总价
4. 有效期
5. 付款条款
6. 交付时间

## 输出格式（JSON）：
{
    "items": [
        {
            "name": "产品名称",
            "specification": "规格",
            "quantity": 100,
            "unit_price": 10.00,
            "subtotal": 1000.00
        }
    ],
    "discount": {
        "type": "percentage",
        "value": 5,
        "reason": "新客户优惠"
    },
    "total": 950.00,
    "valid_until": "2024-02-15",
    "payment_terms": "款到发货",
    "delivery_time": "付款后7个工作日"
}

请只返回 JSON。""",
    },

    # ==================== 聊天助手 ====================
    "chat_agent": {
        "display_name": "聊天助手",
        "category": "agent",
        "description": "通用对话助手的系统提示",
        "model_hint": "claude-3-sonnet-20240229",
        "variables": {},
        "content": """你是 Concord AI 智能助手，一个友好、专业的 AI 对话伙伴。

你的特点：
- 回答准确、简洁、有帮助
- 使用清晰的中文表达
- 保持友好和专业的语调
- 适时使用 Markdown 格式化输出

请根据用户的问题提供有价值的回答。""",
    },

    # ==================== 邮件摘要分析 ====================
    "email_summarizer": {
        "display_name": "邮件摘要分析器",
        "category": "agent",
        "description": "分析外贸邮件，提取意图、产品、金额等业务信息",
        "model_hint": "claude-3-sonnet-20240229",
        "variables": {
            "sender": "发件人邮箱",
            "sender_name": "发件人名称",
            "subject": "邮件主题",
            "received_at": "收件时间",
            "content": "邮件正文",
        },
        "content": """你是一个专业的外贸邮件分析助手。请分析以下邮件内容，提取关键信息。

## 邮件信息
- 发件人: {{sender}} ({{sender_name}})
- 主题: {{subject}}
- 收件时间: {{received_at}}

## 邮件正文
{{content}}

## 分析要求

请以 JSON 格式返回分析结果，包含以下字段：

```json
{
    "summary": "一句话总结邮件核心内容（中文，不超过100字）",

    "key_points": ["关键要点1", "关键要点2", "关键要点3"],

    "original_language": "邮件原文语言代码，如 en/zh/es/ar/ru/de/fr/ja/ko 等",

    "sender_type": "发件方类型: customer(客户)/supplier(供应商)/freight(货代)/bank(银行)/other(其他)",

    "sender_company": "发件方公司名称，如无法识别则为 null",

    "sender_country": "发件方国家/地区，如无法识别则为 null",

    "is_new_contact": "是否像是新联系人（首次询盘/自我介绍）: true/false/null",

    "intent": "主要意图，选择最匹配的一项:
        - inquiry: 询价/询盘
        - quotation: 报价/还价
        - order: 下单/订单确认
        - order_change: 订单修改/取消
        - payment: 付款/汇款通知
        - shipment: 发货/物流跟踪
        - sample: 样品请求
        - complaint: 投诉/质量问题
        - after_sales: 售后服务
        - negotiation: 价格谈判
        - follow_up: 跟进/催促
        - introduction: 公司/产品介绍
        - general: 一般沟通
        - spam: 垃圾邮件/营销
        - other: 其他",

    "intent_confidence": "意图判断的置信度 0.0-1.0",

    "urgency": "紧急程度: urgent(紧急)/high(较高)/medium(一般)/low(较低)",

    "sentiment": "情感倾向: positive(积极)/neutral(中性)/negative(消极)",

    "products": [
        {
            "name": "产品名称",
            "specs": "规格描述",
            "quantity": 数量(数字),
            "unit": "单位",
            "target_price": 目标价格(数字，可选)
        }
    ],

    "amounts": [
        {
            "value": 金额数值,
            "currency": "货币代码 USD/EUR/CNY 等",
            "context": "金额上下文说明"
        }
    ],

    "trade_terms": {
        "incoterm": "贸易术语 FOB/CIF/EXW/DDP 等，如未提及则为 null",
        "payment_terms": "付款方式 T/T/L/C/D/P 等，如未提及则为 null",
        "destination": "目的地/目的港，如未提及则为 null"
    },

    "deadline": "截止日期或交期要求，ISO 格式如 2024-03-15，如无则为 null",

    "questions": ["对方提出的问题1", "对方提出的问题2"],

    "action_required": ["需要我方做的事情1", "需要我方做的事情2"],

    "suggested_reply": "建议的回复要点（简洁的中文说明）",

    "priority": "处理优先级: p0(立即处理)/p1(今日处理)/p2(本周处理)/p3(可延后)"
}
```

## 注意事项
1. 所有字段都要填写，无法识别的填 null 或空数组 []
2. summary 必须用中文，简洁明了
3. 仔细识别产品信息、金额、贸易条款
4. 根据邮件内容判断紧急程度和优先级
5. 只返回 JSON，不要有其他内容""",
    },

    # ==================== 摘要生成 ====================
    "summarizer": {
        "display_name": "摘要生成器",
        "category": "tool",
        "description": "生成文本摘要",
        "model_hint": "claude-3-haiku-20240307",
        "variables": {
            "content": "需要摘要的内容",
            "max_length": "最大长度（可选）",
        },
        "content": """请为以下内容生成简洁的摘要。

## 内容：
{{content}}

## 要求：
- 保留关键信息
- 语言简洁
- 最大长度：{{max_length}}字

请直接输出摘要，不需要额外说明。""",
    },

    # ==================== 翻译 ====================
    "translator": {
        "display_name": "翻译器",
        "category": "tool",
        "description": "翻译文本",
        "model_hint": "claude-3-haiku-20240307",
        "variables": {
            "content": "需要翻译的内容",
            "target_language": "目标语言",
        },
        "content": """请将以下内容翻译成{{target_language}}。

## 原文：
{{content}}

## 要求：
- 保持原意
- 语言自然流畅
- 专业术语翻译准确

请直接输出翻译结果。""",
    },

    # ==================== 实体提取 ====================
    "entity_extraction": {
        "display_name": "通用实体提取",
        "category": "tool",
        "description": "从文本中提取结构化信息（客户、产品、订单等）",
        "model_hint": "claude-3-sonnet-20240229",
        "variables": {
            "content": "需要提取信息的内容",
        },
        "content": """你是一个信息提取专家，专门从文本中提取结构化数据。

请从以下内容中提取关键信息：

<content>
{{content}}
</content>

请提取以下类型的信息，返回 JSON 格式：

{
    "customer": {
        "name": "客户姓名",
        "company": "公司名称",
        "email": "邮箱",
        "phone": "电话"
    },
    "products": [
        {
            "name": "产品名称",
            "model": "型号",
            "specification": "规格",
            "quantity": 数量,
            "unit": "单位",
            "price": 单价
        }
    ],
    "requirements": {
        "delivery_date": "交货日期",
        "delivery_address": "收货地址",
        "payment_terms": "付款方式",
        "notes": "其他备注"
    },
    "dates": [
        {
            "date": "日期",
            "type": "类型（交期/有效期/其他）",
            "original_text": "原文"
        }
    ]
}

提取规则：
1. 无法确定的字段填写 null
2. products 和 dates 如果没有相关信息则为空数组 []
3. 数量、价格保持数字格式，如果是范围则取较大值
4. 日期如果是相对时间（如"下周一"），保留原文
5. 不要猜测，不确定的信息标记为 null

只输出 JSON，不要添加任何其他内容。""",
    },

    # ==================== 询价信息提取 ====================
    "inquiry_extraction": {
        "display_name": "询价信息提取",
        "category": "tool",
        "description": "从询价邮件中提取结构化信息",
        "model_hint": "claude-3-sonnet-20240229",
        "variables": {
            "subject": "邮件主题",
            "sender": "发件人",
            "body": "邮件正文",
        },
        "content": """你是一个询价邮件分析专家。请从以下询价邮件中提取关键信息：

<email>
主题：{{subject}}
发件人：{{sender}}
内容：
{{body}}
</email>

请提取询价相关信息，返回 JSON 格式：

{
    "customer": {
        "name": "客户姓名（从邮件签名或内容推断）",
        "company": "公司名称",
        "email": "{{sender}}",
        "phone": "电话（如有）",
        "contact_preference": "首选联系方式"
    },
    "products": [
        {
            "name": "产品名称",
            "model": "型号（如有）",
            "specification": "规格要求",
            "quantity": 数量,
            "unit": "单位",
            "target_price": "目标价格（如客户提及）"
        }
    ],
    "requirements": {
        "delivery_date": "期望交期",
        "delivery_address": "收货地址",
        "quality_requirements": "质量要求",
        "packaging_requirements": "包装要求",
        "other_requirements": "其他要求"
    },
    "urgency": "紧急程度（high/normal/low）",
    "summary": "一句话总结询价内容"
}

提取规则：
1. 尽可能推断客户姓名（从签名、称呼等）
2. urgency 根据用词判断（"急"、"尽快"等为 high）
3. 无法确定的字段填写 null

只输出 JSON，不要添加任何其他内容。""",
    },

    # ==================== 订单信息提取 ====================
    "order_extraction": {
        "display_name": "订单信息提取",
        "category": "tool",
        "description": "从文本中提取订单相关信息",
        "model_hint": "claude-3-sonnet-20240229",
        "variables": {
            "content": "包含订单信息的内容",
        },
        "content": """你是一个订单信息提取专家。请从以下内容中提取订单信息：

<content>
{{content}}
</content>

请提取订单相关信息，返回 JSON 格式：

{
    "order_info": {
        "order_number": "订单号（如客户提供）",
        "order_date": "下单日期",
        "customer_po": "客户采购单号"
    },
    "customer": {
        "name": "客户姓名",
        "company": "公司名称",
        "email": "邮箱",
        "phone": "电话",
        "shipping_address": "收货地址",
        "billing_address": "账单地址"
    },
    "items": [
        {
            "product_name": "产品名称",
            "model": "型号",
            "specification": "规格",
            "quantity": 数量,
            "unit": "单位",
            "unit_price": 单价,
            "total_price": 总价,
            "notes": "备注"
        }
    ],
    "payment": {
        "method": "付款方式",
        "terms": "付款条款",
        "currency": "币种"
    },
    "delivery": {
        "requested_date": "要求交期",
        "shipping_method": "运输方式",
        "incoterms": "贸易条款"
    },
    "total_amount": 订单总金额,
    "notes": "订单备注"
}

提取规则：
1. 金额保持数字格式，并保留币种信息
2. 日期尽量转换为 YYYY-MM-DD 格式
3. 如果有多个收货地址，使用数组
4. 无法确定的字段填写 null

只输出 JSON，不要添加任何其他内容。""",
    },

    # ==================== 联系人信息提取 ====================
    "contact_extraction": {
        "display_name": "联系人信息提取",
        "category": "tool",
        "description": "从文本中提取联系人信息",
        "model_hint": "claude-3-haiku-20240307",
        "variables": {
            "content": "包含联系人信息的内容",
        },
        "content": """你是一个联系人信息提取专家。请从以下内容中提取联系人信息：

<content>
{{content}}
</content>

请提取所有联系人信息，返回 JSON 格式：

{
    "contacts": [
        {
            "name": "姓名",
            "title": "职位",
            "company": "公司",
            "department": "部门",
            "email": "邮箱",
            "phone": "电话",
            "mobile": "手机",
            "fax": "传真",
            "address": "地址",
            "social": {
                "wechat": "微信",
                "linkedin": "LinkedIn"
            },
            "role": "角色（决策者/联系人/技术对接人等）"
        }
    ]
}

提取规则：
1. 如果内容中有多个联系人，全部提取
2. 电话号码保持原始格式
3. 尝试从签名、落款中提取信息
4. 无法确定的字段填写 null

只输出 JSON，不要添加任何其他内容。""",
    },

    # ==================== 邮件意图分类（带主题） ====================
    "email_intent": {
        "display_name": "邮件意图分类",
        "category": "tool",
        "description": "分析邮件意图（包含主题、发件人和正文）",
        "model_hint": "claude-3-haiku-20240307",
        "variables": {
            "subject": "邮件主题",
            "sender": "发件人",
            "body": "邮件正文",
        },
        "content": """你是一个意图分类专家。请分析以下邮件的意图：

<email>
主题：{{subject}}
发件人：{{sender}}
内容：
{{body}}
</email>

请判断这封邮件的意图类型，并返回 JSON 格式的结果。

意图类型说明：
- inquiry: 询价（询问价格、要求报价、产品咨询）
- order: 订单（下单、采购、购买意向明确）
- support: 支持（技术问题、售后服务、产品使用问题）
- feedback: 反馈（投诉、建议、评价、意见）
- general: 一般（问候、感谢、无特定业务意图）
- unknown: 无法识别

返回格式：
{
    "intent": "意图类型",
    "confidence": 置信度,
    "keywords": ["关键词1", "关键词2"],
    "summary": "一句话总结邮件内容",
    "priority": "high/normal/low"
}

优先级判断依据：
- high: 紧急订单、重要客户、明确的采购意向
- normal: 一般询价、常规问题
- low: 闲聊、不紧急的反馈

注意：
1. confidence 是 0.0-1.0 之间的数字，表示判断的确信程度
2. keywords 是支持判断的关键词列表
3. 只输出 JSON，不要添加任何其他内容""",
    },

    # ==================== 批量意图分类 ====================
    "batch_intent": {
        "display_name": "批量意图分类",
        "category": "tool",
        "description": "对多条内容进行批量意图分类",
        "model_hint": "claude-3-haiku-20240307",
        "variables": {
            "items": "需要分类的内容列表（JSON 或文本）",
        },
        "content": """你是一个意图分类专家。请分析以下多条内容的意图：

<items>
{{items}}
</items>

对每条内容进行意图分类，返回 JSON 数组格式的结果。

返回格式：
[
    {"id": "item_id", "intent": "意图类型", "confidence": 置信度},
    ...
]

只输出 JSON 数组，不要添加任何其他内容。""",
    },
}


def get_default_prompt(name: str) -> Optional[dict]:
    """获取默认 Prompt"""
    return DEFAULT_PROMPTS.get(name)


def list_default_prompts() -> list[str]:
    """列出所有默认 Prompt 名称"""
    return list(DEFAULT_PROMPTS.keys())
