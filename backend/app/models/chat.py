# app/models/chat.py
# 聊天数据模型
#
# 功能说明：
# 1. 定义 chat_sessions 和 chat_messages 表
# 2. 支持多渠道会话（Web Chatbox、飞书等）
# 3. 存储对话历史和上下文
#
# 表结构：
# ┌───────────────────────────────────────────────────────────┐
# │                    chat_sessions 表                        │
# ├───────────────────────────────────────────────────────────┤
# │ id               │ UUID      │ 主键，会话唯一标识          │
# │ user_id          │ UUID      │ 系统用户ID（可空）          │
# │ external_user_id │ VARCHAR   │ 外部用户ID（飞书open_id等） │
# │ source           │ VARCHAR   │ 来源渠道（chatbox/feishu）  │
# │ title            │ VARCHAR   │ 会话标题                    │
# │ agent_id         │ VARCHAR   │ 使用的Agent                 │
# │ feishu_chat_id   │ VARCHAR   │ 飞书群/私聊ID               │
# │ is_active        │ BOOLEAN   │ 是否活跃                    │
# │ created_at       │ TIMESTAMP │ 创建时间                    │
# │ updated_at       │ TIMESTAMP │ 更新时间                    │
# └───────────────────────────────────────────────────────────┘
#
# ┌───────────────────────────────────────────────────────────┐
# │                    chat_messages 表                        │
# ├───────────────────────────────────────────────────────────┤
# │ id                  │ UUID      │ 主键，消息唯一标识       │
# │ session_id          │ UUID      │ 外键，关联会话           │
# │ role                │ VARCHAR   │ 角色（user/assistant）   │
# │ content             │ TEXT      │ 消息内容                 │
# │ tool_calls          │ JSON      │ 工具调用记录             │
# │ tool_results        │ JSON      │ 工具执行结果             │
# │ status              │ VARCHAR   │ 状态（streaming等）      │
# │ model               │ VARCHAR   │ 使用的模型               │
# │ tokens_used         │ INTEGER   │ 消耗的Token数            │
# │ external_message_id │ VARCHAR   │ 外部消息ID               │
# │ created_at          │ TIMESTAMP │ 创建时间                 │
# └───────────────────────────────────────────────────────────┘

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, Text, Integer, ForeignKey, Index, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatSession(Base):
    """
    聊天会话模型

    用于存储对话会话信息，支持多渠道来源（Web、飞书等）

    属性说明：
        id: 会话唯一标识，使用 UUID
        user_id: 系统用户ID（可空，飞书用户可能未绑定系统用户）
        external_user_id: 外部用户ID（如飞书 open_id）
        source: 来源渠道
            - chatbox: Web 聊天框
            - feishu: 飞书机器人
        title: 会话标题
        agent_id: 使用的 Agent 类型
        feishu_chat_id: 飞书群/私聊 ID
        is_active: 会话是否活跃
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = "chat_sessions"

    # ==================== 主键 ====================
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="会话唯一标识"
    )

    # ==================== 用户关联 ====================
    # 系统用户（可空，飞书用户可能未绑定）
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="系统用户ID"
    )

    # 外部用户ID（飞书 open_id 等）
    external_user_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="外部用户ID（如飞书open_id）"
    )

    # ==================== 渠道信息 ====================
    # 来源渠道
    source: Mapped[str] = mapped_column(
        String(20),
        default="chatbox",
        nullable=False,
        index=True,
        comment="来源渠道：chatbox/feishu"
    )

    # 飞书相关
    feishu_chat_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="飞书群/私聊ID"
    )

    # ==================== 会话信息 ====================
    # 会话标题
    title: Mapped[str] = mapped_column(
        String(200),
        default="新对话",
        nullable=False,
        comment="会话标题"
    )

    # 使用的 Agent
    agent_id: Mapped[str] = mapped_column(
        String(50),
        default="chat_agent",
        nullable=False,
        comment="使用的Agent"
    )

    # ==================== 状态 ====================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否活跃"
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    # ==================== 关系 ====================
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, source={self.source}, title={self.title})>"


class ChatMessage(Base):
    """
    聊天消息模型

    用于存储会话中的每条消息

    属性说明：
        id: 消息唯一标识
        session_id: 关联的会话ID
        role: 消息角色
            - user: 用户消息
            - assistant: AI 助手回复
            - system: 系统消息
            - tool: 工具调用结果
        content: 消息文本内容
        tool_calls: 工具调用记录（JSON）
        tool_results: 工具执行结果（JSON）
        status: 消息状态
            - pending: 待处理
            - streaming: 流式输出中
            - completed: 已完成
            - failed: 失败
        model: 使用的 LLM 模型
        tokens_used: 消耗的 Token 数量
        external_message_id: 外部消息ID（如飞书消息ID）
        created_at: 创建时间
    """

    __tablename__ = "chat_messages"

    # ==================== 主键 ====================
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="消息唯一标识"
    )

    # ==================== 会话关联 ====================
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联会话ID"
    )

    # ==================== 消息内容 ====================
    # 消息角色
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="角色：user/assistant/system/tool"
    )

    # 消息文本
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="消息内容"
    )

    # 工具调用记录
    tool_calls: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="工具调用记录"
    )

    # 工具执行结果
    tool_results: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="工具执行结果"
    )

    # ==================== 状态 ====================
    status: Mapped[str] = mapped_column(
        String(20),
        default="completed",
        nullable=False,
        comment="状态：pending/streaming/completed/failed"
    )

    # ==================== LLM 元数据 ====================
    model: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="使用的模型"
    )

    tokens_used: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="消耗的Token数"
    )

    # ==================== 外部关联 ====================
    external_message_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="外部消息ID（如飞书消息ID）"
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )

    # ==================== 关系 ====================
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages"
    )

    # ==================== 索引 ====================
    __table_args__ = (
        Index("idx_message_session_time", session_id, created_at),
    )

    def __repr__(self) -> str:
        content_preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<ChatMessage(id={self.id}, role={self.role}, content={content_preview})>"
