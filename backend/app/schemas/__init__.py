# app/schemas/__init__.py
# Pydantic Schema 包
#
# 这个文件用于导出所有 Schema，方便其他模块导入
# 使用方式：from app.schemas import UserCreate, UserResponse

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    UserInDB,
    Token,
    TokenRefresh,
    MessageResponse,
)
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionList,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatMessageList,
    ChatRequest,
    ChatResponse,
    SSEEvent,
    ChatDeleteResponse,
)
from app.schemas.event import (
    UnifiedEvent,
    EventResponse,
    Attachment,
)
from app.schemas.email_account import (
    EmailAccountCreate,
    EmailAccountUpdate,
    EmailAccountResponse,
    EmailAccountListResponse,
    EmailAccountTestRequest,
    EmailAccountTestResponse,
)

__all__ = [
    # 用户相关
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    "UserInDB",
    # Token 相关
    "Token",
    "TokenRefresh",
    # 通用
    "MessageResponse",
    # Chat 相关
    "ChatSessionCreate",
    "ChatSessionResponse",
    "ChatSessionList",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ChatMessageList",
    "ChatRequest",
    "ChatResponse",
    "SSEEvent",
    "ChatDeleteResponse",
    # 事件相关
    "UnifiedEvent",
    "EventResponse",
    "Attachment",
    # 邮箱账户相关
    "EmailAccountCreate",
    "EmailAccountUpdate",
    "EmailAccountResponse",
    "EmailAccountListResponse",
    "EmailAccountTestRequest",
    "EmailAccountTestResponse",
]
