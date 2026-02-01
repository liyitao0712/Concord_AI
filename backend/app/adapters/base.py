# app/adapters/base.py
# 适配器基类
#
# 定义适配器的标准接口，所有渠道适配器都需要实现这些方法

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.schemas.event import UnifiedEvent, EventResponse


class BaseAdapter(ABC):
    """
    适配器基类

    所有渠道适配器都需要继承此类，并实现以下方法：
    - to_unified_event: 将原始数据转换为统一事件
    - send_response: 将响应发送回原渠道

    示例：
        class FeishuAdapter(BaseAdapter):
            async def to_unified_event(self, raw_data: dict) -> UnifiedEvent:
                # 解析飞书消息格式
                ...

            async def send_response(self, event: UnifiedEvent, response: EventResponse) -> None:
                # 通过飞书 API 发送回复
                ...
    """

    # 适配器名称
    name: str = "base"

    @abstractmethod
    async def to_unified_event(self, raw_data: dict) -> UnifiedEvent:
        """
        将原始数据转换为统一事件

        Args:
            raw_data: 原始请求数据（各渠道格式不同）

        Returns:
            UnifiedEvent: 统一事件对象

        Raises:
            ValueError: 数据格式错误时抛出
        """
        pass

    @abstractmethod
    async def send_response(
        self,
        event: UnifiedEvent,
        response: EventResponse,
        content: Optional[str] = None,
    ) -> None:
        """
        将响应发送回原渠道

        Args:
            event: 原始事件（包含回复所需的上下文信息）
            response: 统一响应对象
            content: 回复内容（如果有）

        Raises:
            Exception: 发送失败时抛出
        """
        pass

    async def validate(self, raw_data: dict) -> bool:
        """
        验证原始数据格式是否有效

        Args:
            raw_data: 原始请求数据

        Returns:
            bool: 数据是否有效
        """
        return True

    def get_idempotency_key(self, raw_data: dict) -> Optional[str]:
        """
        从原始数据中提取幂等键

        用于防止重复处理同一请求

        Args:
            raw_data: 原始请求数据

        Returns:
            Optional[str]: 幂等键，如果无法提取则返回 None
        """
        return None
