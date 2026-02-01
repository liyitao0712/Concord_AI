# app/schemas/chat.py
# Chat API Schemas
#
# 定义 Chat API 的请求和响应数据模型

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ==================== 会话相关 ====================

class ChatSessionCreate(BaseModel):
    """创建会话请求"""
    title: Optional[str] = Field(None, description="会话标题，不填则自动生成")
    agent_id: str = Field("chat_agent", description="使用的 Agent ID")
    source: str = Field("chatbox", description="来源渠道：chatbox / feishu")


class ChatSessionResponse(BaseModel):
    """会话响应"""
    id: str
    user_id: Optional[str]
    external_user_id: Optional[str]
    source: str
    title: str
    agent_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatSessionList(BaseModel):
    """会话列表响应"""
    total: int
    page: int
    page_size: int
    sessions: List[ChatSessionResponse]


# ==================== 消息相关 ====================

class ChatMessageCreate(BaseModel):
    """创建消息请求（用于手动添加消息）"""
    role: str = Field(..., description="角色：user / assistant / system")
    content: str = Field(..., description="消息内容")


class ChatMessageResponse(BaseModel):
    """消息响应"""
    id: str
    session_id: str
    role: str
    content: str
    tool_calls: Optional[dict] = None
    tool_results: Optional[dict] = None
    status: str
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    external_message_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageList(BaseModel):
    """消息列表响应"""
    session_id: str
    messages: List[ChatMessageResponse]


# ==================== 对话请求 ====================

class ChatRequest(BaseModel):
    """对话请求"""
    session_id: Optional[str] = Field(None, description="会话 ID，不填则创建新会话")
    message: str = Field(..., min_length=1, description="用户消息")
    model: Optional[str] = Field(None, description="指定模型（可选）")
    temperature: float = Field(0.7, ge=0, le=2, description="温度参数")


class ChatResponse(BaseModel):
    """对话响应（非流式）"""
    session_id: str
    message_id: str
    content: str
    model: str
    tokens_used: int


# ==================== SSE 事件 ====================

class SSEEvent(BaseModel):
    """SSE 事件"""
    type: str = Field(..., description="事件类型：token / done / error")
    content: Optional[str] = Field(None, description="内容（token 类型）")
    session_id: Optional[str] = Field(None, description="会话 ID")
    message_id: Optional[str] = Field(None, description="消息 ID")
    error: Optional[str] = Field(None, description="错误信息（error 类型）")


# ==================== 通用响应 ====================

class ChatDeleteResponse(BaseModel):
    """删除响应"""
    message: str
    session_id: str
