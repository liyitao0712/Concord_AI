# app/schemas/event.py
# 统一事件模型
#
# 功能说明：
# 1. 定义 UnifiedEvent - 所有渠道的标准事件格式
# 2. 定义 EventResponse - 统一响应格式
#
# 用途：
# - Web API 请求 → UnifiedEvent
# - Chatbox 消息 → UnifiedEvent
# - 飞书消息 → UnifiedEvent
# - Webhook 调用 → UnifiedEvent
# - 邮件 → UnifiedEvent
#
# 设计原则：
# 不同渠道的输入格式各异，通过 Adapter 统一转换为 UnifiedEvent，
# 再进入后续的 Agent / Workflow 处理流程

from datetime import datetime
from typing import Literal, Optional, Any, List
from uuid import uuid4

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """附件信息"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    content_type: str  # MIME 类型
    size: int  # 字节数
    url: Optional[str] = None  # 文件 URL（OSS）
    content: Optional[str] = None  # Base64 编码的内容（小文件）


class UnifiedEvent(BaseModel):
    """
    统一事件模型 - 所有入口的标准格式

    无论是来自 Web、Chatbox、飞书还是邮件，
    最终都转换为这个统一格式进行处理。

    示例：
        # 飞书消息
        event = UnifiedEvent(
            event_type="chat",
            source="feishu",
            source_id="om_xxx",
            user_external_id="ou_xxx",
            content="你好，帮我查一下订单",
            session_id="oc_xxx",
        )

        # Web Chatbox
        event = UnifiedEvent(
            event_type="chat",
            source="chatbox",
            user_id="user-uuid",
            content="写一首诗",
            session_id="session-uuid",
        )
    """

    # ==================== 事件标识 ====================
    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="事件唯一标识"
    )

    event_type: Literal[
        "chat",           # 对话消息
        "email",          # 邮件
        "webhook",        # Webhook 触发
        "command",        # 指令/命令
        "approval",       # 审批操作
        "schedule",       # 定时触发
    ] = Field(description="事件类型")

    # ==================== 来源信息 ====================
    source: Literal[
        "web",        # Web 界面
        "chatbox",    # Chatbox 对话框
        "feishu",     # 飞书机器人
        "webhook",    # Webhook 调用
        "email",      # 邮件
        "schedule",   # 定时任务
    ] = Field(description="来源渠道")

    source_id: Optional[str] = Field(
        None,
        description="来源唯一标识（如飞书消息 ID）"
    )

    # ==================== 用户信息 ====================
    user_id: Optional[str] = Field(
        None,
        description="系统用户 ID"
    )

    user_name: Optional[str] = Field(
        None,
        description="用户名称"
    )

    user_external_id: Optional[str] = Field(
        None,
        description="外部用户 ID（如飞书 open_id）"
    )

    # ==================== 会话信息 ====================
    session_id: Optional[str] = Field(
        None,
        description="会话 ID（对话场景）"
    )

    thread_id: Optional[str] = Field(
        None,
        description="线程 ID（邮件回复链）"
    )

    # ==================== 内容 ====================
    content: str = Field(
        ...,
        description="主要内容（文本）"
    )

    content_type: Literal["text", "html", "markdown"] = Field(
        "text",
        description="内容格式"
    )

    attachments: List[Attachment] = Field(
        default_factory=list,
        description="附件列表"
    )

    # ==================== 上下文 ====================
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="额外上下文信息"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="元数据（如飞书的 chat_type、邮件的 headers 等）"
    )

    # ==================== 时间戳 ====================
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="事件发生时间"
    )

    # ==================== 处理控制 ====================
    priority: Literal["low", "normal", "high"] = Field(
        "normal",
        description="处理优先级"
    )

    idempotency_key: Optional[str] = Field(
        None,
        description="幂等键，用于防止重复处理"
    )


class EventResponse(BaseModel):
    """
    统一响应模型

    用于返回事件处理结果
    """

    event_id: str = Field(description="对应的事件 ID")

    status: Literal[
        "accepted",     # 已接收，待处理
        "processing",   # 处理中
        "completed",    # 处理完成
        "failed",       # 处理失败
    ] = Field(description="处理状态")

    message: Optional[str] = Field(
        None,
        description="状态描述"
    )

    data: Optional[dict] = Field(
        None,
        description="响应数据"
    )

    workflow_id: Optional[str] = Field(
        None,
        description="触发的 Workflow ID（如果有）"
    )

    agent_id: Optional[str] = Field(
        None,
        description="处理的 Agent ID（如果有）"
    )
