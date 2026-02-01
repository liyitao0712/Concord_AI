# app/agents/registry.py
# Agent 注册中心
#
# 管理所有可用的 Agent，提供：
# 1. Agent 注册
# 2. Agent 发现
# 3. Agent 执行

from typing import Optional, Type

from app.core.logging import get_logger
from app.agents.base import BaseAgent, AgentResult

logger = get_logger(__name__)


class AgentRegistry:
    """
    Agent 注册中心

    使用方法：
        # 注册 Agent
        registry = AgentRegistry()
        registry.register(EmailAnalyzerAgent)
        registry.register(QuoteAgent)

        # 执行 Agent
        result = await registry.run("email_analyzer", "分析这封邮件...")

        # 获取 Agent
        agent = registry.get("email_analyzer")
    """

    def __init__(self):
        self._agents: dict[str, Type[BaseAgent]] = {}
        self._instances: dict[str, BaseAgent] = {}

    def register(self, agent_class: Type[BaseAgent]):
        """
        注册 Agent 类

        Args:
            agent_class: Agent 类（继承自 BaseAgent）
        """
        name = agent_class.name
        if name in self._agents:
            logger.warning(f"[AgentRegistry] Agent 已存在，将被覆盖: {name}")

        self._agents[name] = agent_class
        logger.info(f"[AgentRegistry] 注册 Agent: {name}")

    def unregister(self, name: str):
        """取消注册 Agent"""
        if name in self._agents:
            del self._agents[name]
            self._instances.pop(name, None)
            logger.info(f"[AgentRegistry] 取消注册 Agent: {name}")

    def get(self, name: str) -> Optional[BaseAgent]:
        """
        获取 Agent 实例

        会复用已创建的实例
        """
        if name not in self._agents:
            return None

        if name not in self._instances:
            self._instances[name] = self._agents[name]()

        return self._instances[name]

    def list_agents(self) -> list[dict]:
        """
        列出所有注册的 Agent

        Returns:
            list[dict]: Agent 信息列表
        """
        return [
            {
                "name": name,
                "description": cls.description,
                "tools": cls.tools,
                "model": cls.model,
            }
            for name, cls in self._agents.items()
        ]

    async def run(
        self,
        agent_name: str,
        input_text: str,
        db=None,
        **kwargs,
    ) -> AgentResult:
        """
        执行指定 Agent

        Args:
            agent_name: Agent 名称
            input_text: 用户输入
            db: 可选的数据库会话，用于加载 Agent 配置
            **kwargs: 其他参数

        Returns:
            AgentResult: 执行结果
        """
        agent = self.get(agent_name)
        if not agent:
            return AgentResult(
                success=False,
                output="",
                error=f"未知 Agent: {agent_name}",
            )

        # 如果提供了数据库连接，加载配置
        if db is not None:
            try:
                await agent.load_config_from_db(db)
            except Exception as e:
                logger.warning(f"[AgentRegistry] 加载 Agent 配置失败: {e}")

        return await agent.run(input_text, **kwargs)


# 全局单例
agent_registry = AgentRegistry()


def register_agent(agent_class: Type[BaseAgent]):
    """
    便捷注册函数，可用作类装饰器

    使用方法：
        @register_agent
        class MyAgent(BaseAgent):
            name = "my_agent"
            ...
    """
    agent_registry.register(agent_class)
    return agent_class
