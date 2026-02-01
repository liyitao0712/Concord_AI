# app/agents/chat_agent.py
# Chat Agent - 聊天对话 Agent
#
# 功能说明：
# 1. 继承 BaseAgent，使用 LangGraph 状态机
# 2. 支持多轮对话上下文（Redis 缓存）
# 3. 提供流式输出 (SSE)
# 4. 支持 Tools 调用（可选）
#
# 使用场景：
# - Web Chatbox 对话
# - 飞书机器人对话
#
# 架构：
# ┌─────────────────────────────────────────────────────────────┐
# │                ChatAgent (extends BaseAgent)                │
# ├─────────────────────────────────────────────────────────────┤
# │  run()         │ 继承自 BaseAgent，完整响应                 │
# │  run_stream()  │ 流式输出（SSE）                            │
# │  chat()        │ 会话式对话（自动管理上下文）               │
# │  chat_stream() │ 会话式流式对话                             │
# │  context       │ Redis 缓存（24h TTL）                      │
# └─────────────────────────────────────────────────────────────┘

import json
from typing import Optional, AsyncIterator
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.core.config import settings
from app.core.redis import redis_client
from app.llm.gateway import LLMGateway, llm_gateway
from app.agents.base import BaseAgent, AgentState, AgentResult
from app.agents.registry import register_agent

logger = get_logger(__name__)

# 上下文缓存 TTL（24小时）
CONTEXT_TTL = 24 * 60 * 60


@dataclass
class ChatResult:
    """对话结果"""
    success: bool
    content: str
    model: str = ""
    tokens_used: int = 0
    error: Optional[str] = None


