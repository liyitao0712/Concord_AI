# Agents 智能代理

本目录包含系统中所有 Agent 的详细说明文档。

## Agent 列表

| Agent | 说明 | 文档 |
|-------|------|------|
| EmailSummarizer | 邮件摘要分析 | [EmailSummarizer.md](./EmailSummarizer.md) |
| WorkTypeAnalyzer | 工作类型分析 | [WorkTypeAnalyzer.md](./WorkTypeAnalyzer.md) |
| ChatAgent | 聊天对话 | [ChatAgent.md](./ChatAgent.md) |
| CustomerExtractor | 客户信息提取 | [CustomerExtractor.md](./CustomerExtractor.md) |
| AddNewClientHelper | 新客户信息自动填充 | [AddNewClientHelper.md](./AddNewClientHelper.md) |
| AddNewSupplierHelper | 新供应商信息自动填充 | [AddNewSupplierHelper.md](./AddNewSupplierHelper.md) |

## 架构概述

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Layer                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌────────────────┐  ┌────────────────┐  ┌──────────────┐                 │
│   │EmailSummarizer │  │WorkTypeAnalyzer│  │  ChatAgent   │                 │
│   └───────┬────────┘  └───────┬────────┘  └──────┬───────┘                 │
│           │                   │                   │                         │
│   ┌───────────────────┐  ┌───────────────────────────┐                     │
│   │CustomerExtractor  │  │AddNewClientHelper         │                     │
│   └───────┬───────────┘  │AddNewSupplierHelper       │                     │
│           │              └───────────┬───────────────┘                     │
│           │                          │                                     │
│           └──────────┬───────────────┘                                     │
│                      │                                                     │
│             ┌────────┴────────┐                                            │
│             │   BaseAgent     │                                            │
│             │  (LangGraph)    │                                            │
│             └────────┬────────┘                                            │
│                      │                                                     │
│             ┌────────┴────────┐                                            │
│             │  AgentRegistry  │                                            │
│             └─────────────────┘                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LLM Layer                                        │
│           LiteLLM（通用） / Anthropic SDK（web_search Agent）               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 核心概念

### BaseAgent

所有 Agent 的基类，基于 LangGraph 状态机：

```python
class BaseAgent(ABC):
    name: str = "base"
    display_name: str = ""
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

## Agent 分类

### 邮件处理类

| Agent | 触发方式 | 说明 |
|-------|---------|------|
| EmailSummarizer | Dispatcher 自动调用 | 邮件摘要、意图识别、业务信息提取 |
| WorkTypeAnalyzer | Dispatcher 自动调用 | 工作类型匹配 + 新类型建议 |
| CustomerExtractor | Dispatcher 自动调用 | 客户信息提取 + 待审批建议 |

### 表单辅助类

| Agent | 触发方式 | 说明 |
|-------|---------|------|
| AddNewClientHelper | API 手动触发 | 新建客户时自动填充公司信息 |
| AddNewSupplierHelper | API 手动触发 | 新建供应商时自动填充公司信息 |

### 对话交互类

| Agent | 触发方式 | 说明 |
|-------|---------|------|
| ChatAgent | API 手动触发 | 多轮对话、流式输出 |

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
├── __init__.py                  # 模块入口（导入所有 Agent 触发注册）
├── base.py                      # BaseAgent 基类
├── registry.py                  # AgentRegistry
├── chat_agent.py                # 聊天 Agent
├── email_summarizer.py          # 邮件摘要 Agent
├── work_type_analyzer.py        # 工作类型分析 Agent
├── customer_extractor.py        # 客户信息提取 Agent
├── add_new_client_helper.py     # 新客户信息助手 Agent
└── add_new_supplier_helper.py   # 新供应商信息助手 Agent
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
