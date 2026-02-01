# app/agents/base.py
# Agent 基类
#
# 使用 LangGraph 构建 Agent 执行流程
# Agent = LLM + Prompt + Tools + 状态机
#
# 执行流程：
# 1. 接收输入
# 2. LLM 思考 + 决策
# 3. 如需调用工具 → 执行工具 → 返回步骤 2
# 4. 输出最终结果

import json
from abc import ABC, abstractmethod
from typing import Any, Optional, TypedDict
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, END

from app.core.logging import get_logger
from app.core.config import settings as app_settings
from app.llm.gateway import LLMGateway, llm_gateway
from app.llm.prompts import prompt_manager
from app.tools.registry import tool_registry

logger = get_logger(__name__)


class AgentState(TypedDict, total=False):
    """
    Agent 状态

    LangGraph 使用状态来跟踪执行过程
    """
    # 输入
    input: str
    input_data: dict

    # 消息历史
    messages: list[dict]

    # 工具调用
    tool_calls: list[dict]
    tool_results: list[dict]

    # 输出
    output: str
    output_data: dict

    # 执行信息
    iterations: int
    error: Optional[str]


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    output: str
    data: dict = field(default_factory=dict)
    tool_calls: list[dict] = field(default_factory=list)
    iterations: int = 0
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Agent 基类

    所有 Agent 都应继承此类，并实现必要的方法。

    使用方法：
        class MyAgent(BaseAgent):
            name = "my_agent"
            description = "我的 Agent"
            prompt_name = "my_agent_prompt"
            tools = ["tool1", "tool2"]

            def process_output(self, state: AgentState) -> dict:
                # 处理输出
                return {"result": state["output"]}

        agent = MyAgent()
        result = await agent.run("用户输入")
    """

    # Agent 名称
    name: str = "base"
    # Agent 描述
    description: str = ""
    # 使用的 Prompt 名称
    prompt_name: str = ""
    # 可用的工具列表
    tools: list[str] = []
    # 默认模型（None 表示使用配置文件中的默认模型）
    model: str = None
    # 最大迭代次数（防止无限循环）
    max_iterations: int = 10

    def _get_model(self) -> str:
        """
        获取要使用的模型

        优先级：
        1. Agent 显式指定的模型
        2. 环境变量 DEFAULT_LLM_MODEL（Worker 从数据库加载后设置）
        3. config.py 默认值
        """
        if self.model:
            return self.model
        import os
        return os.environ.get("DEFAULT_LLM_MODEL") or app_settings.DEFAULT_LLM_MODEL

    def __init__(
        self,
        llm: Optional[LLMGateway] = None,
    ):
        self.llm = llm or llm_gateway
        self._graph = None

    async def load_config_from_db(self, db):
        """
        从数据库加载 Agent 配置

        这会覆盖类属性中的默认值。
        应该在 Agent 初始化后调用。

        Args:
            db: AsyncSession - 数据库会话
        """
        from app.llm.settings_loader import load_agent_config

        config = await load_agent_config(db, self.name)

        # 只有配置存在时才覆盖
        if config.get("model"):
            self.model = config["model"]
            logger.debug(f"[Agent:{self.name}] 从数据库加载模型配置: {self.model}")

        if config.get("temperature") is not None:
            self.temperature = config["temperature"]
            logger.debug(f"[Agent:{self.name}] 从数据库加载温度配置: {self.temperature}")

        if config.get("max_tokens") is not None:
            self.max_tokens = config["max_tokens"]
            logger.debug(f"[Agent:{self.name}] 从数据库加载 max_tokens 配置: {self.max_tokens}")

    async def _build_graph(self) -> StateGraph:
        """
        构建 LangGraph 执行图

        默认流程：think → (tool_call → tool_execute)* → output
        子类可以重写此方法自定义流程
        """
        graph = StateGraph(AgentState)

        # 添加节点
        graph.add_node("think", self._think)
        graph.add_node("execute_tools", self._execute_tools)
        graph.add_node("output", self._output)

        # 设置入口
        graph.set_entry_point("think")

        # 添加条件边
        graph.add_conditional_edges(
            "think",
            self._should_execute_tools,
            {
                "execute": "execute_tools",
                "output": "output",
            },
        )

        # 工具执行后继续思考
        graph.add_edge("execute_tools", "think")

        # 输出后结束
        graph.add_edge("output", END)

        return graph.compile()

    async def run(
        self,
        input_text: str,
        *,
        input_data: Optional[dict] = None,
        **kwargs,
    ) -> AgentResult:
        """
        执行 Agent

        Args:
            input_text: 用户输入文本
            input_data: 额外的输入数据
            **kwargs: 其他参数

        Returns:
            AgentResult: 执行结果
        """
        logger.info(f"[Agent:{self.name}] 开始执行")
        logger.debug(f"[Agent:{self.name}] 输入: {input_text[:100]}...")

        # 构建图（如果还没有）
        if self._graph is None:
            self._graph = await self._build_graph()

        # 初始化状态
        initial_state: AgentState = {
            "input": input_text,
            "input_data": input_data or {},
            "messages": [],
            "tool_calls": [],
            "tool_results": [],
            "output": "",
            "output_data": {},
            "iterations": 0,
            "error": None,
        }

        try:
            # 执行图
            final_state = await self._graph.ainvoke(initial_state)

            result = AgentResult(
                success=final_state.get("error") is None,
                output=final_state.get("output", ""),
                data=final_state.get("output_data", {}),
                tool_calls=final_state.get("tool_calls", []),
                iterations=final_state.get("iterations", 0),
                error=final_state.get("error"),
            )

            logger.info(f"[Agent:{self.name}] 完成，迭代 {result.iterations} 次")
            return result

        except Exception as e:
            logger.error(f"[Agent:{self.name}] 执行失败: {e}")
            return AgentResult(
                success=False,
                output="",
                error=str(e),
            )

    async def _get_system_prompt(self) -> str:
        """获取系统提示"""
        if self.prompt_name:
            prompt = await prompt_manager.get_prompt(self.prompt_name)
            if prompt:
                return prompt
        return self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """默认系统提示"""
        return f"你是一个 AI 助手，名为 {self.name}。{self.description}"

    async def _think(self, state: AgentState) -> AgentState:
        """
        思考节点：调用 LLM 进行推理
        """
        state["iterations"] = state.get("iterations", 0) + 1

        # 检查迭代次数
        if state["iterations"] > self.max_iterations:
            state["error"] = f"超过最大迭代次数 {self.max_iterations}"
            return state

        # 构建消息
        messages = state.get("messages", [])

        # 首次调用，添加用户消息
        if not messages:
            messages.append({
                "role": "user",
                "content": state["input"],
            })

        # 获取系统提示
        system_prompt = await self._get_system_prompt()

        # 获取工具 schema
        tool_schemas = []
        if self.tools:
            tool_schemas = tool_registry.get_schemas(self.tools, format="openai")

        logger.debug(f"[Agent:{self.name}] 思考 (迭代 {state['iterations']})")

        # 获取模型
        model = self._get_model()

        # 调用 LLM
        if tool_schemas:
            content, tool_calls = await self.llm.chat_with_tools(
                messages[-1]["content"] if messages else state["input"],
                tools=tool_schemas,
                system=system_prompt,
                model=model,
            )

            if tool_calls:
                state["tool_calls"] = tool_calls

            if content:
                messages.append({
                    "role": "assistant",
                    "content": content,
                })
        else:
            response = await self.llm.chat(
                messages[-1]["content"] if messages else state["input"],
                system=system_prompt,
                model=model,
            )
            messages.append({
                "role": "assistant",
                "content": response.content,
            })

        state["messages"] = messages
        return state

    def _should_execute_tools(self, state: AgentState) -> str:
        """
        决策：是否需要执行工具
        """
        if state.get("error"):
            return "output"

        if state.get("tool_calls"):
            return "execute"

        return "output"

    async def _execute_tools(self, state: AgentState) -> AgentState:
        """
        执行工具节点
        """
        tool_calls = state.get("tool_calls", [])
        results = []

        for call in tool_calls:
            tool_name = call.get("name")
            arguments = call.get("arguments", {})

            logger.info(f"[Agent:{self.name}] 调用工具: {tool_name}")

            try:
                result = await tool_registry.execute(tool_name, **arguments)
                results.append({
                    "tool": tool_name,
                    "success": True,
                    "result": result,
                })
            except Exception as e:
                logger.error(f"[Agent:{self.name}] 工具调用失败: {e}")
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": str(e),
                })

        # 添加工具结果到消息
        state["tool_results"].extend(results)

        # 添加工具结果消息
        messages = state.get("messages", [])
        for result in results:
            messages.append({
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False),
            })

        state["messages"] = messages
        state["tool_calls"] = []  # 清空工具调用

        return state

    async def _output(self, state: AgentState) -> AgentState:
        """
        输出节点：处理最终输出
        """
        messages = state.get("messages", [])

        if messages:
            # 获取最后一条助手消息
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    state["output"] = msg.get("content", "")
                    break

        # 调用子类的输出处理
        state["output_data"] = await self.process_output(state)

        return state

    @abstractmethod
    async def process_output(self, state: AgentState) -> dict:
        """
        处理输出（子类必须实现）

        Args:
            state: 当前状态

        Returns:
            dict: 结构化输出数据
        """
        pass

    async def run_stream(
        self,
        input_text: str,
        *,
        input_data: Optional[dict] = None,
        **kwargs,
    ):
        """
        流式执行 Agent（逐 token 输出）

        适用于需要实时显示输出的场景（如 SSE）。
        默认实现不支持流式，子类可重写此方法。

        Args:
            input_text: 用户输入文本
            input_data: 额外的输入数据
            **kwargs: 其他参数

        Yields:
            str: 文本片段
        """
        # 默认实现：调用 run() 并一次性输出
        result = await self.run(input_text, input_data=input_data, **kwargs)
        if result.success and result.output:
            yield result.output
        elif result.error:
            yield f"错误: {result.error}"
