# app/agents/quote_agent.py
# 报价 Agent
#
# 功能：
# 1. 分析询价邮件内容
# 2. 提取产品和数量信息
# 3. 查询产品价格
# 4. 生成报价单 PDF
# 5. 生成回复建议
#
# 使用方法：
#   from app.agents.quote_agent import QuoteAgent
#
#   agent = QuoteAgent()
#   result = await agent.run(
#       "邮件内容...",
#       input_data={"subject": "询价", "sender": "customer@example.com"}
#   )

import json
from typing import Optional

from app.core.logging import get_logger
from app.agents.base import BaseAgent, AgentState, AgentResult
from app.agents.registry import register_agent
from app.llm.prompts import render_prompt

logger = get_logger(__name__)


# 默认系统提示词
DEFAULT_QUOTE_PROMPT = """你是一个专业的销售助理，负责处理客户询价并生成报价。

任务：
1. 分析客户的询价邮件
2. 提取所需产品和数量
3. 使用工具查询产品信息和价格
4. 生成报价明细
5. 如果金额超过一定阈值，建议需要审批

你有以下工具可用：
- search_products: 搜索产品
- get_product: 获取产品详情
- generate_quote_pdf: 生成报价单 PDF

请按以下 JSON 格式返回结果：
```json
{
    "customer_name": "从邮件中提取的客户名称",
    "items": [
        {
            "product_name": "产品名称",
            "product_id": "产品ID（如果查询到）",
            "quantity": 数量,
            "unit_price": 单价,
            "total": 小计
        }
    ],
    "total_price": 总价,
    "currency": "CNY",
    "discount": 折扣（如有）,
    "valid_days": 7,
    "needs_approval": 是否需要审批（总价超过 10000 则为 true）,
    "notes": "备注信息",
    "reply_content": "建议的邮件回复内容"
}
```

如果无法确定某些信息，请在 notes 中说明，并给出合理的估计。"""


@register_agent
class QuoteAgent(BaseAgent):
    """
    报价 Agent

    分析询价邮件，查询产品价格，生成报价单。

    使用方法：
        agent = QuoteAgent()
        result = await agent.run(
            "客户邮件内容...",
            input_data={
                "subject": "询价请求",
                "sender": "customer@example.com",
                "customer_name": "张三"  # 可选
            }
        )

        print(result.data)
        # {
        #     "items": [...],
        #     "total_price": 10000,
        #     "pdf_url": "https://...",
        #     "needs_approval": True,
        #     "reply_content": "..."
        # }
    """

    name = "quote_agent"
    description = "分析询价内容，查询产品价格，生成报价单"
    prompt_name = "quote_agent"
    # 可用工具
    tools = ["search_products", "get_product", "generate_quote_pdf"]
    model = None  # 使用数据库中配置的默认模型
    # 最大迭代次数（因为需要多次工具调用）
    max_iterations = 5

    async def _get_system_prompt(self) -> str:
        """获取系统提示"""
        input_data = getattr(self, "_current_input_data", {})

        # 尝试从数据库加载自定义 Prompt
        prompt = await render_prompt(
            "quote_agent",
            subject=input_data.get("subject", "（无主题）"),
            sender=input_data.get("sender", "（未知发件人）"),
            customer_name=input_data.get("customer_name", ""),
        )

        if prompt:
            return prompt

        return DEFAULT_QUOTE_PROMPT

    async def run(
        self,
        input_text: str,
        *,
        input_data: Optional[dict] = None,
        **kwargs,
    ) -> AgentResult:
        """执行报价生成"""
        # 保存输入数据供 _get_system_prompt 使用
        self._current_input_data = input_data or {}
        return await super().run(input_text, input_data=input_data, **kwargs)

    async def process_output(self, state: AgentState) -> dict:
        """
        处理输出，解析报价结果

        Returns:
            dict: 报价结果
        """
        output = state.get("output", "")
        tool_calls = state.get("tool_calls", [])

        # 尝试解析 JSON 输出
        try:
            content = output.strip()

            # 处理可能的 markdown 代码块
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
                if content.startswith("json"):
                    content = content[4:].strip()

            data = json.loads(content)

            # 提取报价信息
            result = {
                "customer_name": data.get("customer_name", ""),
                "items": data.get("items", []),
                "total_price": data.get("total_price", 0),
                "currency": data.get("currency", "CNY"),
                "discount": data.get("discount"),
                "valid_days": data.get("valid_days", 7),
                "needs_approval": data.get("needs_approval", False),
                "notes": data.get("notes", ""),
                "reply_content": data.get("reply_content", ""),
                "pdf_url": None,  # 从工具调用结果中提取
            }

            # 检查是否需要审批（金额超过阈值）
            if result["total_price"] > 10000 and not result.get("needs_approval"):
                result["needs_approval"] = True
                result["approval_reason"] = "报价金额超过 10,000 元"

            # 从工具调用结果中提取 PDF URL
            for tool_call in tool_calls:
                if tool_call.get("name") == "generate_quote_pdf":
                    tool_result = tool_call.get("result", {})
                    if isinstance(tool_result, dict):
                        result["pdf_url"] = tool_result.get("url")
                        result["quote_no"] = tool_result.get("quote_no")

            logger.info(
                f"[QuoteAgent] 生成报价: items={len(result['items'])} "
                f"total={result['total_price']} needs_approval={result['needs_approval']}"
            )

            return result

        except json.JSONDecodeError:
            logger.warning(f"[QuoteAgent] 无法解析 JSON 输出: {output[:200]}")

            # 返回基本结构
            return {
                "customer_name": "",
                "items": [],
                "total_price": 0,
                "currency": "CNY",
                "valid_days": 7,
                "needs_approval": False,
                "notes": "无法解析报价结果",
                "reply_content": output[:500] if output else "",
                "parse_error": True,
                "raw_output": output,
            }

    def _format_reply_content(self, data: dict) -> str:
        """
        格式化回复内容

        如果 LLM 没有生成回复内容，则使用模板生成
        """
        if data.get("reply_content"):
            return data["reply_content"]

        customer_name = data.get("customer_name", "客户")
        items = data.get("items", [])
        total = data.get("total_price", 0)
        currency = data.get("currency", "CNY")
        valid_days = data.get("valid_days", 7)

        lines = [
            f"尊敬的{customer_name}：",
            "",
            "感谢您的询价！根据您的需求，我们为您提供以下报价：",
            "",
        ]

        for i, item in enumerate(items, 1):
            name = item.get("product_name", item.get("name", ""))
            qty = item.get("quantity", 0)
            price = item.get("unit_price", 0)
            total_item = item.get("total", price * qty)
            lines.append(f"{i}. {name} x {qty}，单价 {currency} {price:,.2f}，小计 {currency} {total_item:,.2f}")

        lines.extend([
            "",
            f"总计：{currency} {total:,.2f}",
            f"报价有效期：{valid_days} 天",
            "",
            "如有任何问题，请随时联系我们。",
            "",
            "祝好！",
        ])

        return "\n".join(lines)
