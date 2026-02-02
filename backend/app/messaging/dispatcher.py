# app/messaging/dispatcher.py
# 事件分发器
#
# 功能说明：
# 1. 接收 UnifiedEvent
# 2. 幂等性检查（防止重复处理）
# 3. 保存事件到数据库
# 4. 调用 EmailSummarizer 进行意图分类
# 5. WorkTypeAnalyzer 需要手动触发（通过 API）
#
# 使用方法：
#   from app.messaging.dispatcher import EventDispatcher, event_dispatcher
#
#   # 分发事件
#   await event_dispatcher.dispatch(event)

import asyncio
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.models.event import Event, EventStatus
from app.schemas.event import UnifiedEvent
from app.agents.registry import agent_registry

logger = get_logger(__name__)


class EventDispatcher:
    """
    事件分发器

    负责：
    1. 接收统一事件
    2. 幂等性检查
    3. 保存事件到数据库
    4. 意图分类（仅 EmailSummarizer，WorkTypeAnalyzer 需手动触发）
    5. 记录日志（不再启动 Workflow，改为人工处理）
    """

    async def dispatch(self, event: UnifiedEvent) -> Optional[str]:
        """
        分发事件

        Args:
            event: 统一事件

        Returns:
            None（不再启动 Workflow）
        """
        logger.info(
            f"[Dispatcher] 接收事件: {event.event_id} "
            f"type={event.event_type} source={event.source}"
        )

        async with async_session_maker() as session:
            try:
                # 1. 幂等性检查
                if event.idempotency_key:
                    existing = await self._check_idempotency(
                        session, event.idempotency_key
                    )
                    if existing:
                        logger.info(
                            f"[Dispatcher] 事件已处理，跳过: {event.idempotency_key}"
                        )
                        return None

                # 2. 保存事件到数据库
                db_event = await self._save_event(session, event)

                # 3. 意图分类（仅 EmailSummarizer）
                # 注意：WorkTypeAnalyzer 需要通过 API 手动触发
                intent = await self._classify_intent(event, session)
                db_event.intent = intent
                logger.info(f"[Dispatcher] 意图分类完成: intent={intent}")

                # 4. 标记为已完成（不再启动 Workflow）
                db_event.mark_completed()

                await session.commit()

                logger.info(
                    f"[Dispatcher] 事件已分类并保存: event_id={event.event_id}, "
                    f"intent={intent}（待人工处理）"
                )

                return None

            except Exception as e:
                logger.error(f"[Dispatcher] 分发失败: {e}")
                await session.rollback()
                raise

    async def _check_idempotency(
        self,
        session: AsyncSession,
        idempotency_key: str
    ) -> Optional[Event]:
        """
        检查幂等性

        Args:
            session: 数据库会话
            idempotency_key: 幂等键

        Returns:
            Optional[Event]: 如果已存在则返回事件，否则返回 None
        """
        stmt = select(Event).where(Event.idempotency_key == idempotency_key)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _save_event(
        self,
        session: AsyncSession,
        event: UnifiedEvent
    ) -> Event:
        """
        保存事件到数据库

        Args:
            session: 数据库会话
            event: 统一事件

        Returns:
            Event: 数据库事件对象
        """
        db_event = Event(
            id=event.event_id,
            idempotency_key=event.idempotency_key or f"{event.source}:{event.event_id}",
            event_type=event.event_type,
            source=event.source,
            source_id=event.source_id,
            content=event.content,
            content_type=event.content_type,
            user_id=event.user_id,
            user_external_id=event.user_external_id,
            session_id=event.session_id,
            thread_id=event.thread_id,
            status=EventStatus.PENDING,
            metadata={
                **event.metadata,
                "context": event.context,
                "priority": event.priority,
            },
        )

        session.add(db_event)
        await session.flush()  # 获取 ID

        logger.debug(f"[Dispatcher] 保存事件: {db_event.id}")
        return db_event

    async def _classify_parallel(
        self,
        event: UnifiedEvent,
        session: AsyncSession,
    ) -> Tuple[str, Optional[str]]:
        """
        并行调用 EmailSummarizer 和 WorkTypeAnalyzer

        Args:
            event: 统一事件
            session: 数据库会话

        Returns:
            Tuple[str, Optional[str]]: (intent, work_type_code)
        """
        # 构建分类输入
        input_text = event.content
        subject = ""

        if event.event_type == "email":
            subject = event.metadata.get("subject", "")
            if subject:
                input_text = f"主题: {subject}\n\n{input_text}"

        # 准备 input_data
        input_data = {
            "email_id": event.event_id,
            "sender": event.metadata.get("sender", ""),
            "sender_name": event.metadata.get("sender_name"),
            "subject": subject,
            "body_text": event.content,
            "body_html": event.metadata.get("body_html"),
            "content": event.content,
            "received_at": event.metadata.get("received_at"),
        }

        # 并行执行两个 Agent
        try:
            results = await asyncio.gather(
                agent_registry.run(
                    "email_summarizer",
                    input_text=input_text,
                    input_data=input_data,
                    db=session,
                ),
                agent_registry.run(
                    "work_type_analyzer",
                    input_text=input_text,
                    input_data=input_data,
                    db=session,
                ),
                return_exceptions=True,  # 一个失败不影响另一个
            )

            # 解析 EmailSummarizer 结果
            intent = "other"
            email_result = results[0]
            if isinstance(email_result, Exception):
                logger.warning(f"[Dispatcher] EmailSummarizer 执行异常: {email_result}")
            elif email_result.success and email_result.data:
                intent = email_result.data.get("intent", "other")

            # 解析 WorkTypeAnalyzer 结果
            work_type = None
            work_type_result = results[1]
            if isinstance(work_type_result, Exception):
                logger.warning(f"[Dispatcher] WorkTypeAnalyzer 执行异常: {work_type_result}")
            elif work_type_result.success and work_type_result.data:
                matched = work_type_result.data.get("matched_work_type")
                if matched and matched.get("code"):
                    work_type = matched.get("code")

            return intent, work_type

        except Exception as e:
            logger.error(f"[Dispatcher] 并行分类失败: {e}")
            return "other", None

    async def _classify_intent(self, event: UnifiedEvent, session) -> str:
        """
        调用 email_summarizer Agent 进行意图分类

        Args:
            event: 统一事件
            session: 数据库会话

        Returns:
            str: 意图类型
        """
        try:
            # 构建分类输入
            input_text = event.content
            subject = ""

            if event.event_type == "email":
                subject = event.metadata.get("subject", "")
                if subject:
                    input_text = f"主题: {subject}\n\n{input_text}"

            # 准备 input_data
            input_data = {
                "email_id": event.event_id,
                "sender": event.metadata.get("sender", ""),
                "sender_name": event.metadata.get("sender_name"),
                "subject": subject,
                "body_text": event.content,
                "body_html": event.metadata.get("body_html"),
                "received_at": event.metadata.get("received_at"),
            }

            # 只执行 EmailSummarizer
            result = await agent_registry.run(
                "email_summarizer",
                input_text=input_text,
                input_data=input_data,
                db=session,
            )

            if result.success and result.data:
                return result.data.get("intent", "other")

            return "other"

        except Exception as e:
            logger.warning(f"[Dispatcher] 意图分类失败，使用默认: {e}")
            return "other"

    async def update_event_status(
        self,
        event_id: str,
        status: str,
        response: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        更新事件状态

        Args:
            event_id: 事件 ID
            status: 新状态
            response: 响应内容
            error: 错误信息
        """
        async with async_session_maker() as session:
            stmt = select(Event).where(Event.id == event_id)
            result = await session.execute(stmt)
            event = result.scalar_one_or_none()

            if not event:
                logger.warning(f"[Dispatcher] 事件不存在: {event_id}")
                return

            event.status = status
            if response:
                event.response_content = response
            if error:
                event.error_message = error
            if status in (EventStatus.COMPLETED, EventStatus.FAILED):
                event.completed_at = datetime.utcnow()

            await session.commit()
            logger.debug(f"[Dispatcher] 更新事件状态: {event_id} -> {status}")


# 全局单例
event_dispatcher = EventDispatcher()
