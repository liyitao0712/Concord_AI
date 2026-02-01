# app/agents/email_analyzer.py
# 邮件分析 Agent
#
# 功能：
# 1. 分析邮件意图（询价、订单、投诉等）
# 2. 提取关键信息（产品、数量、客户等）
# 3. 推荐处理动作
# 4. 可选：查询数据库获取客户/产品信息

import json
from typing import Optional

from app.core.logging import get_logger
from app.agents.base import BaseAgent, AgentState, AgentResult
from app.agents.registry import register_agent
from app.llm.prompts import render_prompt

logger = get_logger(__name__)


@register_agent
class EmailAnalyzerAgent(BaseAgent):
    """
    邮件分析 Agent

    分析邮件内容，提取关键信息，判断意图，推荐处理动作。

    使用方法：
        agent = EmailAnalyzerAgent()
        result = await agent.run(
            "邮件正文...",
            input_data={
                "subject": "询价请求",
                "sender": "customer@example.com",
            }
        )

        print(result.data)
        # {
        #     "intent": "inquiry",
        #     "urgency": "medium",
        #     "entities": {...},
        #     "suggested_action": "reply"
        # }
    """

    name = "email_analyzer"
    description = "分析邮件内容，提取意图和关键信息"
    prompt_name = "email_analyzer"
    tools = ["search_customers", "search_products", "get_customer", "get_product"]
    model = None  # 使用数据库中配置的默认模型

    async def _get_system_prompt(self) -> str:
        """获取系统提示，填充邮件信息"""
        input_data = getattr(self, "_current_input_data", {})

        prompt = await render_prompt(
            "email_analyzer",
            subject=input_data.get("subject", "（无主题）"),
            sender=input_data.get("sender", "（未知发件人）"),
            content="{{content}}",  # 占位符，在 run 中替换
        )

        if prompt:
            return prompt

        # 默认提示
        return """你是一个专业的邮件分析助手。请分析邮件内容，提取关键信息。

请返回 JSON 格式的分析结果，包含：
1. intent: 意图类型（inquiry/order/complaint/follow_up/greeting/other）
2. urgency: 紧急程度（high/medium/low）
3. action: 建议动作（reply/forward/archive/escalate）
4. entities: 提取的实体信息
5. sentiment: 情感倾向（positive/neutral/negative）
6. summary: 一句话总结

请只返回 JSON，不要包含其他文本。"""

    async def run(
        self,
        input_text: str,
        *,
        input_data: Optional[dict] = None,
        **kwargs,
    ) -> AgentResult:
        """执行邮件分析"""
        # 保存输入数据供 _get_system_prompt 使用
        self._current_input_data = input_data or {}
        return await super().run(input_text, input_data=input_data, **kwargs)

    async def process_output(self, state: AgentState) -> dict:
        """
        处理输出，解析 JSON 结果
        """
        output = state.get("output", "")

        # 尝试解析 JSON
        try:
            # 处理可能的 markdown 代码块
            content = output.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                # 去掉首尾的 ``` 行
                content = "\n".join(lines[1:-1])
                if content.startswith("json"):
                    content = content[4:].strip()

            data = json.loads(content)

            # 标准化输出
            return {
                "intent": data.get("intent", "other"),
                "urgency": data.get("urgency", "medium"),
                "action": data.get("action", "reply"),
                "entities": data.get("entities", {}),
                "sentiment": data.get("sentiment", "neutral"),
                "summary": data.get("summary", ""),
                "suggested_reply_points": data.get("suggested_reply_points", []),
                "raw_analysis": data,
            }

        except json.JSONDecodeError:
            logger.warning(f"[EmailAnalyzerAgent] 无法解析 JSON 输出: {output[:200]}")

            # 返回基本结构
            return {
                "intent": "other",
                "urgency": "medium",
                "action": "reply",
                "entities": {},
                "sentiment": "neutral",
                "summary": output[:200] if output else "",
                "parse_error": True,
                "raw_output": output,
            }


# IntentClassifierAgent 已移动到 intent_classifier.py
