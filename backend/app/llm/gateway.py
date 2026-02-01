# app/llm/gateway.py
# LLM Gateway - 统一的大模型调用接口
#
# 功能说明：
# 1. 封装 LiteLLM，支持多模型统一调用
# 2. 从数据库加载 Prompt 模板
# 3. 支持流式输出
# 4. 调用日志记录
#
# 支持的模型：
# - claude-3-opus-20240229
# - claude-3-sonnet-20240229
# - claude-3-haiku-20240307
# - gpt-4-turbo-preview
# - gpt-4
# - gpt-3.5-turbo
# - 自定义本地模型

import json
import os
from typing import Optional, AsyncIterator, Any, Union
from dataclasses import dataclass

import litellm
from litellm import acompletion

from app.core.config import settings
from app.core.logging import get_logger

# 获取 logger
logger = get_logger(__name__)


def get_default_model() -> str:
    """
    获取默认 LLM 模型

    优先级：
    1. 环境变量 DEFAULT_LLM_MODEL（由 Worker 从数据库加载后设置）
    2. config.py 中的默认值
    """
    return os.environ.get("DEFAULT_LLM_MODEL") or settings.DEFAULT_LLM_MODEL

# 配置 LiteLLM
litellm.set_verbose = False  # 生产环境关闭详细日志


@dataclass
class LLMResponse:
    """LLM 响应数据类"""
    content: str
    model: str
    usage: dict
    finish_reason: str
    raw_response: Optional[Any] = None


class LLMGateway:
    """
    LLM Gateway - 统一的大模型调用接口

    使用方法：
        gateway = LLMGateway()

        # 简单调用
        response = await gateway.chat("你好")

        # 使用系统提示
        response = await gateway.chat(
            "分析这封邮件的意图",
            system="你是一个邮件分析助手",
        )

        # 流式输出
        async for chunk in gateway.chat_stream("写一首诗"):
            print(chunk, end="")

        # 指定模型
        response = await gateway.chat(
            "你好",
            model="gpt-4-turbo-preview",
        )
    """

    # 模型别名映射
    MODEL_ALIASES = {
        "claude-opus": "claude-3-opus-20240229",
        "claude-sonnet": "claude-3-sonnet-20240229",
        "claude-haiku": "claude-3-haiku-20240307",
        "gpt-4": "gpt-4-turbo-preview",
        "gpt-4-turbo": "gpt-4-turbo-preview",
        "gpt-3.5": "gpt-3.5-turbo",
    }

    def __init__(self, default_model: Optional[str] = None):
        """
        初始化 LLM Gateway

        Args:
            default_model: 默认使用的模型（如果不传则动态获取）
        """
        # 如果显式指定了模型，使用指定的；否则标记为动态获取
        self._explicit_model = default_model
        self._prompt_cache: dict = {}

    @property
    def default_model(self) -> str:
        """
        获取默认模型

        如果初始化时显式指定了模型，使用指定的；
        否则动态获取（支持运行时从数据库加载的配置）
        """
        if self._explicit_model:
            return self._explicit_model
        return get_default_model()

    def _resolve_model(self, model: Optional[str]) -> str:
        """解析模型名称，支持别名"""
        if model is None:
            return self.default_model
        return self.MODEL_ALIASES.get(model, model)

    async def chat(
        self,
        message: str,
        *,
        history: Optional[list[dict]] = None,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        发送聊天请求

        Args:
            message: 用户消息
            history: 历史消息列表（可选）
            system: 系统提示（可选）
            model: 模型名称（可选，使用默认模型）
            temperature: 温度参数 (0-1)
            max_tokens: 最大输出 token 数
            response_format: 响应格式（用于 JSON 模式）
            **kwargs: 其他 LiteLLM 参数

        Returns:
            LLMResponse: 响应对象
        """
        model = self._resolve_model(model)

        # 构建消息列表
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        # 添加历史消息
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        logger.info(f"[LLM] 调用模型: {model}")
        logger.debug(f"[LLM] 消息: {message[:100]}...")

        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                **kwargs,
            )

            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            logger.info(f"[LLM] 完成，使用 {usage['total_tokens']} tokens")

            return LLMResponse(
                content=content,
                model=model,
                usage=usage,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response,
            )

        except Exception as e:
            logger.error(f"[LLM] 调用失败: {e}")
            raise

    async def chat_stream(
        self,
        message: str,
        *,
        history: Optional[list[dict]] = None,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        流式聊天请求

        Args:
            message: 用户消息
            history: 历史消息列表
            system: 系统提示
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大输出 token
            **kwargs: 其他参数

        Yields:
            str: 逐个输出的文本片段
        """
        model = self._resolve_model(model)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        # 添加历史消息
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        logger.info(f"[LLM Stream] 调用模型: {model}")

        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"[LLM Stream] 调用失败: {e}")
            raise

    async def chat_with_tools(
        self,
        message: str,
        tools: list[dict],
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> tuple[Optional[str], Optional[list[dict]]]:
        """
        带工具调用的聊天

        Args:
            message: 用户消息
            tools: 工具定义列表（OpenAI 格式）
            system: 系统提示
            model: 模型名称
            temperature: 温度参数

        Returns:
            tuple: (文本响应, 工具调用列表)
        """
        model = self._resolve_model(model)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})

        logger.info(f"[LLM Tools] 调用模型: {model}, 工具数: {len(tools)}")

        try:
            response = await acompletion(
                model=model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                **kwargs,
            )

            choice = response.choices[0]
            content = choice.message.content
            tool_calls = None

            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in choice.message.tool_calls
                ]
                logger.info(f"[LLM Tools] 工具调用: {[t['name'] for t in tool_calls]}")

            return content, tool_calls

        except Exception as e:
            logger.error(f"[LLM Tools] 调用失败: {e}")
            raise

    async def chat_json(
        self,
        message: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        请求 JSON 格式响应

        Args:
            message: 用户消息
            system: 系统提示
            model: 模型名称

        Returns:
            dict: 解析后的 JSON 对象
        """
        # 在系统提示中强调返回 JSON
        if system:
            system = f"{system}\n\n重要：请只返回有效的 JSON 格式，不要包含其他文本。"
        else:
            system = "请只返回有效的 JSON 格式，不要包含其他文本。"

        response = await self.chat(
            message,
            system=system,
            model=model,
            response_format={"type": "json_object"},
            **kwargs,
        )

        try:
            # 尝试解析 JSON
            content = response.content.strip()
            # 处理可能的 markdown 代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"[LLM JSON] 解析失败: {e}")
            logger.error(f"[LLM JSON] 原始内容: {response.content}")
            raise ValueError(f"无法解析 LLM 返回的 JSON: {e}")


# 全局单例
llm_gateway = LLMGateway()


# 便捷函数
async def chat(message: str, **kwargs) -> LLMResponse:
    """便捷函数：发送聊天请求"""
    return await llm_gateway.chat(message, **kwargs)


async def chat_stream(message: str, **kwargs) -> AsyncIterator[str]:
    """便捷函数：流式聊天请求"""
    async for chunk in llm_gateway.chat_stream(message, **kwargs):
        yield chunk
