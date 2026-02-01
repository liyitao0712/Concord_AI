# app/prompts/extraction.py
# 实体提取 Prompt 模板
#
# 功能说明：
# 从邮件或消息中提取结构化信息（实体）
#
# 支持提取的实体类型：
# - 客户信息：姓名、公司、邮箱、电话
# - 产品信息：产品名称、型号、规格
# - 订单信息：数量、单价、交期、收货地址
# - 时间日期：日期、时间、期限
#
# 使用方法：
#   from app.prompts.extraction import ENTITY_EXTRACTION_PROMPT
#   from app.llm.gateway import llm_gateway
#
#   prompt = ENTITY_EXTRACTION_PROMPT.render(content="邮件内容")
#   response = await llm_gateway.chat(message=prompt, system=EXTRACTION_SYSTEM.render())

from app.prompts.base import PromptTemplate, SystemPrompt


# ==================== 实体提取系统提示词 ====================

EXTRACTION_SYSTEM = SystemPrompt(
    role="你是一个信息提取专家，专门从文本中提取结构化数据。",
    instructions=[
        "仔细阅读输入的内容",
        "按照指定的格式提取所有相关信息",
        "只输出 JSON 格式的结果",
        "无法提取的字段填写 null",
    ],
    constraints=[
        "严格按照指定的 JSON 格式输出",
        "不确定的信息标记为 null，不要猜测",
        "数量、价格等数字保持原始格式",
        "不要添加任何解释，只输出 JSON",
    ],
    examples=[
        """输入：张三（ABC公司）询问产品A的价格，需要100个，希望下周一前交货。电话13800138000。
输出：{
    "customer": {"name": "张三", "company": "ABC公司", "phone": "13800138000", "email": null},
    "products": [{"name": "产品A", "quantity": 100, "unit": "个", "price": null}],
    "requirements": {"delivery_date": "下周一", "notes": null}
}""",
    ]
)


# ==================== 通用实体提取模板 ====================

ENTITY_EXTRACTION_PROMPT = PromptTemplate(
    name="entity_extraction",
    description="General entity extraction",
    template="""请从以下内容中提取关键信息：

<content>
{content}
</content>

请提取以下类型的信息，返回 JSON 格式：

{{
    "customer": {{
        "name": "客户姓名",
        "company": "公司名称",
        "email": "邮箱",
        "phone": "电话"
    }},
    "products": [
        {{
            "name": "产品名称",
            "model": "型号",
            "specification": "规格",
            "quantity": 数量,
            "unit": "单位",
            "price": 单价
        }}
    ],
    "requirements": {{
        "delivery_date": "交货日期",
        "delivery_address": "收货地址",
        "payment_terms": "付款方式",
        "notes": "其他备注"
    }},
    "dates": [
        {{
            "date": "日期",
            "type": "类型（交期/有效期/其他）",
            "original_text": "原文"
        }}
    ]
}}

提取规则：
1. 无法确定的字段填写 null
2. products 和 dates 如果没有相关信息则为空数组 []
3. 数量、价格保持数字格式，如果是范围则取较大值
4. 日期如果是相对时间（如"下周一"），保留原文

只输出 JSON，不要添加任何其他内容。"""
)


# ==================== 询价邮件信息提取 ====================

INQUIRY_EXTRACTION_PROMPT = PromptTemplate(
    name="inquiry_extraction",
    description="Inquiry email extraction",
    template="""请从以下询价邮件中提取关键信息：

<email>
主题：{subject}
发件人：{sender}
内容：
{body}
</email>

请提取询价相关信息，返回 JSON 格式：

{{
    "inquiry_id": "自动生成的询价编号（格式：INQ-YYYYMMDD-XXX）",
    "customer": {{
        "name": "客户姓名（从邮件签名或内容推断）",
        "company": "公司名称",
        "email": "{sender}",
        "phone": "电话（如有）",
        "contact_preference": "首选联系方式"
    }},
    "products": [
        {{
            "name": "产品名称",
            "model": "型号（如有）",
            "specification": "规格要求",
            "quantity": 数量,
            "unit": "单位",
            "target_price": "目标价格（如客户提及）"
        }}
    ],
    "requirements": {{
        "delivery_date": "期望交期",
        "delivery_address": "收货地址",
        "quality_requirements": "质量要求",
        "packaging_requirements": "包装要求",
        "other_requirements": "其他要求"
    }},
    "urgency": "紧急程度（high/normal/low）",
    "summary": "一句话总结询价内容"
}}

提取规则：
1. inquiry_id 格式：INQ-当前日期-三位序号
2. 尽可能推断客户姓名（从签名、称呼等）
3. urgency 根据用词判断（"急"、"尽快"等为 high）
4. 无法确定的字段填写 null

只输出 JSON，不要添加任何其他内容。"""
)


# ==================== 订单信息提取 ====================

ORDER_EXTRACTION_PROMPT = PromptTemplate(
    name="order_extraction",
    description="Order information extraction",
    template="""请从以下内容中提取订单信息：

<content>
{content}
</content>

请提取订单相关信息，返回 JSON 格式：

{{
    "order_info": {{
        "order_number": "订单号（如客户提供）",
        "order_date": "下单日期",
        "customer_po": "客户采购单号"
    }},
    "customer": {{
        "name": "客户姓名",
        "company": "公司名称",
        "email": "邮箱",
        "phone": "电话",
        "shipping_address": "收货地址",
        "billing_address": "账单地址"
    }},
    "items": [
        {{
            "product_name": "产品名称",
            "model": "型号",
            "specification": "规格",
            "quantity": 数量,
            "unit": "单位",
            "unit_price": 单价,
            "total_price": 总价,
            "notes": "备注"
        }}
    ],
    "payment": {{
        "method": "付款方式",
        "terms": "付款条款",
        "currency": "币种"
    }},
    "delivery": {{
        "requested_date": "要求交期",
        "shipping_method": "运输方式",
        "incoterms": "贸易条款"
    }},
    "total_amount": 订单总金额,
    "notes": "订单备注"
}}

提取规则：
1. 金额保持数字格式，并保留币种信息
2. 日期尽量转换为 YYYY-MM-DD 格式
3. 如果有多个收货地址，使用数组
4. 无法确定的字段填写 null

只输出 JSON，不要添加任何其他内容。"""
)


# ==================== 联系人信息提取 ====================

CONTACT_EXTRACTION_PROMPT = PromptTemplate(
    name="contact_extraction",
    description="Contact information extraction",
    template="""请从以下内容中提取联系人信息：

<content>
{content}
</content>

请提取所有联系人信息，返回 JSON 格式：

{{
    "contacts": [
        {{
            "name": "姓名",
            "title": "职位",
            "company": "公司",
            "department": "部门",
            "email": "邮箱",
            "phone": "电话",
            "mobile": "手机",
            "fax": "传真",
            "address": "地址",
            "social": {{
                "wechat": "微信",
                "linkedin": "LinkedIn"
            }},
            "role": "角色（决策者/联系人/技术对接人等）"
        }}
    ]
}}

提取规则：
1. 如果内容中有多个联系人，全部提取
2. 电话号码保持原始格式
3. 尝试从签名、落款中提取信息
4. 无法确定的字段填写 null

只输出 JSON，不要添加任何其他内容。"""
)
