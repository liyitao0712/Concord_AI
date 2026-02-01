# app/models/execution.py
# 执行记录数据模型
#
# 用于记录 Workflow 和 Agent 的执行历史，供管理员监控查看

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, Integer, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WorkflowExecution(Base):
    """
    工作流执行记录

    记录每次 Workflow 的执行情况，用于监控和审计
    """
    __tablename__ = "workflow_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Temporal Workflow ID
    workflow_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        comment="Temporal Workflow ID",
    )

    # 工作流类型：approval, email_process 等
    workflow_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
        comment="工作流类型",
    )

    # 状态：pending, running, completed, failed, cancelled
    status: Mapped[str] = mapped_column(
        String(20),
        index=True,
        default="pending",
        comment="执行状态",
    )

    # 标题（用于展示）
    title: Mapped[str] = mapped_column(
        String(200),
        default="",
        comment="工作流标题",
    )

    # 输入参数（JSON）
    input_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="输入参数",
    )

    # 输出结果（JSON）
    output_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="输出结果",
    )

    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )

    # 时间戳
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        comment="开始时间",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="完成时间",
    )

    def __repr__(self) -> str:
        return f"<WorkflowExecution {self.workflow_id} ({self.status})>"


class AgentExecution(Base):
    """
    Agent 执行记录

    记录每次 Agent 的调用情况，用于监控和统计
    """
    __tablename__ = "agent_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Agent 名称：email_analyzer, intent_classifier 等
    agent_name: Mapped[str] = mapped_column(
        String(50),
        index=True,
        comment="Agent 名称",
    )

    # 执行结果
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否成功",
    )

    # 执行耗时（毫秒）
    execution_time_ms: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="执行耗时（毫秒）",
    )

    # 使用的模型
    model_used: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="使用的模型",
    )

    # 迭代次数
    iterations: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="迭代次数",
    )

    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        index=True,
        comment="创建时间",
    )

    def __repr__(self) -> str:
        return f"<AgentExecution {self.agent_name} ({self.success})>"
