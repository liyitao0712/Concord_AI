# app/models/event.py
# 事件记录模型
#
# 功能说明：
# 1. 记录所有进入系统的事件（邮件、聊天、Webhook 等）
# 2. 用于审计追踪和问题排查
# 3. 支持幂等性检查（通过 idempotency_key）
# 4. 记录事件处理状态和结果
#
# 表结构：
# ┌─────────────────────────────────────────────────────────────────┐
# │                         events 表                               │
# ├─────────────────────────────────────────────────────────────────┤
# │ id               │ UUID      │ 主键，事件唯一标识               │
# │ idempotency_key  │ VARCHAR   │ 幂等键（唯一索引）               │
# │ event_type       │ VARCHAR   │ 事件类型（email/chat/webhook）   │
# │ source           │ VARCHAR   │ 来源渠道（feishu/web/email）     │
# │ source_id        │ VARCHAR   │ 原始消息 ID                      │
# │ content          │ TEXT      │ 事件内容                         │
# │ content_type     │ VARCHAR   │ 内容类型（text/html/markdown）   │
# │ user_id          │ VARCHAR   │ 系统用户 ID（可空）              │
# │ user_external_id │ VARCHAR   │ 外部用户 ID（如邮箱地址）        │
# │ session_id       │ VARCHAR   │ 会话 ID（可空）                  │
# │ thread_id        │ VARCHAR   │ 线程 ID（邮件回复链）            │
# │ status           │ VARCHAR   │ 处理状态                         │
# │ intent           │ VARCHAR   │ 分类后的意图                     │
# │ workflow_id      │ VARCHAR   │ 关联的 Workflow ID               │
# │ response_content │ TEXT      │ 响应内容                         │
# │ error_message    │ TEXT      │ 错误信息                         │
# │ event_metadata   │ JSON      │ 额外元数据                       │
# │ created_at       │ TIMESTAMP │ 创建时间                         │
# │ processed_at     │ TIMESTAMP │ 开始处理时间                     │
# │ completed_at     │ TIMESTAMP │ 完成时间                         │
# └─────────────────────────────────────────────────────────────────┘

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, JSON, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EventStatus:
    """事件状态常量"""
    PENDING = "pending"          # 待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 处理失败
    SKIPPED = "skipped"          # 已跳过（重复事件）


class EventType:
    """事件类型常量"""
    EMAIL = "email"              # 邮件
    CHAT = "chat"                # 聊天消息
    WEBHOOK = "webhook"          # Webhook 回调
    COMMAND = "command"          # 命令
    APPROVAL = "approval"        # 审批
    SCHEDULE = "schedule"        # 定时任务


class EventSource:
    """事件来源常量"""
    WEB = "web"                  # Web 界面
    CHATBOX = "chatbox"          # Chatbox 组件
    FEISHU = "feishu"            # 飞书
    EMAIL = "email"              # 邮件
    WEBHOOK = "webhook"          # Webhook
    SCHEDULE = "schedule"        # 定时任务


