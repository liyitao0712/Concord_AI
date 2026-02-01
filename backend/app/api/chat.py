# app/api/chat.py
# Chat API 路由
#
# 功能说明：
# 1. 会话管理（创建、列表、删除）
# 2. 消息历史查询
# 3. SSE 流式对话
#
# API 列表：
# ┌─────────────────────────────────────────────────────────────┐
# │  方法  │  路径                              │  说明          │
# ├────────┼────────────────────────────────────┼───────────────┤
# │  POST  │  /api/chat/sessions                │  创建会话      │
# │  GET   │  /api/chat/sessions                │  会话列表      │
# │  GET   │  /api/chat/sessions/{id}           │  会话详情      │
# │  DELETE│  /api/chat/sessions/{id}           │  删除会话      │
# │  GET   │  /api/chat/sessions/{id}/messages  │  消息历史      │
# │  POST  │  /api/chat/stream                  │  SSE 流式对话  │
# │  POST  │  /api/chat/send                    │  非流式对话    │
# └─────────────────────────────────────────────────────────────┘

import json
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.logging import get_logger
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.agents.chat_agent import chat_agent
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionList,
    ChatMessageResponse,
    ChatMessageList,
    ChatRequest,
    ChatResponse,
    ChatDeleteResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ==================== 会话管理 ====================

@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建会话",
    description="创建新的聊天会话"
)
async def create_session(
    data: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """创建新会话"""
    logger.info(f"创建会话: user={current_user.id}, agent={data.agent_id}")

    session = ChatSession(
        id=str(uuid4()),
        user_id=current_user.id,
        source=data.source,
        title=data.title or "新对话",
        agent_id=data.agent_id,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(f"会话创建成功: {session.id}")
    return session


@router.get(
    "/sessions",
    response_model=ChatSessionList,
    summary="会话列表",
    description="获取当前用户的会话列表"
)
async def list_sessions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionList:
    """获取会话列表"""
    # 计算总数
    count_query = select(func.count(ChatSession.id)).where(
        ChatSession.user_id == current_user.id,
        ChatSession.is_active == True,
    )
    total = await db.scalar(count_query) or 0

    # 查询会话
    offset = (page - 1) * page_size
    query = (
        select(ChatSession)
        .where(
            ChatSession.user_id == current_user.id,
            ChatSession.is_active == True,
        )
        .order_by(desc(ChatSession.updated_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    return ChatSessionList(
        total=total,
        page=page,
        page_size=page_size,
        sessions=[ChatSessionResponse.model_validate(s) for s in sessions],
    )


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="会话详情",
    description="获取会话详情"
)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """获取会话详情"""
    query = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    return session


@router.delete(
    "/sessions/{session_id}",
    response_model=ChatDeleteResponse,
    summary="删除会话",
    description="软删除会话（标记为非活跃）"
)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatDeleteResponse:
    """删除会话"""
    query = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 软删除
    session.is_active = False
    await db.commit()

    # 清除 Redis 缓存
    await chat_agent.clear_context(session_id)

    logger.info(f"会话已删除: {session_id}")
    return ChatDeleteResponse(
        message="会话已删除",
        session_id=session_id,
    )


# ==================== 消息历史 ====================

@router.get(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageList,
    summary="消息历史",
    description="获取会话的消息历史"
)
async def get_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=200, description="获取条数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageList:
    """获取消息历史"""
    # 验证会话归属
    session_query = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    # 查询消息
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .limit(limit)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    return ChatMessageList(
        session_id=session_id,
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
    )


# ==================== 对话接口 ====================

@router.post(
    "/send",
    response_model=ChatResponse,
    summary="非流式对话",
    description="发送消息并获取完整响应"
)
async def send_message(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """非流式对话"""
    session_id = data.session_id

    # 如果没有 session_id，创建新会话
    if not session_id:
        session = ChatSession(
            id=str(uuid4()),
            user_id=current_user.id,
            source="chatbox",
            title=data.message[:50] if len(data.message) > 50 else data.message,
            agent_id="chat_agent",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id
        logger.info(f"自动创建会话: {session_id}")
    else:
        # 验证会话归属
        query = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

    # 保存用户消息
    user_message = ChatMessage(
        id=str(uuid4()),
        session_id=session_id,
        role="user",
        content=data.message,
        status="completed",
    )
    db.add(user_message)

    # 调用 Chat Agent
    result = await chat_agent.chat(
        session_id=session_id,
        message=data.message,
        model=data.model,
        temperature=data.temperature,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "对话失败"
        )

    # 保存助手消息
    assistant_message = ChatMessage(
        id=str(uuid4()),
        session_id=session_id,
        role="assistant",
        content=result.content,
        status="completed",
        model=result.model,
        tokens_used=result.tokens_used,
    )
    db.add(assistant_message)
    await db.commit()

    return ChatResponse(
        session_id=session_id,
        message_id=assistant_message.id,
        content=result.content,
        model=result.model,
        tokens_used=result.tokens_used,
    )


@router.post(
    "/stream",
    summary="SSE 流式对话",
    description="发送消息并以 SSE 流式返回响应"
)
async def stream_chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE 流式对话

    返回格式：
    - data: {"type": "token", "content": "你"}
    - data: {"type": "token", "content": "好"}
    - data: {"type": "done", "session_id": "xxx", "message_id": "xxx"}

    错误格式：
    - data: {"type": "error", "error": "错误信息"}
    """
    session_id = data.session_id

    # 如果没有 session_id，创建新会话
    if not session_id:
        session = ChatSession(
            id=str(uuid4()),
            user_id=current_user.id,
            source="chatbox",
            title=data.message[:50] if len(data.message) > 50 else data.message,
            agent_id="chat_agent",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        session_id = session.id
        logger.info(f"自动创建会话: {session_id}")
    else:
        # 验证会话归属
        query = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

    # 保存用户消息
    user_message = ChatMessage(
        id=str(uuid4()),
        session_id=session_id,
        role="user",
        content=data.message,
        status="completed",
    )
    db.add(user_message)
    await db.commit()

    # 创建助手消息（初始状态为 streaming）
    assistant_message_id = str(uuid4())

    async def generate():
        """SSE 事件生成器"""
        full_content = ""

        try:
            # 流式调用 Chat Agent
            async for chunk in chat_agent.chat_stream(
                session_id=session_id,
                message=data.message,
                model=data.model,
                temperature=data.temperature,
            ):
                full_content += chunk
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "token",
                        "content": chunk,
                    }, ensure_ascii=False),
                }

            # 保存完整的助手消息到数据库
            async with db.begin():
                assistant_message = ChatMessage(
                    id=assistant_message_id,
                    session_id=session_id,
                    role="assistant",
                    content=full_content,
                    status="completed",
                )
                db.add(assistant_message)

            # 发送完成事件
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "done",
                    "session_id": session_id,
                    "message_id": assistant_message_id,
                }, ensure_ascii=False),
            }

        except Exception as e:
            logger.error(f"流式对话失败: {e}")
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error",
                    "error": str(e),
                }, ensure_ascii=False),
            }

    return EventSourceResponse(generate())
