# app/agents/work_type_analyzer.py
# 工作类型分析 Agent
#
# 功能说明：
# 1. 使用 LLM 分析邮件内容
# 2. 匹配现有的工作类型
# 3. 识别新的工作类型并建议添加
# 4. 与 EmailSummarizer 并行执行

import json
import asyncio
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.agents.base import BaseAgent, AgentState, AgentResult
from app.agents.registry import register_agent
from app.models.work_type import WorkType, WorkTypeSuggestion

logger = get_logger(__name__)


# 分析 Prompt 模板
WORK_TYPE_ANALYZER_PROMPT = """你是一个工作类型分类专家。请根据邮件内容判断其工作类型。

## 当前系统支持的工作类型

{work_types_list}

## 邮件信息
- 发件人: {sender}
- 主题: {subject}
- 收件时间: {received_at}

## 邮件正文
{content}

## 分析要求

请以 JSON 格式返回分析结果：

```json
{{
    "matched_work_type": {{
        "code": "匹配的工作类型代码，如 ORDER_NEW，如果无法匹配则为 null",
        "confidence": 0.0-1.0,
        "reason": "匹配原因说明"
    }},

    "new_suggestion": {{
        "should_suggest": false,
        "suggested_code": "建议的新类型代码（全大写英文+下划线），如果不建议则为 null",
        "suggested_name": "建议的中文名称",
        "suggested_description": "建议的描述",
        "suggested_parent_code": "建议的父级代码，如 ORDER，如果是顶级则为 null",
        "suggested_keywords": ["关键词1", "关键词2"],
        "confidence": 0.0-1.0,
        "reasoning": "建议添加新类型的原因"
    }}
}}
```

## 注意事项
1. 优先匹配现有类型，只有在确实无法匹配且内容有明显特征时才建议新类型
2. 新类型代码必须全大写英文，如果有父级则以父级代码开头（如 ORDER_URGENT）
3. 建议新类型的置信度门槛是 0.6，低于此值不要建议
4. 只返回 JSON，不要有其他内容
"""


@register_agent
class WorkTypeAnalyzerAgent(BaseAgent):
    """
    工作类型分析 Agent

    功能：
    - 分析邮件内容判断工作类型
    - 匹配现有工作类型
    - 识别并建议新的工作类型
    - 支持 Temporal 审批流程

    与 EmailSummarizer 并行执行。
    """

    name = "work_type_analyzer"
    description = "分析邮件内容判断工作类型，匹配现有类型或建议新类型"
    prompt_name = "work_type_analyzer"
    tools = []
    max_iterations = 3

    # 建议新类型的置信度门槛
    SUGGESTION_CONFIDENCE_THRESHOLD = 0.6

    async def _get_work_types_list(self, session: Optional[AsyncSession] = None) -> str:
        """
        获取当前所有启用的工作类型列表（格式化为 Prompt 可用的文本）

        Args:
            session: 数据库会话

        Returns:
            str: 格式化的工作类型列表
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
        分析邮件的工作类型

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

        # 1. 获取工作类型列表
        work_types_list = await self._get_work_types_list(session)

        # 2. 构建 Prompt
        prompt = WORK_TYPE_ANALYZER_PROMPT.format(
            work_types_list=work_types_list,
            sender=sender,
            subject=subject or "(无主题)",
            received_at=received_at.strftime("%Y-%m-%d %H:%M") if received_at else "未知",
            content=content[:5000],  # 限制长度
        )

        # 3. 调用 LLM
        try:
            model = self._get_model()
            response = await self.llm.chat(
                message=prompt,
                system="你是一个工作类型分类专家。请严格按照要求的 JSON 格式返回分析结果。",
                model=model,
            )

            # 4. 解析结果
            result = self._parse_response(response.content)
            result["email_id"] = email_id
            result["llm_model"] = model

            logger.info(
                f"[WorkTypeAnalyzer] 分析完成: {email_id}, "
                f"matched={result.get('matched_work_type', {}).get('code')}, "
                f"should_suggest={result.get('new_suggestion', {}).get('should_suggest')}"
            )

            return result

        except Exception as e:
            logger.error(f"[WorkTypeAnalyzer] 分析失败: {email_id}, {e}")
            return self._empty_result(email_id, str(e))

    def _parse_response(self, content: str) -> dict:
        """解析 LLM 返回的 JSON"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        import re
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
        """返回空结果"""
        return {
            "email_id": email_id,
            "matched_work_type": None,
            "new_suggestion": {"should_suggest": False},
            "error": error,
        }

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

        # 检查是否已有相同的待审批建议
        existing_suggestion = await session.scalar(
            select(WorkTypeSuggestion).where(
                WorkTypeSuggestion.suggested_code == suggested_code,
                WorkTypeSuggestion.status == "pending",
            )
        )
        if existing_suggestion:
            logger.info(f"[WorkTypeAnalyzer] 已有待审批建议: {suggested_code}")
            return existing_suggestion.id

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

    async def process_output(self, state: AgentState) -> dict:
        """处理输出（BaseAgent 要求实现）"""
        return state.get("output_data", {})

    async def run(
        self,
        input_text: str,
        *,
        input_data: Optional[dict] = None,
        **kwargs,
    ) -> AgentResult:
        """
        执行分析（兼容 BaseAgent 接口）

        可以通过 input_data 传递邮件信息：
        {
            "email_id": "...",
            "sender": "...",
            "subject": "...",
            "content": "...",  # 已清洗的邮件内容
            "received_at": datetime,
        }
        """
        if not input_data:
            # 如果没有 input_data，直接用 input_text
            input_data = {
                "email_id": "",
                "sender": "",
                "subject": "",
                "content": input_text,
            }

        result = await self.analyze(
            email_id=input_data.get("email_id", ""),
            sender=input_data.get("sender", ""),
            subject=input_data.get("subject", ""),
            content=input_data.get("content") or input_text,
            received_at=input_data.get("received_at"),
            session=kwargs.get("db"),
        )

        # 如果需要，创建建议
        if result.get("new_suggestion", {}).get("should_suggest"):
            suggestion_id = await self.create_suggestion_if_needed(
                result=result,
                email_id=input_data.get("email_id", ""),
                trigger_content=input_text[:200],
                session=kwargs.get("db"),
            )
            result["suggestion_id"] = suggestion_id

        return AgentResult(
            success="error" not in result,
            output=result.get("matched_work_type", {}).get("code", ""),
            data=result,
        )


# 全局单例
work_type_analyzer = WorkTypeAnalyzerAgent()
