# app/agents/add_new_client_helper.py
# 新客户信息自动填充 Agent
#
# 使用 LangGraph 状态机执行搜索流程：
# 1. search: 通过 Anthropic SDK + web_search 服务端工具搜索公司信息
# 2. output: 解析 JSON，映射到 Customer 模型字段
#
# 直接使用 Anthropic SDK 调用 Claude web_search 服务端工具，
# 因为 LiteLLM 不支持 Anthropic 的 web_search_20250305 服务端工具类型。
# 无需额外搜索 API Key。

import json
import os
import re
from typing import Optional

from langgraph.graph import StateGraph, END
import anthropic

from app.core.logging import get_logger
from app.agents.base import BaseAgent, AgentState, AgentResult
from app.agents.registry import register_agent
from app.llm.prompts import render_prompt, get_prompt

logger = get_logger(__name__)


@register_agent
class AddNewClientHelperAgent(BaseAgent):
    """
    新客户信息自动填充 Agent

    根据公司名称通过 LLM web search 搜索公司信息，返回结构化数据
    用于自动填充客户表单。

    执行图：search → output → END

    注意：此 Agent 直接使用 Anthropic SDK（而非 LiteLLM），
    因为 LiteLLM 不支持 Anthropic 的 web_search_20250305 服务端工具。
    """

    name = "add_new_client_helper"
    display_name = "新客户信息助手"
    description = "根据公司名称自动搜索并填充客户信息"
    prompt_name = "add_new_client_helper"
    tools = []  # 使用 Anthropic 服务端 web_search，不通过自定义 Tool
    max_iterations = 1

    # ========== Prompt 加载 ==========

    async def _get_system_prompt(self) -> str:
        """获取系统提示（支持 {{company_name}} 等系统变量渲染）"""
        system_prompt = await render_prompt("add_new_client_helper_system")
        if system_prompt:
            return system_prompt
        return (
            "You are a professional company information research assistant. "
            "Search the web and return structured company data in JSON format."
        )

    # ========== Graph 构建 ==========

    async def _build_graph(self) -> StateGraph:
        """
        构建执行图：search → output

        search 节点直接调用 Anthropic SDK 并传入 web_search 服务端工具。
        """
        graph = StateGraph(AgentState)

        graph.add_node("search", self._search)
        graph.add_node("output", self._output)

        graph.set_entry_point("search")
        graph.add_edge("search", "output")
        graph.add_edge("output", END)

        return graph.compile()

    # ========== 节点方法 ==========

    def _resolve_anthropic_model(self, model: str) -> str:
        """
        将 LiteLLM 格式的模型名转换为 Anthropic SDK 格式

        例如：
        - "anthropic/claude-sonnet-4-20250514" → "claude-sonnet-4-20250514"
        - "claude-sonnet-4-20250514" → "claude-sonnet-4-20250514"
        """
        if model.startswith("anthropic/"):
            return model[len("anthropic/"):]
        return model

    async def _search(self, state: AgentState) -> AgentState:
        """
        搜索节点：调用 Anthropic SDK + web_search 服务端工具搜索公司信息

        直接使用 anthropic.AsyncAnthropic 客户端，
        传入 web_search_20250305 服务端工具让 Claude 自动搜索。
        """
        state["iterations"] = 1
        input_data = state.get("input_data", {})
        company_name = input_data.get("company_name", "") or state.get("input", "")

        if not company_name:
            state["error"] = "公司名称不能为空"
            state["output_data"] = self._empty_result("公司名称不能为空")
            return state

        # 渲染 user prompt 模板
        prompt = await render_prompt(
            "add_new_client_helper",
            company_name=company_name,
        )

        if not prompt:
            state["error"] = "Prompt 加载失败"
            state["output_data"] = self._empty_result("Prompt 加载失败")
            return state

        # 获取系统提示和模型
        system_prompt = await self._get_system_prompt()
        model = self._resolve_anthropic_model(self._get_model())

        logger.info(f"[AddNewClientHelper] 搜索公司信息: {company_name}, 模型: {model}")

        try:
            # 使用 Anthropic SDK 直接调用（支持 web_search 服务端工具）
            client = anthropic.AsyncAnthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )

            response = await client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=0.3,
                system=system_prompt,
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
                }],
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )

            # 提取文本内容（响应包含 text + web_search_tool_result 等 content block）
            content = self._extract_text_content(response)

            state["messages"] = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": content},
            ]

            # 保存元数据
            output_data = state.get("output_data", {})
            output_data["company_name"] = company_name
            output_data["llm_model"] = model
            if response.usage:
                output_data["token_used"] = (
                    response.usage.input_tokens + response.usage.output_tokens
                )
            state["output_data"] = output_data

        except Exception as e:
            logger.error(f"[AddNewClientHelper] LLM 调用失败: {e}")
            state["error"] = str(e)
            state["output_data"] = self._empty_result(str(e))

        return state

    def _extract_text_content(self, response) -> str:
        """
        从 Anthropic SDK 响应中提取文本内容

        Anthropic messages.create 响应的 content 是 ContentBlock 列表，
        包含 text、web_search_tool_result 等类型。
        只提取 text 类型的内容。
        """
        text_parts = []
        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                text_parts.append(block.text)
        return "\n".join(text_parts)

    async def process_output(self, state: AgentState) -> dict:
        """
        处理输出：解析 LLM 返回的 JSON，映射到 Customer 字段
        """
        output_data = state.get("output_data", {})

        # 如果搜索阶段就失败了
        if state.get("error") and "confidence" in output_data:
            return output_data

        # 解析 LLM 输出的 JSON
        raw_output = state.get("output", "")
        if raw_output:
            logger.info(f"[AddNewClientHelper] LLM 原始返回: {raw_output[:500]}")
            parsed = self._parse_response(raw_output)
        else:
            parsed = {}

        # 合并解析结果和元数据
        result = {**parsed}
        result["company_name"] = output_data.get("company_name", "")
        result["llm_model"] = output_data.get("llm_model")
        result["token_used"] = output_data.get("token_used")

        logger.info(
            f"[AddNewClientHelper] 搜索完成: {result.get('company_name')}, "
            f"confidence={result.get('confidence')}"
        )
        return result

    # ========== 便捷方法 ==========

    async def lookup(self, company_name: str) -> dict:
        """
        搜索公司信息（便捷方法）

        Args:
            company_name: 公司全称

        Returns:
            dict: 可直接用于 CustomerCreate 的结构化数据
        """
        logger.info(f"[AddNewClientHelper] 开始搜索: {company_name}")

        result = await self.run(
            f"搜索公司信息: {company_name}",
            input_data={"company_name": company_name},
        )

        if result.success:
            return result.data
        else:
            return self._empty_result(result.error or "搜索失败")

    # ========== 辅助方法 ==========

    def _parse_response(self, content: str) -> dict:
        """
        解析 LLM 返回的 JSON（三级回退策略）

        1. 直接 json.loads
        2. 从 ```json ``` 代码块提取
        3. 找第一个 { 到最后一个 }
        """
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找到 { } 包围的内容
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass

        logger.warning(f"[AddNewClientHelper] 无法解析 LLM 返回: {content[:200]}...")
        return {"parse_error": True, "raw_response": content[:500]}

    def _empty_result(self, error: str) -> dict:
        """返回空结果（错误降级）"""
        return {
            "short_name": None,
            "country": None,
            "region": None,
            "industry": None,
            "company_size": None,
            "website": None,
            "email": None,
            "phone": None,
            "address": None,
            "tags": [],
            "notes": None,
            "confidence": 0,
            "error": error,
        }


# 全局单例
add_new_client_helper = AddNewClientHelperAgent()
