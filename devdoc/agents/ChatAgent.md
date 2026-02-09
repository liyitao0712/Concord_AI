# ChatAgent

## 概述

ChatAgent 是通用聊天对话 Agent，负责：
- 处理用户的多轮对话交互
- 管理对话上下文（Redis 缓存，24 小时 TTL）
- 提供流式输出（SSE）
- 支持 Tools 调用（可选，默认关闭）
- 兼容多种调用模式（会话式 / 一次性 / 显式历史）

## 基本信息

| 属性 | 值 |
|------|-----|
| name | chat_agent |
| display_name | 对话助手 |
| description | 通用聊天助手，支持多轮对话和工具调用 |
| prompt_name | chat_agent |
| tools | 可配置（默认无，启用后：search_customers, search_products） |
| model | 使用数据库配置的默认模型 |
| max_iterations | 5 |
| max_context_messages | 20 |

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                ChatAgent (extends BaseAgent)                 │
├─────────────────────────────────────────────────────────────┤
│  run()              │ 继承自 BaseAgent，完整响应             │
│  run_stream()       │ 流式输出（一次性，不使用会话上下文）   │
│  chat()             │ 会话式对话（自动管理 Redis 上下文）    │
│  chat_stream()      │ 会话式流式对话                         │
│  chat_with_history()│ 显式历史对话（不使用 Redis 缓存）      │
│  chat_stream_with_history() │ 显式历史流式对话               │
│  clear_context()    │ 清除会话上下文                         │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │     BaseAgent      │
                    │  (LangGraph 状态机) │
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │    LLM Gateway     │
                    │   (LiteLLM 封装)    │
                    └────────────────────┘
```

## 执行流程

### 模式一：会话式对话（chat / chat_stream）

```
用户输入
    ↓
从 Redis 加载会话历史
    ↓
添加用户消息到上下文
    ↓
确定系统提示 + 模型
    ↓
调用 LLM（chat / chat_stream）
    ↓
保存助手回复到 Redis（含上下文裁剪）
    ↓
返回 ChatResult / 逐 token 输出
```

### 模式二：BaseAgent 执行（run）

```
用户输入
    ↓
[think] 调用 LLM 推理
    ↓
(如果启用 Tools) [execute_tools] 执行工具调用
    ↓
[output] 处理输出
    ↓
返回 AgentResult
```

### 模式三：显式历史（chat_with_history）

```
消息历史列表（外部传入）
    ↓
提取最后一条用户消息
    ↓
调用 LLM
    ↓
返回 ChatResult
```

## 输入格式

### chat() / chat_stream()

```python
await chat_agent.chat(
    session_id="session-uuid-123",
    message="你好，帮我查一下订单",
    org_id="org-uuid",           # 可选，组织隔离
    system_prompt="自定义提示",    # 可选，覆盖默认
    model="anthropic/claude-sonnet-4-20250514",  # 可选
    temperature=0.7,              # 可选
)
```

### chat_with_history()

```python
await chat_agent.chat_with_history(
    messages=[
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮您？"},
        {"role": "user", "content": "帮我查一下最新订单"},
    ],
    system_prompt="...",
    model="...",
)
```

## 输出格式

### ChatResult（chat 系列方法）

```python
@dataclass
class ChatResult:
    success: bool        # 是否成功
    content: str         # 助手回复内容
    model: str           # 使用的模型名称
    tokens_used: int     # Token 消耗
    error: Optional[str] # 错误信息
```

### AgentResult（run 方法）

```python
# result.data 的结构：
{
    "response": "助手回复内容",
    "tool_calls": [],    # 工具调用记录
    "tool_results": [],  # 工具执行结果
}
```

## 上下文管理

### Redis 缓存

- Key 格式：`chat:context:{org_id}:{session_id}`（有 org_id 时）
- Key 格式：`chat:context:{session_id}`（无 org_id 时）
- TTL：24 小时
- 最大消息数：20 条（超出时自动裁剪旧消息）
- 向后兼容：新 key 找不到时会尝试旧格式 key

### 上下文操作

```python
# 获取上下文
messages = await chat_agent._get_context(session_id, org_id)

# 保存上下文
await chat_agent._save_context(session_id, messages, org_id)

# 清除上下文
await chat_agent.clear_context(session_id, org_id)
```

## 系统提示加载优先级

1. 构造函数传入的 `system_prompt` 参数
2. 数据库 Prompt: `chat_agent_system`（支持 `{{company_name}}` 等系统变量渲染）
3. 数据库 Prompt: `chat_agent`（兼容旧条目）
4. 硬编码默认值

## 初始化选项

```python
# 默认初始化（不启用工具）
agent = ChatAgent()

# 自定义系统提示
agent = ChatAgent(system_prompt="你是一个专业的外贸助手...")

# 启用工具调用
agent = ChatAgent(enable_tools=True)
# 启用后可用工具：search_customers, search_products

# 自定义 LLM Gateway
agent = ChatAgent(llm=custom_llm_gateway)
```

## Prompt 配置

| Prompt Key | 用途 | 文件 |
|------------|------|------|
| `chat_agent_system` | 系统提示（推荐） | `backend/app/llm/prompts/defaults.py` |
| `chat_agent` | 兼容旧版系统提示 | `backend/app/llm/prompts/defaults.py` |

## 使用场景

- Web Chatbox 用户对话界面
- 飞书机器人对话
- 邮件草稿生成
- 问答交互

## 相关文件

- Agent: `backend/app/agents/chat_agent.py`
- 基类: `backend/app/agents/base.py`
- API: `backend/app/api/chat.py`
- LLM Gateway: `backend/app/llm/gateway.py`
- Redis 缓存: `backend/app/core/redis.py`
- Prompt 默认值: `backend/app/llm/prompts/defaults.py`

## 使用示例

```python
from app.agents.chat_agent import chat_agent

# 方式一：会话式对话（自动管理上下文）
result = await chat_agent.chat(
    session_id="session-123",
    message="你好，帮我查一下最新的询盘邮件",
    org_id="org-456",
)
print(f"回复: {result.content}")
print(f"Token: {result.tokens_used}")

# 方式二：流式对话（逐 token 输出）
async for chunk in chat_agent.chat_stream(
    session_id="session-123",
    message="帮我写一封报价邮件",
    org_id="org-456",
):
    print(chunk, end="", flush=True)

# 方式三：使用 BaseAgent 的 run() 方法
result = await chat_agent.run("帮我总结这封邮件的要点")
if result.success:
    print(result.data["response"])

# 方式四：显式历史对话（从数据库加载历史）
result = await chat_agent.chat_with_history(
    messages=db_messages,
    system_prompt="你是一个专业的外贸助手",
)

# 清除会话上下文
await chat_agent.clear_context("session-123", org_id="org-456")
```
