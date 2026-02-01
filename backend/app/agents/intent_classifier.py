# app/agents/intent_classifier.py
# 意图分类 Agent
#
# 功能：
# 快速分类用户意图，比 EmailAnalyzerAgent 更轻量
# 适用于：
# - 快速路由用户请求
# - 简单的意图识别
# - 不需要复杂分析的场景

import json
from app.core.logging import get_logger
from app.agents.base import BaseAgent, AgentState
from app.agents.registry import register_agent

logger = get_logger(__name__)


@register_agent
class IntentClassifierAgent(BaseAgent):
    """
    意图分类 Agent

    快速分类用户意图，比 EmailAnalyzerAgent 更轻量。
    不使用工具，直接由 LLM 判断意图。

    使用方法：
        agent = IntentClassifierAgent()
        result = await agent.run("我想询问产品A的价格")

        print(result.data)
        # {
        #     "intent": "inquiry",
        #     "confidence": 0.95,
        #     "reason": "用户明确表示想询问价格",
        #     "entities": {"product": "产品A"}
        # }

    支持的意图类型：
        - inquiry: 询价/咨询
        - order: 下单/采购
        - complaint: 投诉/问题
        - follow_up: 跟进/催促
        - greeting: 问候/寒暄
        - other: 其他
    """

    name = "intent_classifier"
    description = "快速分类用户意图"
    prompt_name = "intent_classifier"
    tools = []  # 不使用工具，快速分类
    model = None  # 使用数据库中配置的默认模型

    def _default_system_prompt(self) -> str:
        """默认系统提示"""
        return """你是一个专业的意图分类助手。请分析用户输入，判断其主要意图。

请返回 JSON 格式的结果，包含：
1. intent: 意图类型，必须是以下之一：
   - inquiry: 询价、咨询产品/服务信息
   - order: 下单、采购、购买
   - complaint: 投诉、问题反馈、不满
   - follow_up: 跟进、催促、查询进度
   - greeting: 问候、寒暄、打招呼
   - other: 其他无法归类的意图

2. confidence: 置信度，0-1 之间的数值，表示对分类结果的确定程度

3. reason: 简短说明为什么判断为该意图

4. entities: 提取的关键实体（如产品名、数量、日期等）

请只返回 JSON，不要包含其他文字。

示例输出：
```json
{
  "intent": "inquiry",
  "confidence": 0.92,
  "reason": "用户询问产品价格",
  "entities": {
    "product": "产品A",
    "quantity": 100
  }
}
```"""

    async def process_output(self, state: AgentState) -> dict:
        """处理输出，解析 JSON 结果"""
        output = state.get("output", "")

        try:
            content = output.strip()

            # 处理可能的 markdown 代码块
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
                if content.startswith("json"):
                    content = content[4:].strip()

            data = json.loads(content)

            return {
                "intent": data.get("intent", "other"),
                "confidence": data.get("confidence", 0.5),
                "reason": data.get("reason", ""),
                "entities": data.get("entities", {}),
            }

        except json.JSONDecodeError:
            logger.warning(f"[IntentClassifierAgent] 无法解析 JSON 输出: {output[:200]}")
            return {
                "intent": "other",
                "confidence": 0.0,
                "reason": "无法解析响应",
                "raw_output": output,
            }
