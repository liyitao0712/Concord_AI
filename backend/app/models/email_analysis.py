# app/models/email_analysis.py
# 邮件分析结果模型
#
# 功能说明：
# 1. 存储 EmailSummarizerAgent 分析结果
# 2. 支持外贸场景：客户/供应商识别、产品、金额、贸易条款等
# 3. 关联 email_raw_messages 表

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey, Float, Date, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class EmailAnalysis(Base):
    """
    邮件分析结果

    存储 AI 对邮件的分析结果，包括摘要、意图、发件方信息、业务信息等。
    针对外贸场景优化，支持客户/供应商识别、产品提取、金额识别等。
    """
    __tablename__ = "email_analyses"

    # ==================== 基础关联 ====================
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    email_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("email_raw_messages.id", ondelete="CASCADE"),
        index=True,
        comment="关联的邮件 ID",
    )

    # ==================== 摘要与翻译 ====================
    summary: Mapped[str] = mapped_column(
        Text,
        comment="一句话摘要",
    )

    key_points: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="关键要点列表 ['要点1', '要点2']",
    )

    original_language: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="原文语言 en/zh/es/ar/ru 等",
    )

    # ==================== 发件方信息 ====================
    sender_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="发件方类型: customer/supplier/freight/bank/other",
    )

    sender_company: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="公司名称",
    )

    sender_country: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="国家/地区",
    )

    is_new_contact: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="是否新联系人（首次来信）",
    )

    # ==================== 意图分类 ====================
    intent: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="主意图: inquiry/quotation/order/payment/shipment/complaint 等",
    )

    intent_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="意图置信度 0-1",
    )

    urgency: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="紧急程度: urgent/high/medium/low",
    )

    sentiment: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="情感倾向: positive/neutral/negative",
    )

    # ==================== 业务信息 ====================
    products: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="产品列表 [{name, specs, quantity, unit, target_price}]",
    )

    amounts: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="金额列表 [{value, currency, context}]",
    )

    trade_terms: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="贸易条款 {incoterm, payment_terms, destination}",
    )

    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="截止/交期要求",
    )

    # ==================== 跟进建议 ====================
    questions: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="对方提出的问题列表",
    )

    action_required: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="需要我方做的事情列表",
    )

    suggested_reply: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="建议回复要点",
    )

    priority: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="处理优先级: p0/p1/p2/p3",
    )

    # ==================== 分析元数据 ====================
    cleaned_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="清洗后的邮件正文（用于分析的内容）",
    )

    llm_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="使用的 LLM 模型",
    )

    token_used: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="消耗的 token 数",
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="创建时间",
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "email_id": self.email_id,
            "summary": self.summary,
            "key_points": self.key_points,
            "original_language": self.original_language,
            "sender_type": self.sender_type,
            "sender_company": self.sender_company,
            "sender_country": self.sender_country,
            "is_new_contact": self.is_new_contact,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "urgency": self.urgency,
            "sentiment": self.sentiment,
            "products": self.products,
            "amounts": self.amounts,
            "trade_terms": self.trade_terms,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "questions": self.questions,
            "action_required": self.action_required,
            "suggested_reply": self.suggested_reply,
            "priority": self.priority,
            "llm_model": self.llm_model,
            "token_used": self.token_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
