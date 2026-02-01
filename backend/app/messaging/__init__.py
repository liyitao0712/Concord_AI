# app/messaging/__init__.py
# 消息层模块
#
# 提供：
# 1. Redis Streams 事件流处理
# 2. 事件分发器

from app.messaging.streams import RedisStreams, redis_streams
from app.messaging.dispatcher import EventDispatcher, event_dispatcher

__all__ = [
    "RedisStreams",
    "redis_streams",
    "EventDispatcher",
    "event_dispatcher",
]
