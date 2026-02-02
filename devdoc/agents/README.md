# Agents 智能代理

本目录包含系统中所有 Agent 的详细说明文档。

## Agent 列表

| Agent | 说明 | 文档 |
|-------|------|------|
| EmailSummarizer | 邮件摘要分析 | [EmailSummarizer.md](./EmailSummarizer.md) |
| WorkTypeAnalyzer | 工作类型分析 | [WorkTypeAnalyzer.md](./WorkTypeAnalyzer.md) |
| ChatAgent | 聊天对话 | [ChatAgent.md](./ChatAgent.md) |

## 架构概述

```
┌─────────────────────────────────────────────────────────┐
│                     Agent Layer                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌──────────────┐   ┌──────────────┐   ┌────────────┐  │
│   │ EmailSummarizer│   │WorkTypeAnalyzer│   │ ChatAgent │  │
│   └──────┬───────┘   └──────┬───────┘   └─────┬──────┘  │
│          │                  │                  │         │
│          └──────────────────┼──────────────────┘         │
│                             │                            │
│                    ┌────────┴────────┐                   │
│                    │   BaseAgent     │                   │
│                    │  (LangGraph)    │                   │
│                    └────────┬────────┘                   │
│                             │                            │
│                    ┌────────┴────────┐                   │
│                    │  AgentRegistry  │                   │
│                    └─────────────────┘                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────┐
│                      LLM Layer                           │
│               (LiteLLM + 多模型支持)                      │
└─────────────────────────────────────────────────────────┘
```

## 核心概念

### BaseAgent

所有 Agent 的基类，基于 LangGraph 状态机：

```python
class BaseAgent(ABC):
    name: str = "base"
    description: str = ""
    prompt_name: str = ""
    tools: list[str] = []
    model: str = None
    max_iterations: int = 10

    async def run(self, input_text, input_data=None) -> AgentResult
    async def process_output(self, state: AgentState) -> dict  # 子类实现
```

### AgentResult

Agent 执行结果：

```python
@dataclass
class AgentResult:
    success: bool
    output: str
    data: dict = None
    error: str = None
    iterations: int = 0
    tool_calls: list = None
```

### AgentRegistry

Agent 注册中心：

```python
# 注册 Agent
@register_agent
class MyAgent(BaseAgent):
    name = "my_agent"

# 获取 Agent
agent = agent_registry.get("my_agent")

# 执行 Agent
result = await agent_registry.run("my_agent", "input text")

# 列出所有 Agent
agents = agent_registry.list_agents()
```

## 并行执行

使用 `asyncio.gather()` 并行执行多个 Agent：

```python
results = await asyncio.gather(
    agent_registry.run("email_summarizer", ...),
    agent_registry.run("work_type_analyzer", ...),
    return_exceptions=True,
)
```

## 文件结构

```
backend/app/agents/
├── __init__.py          # 模块入口
├── base.py              # BaseAgent 基类
├── registry.py          # AgentRegistry
├── chat_agent.py        # 聊天 Agent
├── email_summarizer.py  # 邮件摘要 Agent
└── work_type_analyzer.py # 工作类型分析 Agent
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/agents | 获取 Agent 列表 |
| POST | /admin/agents/{name}/run | 执行指定 Agent |

## 配置管理

Agent 配置可从数据库动态加载：

- Prompt 模板
- LLM 模型选择
- 参数设置

## 创建新 Agent

1. 创建文件 `backend/app/agents/my_agent.py`
2. 继承 `BaseAgent` 并使用 `@register_agent` 装饰器
3. 实现 `process_output()` 方法
4. 在 `__init__.py` 中导入触发注册
5. 添加文档到 `devdoc/agents/`
