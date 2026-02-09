# app/models/project_suggestion.py
# 项目建议模型
#
# 功能说明：
# ProjectSuggestion - AI 从邮件中建议创建的项目，待人工审批
#
# 审批流程：
# 1. AI Agent 从邮件中识别到应创建项目 → 保存到此表（status=pending）
# 2. 管理员在后台审批
# 3. 批准 → 创建 Project 记录
#    拒绝 → 标记为 rejected
#
# 使用方法：
#   from app.models.project_suggestion import ProjectSuggestion

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, Float, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProjectSuggestion(Base):
    """
    项目建议表

    当 AI Agent 从邮件中识别到应该创建项目时，
    将建议信息保存到这个表，等待管理员审批。

    审批通过后创建 Project 记录。
    """

    __tablename__ = "project_suggestions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== AI 建议的项目信息 ====================
    suggested_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="建议的项目名称",
    )
    suggested_type: Mapped[str] = mapped_column(
        String(50),
        default="general",
        comment="建议的项目类型",
    )
    suggested_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="建议的项目描述",
    )
    suggested_priority: Mapped[str] = mapped_column(
        String(10),
        default="medium",
        comment="建议的优先级: low/medium/high/urgent",
    )
    suggested_associations: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="建议的关联实体 [{entity_type, entity_id, entity_name}]",
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
        comment="触发建议的内容摘要",
    )
    trigger_source: Mapped[str] = mapped_column(
        String(20),
        default="email",
        comment="来源: email / manual",
    )

    # ==================== 审批状态 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="状态: pending / approved / rejected",
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
    created_project_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="审批通过后创建的项目 ID",
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_project_suggestions_status", "status"),
        Index("ix_project_suggestions_trigger_email_id", "trigger_email_id"),
        Index("ix_project_suggestions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ProjectSuggestion {self.suggested_name} ({self.status})>"
