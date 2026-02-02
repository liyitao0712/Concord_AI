# ChatAgent

## 概述

ChatAgent 是聊天对话 Agent，负责处理用户的对话交互。

## 基本信息

| 属性 | 值 |
|------|-----|
| name | chat_agent |
| description | 通用聊天对话 Agent |
| prompt_name | chat_agent |
| tools | 可配置 |
| max_iterations | 10 |

## 执行流程

```
用户输入
    ↓
加载会话历史
    ↓
构建 Prompt（系统提示 + 历史消息 + 用户输入）
    ↓
调用 LLM
    ↓
(如果需要) 执行工具调用
    ↓
返回响应
```

## 使用场景

- 用户聊天界面
- 邮件草稿生成
- 问答交互

## 相关文件

- Agent: `backend/app/agents/chat_agent.py`
- API: `backend/app/api/chat.py`
