# app/models/progress.py
# 进度记录模型
#
# 功能说明：
# Progress - 进度记录/时间线表，记录任务的状态更新、完成度变化、沟通记录
#
# 使用方法：
#   from app.models.progress import Progress

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, Integer, JSON, DateTime, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Progress(Base):
    """
    进度记录表（时间线/活动日志）

    三种用途：
    - progress_type = "status_update": 状态变更记录
    - progress_type = "completion": 完成度更新
    - progress_type = "communication": 沟通/备注记录

    支持关联邮件（email_id），实现邮件驱动的进度追踪。
    Append-only 设计，记录不可编辑。
    """

    __tablename__ = "progress_entries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 关联 ====================
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属任务 ID",
    )

    # ==================== 记录类型 ====================
    progress_type: Mapped[str] = mapped_column(
        String(20),
        default="status_update",
        comment="记录类型: status_update/completion/communication",
    )

    # ==================== 内容 ====================
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="记录内容/备注",
    )

    # ==================== 状态变更 ====================
    old_status: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="变更前状态（status_update 类型使用）",
    )
    new_status: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="变更后状态（status_update 类型使用）",
    )

    # ==================== 完成度 ====================
    percentage: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="完成百分比（completion 类型使用）",
    )

    # ==================== 邮件关联 ====================
    email_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("email_raw_messages.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联邮件 ID（沟通记录来源）",
    )

    # ==================== 附件 ====================
    attachments: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="附件列表 [{name, key, storage_type}]",
    )

    # ==================== 审计 ====================
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建人 ID",
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    # ==================== 关系 ====================
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="progress_entries",
    )

    __table_args__ = (
        Index("ix_progress_entries_task_id", "task_id"),
        Index("ix_progress_entries_progress_type", "progress_type"),
        Index("ix_progress_entries_email_id", "email_id"),
        Index("ix_progress_entries_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Progress {self.progress_type} @ task={self.task_id}>"
