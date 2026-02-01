# app/tools/__init__.py
# Tools Layer - Agent 可调用的工具
#
# Tool 是 Agent 的能力扩展，提供：
# - 数据库查询
# - 邮件发送/读取
# - 文件操作
# - HTTP 请求
# - 等等...
#
# Tool 设计原则：
# 1. 每个 Tool 是原子操作，做一件事
# 2. Tool 有清晰的输入输出定义
# 3. Tool 可以被 LLM 通过 Function Calling 调用
# 4. Tool 自动生成 OpenAI 格式的 schema

from app.tools.base import BaseTool, tool
from app.tools.registry import ToolRegistry, tool_registry

# 导入 Tool 实现以触发注册
from app.tools import database  # noqa: F401
from app.tools import http  # noqa: F401
from app.tools import email  # noqa: F401
from app.tools import file  # noqa: F401
from app.tools import pdf  # noqa: F401
from app.tools import email_cleaner  # noqa: F401

__all__ = [
    "BaseTool",
    "tool",
    "ToolRegistry",
    "tool_registry",
]
