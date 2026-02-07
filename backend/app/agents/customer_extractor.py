# app/agents/customer_extractor.py
# 客户提取 Agent
#
# 从邮件中提取客户和联系人信息，创建待审批的客户建议。
# 支持两种场景：
# 1. 新客户 + 新联系人（new_customer）
# 2. 已有客户的新联系人（new_contact）
#
# 执行图：preprocess → think → output → END
# run() 后处理：如需创建建议，写入 CustomerSuggestion + 启动 Temporal 审批流

import json
import re
from typing import Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, END

from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.agents.base import BaseAgent, AgentState, AgentResult
from app.agents.registry import register_agent
from app.models.customer import Customer, Contact
from app.models.customer_suggestion import CustomerSuggestion
from app.llm.prompts import render_prompt, get_prompt

logger = get_logger(__name__)


# 免费邮箱域名列表（不作为公司标识）
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
    "icloud.com", "aol.com", "mail.com", "protonmail.com", "zoho.com",
    "yandex.com", "gmx.com", "163.com", "126.com", "qq.com",
    "sina.com", "foxmail.com", "yeah.net", "msn.com",
}


@register_agent
class CustomerExtractorAgent(BaseAgent):
    """
    客户提取 Agent

    从邮件中提取客户和联系人信息：
    - 利用 EmailSummarizer 的分析结果（sender_company, sender_country 等）
    - 调 LLM 提取详细联系人信息（姓名、职位、部门、电话等）
    - 查重：邮箱域名 + 公司名模糊匹配
    - 创建 CustomerSuggestion 记录 + 启动 Temporal 审批工作流

    执行图：preprocess → think → output → END
    """

    name = "customer_extractor"
    display_name = "客户信息提取器"
    description = "从邮件中提取客户和联系人信息，创建待审批的客户建议"
    prompt_name = "customer_extractor"
    tools = []
    max_iterations = 1  # 单次 LLM 调用

    # ========== Prompt 加载 ==========

    async def _get_system_prompt(self) -> str:
        """获取系统提示（支持 {{company_name}} 等系统变量渲染）"""
        system_prompt = await render_prompt("customer_extractor_system")
        if system_prompt:
            return system_prompt
        return (
            "You are a customer information extraction expert. "
            "Return results strictly in the requested JSON format."
        )

    # ========== Graph 构建 ==========

    async def _build_graph(self) -> StateGraph:
        """构建执行图：preprocess → think → output"""
        graph = StateGraph(AgentState)

        graph.add_node("preprocess", self._preprocess)
        graph.add_node("think", self._think)
        graph.add_node("execute_tools", self._execute_tools)
        graph.add_node("output", self._output)

        graph.set_entry_point("preprocess")

        graph.add_conditional_edges(
            "preprocess",
            self._should_continue_after_preprocess,
            {
                "continue": "think",
                "skip": "output",  # 无需提取（非客户邮件等）
                "error": "output",
            },
        )

        graph.add_conditional_edges(
            "think",
            self._should_execute_tools,
            {
                "execute": "execute_tools",
                "output": "output",
            },
        )

        graph.add_edge("execute_tools", "think")
        graph.add_edge("output", END)

        return graph.compile()

    def _should_continue_after_preprocess(self, state: AgentState) -> str:
        """预处理后的路由"""
        if state.get("error"):
            return "error"
        # 如果预处理标记跳过（非客户邮件、免费邮箱域名等）
        output_data = state.get("output_data", {})
        if output_data.get("skip_extraction"):
            return "skip"
        return "continue"

    # ========== 节点方法 ==========

    async def _preprocess(self, state: AgentState) -> AgentState:
        """
        预处理节点：
        1. 提取邮箱域名
        2. 检查是否应跳过（免费邮箱、非客户类型）
        3. 查询已有客户和 pending 建议
        4. 渲染 prompt
        """
        input_data = state.get("input_data", {})

        email_id = input_data.get("email_id", "")
        sender = input_data.get("sender", "")
        sender_name = input_data.get("sender_name", "")
        subject = input_data.get("subject", "")
        content = input_data.get("content", "")
        email_analysis = input_data.get("email_analysis") or {}
        session = input_data.get("_session")

        # 1. 提取邮箱域名
        email_domain = self._extract_domain(sender)

        # 2. 检查是否应跳过
        skip_reason = self._should_skip(email_domain, email_analysis)
        if skip_reason:
            logger.info(f"[CustomerExtractor] 跳过提取: {skip_reason}")
            state["output_data"] = {
                "email_id": email_id,
                "skip_extraction": True,
                "skip_reason": skip_reason,
                "is_new_customer": False,
            }
            return state

        # 3. 查询已有客户列表和 pending 建议（用于 prompt 上下文）
        existing_customers_text = await self._get_existing_customers_context(
            email_domain, session
        )
        pending_suggestions_text = await self._get_pending_suggestions_context(session)

        # 4. 构建 email_analysis 上下文
        analysis_context = self._format_analysis_context(email_analysis)

        # 5. 渲染 prompt
        prompt = await render_prompt(
            "customer_extractor",
            sender=sender,
            sender_name=sender_name or "",
            subject=subject or "(No subject)",
            content=content[:5000],
            email_analysis_context=analysis_context,
            existing_customers=existing_customers_text,
            pending_suggestions=pending_suggestions_text,
        )

        if not prompt:
            logger.error("[CustomerExtractor] Failed to load prompt")
            state["error"] = "Prompt loading failed"
            state["output_data"] = self._empty_result(email_id, "Prompt loading failed")
            return state

        state["input"] = prompt
        state["output_data"] = {
            "email_id": email_id,
            "email_domain": email_domain,
        }

        logger.info(f"[CustomerExtractor] 预处理完成: {email_id}, domain={email_domain}")
        return state

    async def _think(self, state: AgentState) -> AgentState:
        """思考节点：调用 LLM"""
        state["iterations"] = state.get("iterations", 0) + 1

        if state["iterations"] > self.max_iterations:
            state["error"] = f"超过最大迭代次数 {self.max_iterations}"
            return state

        messages = state.get("messages", [])
        if not messages:
            messages.append({
                "role": "user",
                "content": state["input"],
            })

        system_prompt = await self._get_system_prompt()
        model = self._get_model()

        logger.debug(f"[CustomerExtractor] 思考 (迭代 {state['iterations']})")

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

        output_data = state.get("output_data", {})
        output_data["llm_model"] = model
        state["output_data"] = output_data

        return state

    async def process_output(self, state: AgentState) -> dict:
        """处理输出：解析 LLM 返回的 JSON"""
        output_data = state.get("output_data", {})

        # 跳过提取的场景，直接返回
        if output_data.get("skip_extraction"):
            return output_data

        # 解析 LLM 输出
        raw_output = state.get("output", "")
        if raw_output:
            parsed = self._parse_response(raw_output)
        else:
            parsed = {}

        result = {**parsed}
        result["email_id"] = output_data.get("email_id", "")
        result["email_domain"] = output_data.get("email_domain")
        result["llm_model"] = output_data.get("llm_model")

        logger.info(
            f"[CustomerExtractor] 分析完成: {result.get('email_id')}, "
            f"is_new_customer={result.get('is_new_customer')}, "
            f"confidence={result.get('confidence')}"
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
        执行提取 + 后处理

        1. 执行 LangGraph 图（preprocess → think → output）
        2. 如果检测到新客户/新联系人，创建 CustomerSuggestion + Temporal 审批流
        """
        if input_data is None:
            input_data = {
                "email_id": "",
                "sender": "",
                "subject": "",
                "content": input_text,
            }

        result = await super().run(input_text, input_data=input_data, **kwargs)

        # 后处理：创建建议
        if result.success and not result.data.get("skip_extraction"):
            session = input_data.get("_session")
            suggestion_id = await self.create_suggestion_if_needed(
                result=result.data,
                email_id=input_data.get("email_id", ""),
                trigger_content=f"{input_data.get('subject', '')} - {input_text[:200]}",
                session=session,
            )
            result.data["suggestion_id"] = suggestion_id

        return result

    # ========== 便捷方法 ==========

    async def analyze(
        self,
        email_id: str,
        sender: str,
        sender_name: Optional[str],
        subject: str,
        content: str,
        email_analysis: Optional[dict] = None,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        """
        提取客户信息（便捷方法）

        Args:
            email_id: 邮件 ID
            sender: 发件人邮箱
            sender_name: 发件人显示名
            subject: 主题
            content: 邮件内容（已清洗）
            email_analysis: EmailSummarizer 的分析结果（可选，用于复用）
            session: 数据库会话

        Returns:
            dict: 提取结果
        """
        logger.info(f"[CustomerExtractor] 开始分析邮件: {email_id}")

        input_data = {
            "email_id": email_id,
            "sender": sender,
            "sender_name": sender_name,
            "subject": subject,
            "content": content,
            "email_analysis": email_analysis,
            "_session": session,
        }

        result = await self.run(
            f"提取客户信息: {email_id}",
            input_data=input_data,
        )

        if result.success:
            return result.data
        else:
            return self._empty_result(email_id, result.error or "提取失败")

    # ========== 数据库查询 ==========

    async def _get_existing_customers_context(
        self,
        email_domain: Optional[str],
        session: Optional[AsyncSession] = None,
    ) -> str:
        """获取已有客户列表（格式化为 Prompt 上下文）"""
        if session is None:
            async with async_session_maker() as session:
                return await self._get_existing_customers_context(email_domain, session)

        # 查询最近 100 个活跃客户
        result = await session.execute(
            select(Customer)
            .where(Customer.is_active == True)
            .order_by(Customer.created_at.desc())
            .limit(100)
        )
        customers = list(result.scalars().all())

        if not customers:
            return "（暂无已有客户）"

        lines = []
        for c in customers:
            domain_info = ""
            if c.email and "@" in c.email:
                domain_info = f" [域名: {c.email.split('@')[1]}]"
            lines.append(
                f"- {c.name}"
                f"{f' ({c.short_name})' if c.short_name else ''}"
                f"{f' - {c.country}' if c.country else ''}"
                f"{domain_info}"
            )

        return "\n".join(lines)

    async def _get_pending_suggestions_context(
        self,
        session: Optional[AsyncSession] = None,
    ) -> str:
        """获取待审批的客户建议列表（避免重复建议）"""
        if session is None:
            async with async_session_maker() as session:
                return await self._get_pending_suggestions_context(session)

        result = await session.execute(
            select(CustomerSuggestion)
            .where(CustomerSuggestion.status == "pending")
            .order_by(CustomerSuggestion.created_at.desc())
            .limit(50)
        )
        suggestions = list(result.scalars().all())

        if not suggestions:
            return "（暂无待审批建议）"

        lines = []
        for s in suggestions:
            lines.append(
                f"- [待审批] {s.suggested_company_name}"
                f"{f' ({s.suggested_email_domain})' if s.suggested_email_domain else ''}"
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
        如果分析结果需要创建客户建议，创建 CustomerSuggestion + Temporal 审批流

        Returns:
            Optional[str]: suggestion_id，不需要创建则返回 None
        """
        # AI 判断不需要创建
        if not result.get("is_new_customer") and not result.get("matched_existing_customer"):
            return None

        confidence = result.get("confidence", 0)
        company_data = result.get("company", {})
        if not company_data or not company_data.get("name"):
            return None

        email_domain = result.get("email_domain")

        if session is None:
            async with async_session_maker() as session:
                return await self._create_suggestion(
                    session, result, email_id, trigger_content, email_domain
                )

        return await self._create_suggestion(
            session, result, email_id, trigger_content, email_domain
        )

    async def _create_suggestion(
        self,
        session: AsyncSession,
        result: dict,
        email_id: str,
        trigger_content: str,
        email_domain: Optional[str],
    ) -> Optional[str]:
        """创建建议记录并启动审批流程"""
        company_data = result.get("company", {})
        contact_data = result.get("contact", {})
        matched_customer_id = result.get("matched_existing_customer")

        # 查重：同域名是否已有 pending 建议
        if email_domain:
            existing_suggestion = await session.scalar(
                select(CustomerSuggestion).where(
                    CustomerSuggestion.email_domain == email_domain,
                    CustomerSuggestion.status == "pending",
                )
            )
            if existing_suggestion:
                logger.info(
                    f"[CustomerExtractor] 已有待审批建议 (domain={email_domain}): "
                    f"{existing_suggestion.id}"
                )
                return None

        # 判断类型
        if matched_customer_id:
            suggestion_type = "new_contact"
        else:
            suggestion_type = "new_customer"

        # 创建建议
        suggestion = CustomerSuggestion(
            id=str(uuid4()),
            suggestion_type=suggestion_type,
            suggested_company_name=company_data.get("name", ""),
            suggested_short_name=company_data.get("short_name"),
            suggested_country=company_data.get("country"),
            suggested_region=company_data.get("region"),
            suggested_industry=company_data.get("industry"),
            suggested_website=company_data.get("website"),
            suggested_email_domain=email_domain,
            suggested_customer_level="potential",
            suggested_tags=result.get("suggested_tags", []),
            suggested_contact_name=contact_data.get("name"),
            suggested_contact_email=contact_data.get("email"),
            suggested_contact_title=contact_data.get("title"),
            suggested_contact_phone=contact_data.get("phone"),
            suggested_contact_department=contact_data.get("department"),
            confidence=result.get("confidence", 0),
            reasoning=result.get("reasoning"),
            sender_type=result.get("sender_type"),
            trigger_email_id=email_id,
            trigger_content=trigger_content[:500],
            trigger_source="email",
            email_domain=email_domain,
            matched_customer_id=matched_customer_id,
            status="pending",
        )

        session.add(suggestion)
        await session.flush()

        # 启动 Temporal 审批工作流
        try:
            from app.temporal import start_customer_approval_workflow
            workflow_id = await start_customer_approval_workflow(suggestion.id)
            suggestion.workflow_id = workflow_id
            logger.info(
                f"[CustomerExtractor] 审批工作流已启动: "
                f"suggestion={suggestion.id}, workflow={workflow_id}"
            )
        except Exception as e:
            logger.warning(
                f"[CustomerExtractor] 启动审批工作流失败（建议仍可手动审批）: {e}"
            )

        await session.commit()
        return suggestion.id

    # ========== 辅助方法 ==========

    @staticmethod
    def _extract_domain(email: str) -> Optional[str]:
        """从邮箱地址提取域名"""
        if not email or "@" not in email:
            return None
        return email.split("@")[1].lower().strip()

    @staticmethod
    def _should_skip(email_domain: Optional[str], email_analysis: dict) -> Optional[str]:
        """检查是否应跳过提取，返回跳过原因或 None"""
        # 非客户类型跳过
        sender_type = email_analysis.get("sender_type")
        if sender_type and sender_type not in ("customer", "other", None):
            return f"sender_type={sender_type}，非客户类型"

        # 免费邮箱域名跳过（但仍可从邮件签名中提取）
        if email_domain and email_domain in FREE_EMAIL_DOMAINS:
            return f"免费邮箱域名: {email_domain}"

        return None

    @staticmethod
    def _format_analysis_context(email_analysis: dict) -> str:
        """将 EmailSummarizer 分析结果格式化为上下文文本"""
        if not email_analysis:
            return "（无预分析结果）"

        lines = []
        if email_analysis.get("sender_company"):
            lines.append(f"- 发件人公司: {email_analysis['sender_company']}")
        if email_analysis.get("sender_country"):
            lines.append(f"- 发件人国家: {email_analysis['sender_country']}")
        if email_analysis.get("sender_type"):
            lines.append(f"- 发件人类型: {email_analysis['sender_type']}")
        if email_analysis.get("is_new_contact") is not None:
            lines.append(f"- 是否新联系人: {email_analysis['is_new_contact']}")
        if email_analysis.get("intent"):
            lines.append(f"- 邮件意图: {email_analysis['intent']}")
        if email_analysis.get("products"):
            products = email_analysis["products"]
            product_names = [p.get("name", "") for p in products if p.get("name")]
            if product_names:
                lines.append(f"- 涉及产品: {', '.join(product_names)}")

        return "\n".join(lines) if lines else "（无预分析结果）"

    def _parse_response(self, content: str) -> dict:
        """解析 LLM 返回的 JSON（三级回退策略）"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass

        logger.warning(f"[CustomerExtractor] 无法解析 LLM 返回: {content[:200]}...")
        return {"parse_error": True, "raw_response": content[:500]}

    def _empty_result(self, email_id: str, error: str) -> dict:
        """返回空结果"""
        return {
            "email_id": email_id,
            "is_new_customer": False,
            "skip_extraction": True,
            "error": error,
        }


# 全局单例
customer_extractor = CustomerExtractorAgent()
