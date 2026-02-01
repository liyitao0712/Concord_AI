# app/tools/base.py
# Tool 基类和装饰器
#
# 提供 Tool 的基础框架：
# 1. @tool 装饰器 - 将方法标记为可被 Agent 调用的工具
# 2. BaseTool 基类 - 提供通用功能
# 3. 自动生成 OpenAI 格式的 Function Schema

import inspect
import functools
from typing import Any, Callable, Optional, get_type_hints
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[list] = None


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: list[ToolParameter]
    func: Callable
    returns: Optional[str] = None


def _python_type_to_json_type(python_type: type) -> str:
    """将 Python 类型转换为 JSON Schema 类型"""
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    # 处理 Optional 等复杂类型
    type_name = getattr(python_type, "__name__", str(python_type))

    if type_name in type_mapping:
        return type_mapping[type_name]

    if hasattr(python_type, "__origin__"):
        origin = python_type.__origin__
        if origin in type_mapping:
            return type_mapping[origin]

    return "string"


def tool(
    name: Optional[str] = None,
    description: str = "",
    parameters: Optional[dict] = None,
):
    """
    Tool 装饰器

    将方法标记为可被 Agent 调用的工具，并提取参数信息生成 schema。

    使用方法：
        class MyTool(BaseTool):
            @tool(
                name="search_products",
                description="搜索产品",
                parameters={
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "limit": {"type": "integer", "description": "返回数量", "default": 10},
                }
            )
            async def search_products(self, keyword: str, limit: int = 10) -> list:
                ...

    Args:
        name: 工具名称（默认使用函数名）
        description: 工具描述
        parameters: 参数定义（可选，会自动从函数签名推断）
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__

        # 提取参数信息
        sig = inspect.signature(func)
        type_hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}

        params = []
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            # 从装饰器参数或函数签名获取信息
            if parameters and param_name in parameters:
                param_def = parameters[param_name]
                params.append(ToolParameter(
                    name=param_name,
                    type=param_def.get("type", "string"),
                    description=param_def.get("description", ""),
                    required=param.default == inspect.Parameter.empty,
                    default=None if param.default == inspect.Parameter.empty else param.default,
                    enum=param_def.get("enum"),
                ))
            else:
                # 从类型提示推断
                param_type = type_hints.get(param_name, str)
                params.append(ToolParameter(
                    name=param_name,
                    type=_python_type_to_json_type(param_type),
                    description="",
                    required=param.default == inspect.Parameter.empty,
                    default=None if param.default == inspect.Parameter.empty else param.default,
                ))

        # 存储工具定义
        func._tool_definition = ToolDefinition(
            name=tool_name,
            description=description or func.__doc__ or "",
            parameters=params,
            func=func,
            returns=type_hints.get("return", None),
        )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(f"[Tool] 调用 {tool_name}: {kwargs}")
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"[Tool] {tool_name} 完成")
                return result
            except Exception as e:
                logger.error(f"[Tool] {tool_name} 失败: {e}")
                raise

        wrapper._tool_definition = func._tool_definition
        return wrapper

    return decorator


class BaseTool:
    """
    Tool 基类

    所有 Tool 类都应该继承此基类。

    使用方法：
        class EmailTool(BaseTool):
            name = "email"
            description = "邮件相关操作"

            @tool(name="send_email", description="发送邮件")
            async def send_email(self, to: str, subject: str, body: str) -> dict:
                ...

            @tool(name="read_emails", description="读取邮件")
            async def read_emails(self, folder: str = "INBOX") -> list:
                ...
    """

    # 工具集名称
    name: str = "base"
    # 工具集描述
    description: str = ""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._collect_tools()

    def _collect_tools(self):
        """收集所有标记为 @tool 的方法"""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_tool_definition"):
                tool_def = attr._tool_definition
                self._tools[tool_def.name] = tool_def

    def list_tools(self) -> list[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self._tools.get(name)

    async def execute(self, name: str, **kwargs) -> Any:
        """
        执行工具

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        tool_def = self._tools.get(name)
        if not tool_def:
            raise ValueError(f"未知工具: {name}")

        # 获取绑定到实例的方法
        method = getattr(self, tool_def.func.__name__)
        return await method(**kwargs)

    def to_openai_schema(self) -> list[dict]:
        """
        生成 OpenAI Function Calling 格式的 schema

        Returns:
            list[dict]: OpenAI 格式的工具定义列表
        """
        schemas = []
        for tool_def in self._tools.values():
            properties = {}
            required = []

            for param in tool_def.parameters:
                prop = {
                    "type": param.type,
                    "description": param.description,
                }
                if param.enum:
                    prop["enum"] = param.enum
                properties[param.name] = prop

                if param.required:
                    required.append(param.name)

            schemas.append({
                "type": "function",
                "function": {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })

        return schemas

    def to_anthropic_schema(self) -> list[dict]:
        """
        生成 Anthropic Tool Use 格式的 schema

        Returns:
            list[dict]: Anthropic 格式的工具定义列表
        """
        schemas = []
        for tool_def in self._tools.values():
            properties = {}
            required = []

            for param in tool_def.parameters:
                prop = {
                    "type": param.type,
                    "description": param.description,
                }
                if param.enum:
                    prop["enum"] = param.enum
                properties[param.name] = prop

                if param.required:
                    required.append(param.name)

            schemas.append({
                "name": tool_def.name,
                "description": tool_def.description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            })

        return schemas
