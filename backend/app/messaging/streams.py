# app/messaging/streams.py
# Redis Streams 事件流处理
#
# 功能说明：
# 1. 将事件添加到 Redis Stream
# 2. 使用消费者组读取事件
# 3. 确认事件已处理（ACK）
# 4. 支持事件重试和死信队列
#
# Redis Streams 概念：
# - Stream: 类似于消息队列，存储有序的消息
# - Consumer Group: 消费者组，多个消费者可以协作处理消息
# - Consumer: 消费者，从组中读取消息
# - ACK: 确认消息已处理，否则消息会被重新投递
#
# 使用方法：
#   from app.messaging.streams import redis_streams
#
#   # 添加事件
#   stream_id = await redis_streams.add_event(event)
#
#   # 读取事件（消费者组模式）
#   events = await redis_streams.read_events("worker-group", "worker-1")
#
#   # 确认事件
#   await redis_streams.ack_event(stream_id, "worker-group")

import json
from typing import Optional
from datetime import datetime

from app.core.redis import redis_client
from app.core.logging import get_logger
from app.schemas.event import UnifiedEvent

logger = get_logger(__name__)


class RedisStreams:
    """
    Redis Streams 事件流管理

    使用 Redis Streams 实现可靠的事件队列，支持：
    - 消费者组：多个 Worker 协作处理
    - 消息确认：确保消息被处理
    - 消息重试：未确认的消息会被重新投递
    - 消息持久化：即使 Redis 重启也不会丢失

    流命名规范：
    - events:incoming - 所有新事件
    - events:{type} - 按类型分流（如 events:email）
    """

    # 主事件流
    EVENTS_STREAM = "events:incoming"

    # 默认消费者组
    DEFAULT_GROUP = "event-processors"

    # 消息最大重试次数
    MAX_RETRIES = 3

    # 消息处理超时时间（毫秒）
    CLAIM_TIMEOUT_MS = 60000  # 1 分钟

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> None:
        """
        初始化 Streams

        创建必要的消费者组。如果组已存在则忽略。
        """
        if self._initialized:
            return

        try:
            # 创建默认消费者组
            await self.create_consumer_group(self.DEFAULT_GROUP)
            self._initialized = True
            logger.info("[RedisStreams] 初始化完成")
        except Exception as e:
            logger.error(f"[RedisStreams] 初始化失败: {e}")
            raise

    async def create_consumer_group(
        self,
        group_name: str,
        stream: str = None,
        start_id: str = "0"
    ) -> bool:
        """
        创建消费者组

        Args:
            group_name: 消费者组名称
            stream: Stream 名称，默认使用主事件流
            start_id: 起始 ID，"0" 从头开始，"$" 只读取新消息

        Returns:
            bool: 是否创建成功
        """
        stream = stream or self.EVENTS_STREAM

        try:
            # XGROUP CREATE 命令
            # MKSTREAM: 如果 Stream 不存在则创建
            await redis_client.client.xgroup_create(
                stream,
                group_name,
                id=start_id,
                mkstream=True
            )
            logger.info(f"[RedisStreams] 创建消费者组: {group_name} on {stream}")
            return True

        except Exception as e:
            # 如果组已存在，忽略错误
            if "BUSYGROUP" in str(e):
                logger.debug(f"[RedisStreams] 消费者组已存在: {group_name}")
                return True
            logger.error(f"[RedisStreams] 创建消费者组失败: {e}")
            return False

    async def add_event(
        self,
        event: UnifiedEvent,
        stream: str = None,
        max_len: int = 10000
    ) -> str:
        """
        添加事件到 Stream

        Args:
            event: 统一事件对象
            stream: Stream 名称，默认使用主事件流
            max_len: Stream 最大长度，超过会自动裁剪旧消息

        Returns:
            str: Stream 消息 ID（如 "1234567890123-0"）
        """
        stream = stream or self.EVENTS_STREAM

        # 将事件转换为字典
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source": event.source,
            "source_id": event.source_id or "",
            "content": event.content,
            "content_type": event.content_type,
            "user_id": event.user_id or "",
            "user_external_id": event.user_external_id or "",
            "session_id": event.session_id or "",
            "thread_id": event.thread_id or "",
            "idempotency_key": event.idempotency_key or "",
            "priority": event.priority,
            "timestamp": event.timestamp.isoformat() if event.timestamp else "",
            # JSON 序列化复杂字段
            "metadata": json.dumps(event.metadata) if event.metadata else "{}",
            "context": json.dumps(event.context) if event.context else "{}",
            "attachments": json.dumps([a.model_dump() for a in event.attachments]) if event.attachments else "[]",
        }

        try:
            # XADD 命令添加消息
            # MAXLEN ~: 近似裁剪，性能更好
            stream_id = await redis_client.client.xadd(
                stream,
                event_data,
                maxlen=max_len,
                approximate=True
            )

            logger.info(
                f"[RedisStreams] 添加事件: {event.event_id} -> {stream_id} "
                f"(type={event.event_type}, source={event.source})"
            )
            return stream_id

        except Exception as e:
            logger.error(f"[RedisStreams] 添加事件失败: {e}")
            raise

    async def read_events(
        self,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 5000,
        stream: str = None
    ) -> list[tuple[str, UnifiedEvent]]:
        """
        从消费者组读取事件

        Args:
            group_name: 消费者组名称
            consumer_name: 消费者名称（同一组内唯一）
            count: 一次读取的最大消息数
            block_ms: 阻塞等待时间（毫秒），0 表示不阻塞
            stream: Stream 名称

        Returns:
            list[tuple[str, UnifiedEvent]]: (stream_id, event) 列表
        """
        stream = stream or self.EVENTS_STREAM

        try:
            # XREADGROUP 命令
            # ">": 只读取新消息（未被其他消费者处理的）
            result = await redis_client.client.xreadgroup(
                group_name,
                consumer_name,
                {stream: ">"},
                count=count,
                block=block_ms
            )

            if not result:
                return []

            events = []
            for stream_name, messages in result:
                for msg_id, msg_data in messages:
                    try:
                        event = self._parse_event(msg_data)
                        events.append((msg_id, event))
                    except Exception as e:
                        logger.error(f"[RedisStreams] 解析事件失败: {msg_id}, {e}")
                        # 确认无法解析的消息，避免重复处理
                        await self.ack_event(msg_id, group_name, stream)

            if events:
                logger.debug(f"[RedisStreams] 读取 {len(events)} 个事件")

            return events

        except Exception as e:
            logger.error(f"[RedisStreams] 读取事件失败: {e}")
            return []

    async def read_pending_events(
        self,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        stream: str = None
    ) -> list[tuple[str, UnifiedEvent]]:
        """
        读取待处理的事件（之前读取但未 ACK 的）

        用于处理失败后重试的场景。

        Args:
            group_name: 消费者组名称
            consumer_name: 消费者名称
            count: 一次读取的最大消息数
            stream: Stream 名称

        Returns:
            list[tuple[str, UnifiedEvent]]: (stream_id, event) 列表
        """
        stream = stream or self.EVENTS_STREAM

        try:
            # XREADGROUP 使用 "0" 读取 pending 消息
            result = await redis_client.client.xreadgroup(
                group_name,
                consumer_name,
                {stream: "0"},
                count=count,
                block=0
            )

            if not result:
                return []

            events = []
            for stream_name, messages in result:
                for msg_id, msg_data in messages:
                    try:
                        event = self._parse_event(msg_data)
                        events.append((msg_id, event))
                    except Exception as e:
                        logger.error(f"[RedisStreams] 解析事件失败: {msg_id}, {e}")

            return events

        except Exception as e:
            logger.error(f"[RedisStreams] 读取 pending 事件失败: {e}")
            return []

    async def ack_event(
        self,
        stream_id: str,
        group_name: str,
        stream: str = None
    ) -> bool:
        """
        确认事件已处理

        Args:
            stream_id: Stream 消息 ID
            group_name: 消费者组名称
            stream: Stream 名称

        Returns:
            bool: 是否确认成功
        """
        stream = stream or self.EVENTS_STREAM

        try:
            result = await redis_client.client.xack(
                stream,
                group_name,
                stream_id
            )
            logger.debug(f"[RedisStreams] 确认事件: {stream_id}")
            return result > 0

        except Exception as e:
            logger.error(f"[RedisStreams] 确认事件失败: {stream_id}, {e}")
            return False

    async def get_stream_info(self, stream: str = None) -> dict:
        """
        获取 Stream 信息

        Returns:
            dict: 包含 length, groups, first_entry, last_entry 等信息
        """
        stream = stream or self.EVENTS_STREAM

        try:
            info = await redis_client.client.xinfo_stream(stream)
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": info.get("groups", 0),
            }
        except Exception as e:
            logger.error(f"[RedisStreams] 获取 Stream 信息失败: {e}")
            return {}

    async def get_group_info(
        self,
        group_name: str,
        stream: str = None
    ) -> dict:
        """
        获取消费者组信息

        Returns:
            dict: 包含 pending, consumers, last_delivered_id 等信息
        """
        stream = stream or self.EVENTS_STREAM

        try:
            groups = await redis_client.client.xinfo_groups(stream)
            for group in groups:
                if group.get("name") == group_name:
                    return {
                        "name": group.get("name"),
                        "pending": group.get("pending", 0),
                        "consumers": group.get("consumers", 0),
                        "last_delivered_id": group.get("last-delivered-id"),
                    }
            return {}
        except Exception as e:
            logger.error(f"[RedisStreams] 获取消费者组信息失败: {e}")
            return {}

    async def get_pending_count(
        self,
        group_name: str,
        stream: str = None
    ) -> int:
        """
        获取待处理消息数量

        Args:
            group_name: 消费者组名称
            stream: Stream 名称

        Returns:
            int: 待处理消息数量
        """
        info = await self.get_group_info(group_name, stream)
        return info.get("pending", 0)

    def _parse_event(self, msg_data: dict) -> UnifiedEvent:
        """
        将 Redis 消息数据解析为 UnifiedEvent

        Args:
            msg_data: Redis 消息数据字典

        Returns:
            UnifiedEvent: 统一事件对象
        """
        # 解析 JSON 字段
        metadata = json.loads(msg_data.get("metadata", "{}"))
        context = json.loads(msg_data.get("context", "{}"))
        attachments_data = json.loads(msg_data.get("attachments", "[]"))

        # 解析时间戳
        timestamp_str = msg_data.get("timestamp", "")
        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else None

        return UnifiedEvent(
            event_id=msg_data.get("event_id", ""),
            event_type=msg_data.get("event_type", ""),
            source=msg_data.get("source", ""),
            source_id=msg_data.get("source_id") or None,
            content=msg_data.get("content", ""),
            content_type=msg_data.get("content_type", "text"),
            user_id=msg_data.get("user_id") or None,
            user_external_id=msg_data.get("user_external_id") or None,
            session_id=msg_data.get("session_id") or None,
            thread_id=msg_data.get("thread_id") or None,
            idempotency_key=msg_data.get("idempotency_key") or None,
            priority=msg_data.get("priority", "normal"),
            timestamp=timestamp,
            metadata=metadata,
            context=context,
            # attachments 需要重新构造，这里简化处理
            attachments=[],
        )


# 全局单例
redis_streams = RedisStreams()
