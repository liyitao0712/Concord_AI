# app/tools/registry.py
# Tool 注册中心
#
# 管理所有可用的 Tool，提供：
# 1. Tool 注册
# 2. Tool 发现
# 3. Tool 执行
# 4. Schema 生成

from typing import Optional, Type, Any

from app.core.logging import get_logger
from app.tools.base import BaseTool

logger = get_logger(__name__)


class ToolRegistry:
    """
    Tool 注册中心

    使用方法：
        # 注册 Tool
        registry = ToolRegistry()
        registry.register(EmailTool)
        registry.register(DatabaseTool)

        # 获取所有工具 schema
        schemas = registry.get_all_schemas()

        # 执行工具
        result = await registry.execute("send_email", to="...", subject="...", body="...")

        # 获取特定 Tool
        email_tool = registry.get_tool_instance("email")
    """

    def __init__(self):
        # 注册的 Tool 类
        self._tool_classes: dict[str, Type[BaseTool]] = {}
        # Tool 实例缓存
        self._instances: dict[str, BaseTool] = {}
        # 工具名称到 Tool 类的映射
        self._tool_to_class: dict[str, str] = {}

    def register(self, tool_class: Type[BaseTool]):
        """
        注册 Tool 类

        Args:
            tool_class: Tool 类（继承自 BaseTool）
        """
        name = tool_class.name
        if name in self._tool_classes:
            logger.warning(f"[ToolRegistry] Tool 已存在，将被覆盖: {name}")

        self._tool_classes[name] = tool_class

        # 创建实例并记录工具映射
        instance = tool_class()
        self._instances[name] = instance

        for tool_name in instance.list_tools():
            self._tool_to_class[tool_name] = name

        logger.info(f"[ToolRegistry] 注册 Tool: {name} ({len(instance.list_tools())} 个工具)")

    def unregister(self, name: str):
        """取消注册 Tool"""
        if name in self._tool_classes:
            # 移除工具映射
            instance = self._instances.get(name)
            if instance:
                for tool_name in instance.list_tools():
                    self._tool_to_class.pop(tool_name, None)

            del self._tool_classes[name]
            self._instances.pop(name, None)
            logger.info(f"[ToolRegistry] 取消注册 Tool: {name}")

    def get_tool_instance(self, name: str) -> Optional[BaseTool]:
        """获取 Tool 实例"""
        return self._instances.get(name)

    def list_tools(self) -> list[str]:
        """列出所有可用的工具名称"""
        return list(self._tool_to_class.keys())

    def list_tool_classes(self) -> list[str]:
        """列出所有注册的 Tool 类名称"""
        return list(self._tool_classes.keys())

    async def execute(self, tool_name: str, **kwargs) -> Any:
        """
        执行工具

        Args:
            tool_name: 工具名称（如 "send_email"）
            **kwargs: 工具参数

        Returns:
            工具执行结果

        Raises:
            ValueError: 工具不存在
        """
        class_name = self._tool_to_class.get(tool_name)
        if not class_name:
            raise ValueError(f"未知工具: {tool_name}")

        instance = self._instances.get(class_name)
        if not instance:
            raise ValueError(f"Tool 实例不存在: {class_name}")

        logger.info(f"[ToolRegistry] 执行工具: {tool_name}")
        return await instance.execute(tool_name, **kwargs)

    def get_schemas(
        self,
        tool_names: Optional[list[str]] = None,
        format: str = "openai",
    ) -> list[dict]:
        """
        获取工具 schema

        Args:
            tool_names: 指定工具名称列表，为空则返回全部
            format: schema 格式，"openai" 或 "anthropic"

        Returns:
            list[dict]: 工具 schema 列表
        """
        schemas = []

        for class_name, instance in self._instances.items():
            if format == "openai":
                class_schemas = instance.to_openai_schema()
            else:
                class_schemas = instance.to_anthropic_schema()

            if tool_names:
                # 过滤指定的工具
                class_schemas = [
                    s for s in class_schemas
                    if s.get("function", {}).get("name") in tool_names
                    or s.get("name") in tool_names
                ]

            schemas.extend(class_schemas)

        return schemas

    def get_all_schemas(self, format: str = "openai") -> list[dict]:
        """获取所有工具的 schema"""
        return self.get_schemas(format=format)


# 全局单例
tool_registry = ToolRegistry()


def register_tool(tool_class: Type[BaseTool]):
    """
    便捷注册函数，可用作类装饰器

    使用方法：
        @register_tool
        class MyTool(BaseTool):
            name = "my_tool"
            ...
    """
    tool_registry.register(tool_class)
    return tool_class
