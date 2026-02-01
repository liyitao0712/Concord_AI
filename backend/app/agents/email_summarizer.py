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

logger = get_logger(__name__)


# 分析 Prompt 模板
SUMMARIZER_PROMPT = """你是一个专业的外贸邮件分析助手。请分析以下邮件内容，提取关键信息。

## 邮件信息
- 发件人: {sender} ({sender_name})
- 主题: {subject}
- 收件时间: {received_at}

## 邮件正文
{content}

## 分析要求

请以 JSON 格式返回分析结果，包含以下字段：

```json
{{
    "summary": "一句话总结邮件核心内容（中文，不超过100字）",

    "key_points": ["关键要点1", "关键要点2", "关键要点3"],

    "original_language": "邮件原文语言代码，如 en/zh/es/ar/ru/de/fr/ja/ko 等",

    "sender_type": "发件方类型: customer(客户)/supplier(供应商)/freight(货代)/bank(银行)/other(其他)",

    "sender_company": "发件方公司名称，如无法识别则为 null",

    "sender_country": "发件方国家/地区，如无法识别则为 null",

    "is_new_contact": "是否像是新联系人（首次询盘/自我介绍）: true/false/null",

    "intent": "主要意图，选择最匹配的一项:
        - inquiry: 询价/询盘
        - quotation: 报价/还价
        - order: 下单/订单确认
        - order_change: 订单修改/取消
        - payment: 付款/汇款通知
        - shipment: 发货/物流跟踪
        - sample: 样品请求
        - complaint: 投诉/质量问题
        - after_sales: 售后服务
        - negotiation: 价格谈判
        - follow_up: 跟进/催促
        - introduction: 公司/产品介绍
        - general: 一般沟通
        - spam: 垃圾邮件/营销
        - other: 其他",

    "intent_confidence": "意图判断的置信度 0.0-1.0",

    "urgency": "紧急程度: urgent(紧急)/high(较高)/medium(一般)/low(较低)",

    "sentiment": "情感倾向: positive(积极)/neutral(中性)/negative(消极)",

    "products": [
        {{
            "name": "产品名称",
            "specs": "规格描述",
            "quantity": 数量(数字),
            "unit": "单位",
            "target_price": 目标价格(数字，可选)
        }}
    ],

    "amounts": [
        {{
            "value": 金额数值,
            "currency": "货币代码 USD/EUR/CNY 等",
            "context": "金额上下文说明"
        }}
    ],

    "trade_terms": {{
        "incoterm": "贸易术语 FOB/CIF/EXW/DDP 等，如未提及则为 null",
        "payment_terms": "付款方式 T/T/L/C/D/P 等，如未提及则为 null",
        "destination": "目的地/目的港，如未提及则为 null"
    }},

    "deadline": "截止日期或交期要求，ISO 格式如 2024-03-15，如无则为 null",

    "questions": ["对方提出的问题1", "对方提出的问题2"],

    "action_required": ["需要我方做的事情1", "需要我方做的事情2"],

    "suggested_reply": "建议的回复要点（简洁的中文说明）",

    "priority": "处理优先级: p0(立即处理)/p1(今日处理)/p2(本周处理)/p3(可延后)"
}}
```

## 注意事项
1. 所有字段都要填写，无法识别的填 null 或空数组 []
2. summary 必须用中文，简洁明了
3. 仔细识别产品信息、金额、贸易条款
4. 根据邮件内容判断紧急程度和优先级
5. 只返回 JSON，不要有其他内容
"""


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

        # 2. 构建 prompt
        prompt = SUMMARIZER_PROMPT.format(
            sender=sender,
            sender_name=sender_name or "",
            subject=subject or "(无主题)",
            received_at=received_at.strftime("%Y-%m-%d %H:%M") if received_at else "未知",
            content=cleaned_content,
        )

        # 3. 调用 LLM
        try:
            model = self._get_model()
            response = await self.llm.chat(
                message=prompt,
                system="你是一个专业的外贸邮件分析助手。请严格按照要求的 JSON 格式返回分析结果。",
                model=model,
            )

            # 4. 解析结果
            # DEBUG: 打印 LLM 原始返回（前 500 字符）
            logger.info(f"[EmailSummarizer] LLM 原始返回: {response.content[:500]}")

            result = self._parse_response(response.content)

            # DEBUG: 打印解析后的结果
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
