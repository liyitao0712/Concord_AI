# app/agents/email_summarizer.py
# 邮件摘要分析 Agent
#
# 使用 LangGraph 状态机执行分析流程：
# 1. preprocess: 清洗邮件正文 + 渲染 prompt 模板
# 2. think: LLM 分析，提取摘要、意图、发件方信息、业务信息等
# 3. output: 解析 JSON，组装结果字典
#
# 针对外贸场景优化。

import json
import re
from typing import Optional
from datetime import datetime

from langgraph.graph import StateGraph, END

from app.core.logging import get_logger
from app.agents.base import BaseAgent, AgentState, AgentResult
from app.agents.registry import register_agent
from app.tools.email_cleaner import clean_email_content
from app.llm.prompts import render_prompt, get_prompt

logger = get_logger(__name__)


@register_agent
class EmailSummarizerAgent(BaseAgent):
    """
    邮件摘要分析 Agent

    使用 LangGraph 状态机分析邮件内容，提取：
    - 摘要和关键要点
    - 发件方身份（客户/供应商）
    - 意图分类
    - 产品信息、金额、贸易条款
    - 处理建议

    执行图：preprocess → think → output → END
    """

    name = "email_summarizer"
    display_name = "邮件摘要分析器"
    description = "邮件摘要分析，提取意图、产品、金额等业务信息"
    prompt_name = "email_summarizer"
    tools = []  # 邮件清洗是确定性预处理，不通过 LLM 工具调用
    max_iterations = 1  # 单次 LLM 调用，无需迭代

    # ========== Prompt 加载 ==========

    async def _get_system_prompt(self) -> str:
        """获取系统提示：优先 email_summarizer_system，回退到硬编码默认值

        使用 render_prompt 而非 get_prompt，支持 {{company_name}} 等系统变量注入。
        """
        system_prompt = await render_prompt("email_summarizer_system")
        if system_prompt:
            return system_prompt
        return (
            "You are a professional foreign trade email analysis assistant. "
            "Return analysis results strictly in the requested JSON format."
        )

    # ========== Graph 构建 ==========

    async def _build_graph(self) -> StateGraph:
        """
        构建执行图：preprocess → think → output

        在 BaseAgent 默认流程前添加预处理节点，用于清洗邮件和渲染 prompt。
        """
        graph = StateGraph(AgentState)

        # 添加节点
        graph.add_node("preprocess", self._preprocess)
        graph.add_node("think", self._think)
        graph.add_node("execute_tools", self._execute_tools)
        graph.add_node("output", self._output)

        # 入口是 preprocess
        graph.set_entry_point("preprocess")

        # preprocess → think（正常）或 output（出错时跳过 LLM）
        graph.add_conditional_edges(
            "preprocess",
            self._should_continue_after_preprocess,
            {
                "continue": "think",
                "error": "output",
            },
        )

        # think → 条件判断是否需要工具（保留标准边，但 tools=[] 不会触发）
        graph.add_conditional_edges(
            "think",
            self._should_execute_tools,
            {
                "execute": "execute_tools",
                "output": "output",
            },
        )

        # 工具执行后继续思考（保留标准边）
        graph.add_edge("execute_tools", "think")

        # 输出后结束
        graph.add_edge("output", END)

        return graph.compile()

    def _should_continue_after_preprocess(self, state: AgentState) -> str:
        """预处理后的路由：有错误直接到 output，否则继续 think"""
        if state.get("error"):
            return "error"
        return "continue"

    # ========== 节点方法 ==========

    async def _preprocess(self, state: AgentState) -> AgentState:
        """
        预处理节点：清洗邮件正文、渲染 prompt 模板

        从 input_data 中获取邮件信息，执行：
        1. 清洗邮件正文（确定性操作，非 LLM 工具调用）
        2. 渲染 user prompt 模板
        3. 将渲染后的 prompt 设置为 state["input"]（供 _think 使用）
        4. 将 email_id 和 cleaned_content 存入 state["output_data"]
        """
        input_data = state.get("input_data", {})

        email_id = input_data.get("email_id", "")
        sender = input_data.get("sender", "")
        sender_name = input_data.get("sender_name", "")
        subject = input_data.get("subject", "")
        body_text = input_data.get("body_text", "")
        body_html = input_data.get("body_html", "")
        received_at = input_data.get("received_at")

        # 1. 清洗邮件正文（保留引用历史和签名）
        cleaned_content = await clean_email_content(
            body_text=body_text or "",
            body_html=body_html or "",
            max_length=10000,
            remove_signature=False,
            remove_quotes=False,
        )

        if not cleaned_content:
            logger.warning(f"[EmailSummarizer] 邮件正文为空: {email_id}")
            state["error"] = "邮件正文为空"
            state["output_data"] = self._empty_result(email_id, "邮件正文为空")
            return state

        # 2. 格式化收件时间
        if hasattr(received_at, "strftime"):
            received_at_str = received_at.strftime("%Y-%m-%d %H:%M")
        elif received_at:
            received_at_str = str(received_at)
        else:
            received_at_str = "Unknown"

        # 3. 渲染 user prompt 模板
        prompt = await render_prompt(
            "email_summarizer",
            sender=sender,
            sender_name=sender_name or "",
            subject=subject or "(No subject)",
            received_at=received_at_str,
            content=cleaned_content,
        )

        if not prompt:
            logger.error("[EmailSummarizer] Failed to load prompt, aborting analysis")
            state["error"] = "Prompt loading failed"
            state["output_data"] = self._empty_result(email_id, "Prompt loading failed")
            return state

        # 4. 设置 state
        # 直接将渲染后的 prompt 写入 messages（避免依赖 state["input"] 在节点间传播）
        state["input"] = prompt
        state["messages"] = [{"role": "user", "content": prompt}]
        state["output_data"] = {
            "email_id": email_id,
            "cleaned_content": cleaned_content,
        }

        logger.info(
            f"[EmailSummarizer] 预处理完成: {email_id}, "
            f"清洗后 {len(cleaned_content)} 字符"
        )
        return state

    async def _think(self, state: AgentState) -> AgentState:
        """
        思考节点：调用 LLM 进行分析（覆盖以捕获响应元数据）

        BaseAgent._think() 丢弃了 response.model 和 response.usage，
        但 EmailAnalysis 表需要 llm_model 和 token_used，因此覆盖此方法。
        """
        state["iterations"] = state.get("iterations", 0) + 1

        if state["iterations"] > self.max_iterations:
            state["error"] = f"超过最大迭代次数 {self.max_iterations}"
            return state

        # 构建消息
        messages = state.get("messages", [])
        if not messages:
            messages.append({
                "role": "user",
                "content": state["input"],
            })

        # 获取系统提示和模型
        system_prompt = await self._get_system_prompt()
        model = self._get_model()

        logger.debug(
            f"[EmailSummarizer] 思考 (迭代 {state['iterations']}), "
            f"user_prompt_len={len(messages[-1]['content']) if messages else 0}, "
            f"system_prompt_len={len(system_prompt)}"
        )

        # 调用 LLM（无工具调用）
        response = await self.llm.chat(
            messages[-1]["content"] if messages else state["input"],
            system=system_prompt,
            model=model,
        )

        messages.append({
            "role": "assistant",
            "content": response.content,
        })
        state["messages"] = messages

        # 捕获 LLM 响应元数据
        output_data = state.get("output_data", {})
        output_data["llm_model"] = model
        output_data["token_used"] = (
            response.usage.get("total_tokens")
            if isinstance(response.usage, dict)
            else None
        )
        state["output_data"] = output_data

        return state

    async def process_output(self, state: AgentState) -> dict:
        """
        处理输出：解析 LLM 返回的 JSON，合并预处理阶段的元数据
        """
        output_data = state.get("output_data", {})

        # 如果预处理就已经失败了（error 路径），output_data 已经是 _empty_result
        if state.get("error") and "summary" in output_data:
            return output_data

        # 解析 LLM 输出的 JSON
        raw_output = state.get("output", "")
        if raw_output:
            logger.info(f"[EmailSummarizer] LLM 原始返回: {raw_output[:500]}")
            parsed = self._parse_response(raw_output)
        else:
            parsed = {}

        # 合并解析结果和预处理阶段的元数据
        result = {**parsed}
        result["email_id"] = output_data.get("email_id", "")
        result["cleaned_content"] = output_data.get("cleaned_content", "")
        result["llm_model"] = output_data.get("llm_model")
        result["token_used"] = output_data.get("token_used")

        logger.info(
            f"[EmailSummarizer] 分析完成: {result.get('email_id')}, "
            f"intent={result.get('intent')}"
        )
        return result

    # ========== 便捷方法 ==========

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
        """
        分析邮件（便捷方法，兼容现有调用方）

        将参数打包为 input_data 并调用 BaseAgent.run()。
        返回分析结果字典（非 AgentResult）以兼容现有 API。

        Args:
            email_id: 邮件 ID
            sender: 发件人邮箱
            sender_name: 发件人名称
            subject: 邮件主题
            body_text: 邮件纯文本正文
            body_html: 邮件 HTML 正文（可选）
            received_at: 收件时间

        Returns:
            dict: 分析结果
        """
        logger.info(f"[EmailSummarizer] 开始分析邮件: {email_id}")

        input_data = {
            "email_id": email_id,
            "sender": sender,
            "sender_name": sender_name,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "received_at": received_at,
        }

        result = await self.run(
            f"分析邮件: {email_id}",
            input_data=input_data,
        )

        if result.success:
            return result.data
        else:
            return self._empty_result(email_id, result.error or "分析失败")

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

        logger.warning(f"[EmailSummarizer] 无法解析 LLM 返回: {content[:200]}...")
        return {"parse_error": True, "raw_response": content[:500]}

    def _empty_result(self, email_id: str, error: str) -> dict:
        """返回空结果（错误降级）"""
        return {
            "email_id": email_id,
            "summary": f"分析失败: {error}",
            "key_points": [],
            "intent": "other",
            "intent_confidence": 0,
            "urgency": "low",
            "sentiment": "neutral",
            "priority": "p3",
            "error": error,
        }


# 全局单例
email_summarizer = EmailSummarizerAgent()
