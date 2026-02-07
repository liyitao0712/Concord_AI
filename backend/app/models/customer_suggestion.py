# app/models/customer_suggestion.py
# 客户建议模型
#
# 功能说明：
# CustomerSuggestion - AI 从邮件中提取的客户/联系人建议，待人工审批
#
# 支持两种场景：
# 1. suggestion_type = "new_customer": 新客户 + 新联系人
# 2. suggestion_type = "new_contact": 已有客户的新联系人
#
# 审批流程（通过 Temporal Workflow）：
# 1. CustomerExtractorAgent 提取客户信息 → 保存到此表（status=pending）
# 2. 启动 CustomerApprovalWorkflow
# 3. 通知管理员审批
# 4. 管理员批准 → 创建 Customer + Contact 记录
#    管理员拒绝 → 标记为 rejected
#
# 使用方法：
#   from app.models.customer_suggestion import CustomerSuggestion

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, Boolean, Float, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CustomerSuggestion(Base):
    """
    客户建议表

    当 CustomerExtractorAgent 从邮件中识别到新客户或新联系人时，
    会将提取的信息保存到这个表，等待管理员审批。

    审批通过后：
    - new_customer: 创建 Customer + Contact 记录
    - new_contact: 仅创建 Contact 记录关联到已有 Customer
    """

    __tablename__ = "customer_suggestions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 建议类型 ====================
    suggestion_type: Mapped[str] = mapped_column(
        String(20),
        default="new_customer",
        comment="建议类型: new_customer | new_contact",
    )

    # ==================== AI 提取的客户信息 ====================
    suggested_company_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="建议的公司名称",
    )
    suggested_short_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="建议的简称",
    )
    suggested_country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="建议的国家",
    )
    suggested_region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="建议的地区/洲",
    )
    suggested_industry: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="建议的行业",
    )
    suggested_website: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="建议的公司网站",
    )
    suggested_email_domain: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="邮箱域名，如 hydetools.com",
    )
    suggested_customer_level: Mapped[str] = mapped_column(
        String(20),
        default="potential",
        comment="建议的客户等级: potential/normal/important/vip",
    )
    suggested_tags: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="建议的标签列表",
    )

    # ==================== AI 提取的联系人信息 ====================
    suggested_contact_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="建议的联系人姓名",
    )
    suggested_contact_email: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="建议的联系人邮箱",
    )
    suggested_contact_title: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="建议的联系人职位",
    )
    suggested_contact_phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="建议的联系人电话",
    )
    suggested_contact_department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="建议的联系人部门",
    )

    # ==================== AI 分析信息 ====================
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="AI 置信度 0-1",
    )
    reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI 推理说明",
    )
    sender_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="发件人类型: customer/supplier/other",
    )

    # ==================== 触发来源 ====================
    trigger_email_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="触发的邮件 ID",
    )
    trigger_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="触发建议的内容摘要（邮件主题 + 片段）",
    )
    trigger_source: Mapped[str] = mapped_column(
        String(20),
        default="email",
        comment="来源: email | manual",
    )

    # ==================== 查重关联 ====================
    email_domain: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="提取的邮箱域名，用于快速查重",
    )
    matched_customer_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="匹配到的已有客户 ID（new_contact 场景）",
    )

    # ==================== 审批状态 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="状态: pending | approved | rejected",
    )
    workflow_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Temporal Workflow ID",
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="审批人 ID",
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="审批时间",
    )
    review_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="审批备注",
    )

    # ==================== 结果追踪 ====================
    created_customer_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="审批通过后创建的客户 ID",
    )
    created_contact_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="审批通过后创建的联系人 ID",
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_customer_suggestions_status", "status"),
        Index("ix_customer_suggestions_email_domain", "email_domain"),
        Index("ix_customer_suggestions_trigger_email_id", "trigger_email_id"),
        Index("ix_customer_suggestions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CustomerSuggestion {self.suggested_company_name} ({self.status})>"
