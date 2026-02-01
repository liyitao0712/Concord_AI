# app/messaging/dispatcher.py
# 事件分发器
#
# 功能说明：
# 1. 接收 UnifiedEvent
# 2. 幂等性检查（防止重复处理）
# 3. 保存事件到数据库
# 4. 调用 Agent 进行意图分类
# 5. 根据意图启动对应的 Temporal Workflow
#
# 使用方法：
#   from app.messaging.dispatcher import EventDispatcher, event_dispatcher
#
#   # 分发事件
#   await event_dispatcher.dispatch(event)

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.models.event import Event, EventStatus
from app.schemas.event import UnifiedEvent
from app.agents.registry import agent_registry
from app.workflows.client import start_workflow

logger = get_logger(__name__)


class EventDispatcher:
    """
    事件分发器

    负责：
    1. 接收统一事件
    2. 幂等性检查
    3. 保存事件到数据库
    4. 意图分类
    5. 启动对应的 Workflow

    意图 -> Workflow 映射：
    - inquiry: 询价流程
    - order: 订单流程
    - complaint: 投诉流程
    - follow_up: 跟进流程
    - greeting: 直接回复（不启动 Workflow）
    - other: 人工处理
    """

    # 意图到 Workflow 的映射
    INTENT_WORKFLOW_MAP = {
        "inquiry": "EmailProcessWorkflow",      # 询价 -> 邮件处理流程
        "order": "EmailProcessWorkflow",        # 订单 -> 邮件处理流程
        "complaint": "EmailProcessWorkflow",    # 投诉 -> 邮件处理流程
        "follow_up": "EmailProcessWorkflow",    # 跟进 -> 邮件处理流程
        "greeting": None,                       # 问候 -> 直接回复
        "other": "EmailProcessWorkflow",        # 其他 -> 邮件处理流程（人工处理）
    }

    # 默认 Workflow
    DEFAULT_WORKFLOW = "EmailProcessWorkflow"

    async def dispatch(self, event: UnifiedEvent) -> Optional[str]:
        """
        分发事件

        Args:
            event: 统一事件

        Returns:
            Optional[str]: Workflow ID（如果启动了 Workflow）
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
                        return existing.workflow_id

                # 2. 保存事件到数据库
                db_event = await self._save_event(session, event)

                # 3. 意图分类
                intent = await self._classify_intent(event, session)
                db_event.intent = intent
                logger.info(f"[Dispatcher] 意图分类: {intent}")

                # 4. 根据意图启动 Workflow
                workflow_id = await self._start_workflow(event, intent)

                # 5. 更新事件状态
                if workflow_id:
                    db_event.workflow_id = workflow_id
                    db_event.mark_processing()
                else:
                    # 无需启动 Workflow（如 greeting）
                    db_event.mark_completed()

                await session.commit()

                logger.info(
                    f"[Dispatcher] 分发完成: event={event.event_id} "
                    f"intent={intent} workflow={workflow_id}"
                )

                return workflow_id

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

    async def _classify_intent(self, event: UnifiedEvent, session) -> str:
        """
        调用 Agent 进行意图分类

        Args:
            event: 统一事件
            session: 数据库会话

        Returns:
            str: 意图类型
        """
        try:
            # 构建分类输入
            input_text = event.content

            # 如果是邮件，添加主题信息
            if event.event_type == "email":
                subject = event.metadata.get("subject", "")
                if subject:
                    input_text = f"主题: {subject}\n\n{input_text}"

            # 调用意图分类 Agent（传递 db 参数以加载 Agent 配置）
            result = await agent_registry.run(
                "intent_classifier",
                input_text=input_text,
                db=session,
            )

            if result.success and result.data:
                intent = result.data.get("intent", "other")
                return intent

            return "other"

        except Exception as e:
            logger.warning(f"[Dispatcher] 意图分类失败，使用默认: {e}")
            return "other"

    async def _start_workflow(
        self,
        event: UnifiedEvent,
        intent: str
    ) -> Optional[str]:
        """
        根据意图启动对应的 Workflow

        Args:
            event: 统一事件
            intent: 意图类型

        Returns:
            Optional[str]: Workflow ID
        """
        # 获取对应的 Workflow
        workflow_name = self.INTENT_WORKFLOW_MAP.get(intent)

        if not workflow_name:
            logger.info(f"[Dispatcher] 意图 {intent} 无需启动 Workflow")
            return None

        # 准备 Workflow 参数
        workflow_input = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source": event.source,
            "source_id": event.source_id,
            "content": event.content,
            "content_type": event.content_type,
            "user_external_id": event.user_external_id,
            "user_name": event.user_name,
            "session_id": event.session_id,
            "thread_id": event.thread_id,
            "intent": intent,
            "metadata": event.metadata,
        }

        try:
            # 生成 Workflow ID
            workflow_id = f"{workflow_name.lower()}-{event.event_id}"

            # 启动 Workflow
            # 注意：这里假设 Workflow 已经在 worker 中注册
            # 如果 Workflow 尚未实现，会报错
            from app.workflows.definitions.email_process import EmailProcessWorkflow

            handle = await start_workflow(
                EmailProcessWorkflow.run,
                args=(workflow_input, intent),
                id=workflow_id,
            )

            logger.info(f"[Dispatcher] 启动 Workflow: {workflow_id}")
            return workflow_id

        except ImportError:
            # Workflow 尚未实现，跳过
            logger.warning(
                f"[Dispatcher] Workflow {workflow_name} 尚未实现，跳过启动"
            )
            return None

        except Exception as e:
            logger.error(f"[Dispatcher] 启动 Workflow 失败: {e}")
            raise

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
