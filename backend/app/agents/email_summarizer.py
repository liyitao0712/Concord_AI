# app/agents/email_summarizer.py
# 邮件摘要分析 Agent
#
# 功能说明：
# 1. 使用 LLM 分析邮件内容
# 2. 提取摘要、意图、发件方信息、业务信息等
# 3. 针对外贸场景优化
# 4. 先调用 email_cleaner 工具清洗邮件正文

import json
from typing import Optional
from datetime import datetime

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

    使用 LLM 分析邮件内容，提取：
    - 摘要和关键要点
    - 发件方身份（客户/供应商）
    - 意图分类
    - 产品信息、金额、贸易条款
    - 处理建议

    针对外贸场景优化。
    """

    name = "email_summarizer"
    description = "邮件摘要分析，提取意图、产品、金额等业务信息"
    prompt_name = "email_summarizer"  # 可从数据库加载 prompt
    tools = ["clean_email"]  # 使用邮件清洗工具
    max_iterations = 3

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
        分析邮件

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

        # 1. 清洗邮件正文（保留引用历史和签名，增加 token 限制）
        cleaned_content = await clean_email_content(
            body_text=body_text or "",
            body_html=body_html or "",
            max_length=10000,  # 增加到 10000 字符
            remove_signature=False,  # 保留签名（否则签名后的引用也会被删）
            remove_quotes=False,  # 保留引用历史邮件
        )

        if not cleaned_content:
            logger.warning(f"[EmailSummarizer] 邮件正文为空: {email_id}")
            return self._empty_result(email_id, "邮件正文为空")

        # 2. 加载 system prompt（优先从数据库，fallback 到 defaults.py）
        system_prompt = await get_prompt("email_summarizer_system")
        if not system_prompt:
            system_prompt = (
                "You are a professional foreign trade email analysis assistant. "
                "Return analysis results strictly in the requested JSON format."
            )

        # 3. 构建 user prompt（优先从数据库加载，fallback 到 defaults.py）
        prompt = await render_prompt(
            "email_summarizer",
            sender=sender,
            sender_name=sender_name or "",
            subject=subject or "(No subject)",
            received_at=received_at.strftime("%Y-%m-%d %H:%M") if received_at else "Unknown",
            content=cleaned_content,
        )

        if not prompt:
            logger.error("[EmailSummarizer] Failed to load prompt, aborting analysis")
            return self._empty_result(email_id, "Prompt loading failed")

        # 4. 调用 LLM
        try:
            model = self._get_model()
            response = await self.llm.chat(
                message=prompt,
                system=system_prompt,
                model=model,
            )

            # 5. 解析结果
            logger.info(f"[EmailSummarizer] LLM 原始返回: {response.content[:500]}")

            result = self._parse_response(response.content)

            logger.info(f"[EmailSummarizer] 解析结果: intent={result.get('intent')}, summary={result.get('summary', '')[:50]}")

            result["email_id"] = email_id
            result["cleaned_content"] = cleaned_content
            result["llm_model"] = model
            result["token_used"] = getattr(response, "usage", {}).get("total_tokens")

            logger.info(f"[EmailSummarizer] 分析完成: {email_id}, intent={result.get('intent')}")
            return result

        except Exception as e:
            logger.error(f"[EmailSummarizer] 分析失败: {email_id}, {e}")
            return self._empty_result(email_id, str(e))

    def _parse_response(self, content: str) -> dict:
        """
        解析 LLM 返回的 JSON

        Args:
            content: LLM 返回的文本

        Returns:
            dict: 解析后的结果
        """
        # 尝试提取 JSON
        try:
            # 先尝试直接解析
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

        logger.warning(f"[EmailSummarizer] 无法解析 LLM 返回: {content[:200]}...")
        return {"parse_error": True, "raw_response": content[:500]}

    def _empty_result(self, email_id: str, error: str) -> dict:
        """返回空结果"""
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
            "sender_name": "...",
            "subject": "...",
            "body_text": "...",
            "body_html": "...",
            "received_at": "...",
        }
        """
        if not input_data:
            return AgentResult(
                success=False,
                output="",
                error="需要通过 input_data 传递邮件信息",
            )

        result = await self.analyze(
            email_id=input_data.get("email_id", ""),
            sender=input_data.get("sender", ""),
            sender_name=input_data.get("sender_name"),
            subject=input_data.get("subject", ""),
            body_text=input_data.get("body_text", ""),
            body_html=input_data.get("body_html"),
            received_at=input_data.get("received_at"),
        )

        return AgentResult(
            success="error" not in result,
            output=result.get("summary", ""),
            data=result,
        )


# 全局单例
email_summarizer = EmailSummarizerAgent()
