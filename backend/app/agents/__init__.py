# app/agents/__init__.py
# Agent Layer - 智能代理模块
#
# Agent 是 LLM + Prompt + Tools 的组合，负责：
# 1. 理解用户意图
# 2. 决策下一步行动
# 3. 调用合适的工具
# 4. 返回结构化结果
#
# 使用 LangGraph 构建，支持：
# - 状态机式的执行流程
# - 可视化调试
# - 与 Temporal 集成

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry, agent_registry
from app.agents.chat_agent import ChatAgent, chat_agent

# 导入 Agent 实现以触发注册
from app.agents import email_summarizer  # noqa: F401
from app.agents import work_type_analyzer  # noqa: F401
from app.agents import customer_extractor  # noqa: F401
from app.agents import add_new_client_helper  # noqa: F401

__all__ = [
    "BaseAgent",
    "AgentRegistry",
    "agent_registry",
    "ChatAgent",
    "chat_agent",
]
