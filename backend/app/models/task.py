# app/models/task.py
# 任务管理模型
#
# 功能说明：
# Task - 任务/里程碑表，属于某个项目，支持子任务（自引用 FK）
#
# 使用方法：
#   from app.models.task import Task

from datetime import datetime, date
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import String, Text, Integer, DateTime, Date, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Task(Base):
    """
    任务/里程碑表

    双重用途：
    - task_type = "action": 具体的可执行任务
    - task_type = "milestone": 里程碑/阶段节点

    支持自引用 parent_task_id 实现子任务树。

    状态流转：
    pending → in_progress → completed / cancelled
    """

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 关联 ====================
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属项目 ID",
    )
    parent_task_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        comment="父任务 ID（子任务场景）",
    )

    # ==================== 基本信息 ====================
    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="任务标题",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="任务描述",
    )
    task_type: Mapped[str] = mapped_column(
        String(20),
        default="action",
        comment="任务类型: action（具体任务）/ milestone（里程碑）",
    )
    phase_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="阶段名称（milestone 类型使用）",
    )

    # ==================== 状态与优先级 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="状态: pending/in_progress/completed/cancelled",
    )
    priority: Mapped[str] = mapped_column(
        String(10),
        default="medium",
        comment="优先级: low/medium/high/urgent",
    )

    # ==================== 指派与排序 ====================
    assignee_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="负责人 ID",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="排序序号（越小越靠前）",
    )

    # ==================== 进度 ====================
    completion_percentage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="完成百分比 0-100",
    )

    # ==================== 日期 ====================
    due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="截止日期",
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # ==================== 权限字段 ====================
    org_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True,
        index=True, comment="所属组织"
    )
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True,
        index=True, comment="负责人"
    )
    owner_dept_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), nullable=True,
        index=True, comment="负责人部门"
    )

    # ==================== 关系 ====================
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks",
    )
    parent_task: Mapped[Optional["Task"]] = relationship(
        "Task",
        remote_side="Task.id",
        back_populates="sub_tasks",
    )
    sub_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="parent_task",
        cascade="all, delete-orphan",
    )
    progress_entries: Mapped[List["Progress"]] = relationship(
        "Progress",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Progress.created_at.desc()",
    )

    __table_args__ = (
        Index("ix_tasks_project_id", "project_id"),
        Index("ix_tasks_parent_task_id", "parent_task_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_task_type", "task_type"),
        Index("ix_tasks_assignee_id", "assignee_id"),
        Index("ix_tasks_sort_order", "sort_order"),
    )

    def __repr__(self) -> str:
        return f"<Task {self.title} ({self.status})>"
