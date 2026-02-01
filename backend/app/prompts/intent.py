# app/prompts/intent.py
# 意图分类 Prompt 模板
#
# 功能说明：
# 用于识别邮件或消息的意图类型
#
# 支持的意图类型：
# - inquiry: 询价（询问产品价格、报价请求）
# - order: 订单（下单、采购）
# - support: 支持（技术支持、售后服务）
# - feedback: 反馈（投诉、建议、评价）
# - general: 一般（问候、闲聊、其他）
# - unknown: 无法识别
#
# 使用方法：
#   from app.prompts.intent import INTENT_CLASSIFIER_PROMPT
#   from app.llm.gateway import llm_gateway
#
#   prompt = INTENT_CLASSIFIER_PROMPT.render(content="请问产品A的价格？")
#   response = await llm_gateway.chat(message=prompt, system=INTENT_SYSTEM.render())

from app.prompts.base import PromptTemplate, SystemPrompt


# ==================== 意图分类系统提示词 ====================

INTENT_SYSTEM = SystemPrompt(
    role="你是一个意图分类专家，专门分析邮件和消息的意图。",
    instructions=[
        "仔细阅读输入的内容",
        "判断内容的主要意图",
        "只输出 JSON 格式的结果",
    ],
    constraints=[
        "意图类型必须是以下之一：inquiry, order, support, feedback, general, unknown",
        "confidence 范围是 0.0 到 1.0",
        "不要添加任何解释，只输出 JSON",
    ],
    examples=[
        """输入：请问贵公司的产品A价格是多少？
输出：{"intent": "inquiry", "confidence": 0.95, "keywords": ["价格", "产品A"]}""",
        """输入：我想订购100个产品B
输出：{"intent": "order", "confidence": 0.90, "keywords": ["订购", "100个", "产品B"]}""",
        """输入：你好，最近怎么样？
输出：{"intent": "general", "confidence": 0.85, "keywords": ["问候"]}""",
    ]
)


# ==================== 意图分类 Prompt 模板 ====================

INTENT_CLASSIFIER_PROMPT = PromptTemplate(
    name="intent_classifier",
    description="Email/message intent classification",
    template="""请分析以下内容的意图：

<content>
{content}
</content>

请判断这段内容的意图类型，并返回 JSON 格式的结果。

意图类型说明：
- inquiry: 询价（询问价格、要求报价、产品咨询）
- order: 订单（下单、采购、购买意向）
- support: 支持（技术问题、售后服务、产品使用问题）
- feedback: 反馈（投诉、建议、评价、意见）
- general: 一般（问候、闲聊、无特定业务意图）
- unknown: 无法识别（内容不清或与业务无关）

返回格式：
{{"intent": "意图类型", "confidence": 置信度, "keywords": ["关键词1", "关键词2"]}}

注意：
1. confidence 是 0.0-1.0 之间的数字，表示判断的确信程度
2. keywords 是支持判断的关键词列表
3. 只输出 JSON，不要添加任何其他内容"""
)


# ==================== 邮件意图分类（带主题） ====================

EMAIL_INTENT_PROMPT = PromptTemplate(
    name="email_intent_classifier",
    description="Email intent classification (with subject)",
    template="""请分析以下邮件的意图：

<email>
主题：{subject}
发件人：{sender}
内容：
{body}
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
{{
    "intent": "意图类型",
    "confidence": 置信度,
    "keywords": ["关键词1", "关键词2"],
    "summary": "一句话总结邮件内容",
    "priority": "high/normal/low"
}}

优先级判断依据：
- high: 紧急订单、重要客户、明确的采购意向
- normal: 一般询价、常规问题
- low: 闲聊、不紧急的反馈

只输出 JSON，不要添加任何其他内容。"""
)


# ==================== 批量意图分类 ====================

BATCH_INTENT_PROMPT = PromptTemplate(
    name="batch_intent_classifier",
    description="Batch intent classification",
    template="""请分析以下多条内容的意图：

<items>
{items}
</items>

对每条内容进行意图分类，返回 JSON 数组格式的结果。

返回格式：
[
    {{"id": "item_id", "intent": "意图类型", "confidence": 置信度}},
    ...
]

只输出 JSON 数组，不要添加任何其他内容。"""
)
