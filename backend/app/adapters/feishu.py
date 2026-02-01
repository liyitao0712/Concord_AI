# app/adapters/feishu.py
# 飞书适配器
#
# 功能说明：
# 1. FeishuClient - 飞书 API 客户端
# 2. FeishuAdapter - 飞书消息 → UnifiedEvent 转换
#
# 飞书消息格式参考：
# https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/events/receive

import json
import time
from typing import Optional, Any

import httpx

from app.core.logging import get_logger
from app.core.config import settings
from app.adapters.base import BaseAdapter
from app.schemas.event import UnifiedEvent, EventResponse

logger = get_logger(__name__)


class FeishuClient:
    """
    飞书 API 客户端

    封装飞书开放平台 API 调用

    使用方法：
        client = FeishuClient(app_id="xxx", app_secret="xxx")

        # 发送文本消息
        await client.send_text(
            receive_id="ou_xxx",
            receive_id_type="open_id",
            text="你好",
        )

        # 发送富文本消息
        await client.send_post(
            receive_id="oc_xxx",
            receive_id_type="chat_id",
            content={"title": "标题", "content": [[{"tag": "text", "text": "内容"}]]}
        )
    """

    BASE_URL = "https://open.feishu.cn/open-apis"
    TOKEN_URL = "/auth/v3/tenant_access_token/internal"
    SEND_MSG_URL = "/im/v1/messages"
    REPLY_MSG_URL = "/im/v1/messages/{message_id}/reply"

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
    ):
        """
        初始化飞书客户端

        Args:
            app_id: 飞书应用 App ID
            app_secret: 飞书应用 App Secret
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    def configure(self, app_id: str, app_secret: str) -> None:
        """动态配置凭证"""
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token = None
        self._token_expires_at = 0

    async def _get_access_token(self) -> str:
        """
        获取 tenant_access_token

        Token 有效期为 2 小时，会自动缓存和刷新
        """
        # 检查 token 是否仍然有效（提前 5 分钟刷新）
        if self._access_token and time.time() < self._token_expires_at - 300:
            return self._access_token

        if not self.app_id or not self.app_secret:
            raise ValueError("飞书 App ID 和 App Secret 未配置")

        url = f"{self.BASE_URL}{self.TOKEN_URL}"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        if data.get("code") != 0:
            raise Exception(f"获取飞书 Token 失败: {data.get('msg')}")

        self._access_token = data["tenant_access_token"]
        # Token 有效期 2 小时
        self._token_expires_at = time.time() + data.get("expire", 7200)

        logger.info("飞书 Token 获取成功")
        return self._access_token

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> dict:
        """
        发送 API 请求

        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: 查询参数
            json_data: 请求体

        Returns:
            dict: 响应数据
        """
        token = await self._get_access_token()
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json_data,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def send_text(
        self,
        receive_id: str,
        receive_id_type: str,
        text: str,
    ) -> dict:
        """
        发送文本消息

        Args:
            receive_id: 接收者 ID
            receive_id_type: ID 类型 (open_id / user_id / union_id / email / chat_id)
            text: 文本内容

        Returns:
            dict: 发送结果
        """
        content = json.dumps({"text": text})
        return await self._send_message(
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            msg_type="text",
            content=content,
        )

    async def send_post(
        self,
        receive_id: str,
        receive_id_type: str,
        content: dict,
    ) -> dict:
        """
        发送富文本消息

        Args:
            receive_id: 接收者 ID
            receive_id_type: ID 类型
            content: 富文本内容（包含 title 和 content）

        Returns:
            dict: 发送结果

        富文本格式：
            {
                "zh_cn": {
                    "title": "标题",
                    "content": [
                        [{"tag": "text", "text": "内容"}],
                        [{"tag": "a", "text": "链接", "href": "https://..."}]
                    ]
                }
            }
        """
        return await self._send_message(
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            msg_type="post",
            content=json.dumps(content),
        )

    async def _send_message(
        self,
        receive_id: str,
        receive_id_type: str,
        msg_type: str,
        content: str,
    ) -> dict:
        """发送消息的底层方法"""
        endpoint = f"{self.SEND_MSG_URL}?receive_id_type={receive_id_type}"
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": content,
        }

        result = await self._request("POST", endpoint, json_data=payload)

        if result.get("code") != 0:
            logger.error(f"飞书消息发送失败: {result.get('msg')}")
            raise Exception(f"发送消息失败: {result.get('msg')}")

        logger.info(f"飞书消息发送成功: {receive_id}")
        return result

    async def reply_message(
        self,
        message_id: str,
        msg_type: str,
        content: str,
    ) -> dict:
        """
        回复消息

        Args:
            message_id: 要回复的消息 ID
            msg_type: 消息类型
            content: 消息内容

        Returns:
            dict: 发送结果
        """
        endpoint = self.REPLY_MSG_URL.format(message_id=message_id)
        payload = {
            "msg_type": msg_type,
            "content": content,
        }

        result = await self._request("POST", endpoint, json_data=payload)

        if result.get("code") != 0:
            logger.error(f"飞书消息回复失败: {result.get('msg')}")
            raise Exception(f"回复消息失败: {result.get('msg')}")

        logger.info(f"飞书消息回复成功: {message_id}")
        return result

    async def test_connection(self) -> bool:
        """
        测试连接是否正常

        Returns:
            bool: 连接是否成功
        """
        try:
            await self._get_access_token()
            return True
        except Exception as e:
            logger.error(f"飞书连接测试失败: {e}")
            return False


class FeishuAdapter(BaseAdapter):
    """
    飞书适配器

    将飞书消息转换为 UnifiedEvent，并支持发送回复

    飞书消息格式示例：
        {
            "schema": "2.0",
            "header": {
                "event_id": "xxx",
                "event_type": "im.message.receive_v1",
                "create_time": "1234567890",
                "token": "xxx",
                "app_id": "cli_xxx",
                "tenant_key": "xxx"
            },
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_xxx", "user_id": "xxx"},
                    "sender_type": "user"
                },
                "message": {
                    "message_id": "om_xxx",
                    "root_id": "om_xxx",
                    "parent_id": "om_xxx",
                    "create_time": "1234567890",
                    "chat_id": "oc_xxx",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": "{\"text\":\"@_user_1 你好\"}"
                }
            }
        }
    """

    name = "feishu"

    def __init__(self, client: Optional[FeishuClient] = None):
        """
        初始化飞书适配器

        Args:
            client: 飞书客户端实例
        """
        self.client = client or FeishuClient()

    async def to_unified_event(self, raw_data: dict) -> UnifiedEvent:
        """
        将飞书消息转换为统一事件

        Args:
            raw_data: 飞书回调的原始数据

        Returns:
            UnifiedEvent: 统一事件对象
        """
        header = raw_data.get("header", {})
        event = raw_data.get("event", {})
        sender = event.get("sender", {})
        message = event.get("message", {})
        sender_id = sender.get("sender_id", {})

        # 解析消息内容
        content = self._parse_content(message)

        # 提取 @机器人 后的真实消息
        content = self._extract_real_content(content)

        return UnifiedEvent(
            event_id=header.get("event_id", ""),
            event_type="chat",
            source="feishu",
            source_id=message.get("message_id"),
            user_external_id=sender_id.get("open_id"),
            user_name=sender.get("sender_type"),
            session_id=message.get("chat_id"),
            content=content,
            content_type="text",
            metadata={
                "chat_type": message.get("chat_type"),  # p2p / group
                "message_type": message.get("message_type"),
                "root_id": message.get("root_id"),
                "parent_id": message.get("parent_id"),
                "app_id": header.get("app_id"),
                "tenant_key": header.get("tenant_key"),
            },
            idempotency_key=message.get("message_id"),
        )

    def _parse_content(self, message: dict) -> str:
        """解析消息内容"""
        message_type = message.get("message_type", "text")
        content_str = message.get("content", "{}")

        try:
            content_json = json.loads(content_str)
        except json.JSONDecodeError:
            return content_str

        if message_type == "text":
            return content_json.get("text", "")
        elif message_type == "post":
            # 富文本消息，提取纯文本
            return self._extract_post_text(content_json)
        else:
            # 其他类型，返回原始内容
            return content_str

    def _extract_post_text(self, content: dict) -> str:
        """从富文本消息中提取纯文本"""
        texts = []
        # 富文本可能有多语言版本
        for lang_content in content.values():
            if isinstance(lang_content, dict):
                for line in lang_content.get("content", []):
                    for item in line:
                        if item.get("tag") == "text":
                            texts.append(item.get("text", ""))
        return "".join(texts)

    def _extract_real_content(self, content: str) -> str:
        """
        提取 @机器人 后的真实消息内容

        飞书消息中 @机器人 会显示为 @_user_1 或类似格式
        """
        # 移除 @提及 标记
        import re
        # 匹配 @_user_N 格式
        content = re.sub(r"@_user_\d+\s*", "", content)
        # 移除首尾空白
        return content.strip()

    async def send_response(
        self,
        event: UnifiedEvent,
        response: EventResponse,
        content: Optional[str] = None,
    ) -> None:
        """
        发送响应回飞书

        Args:
            event: 原始事件
            response: 响应对象
            content: 回复内容
        """
        if not content:
            content = response.message or "处理完成"

        # 优先回复原消息
        message_id = event.source_id
        if message_id:
            try:
                await self.client.reply_message(
                    message_id=message_id,
                    msg_type="text",
                    content=json.dumps({"text": content}),
                )
                return
            except Exception as e:
                logger.warning(f"回复消息失败，尝试直接发送: {e}")

        # 如果回复失败，直接发送到群/私聊
        chat_id = event.session_id
        if chat_id:
            await self.client.send_text(
                receive_id=chat_id,
                receive_id_type="chat_id",
                text=content,
            )

    async def validate(self, raw_data: dict) -> bool:
        """验证飞书回调数据"""
        # 检查必要字段
        if "header" not in raw_data or "event" not in raw_data:
            return False

        header = raw_data.get("header", {})
        if not header.get("event_id"):
            return False

        return True

    def get_idempotency_key(self, raw_data: dict) -> Optional[str]:
        """获取幂等键"""
        event = raw_data.get("event", {})
        message = event.get("message", {})
        return message.get("message_id")


# 全局单例
feishu_client = FeishuClient()
feishu_adapter = FeishuAdapter(client=feishu_client)
