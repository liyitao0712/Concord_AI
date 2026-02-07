# app/agents/work_type_analyzer.py
# 工作类型分析 Agent
#
# 使用 LangGraph 状态机执行分析流程：
# 1. preprocess: 查询现有工作类型 + 待审批建议，渲染 prompt 模板
# 2. think: LLM 分析，匹配工作类型或建议新类型
# 3. output: 解析 JSON，组装结果字典
# 4. run() 后处理: 如需建议新类型，创建 WorkTypeSuggestion + Temporal 审批流
#
# 与 EmailSummarizer 并行执行。

import json
import re
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, END

from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.agents.base import BaseAgent, AgentState, AgentResult
from app.agents.registry import register_agent
from app.models.work_type import WorkType, WorkTypeSuggestion
from app.llm.prompts import render_prompt, get_prompt

logger = get_logger(__name__)


@register_agent
class WorkTypeAnalyzerAgent(BaseAgent):
    """
    工作类型分析 Agent

    使用 LangGraph 状态机分析邮件内容：
    - 匹配现有工作类型
    - 识别并建议新的工作类型
    - 支持 Temporal 审批流程

    执行图：preprocess → think → output → END
    """

    name = "work_type_analyzer"
    display_name = "工作类型分析器"
    description = "分析邮件内容判断工作类型，匹配现有类型或建议新类型"
    prompt_name = "work_type_analyzer"
    tools = []
    max_iterations = 1  # 单次 LLM 调用，无需迭代

    # 建议新类型的置信度门槛（设为 0 不过滤，让 LLM 自由建议）
    SUGGESTION_CONFIDENCE_THRESHOLD = 0.0

    # ========== Prompt 加载 ==========

    async def _get_system_prompt(self) -> str:
        """获取系统提示：优先 work_type_analyzer_system，回退到硬编码默认值

        使用 render_prompt 而非 get_prompt，支持 {{company_name}} 等系统变量注入。
        """
        system_prompt = await render_prompt("work_type_analyzer_system")
        if system_prompt:
            return system_prompt
        return (
            "You are a work type classification expert. "
            "Return results strictly in the requested JSON format."
        )

    # ========== Graph 构建 ==========

    async def _build_graph(self) -> StateGraph:
        """
        构建执行图：preprocess → think → output

        在 BaseAgent 默认流程前添加预处理节点，用于查询工作类型和渲染 prompt。
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
        预处理节点：查询工作类型列表、渲染 prompt 模板

        从 input_data 中获取邮件信息，执行：
        1. 查询现有工作类型列表
        2. 查询待审批/已拒绝的建议列表（避免重复建议）
        3. 渲染 user prompt 模板
        4. 将渲染后的 prompt 设置为 state["input"]
        """
        input_data = state.get("input_data", {})

        email_id = input_data.get("email_id", "")
        sender = input_data.get("sender", "")
        subject = input_data.get("subject", "")
        content = input_data.get("content", "")
        received_at = input_data.get("received_at")
        session = input_data.get("_session")

        # 1. 查询工作类型列表 + 待审批建议列表
        work_types_list = await self._get_work_types_list(session)
        pending_suggestions_list = await self._get_pending_suggestions_list(session)

        # 2. 格式化收件时间
        if hasattr(received_at, "strftime"):
            received_at_str = received_at.strftime("%Y-%m-%d %H:%M")
        elif received_at:
            received_at_str = str(received_at)
        else:
            received_at_str = "Unknown"

        # 3. 渲染 user prompt 模板
        prompt = await render_prompt(
            "work_type_analyzer",
            work_types_list=work_types_list,
            pending_suggestions_list=pending_suggestions_list,
            sender=sender,
            subject=subject or "(No subject)",
            received_at=received_at_str,
            content=content[:5000],  # 限制长度
        )

        if not prompt:
            logger.error("[WorkTypeAnalyzer] Failed to load prompt, aborting analysis")
            state["error"] = "Prompt loading failed"
            state["output_data"] = self._empty_result(email_id, "Prompt loading failed")
            return state

        # 4. 设置 state
        # 直接将渲染后的 prompt 写入 messages（避免依赖 state["input"] 在节点间传播）
        state["input"] = prompt
        state["messages"] = [{"role": "user", "content": prompt}]
        state["output_data"] = {
            "email_id": email_id,
        }

        logger.info(f"[WorkTypeAnalyzer] 预处理完成: {email_id}")
        return state

    async def _think(self, state: AgentState) -> AgentState:
        """
        思考节点：调用 LLM 进行分析（覆盖以捕获响应元数据）

        BaseAgent._think() 丢弃了 response.model 和 response.usage，
        但需要 llm_model 返回给调用方，因此覆盖此方法。
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
            f"[WorkTypeAnalyzer] 思考 (迭代 {state['iterations']}), "
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
        state["output_data"] = output_data

        return state

    async def process_output(self, state: AgentState) -> dict:
        """
        处理输出：解析 LLM 返回的 JSON，合并预处理阶段的元数据
        """
        output_data = state.get("output_data", {})

        # 如果预处理就已经失败了（error 路径），output_data 已经是 _empty_result
        if state.get("error") and "matched_work_type" in output_data:
            return output_data

        # 解析 LLM 输出的 JSON
        raw_output = state.get("output", "")
        if raw_output:
            parsed = self._parse_response(raw_output)
        else:
            parsed = {}

        # 合并解析结果和预处理阶段的元数据
        result = {**parsed}
        result["email_id"] = output_data.get("email_id", "")
        result["llm_model"] = output_data.get("llm_model")

        logger.info(
            f"[WorkTypeAnalyzer] 分析完成: {result.get('email_id')}, "
            f"matched={result.get('matched_work_type', {}).get('code') if result.get('matched_work_type') else None}, "
            f"should_suggest={result.get('new_suggestion', {}).get('should_suggest')}"
        )
        return result

    # ========== run() 覆盖（后处理：创建建议） ==========

    async def run(
        self,
        input_text: str,
        *,
        input_data: Optional[dict] = None,
        **kwargs,
    ) -> AgentResult:
        """
        执行分析 + 后处理

        覆盖 BaseAgent.run() 以在图执行后处理建议创建：
        1. 执行 LangGraph 图（preprocess → think → output）
        2. 如果 LLM 建议新类型，创建 WorkTypeSuggestion 并启动 Temporal 审批流
        """
        if input_data is None:
            input_data = {
                "email_id": "",
                "sender": "",
                "subject": "",
                "content": input_text,
            }

        # 执行 LangGraph 图
        result = await super().run(input_text, input_data=input_data, **kwargs)

        # 后处理：如果建议新类型，创建建议
        if result.success and result.data.get("new_suggestion", {}).get("should_suggest"):
            session = input_data.get("_session")
            suggestion_id = await self.create_suggestion_if_needed(
                result=result.data,
                email_id=input_data.get("email_id", ""),
                trigger_content=input_text[:200],
                session=session,
            )
            result.data["suggestion_id"] = suggestion_id

        return result

    # ========== 便捷方法 ==========

    async def analyze(
        self,
        email_id: str,
        sender: str,
        subject: str,
        content: str,
        received_at: Optional[datetime] = None,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        """
        分析邮件的工作类型（便捷方法，兼容现有调用方）

        将参数打包为 input_data 并调用 BaseAgent.run()（不含建议创建）。
        返回分析结果字典（非 AgentResult）以兼容现有 API。

        注意：此方法不创建建议，调用方需自行调用 create_suggestion_if_needed()。

        Args:
            email_id: 邮件 ID
            sender: 发件人
            subject: 主题
            content: 邮件内容（已清洗）
            received_at: 收件时间
            session: 数据库会话

        Returns:
            dict: 分析结果
        """
        logger.info(f"[WorkTypeAnalyzer] 开始分析邮件: {email_id}")

        input_data = {
            "email_id": email_id,
            "sender": sender,
            "subject": subject,
            "content": content,
            "received_at": received_at,
            "_session": session,
        }

        # 调用 BaseAgent.run() 直接执行图（跳过 self.run() 的建议创建逻辑）
        result = await BaseAgent.run(
            self,
            f"分析邮件工作类型: {email_id}",
            input_data=input_data,
        )

        if result.success:
            return result.data
        else:
            return self._empty_result(email_id, result.error or "分析失败")

    # ========== 数据库查询 ==========

    async def _get_work_types_list(self, session: Optional[AsyncSession] = None) -> str:
        """
        获取当前所有启用的工作类型列表（格式化为 Prompt 可用的文本）
        """
        if session is None:
            async with async_session_maker() as session:
                return await self._get_work_types_list(session)

        # 查询所有启用的工作类型
        result = await session.execute(
            select(WorkType)
            .where(WorkType.is_active == True)
            .order_by(WorkType.level, WorkType.code)
        )
        work_types = list(result.scalars().all())

        if not work_types:
            return "（暂无工作类型，请根据邮件内容建议合适的类型）"

        # 格式化为层级结构
        lines = []
        for wt in work_types:
            indent = "  " * (wt.level - 1)
            keywords_str = ", ".join(wt.keywords) if wt.keywords else ""
            lines.append(
                f"{indent}- {wt.code} ({wt.name}): {wt.description}"
                f"{f' [关键词: {keywords_str}]' if keywords_str else ''}"
            )

        return "\n".join(lines)

    async def _get_pending_suggestions_list(self, session: Optional[AsyncSession] = None) -> str:
        """
        获取待审批和已拒绝的工作类型建议（格式化为 Prompt 可用的文本）

        让 LLM 知道哪些类型已经在审批中或已被拒绝，避免重复建议。
        """
        if session is None:
            async with async_session_maker() as session:
                return await self._get_pending_suggestions_list(session)

        result = await session.execute(
            select(WorkTypeSuggestion)
            .where(WorkTypeSuggestion.status.in_(["pending", "rejected"]))
            .order_by(WorkTypeSuggestion.status, WorkTypeSuggestion.created_at.desc())
        )
        suggestions = list(result.scalars().all())

        if not suggestions:
            return "（暂无待审批或已拒绝的建议）"

        lines = []
        for s in suggestions:
            keywords_str = ", ".join(s.suggested_keywords) if s.suggested_keywords else ""
            status_label = "待审批" if s.status == "pending" else "已拒绝"
            lines.append(
                f"- [{status_label}] {s.suggested_code} ({s.suggested_name}): {s.suggested_description}"
                f"{f' [关键词: {keywords_str}]' if keywords_str else ''}"
                f" [置信度: {s.confidence:.2f}]"
            )

        return "\n".join(lines)

    # ========== 建议创建 ==========

    async def create_suggestion_if_needed(
        self,
        result: dict,
        email_id: str,
        trigger_content: str,
        session: Optional[AsyncSession] = None,
    ) -> Optional[str]:
        """
        如果分析结果建议新类型，创建 WorkTypeSuggestion 并启动 Temporal 审批流

        Args:
            result: 分析结果
            email_id: 触发邮件 ID
            trigger_content: 触发内容摘要
            session: 数据库会话

        Returns:
            Optional[str]: 创建的 suggestion_id，如果不需要则返回 None
        """
        suggestion_data = result.get("new_suggestion", {})

        # 检查是否需要建议
        if not suggestion_data.get("should_suggest"):
            return None

        confidence = suggestion_data.get("confidence", 0)
        if confidence < self.SUGGESTION_CONFIDENCE_THRESHOLD:
            logger.info(
                f"[WorkTypeAnalyzer] 置信度 {confidence} 低于门槛 "
                f"{self.SUGGESTION_CONFIDENCE_THRESHOLD}，跳过建议"
            )
            return None

        suggested_code = suggestion_data.get("suggested_code")
        if not suggested_code:
            return None

        logger.info(f"[WorkTypeAnalyzer] 创建工作类型建议: {suggested_code}")

        if session is None:
            async with async_session_maker() as session:
                return await self._create_suggestion(
                    session, suggestion_data, email_id, trigger_content
                )

        return await self._create_suggestion(
            session, suggestion_data, email_id, trigger_content
        )

    async def _create_suggestion(
        self,
        session: AsyncSession,
        suggestion_data: dict,
        email_id: str,
        trigger_content: str,
    ) -> Optional[str]:
        """创建建议记录并启动审批流程"""
        from uuid import uuid4

        suggested_code = suggestion_data.get("suggested_code")
        suggested_parent_code = suggestion_data.get("suggested_parent_code")

        # 检查 code 是否已存在
        existing = await session.scalar(
            select(WorkType).where(WorkType.code == suggested_code)
        )
        if existing:
            logger.info(f"[WorkTypeAnalyzer] 工作类型已存在: {suggested_code}")
            return None

        # 检查是否已有相同 code 的待审批或已拒绝建议
        existing_suggestion = await session.scalar(
            select(WorkTypeSuggestion).where(
                WorkTypeSuggestion.suggested_code == suggested_code,
                WorkTypeSuggestion.status.in_(["pending", "rejected"]),
            )
        )
        if existing_suggestion:
            logger.info(
                f"[WorkTypeAnalyzer] 已有建议 ({existing_suggestion.status}): {suggested_code}"
            )
            return None

        # 确定父级
        parent_id = None
        level = 1
        if suggested_parent_code:
            parent = await session.scalar(
                select(WorkType).where(WorkType.code == suggested_parent_code)
            )
            if parent:
                parent_id = parent.id
                level = parent.level + 1

        # 创建建议
        suggestion = WorkTypeSuggestion(
            id=str(uuid4()),
            suggested_code=suggested_code,
            suggested_name=suggestion_data.get("suggested_name", suggested_code),
            suggested_description=suggestion_data.get("suggested_description", ""),
            suggested_parent_id=parent_id,
            suggested_parent_code=suggested_parent_code,
            suggested_level=level,
            suggested_examples=[],
            suggested_keywords=suggestion_data.get("suggested_keywords", []),
            confidence=suggestion_data.get("confidence", 0),
            reasoning=suggestion_data.get("reasoning", ""),
            trigger_email_id=email_id,
            trigger_content=trigger_content[:500],  # 限制长度
            status="pending",
        )

        session.add(suggestion)
        await session.flush()

        # 启动 Temporal 审批工作流
        try:
            from app.temporal import start_suggestion_workflow
            workflow_id = await start_suggestion_workflow(suggestion.id)
            suggestion.workflow_id = workflow_id
            logger.info(
                f"[WorkTypeAnalyzer] 审批工作流已启动: "
                f"suggestion={suggestion.id}, workflow={workflow_id}"
            )
        except Exception as e:
            logger.warning(
                f"[WorkTypeAnalyzer] 启动审批工作流失败（建议仍可手动审批）: {e}"
            )

        await session.commit()
        return suggestion.id

    # ========== 辅助方法 ==========

    def _parse_response(self, content: str) -> dict:
        """
        解析 LLM 返回的 JSON（三级回退策略）

        1. 直接 json.loads
        2. 从 ```json ``` 代码块提取
        3. 找第一个 { 到最后一个 }
        """
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

        logger.warning(f"[WorkTypeAnalyzer] 无法解析 LLM 返回: {content[:200]}...")
        return {"parse_error": True, "raw_response": content[:500]}

    def _empty_result(self, email_id: str, error: str) -> dict:
        """返回空结果（错误降级）"""
        return {
            "email_id": email_id,
            "matched_work_type": None,
            "new_suggestion": {"should_suggest": False},
            "error": error,
        }


# 全局单例
work_type_analyzer = WorkTypeAnalyzerAgent()