@register_agent
class ChatAgent(BaseAgent):
    """
    聊天对话 Agent

    继承 BaseAgent，支持 LangGraph 状态机、Tools 调用。
    额外提供多轮对话上下文管理和流式输出。

    使用方法：
        agent = ChatAgent()

        # 方式一：使用 BaseAgent 的 run() 方法（一次性执行）
        result = await agent.run("你好")

        # 方式二：使用会话式对话（自动管理上下文）
        result = await agent.chat(
            session_id="session-123",
            message="你好",
        )

        # 方式三：流式对话
        async for chunk in agent.chat_stream(
            session_id="session-123",
            message="写一首诗",
        ):
            print(chunk, end="")
    """

    name = "chat_agent"
    description = "通用聊天助手，支持多轮对话和工具调用"
    prompt_name = "chat_agent"
    # 可用工具（默认不使用，可通过配置启用）
    tools = []
    model = None  # 使用数据库中配置的默认模型
    max_iterations = 5  # 对话场景不需要太多迭代
    max_context_messages = 20  # 最大上下文消息数

    def __init__(
        self,
        llm: Optional[LLMGateway] = None,
        system_prompt: Optional[str] = None,
        enable_tools: bool = False,
    ):
        """
        初始化 ChatAgent

        Args:
            llm: LLM Gateway 实例（可选）
            system_prompt: 自定义系统提示（可选）
            enable_tools: 是否启用工具调用
        """
        super().__init__(llm)
        self._custom_system_prompt = system_prompt
        if enable_tools:
            # 启用常用工具
            self.tools = ["search_customers", "search_products"]

    def _default_system_prompt(self) -> str:
        """默认系统提示"""
        if self._custom_system_prompt:
            return self._custom_system_prompt

        return """你是 Concord AI 智能助手，一个友好、专业的 AI 对话伙伴。

你的特点：
- 回答准确、简洁、有帮助
- 使用清晰的中文表达
- 保持友好和专业的语调
- 适时使用 Markdown 格式化输出

请根据用户的问题提供有价值的回答。"""

    async def process_output(self, state: AgentState) -> dict:
        """
        处理输出（实现 BaseAgent 抽象方法）
        """
        return {
            "response": state.get("output", ""),
            "tool_calls": state.get("tool_calls", []),
            "tool_results": state.get("tool_results", []),
        }

    # ========== 上下文管理 ==========

    def _context_key(self, session_id: str) -> str:
        """生成上下文缓存的 Redis Key"""
        return f"chat:context:{session_id}"

    async def _get_context(self, session_id: str) -> list[dict]:
        """
        从 Redis 获取对话上下文

        Args:
            session_id: 会话 ID

        Returns:
            list[dict]: 消息列表
        """
        key = self._context_key(session_id)
        try:
            data = await redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"[ChatAgent] 获取上下文失败: {e}")
        return []

    async def _save_context(self, session_id: str, messages: list[dict]) -> None:
        """
        保存对话上下文到 Redis

        Args:
            session_id: 会话 ID
            messages: 消息列表
        """
        key = self._context_key(session_id)

        # 限制消息数量
        if len(messages) > self.max_context_messages:
            messages = messages[-self.max_context_messages:]

        try:
            await redis_client.set(
                key,
                json.dumps(messages, ensure_ascii=False),
                ex=CONTEXT_TTL,
            )
        except Exception as e:
            logger.warning(f"[ChatAgent] 保存上下文失败: {e}")

    async def clear_context(self, session_id: str) -> None:
        """
        清除会话上下文

        Args:
            session_id: 会话 ID
        """
        key = self._context_key(session_id)
        try:
            await redis_client.delete(key)
            logger.info(f"[ChatAgent] 清除上下文: {session_id}")
        except Exception as e:
            logger.warning(f"[ChatAgent] 清除上下文失败: {e}")

    # ========== 会话式对话 ==========

    async def chat(
        self,
        session_id: str,
        message: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> ChatResult:
        """
        会话式对话（自动管理上下文）

        Args:
            session_id: 会话 ID
            message: 用户消息
            system_prompt: 系统提示（可选，覆盖默认）
            model: 模型名称（可选）
            temperature: 温度参数

        Returns:
            ChatResult: 对话结果
        """
        logger.info(f"[ChatAgent] 开始对话: session={session_id}")
        logger.debug(f"[ChatAgent] 用户消息: {message[:100]}...")

        # 获取上下文
        context_messages = await self._get_context(session_id)

        # 添加用户消息
        context_messages.append({"role": "user", "content": message})

        # 确定系统提示和模型
        system = system_prompt or self._default_system_prompt()
        use_model = model or self._get_model()

        try:
            # 调用 LLM
            response = await self.llm.chat(
                message=message,
                history=context_messages[:-1],  # 历史消息（不含当前消息）
                system=system,
                model=use_model,
                temperature=temperature,
            )

            # 保存上下文（包括助手回复）
            context_messages.append({"role": "assistant", "content": response.content})
            await self._save_context(session_id, context_messages)

            logger.info(f"[ChatAgent] 完成，使用 {response.usage.get('total_tokens', 0)} tokens")

            return ChatResult(
                success=True,
                content=response.content,
                model=use_model,
                tokens_used=response.usage.get("total_tokens", 0),
            )

        except Exception as e:
            logger.error(f"[ChatAgent] 对话失败: {e}")
            return ChatResult(
                success=False,
                content="",
                error=str(e),
            )

    async def chat_stream(
        self,
        session_id: str,
        message: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        流式会话对话（逐 token 输出）

        Args:
            session_id: 会话 ID
            message: 用户消息
            system_prompt: 系统提示
            model: 模型名称
            temperature: 温度参数

        Yields:
            str: 文本片段
        """
        logger.info(f"[ChatAgent] 流式对话: session={session_id}")
        logger.debug(f"[ChatAgent] 用户消息: {message[:100]}...")

        # 获取上下文
        context_messages = await self._get_context(session_id)

        # 添加用户消息到上下文
        context_messages.append({"role": "user", "content": message})

        # 确定系统提示和模型
        system = system_prompt or self._default_system_prompt()
        use_model = model or self._get_model()

        # 收集完整响应
        full_response = ""

        try:
            # 流式调用 LLM
            async for chunk in self.llm.chat_stream(
                message=message,
                history=context_messages[:-1],  # 历史消息
                system=system,
                model=use_model,
                temperature=temperature,
            ):
                full_response += chunk
                yield chunk

            # 保存上下文（包括助手回复）
            context_messages.append({"role": "assistant", "content": full_response})
            await self._save_context(session_id, context_messages)

            logger.info(f"[ChatAgent] 流式完成")

        except Exception as e:
            logger.error(f"[ChatAgent] 流式对话失败: {e}")
            raise

    # ========== 流式 run（重写 BaseAgent 方法） ==========

    async def run_stream(
        self,
        input_text: str,
        *,
        input_data: Optional[dict] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        流式执行（不使用会话上下文）

        适用于一次性流式输出场景。

        Args:
            input_text: 用户输入
            input_data: 额外数据
            **kwargs: 其他参数

        Yields:
            str: 文本片段
        """
        system = self._default_system_prompt()
        model = self._get_model()

        try:
            async for chunk in self.llm.chat_stream(
                message=input_text,
                system=system,
                model=model,
            ):
                yield chunk

        except Exception as e:
            logger.error(f"[ChatAgent] 流式执行失败: {e}")
            yield f"错误: {e}"

    # ========== 兼容旧 API ==========

    async def chat_with_history(
        self,
        messages: list[dict],
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> ChatResult:
        """
        使用显式历史消息对话（不使用 Redis 缓存）

        适用于从数据库加载历史消息的场景

        Args:
            messages: 消息历史列表 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示
            model: 模型名称
            temperature: 温度参数

        Returns:
            ChatResult: 对话结果
        """
        if not messages:
            return ChatResult(
                success=False,
                content="",
                error="消息列表为空",
            )

        system = system_prompt or self._default_system_prompt()
        use_model = model or self._get_model()

        # 获取最后一条用户消息
        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        if not last_user_message:
            return ChatResult(
                success=False,
                content="",
                error="未找到用户消息",
            )

        try:
            response = await self.llm.chat(
                message=last_user_message,
                history=messages[:-1],  # 除最后一条外的历史
                system=system,
                model=use_model,
                temperature=temperature,
            )

            return ChatResult(
                success=True,
                content=response.content,
                model=use_model,
                tokens_used=response.usage.get("total_tokens", 0),
            )

        except Exception as e:
            logger.error(f"[ChatAgent] 对话失败: {e}")
            return ChatResult(
                success=False,
                content="",
                error=str(e),
            )

    async def chat_stream_with_history(
        self,
        messages: list[dict],
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        使用显式历史消息进行流式对话（不使用 Redis 缓存）

        Args:
            messages: 消息历史列表
            system_prompt: 系统提示
            model: 模型名称
            temperature: 温度参数

        Yields:
            str: 文本片段
        """
        if not messages:
            raise ValueError("消息列表为空")

        system = system_prompt or self._default_system_prompt()
        use_model = model or self._get_model()

        # 获取最后一条用户消息
        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        if not last_user_message:
            raise ValueError("未找到用户消息")

        async for chunk in self.llm.chat_stream(
            message=last_user_message,
            history=messages[:-1],
            system=system,
            model=use_model,
            temperature=temperature,
        ):
            yield chunk


# 全局单例
chat_agent = ChatAgent()