class Event(Base):
    """
    事件记录模型

    用于记录所有进入系统的事件，支持审计追踪和幂等性检查。

    属性说明：
        id: 事件唯一标识，使用 UUID 格式
        idempotency_key: 幂等键，用于防止重复处理
        event_type: 事件类型（email/chat/webhook 等）
        source: 来源渠道（feishu/web/email 等）
        source_id: 原始消息 ID（如邮件的 Message-ID）
        content: 事件主要内容
        content_type: 内容格式（text/html/markdown）
        user_id: 系统用户 ID（如果已关联）
        user_external_id: 外部用户 ID（如邮箱地址、飞书 open_id）
        session_id: 会话 ID（对话场景）
        thread_id: 线程 ID（邮件回复链）
        status: 处理状态（pending/processing/completed/failed）
        intent: 分类后的意图（inquiry/order/complaint 等）
        workflow_id: 关联的 Temporal Workflow ID
        response_content: 系统响应内容
        error_message: 处理失败时的错误信息
        event_metadata: 额外元数据（JSON 格式）
        created_at: 事件创建时间
        processed_at: 开始处理时间
        completed_at: 处理完成时间

    使用示例：
        # 创建事件记录
        event = Event(
            idempotency_key="email:abc123",
            event_type="email",
            source="email",
            source_id="abc123",
            content="我想询问产品价格...",
            content_type="text",
            user_external_id="customer@example.com",
        )
        session.add(event)
        await session.commit()

        # 更新处理状态
        event.status = EventStatus.PROCESSING
        event.processed_at = datetime.utcnow()
        await session.commit()
    """

    __tablename__ = "events"

    # ==================== 表级索引 ====================
    # 复合索引：常用查询组合
    __table_args__ = (
        # 按状态和创建时间查询（获取待处理事件）
        Index("ix_events_status_created", "status", "created_at"),
        # 按来源和创建时间查询（查看某渠道的事件）
        Index("ix_events_source_created", "source", "created_at"),
        # 按用户查询
        Index("ix_events_user_external_id", "user_external_id"),
    )

    # ==================== 主键 ====================
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="事件唯一标识"
    )

    # ==================== 幂等性 ====================
    # 幂等键：用于防止重复处理同一事件
    # 格式通常为: "{source}:{source_id}"，如 "email:abc123"
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="幂等键，防止重复处理"
    )

    # ==================== 事件标识 ====================
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="事件类型：email/chat/webhook/command/approval/schedule"
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="来源渠道：web/chatbox/feishu/email/webhook/schedule"
    )

    source_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="原始消息 ID"
    )

    # ==================== 内容 ====================
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="事件内容"
    )

    content_type: Mapped[str] = mapped_column(
        String(20),
        default="text",
        nullable=False,
        comment="内容类型：text/html/markdown"
    )

    # ==================== 用户信息 ====================
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="系统用户 ID"
    )

    user_external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="外部用户 ID（邮箱/open_id 等）"
    )

    # ==================== 会话信息 ====================
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="会话 ID"
    )

    thread_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="线程 ID（邮件回复链）"
    )

    # ==================== 处理状态 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default=EventStatus.PENDING,
        nullable=False,
        index=True,
        comment="处理状态：pending/processing/completed/failed/skipped"
    )

    intent: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="分类后的意图"
    )

    workflow_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="关联的 Workflow ID"
    )

    # ==================== 结果 ====================
    response_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="响应内容"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息"
    )

    # ==================== 元数据 ====================
    event_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="额外元数据"
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )

    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="开始处理时间"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="完成时间"
    )

    def __repr__(self) -> str:
        """返回事件对象的字符串表示"""
        return (
            f"<Event(id={self.id}, type={self.event_type}, "
            f"source={self.source}, status={self.status})>"
        )

    def mark_processing(self) -> None:
        """标记为处理中"""
        self.status = EventStatus.PROCESSING
        self.processed_at = datetime.utcnow()

    def mark_completed(self, response: Optional[str] = None) -> None:
        """标记为已完成"""
        self.status = EventStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if response:
            self.response_content = response

    def mark_failed(self, error: str) -> None:
        """标记为失败"""
        self.status = EventStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error

    def mark_skipped(self) -> None:
        """标记为跳过（重复事件）"""
        self.status = EventStatus.SKIPPED
        self.completed_at = datetime.utcnow()

    @property
    def is_pending(self) -> bool:
        """是否待处理"""
        return self.status == EventStatus.PENDING

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == EventStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """是否失败"""
        return self.status == EventStatus.FAILED

    @property
    def processing_time_ms(self) -> Optional[int]:
        """处理耗时（毫秒）"""
        if self.processed_at and self.completed_at:
            delta = self.completed_at - self.processed_at
            return int(delta.total_seconds() * 1000)
        return None
