# app/tools/http.py
# HTTP 请求 Tool
#
# 提供 Agent 调用外部 API 的能力

import json
from typing import Optional

import httpx

from app.core.logging import get_logger
from app.tools.base import BaseTool, tool
from app.tools.registry import register_tool

logger = get_logger(__name__)


@register_tool
class HTTPTool(BaseTool):
    """
    HTTP 请求工具

    提供 Agent 调用外部 API 的能力
    """

    name = "http"
    description = "发送 HTTP 请求，调用外部 API"

    # 请求超时时间（秒）
    DEFAULT_TIMEOUT = 30

    @tool(
        name="http_get",
        description="发送 HTTP GET 请求",
        parameters={
            "url": {
                "type": "string",
                "description": "请求 URL",
            },
            "headers": {
                "type": "object",
                "description": "请求头（可选）",
            },
            "params": {
                "type": "object",
                "description": "URL 参数（可选）",
            },
        },
    )
    async def http_get(
        self,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """发送 GET 请求"""
        logger.info(f"[HTTPTool] GET {url}")

        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
            try:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                )

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": self._parse_response(response),
                }

            except httpx.TimeoutException:
                return {
                    "success": False,
                    "error": "请求超时",
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                }

    @tool(
        name="http_post",
        description="发送 HTTP POST 请求",
        parameters={
            "url": {
                "type": "string",
                "description": "请求 URL",
            },
            "data": {
                "type": "object",
                "description": "请求体数据（JSON）",
            },
            "headers": {
                "type": "object",
                "description": "请求头（可选）",
            },
        },
    )
    async def http_post(
        self,
        url: str,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> dict:
        """发送 POST 请求"""
        logger.info(f"[HTTPTool] POST {url}")

        # 默认使用 JSON 内容类型
        if headers is None:
            headers = {}
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
            try:
                response = await client.post(
                    url,
                    json=data,
                    headers=headers,
                )

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": self._parse_response(response),
                }

            except httpx.TimeoutException:
                return {
                    "success": False,
                    "error": "请求超时",
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                }

    @tool(
        name="webhook_call",
        description="调用 Webhook URL",
        parameters={
            "url": {
                "type": "string",
                "description": "Webhook URL",
            },
            "payload": {
                "type": "object",
                "description": "发送的数据",
            },
        },
    )
    async def webhook_call(
        self,
        url: str,
        payload: dict,
    ) -> dict:
        """调用 Webhook"""
        logger.info(f"[HTTPTool] Webhook {url}")

        return await self.http_post(
            url=url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Concord-AI/1.0",
            },
        )

    def _parse_response(self, response: httpx.Response) -> any:
        """解析响应体"""
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        else:
            return response.text
