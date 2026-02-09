# ChatSession 聊天会话

## 概述

ChatSession 是聊天会话实体，ChatMessage 是会话中的消息。支持多来源（Web 聊天框、飞书、API）的对话管理。

## 数据模型

### ChatSession（聊天会话）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| user_id | String(36) | 系统用户 ID（外键） |
| external_user_id | String(100) | 外部用户 ID（飞书等） |
| source | String(20) | 来源 (chatbox/feishu/api) |
| feishu_chat_id | String(100) | 飞书会话 ID |
| title | String(200) | 会话标题（默认"新对话"） |
| agent_id | String(50) | 使用的 Agent (默认 chat_agent) |
| is_active | Boolean | 是否活跃 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### ChatMessage（聊天消息）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| session_id | String(36) | 会话 ID（外键） |
| role | String(20) | 角色 (user/assistant/system/tool) |
| content | Text | 消息内容 |
| tool_calls | JSON | 工具调用信息 |
| tool_results | JSON | 工具返回结果 |
| status | String(20) | 状态 (completed/streaming/error) |
| model | String(50) | 使用的模型 |
| tokens_used | Integer | token 消耗 |
| external_message_id | String(100) | 外部消息 ID |
| created_at | DateTime | 创建时间 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /chat/sessions | 会话列表 |
| POST | /chat/sessions | 创建会话 |
| GET | /chat/sessions/{id}/messages | 获取消息列表 |
| POST | /chat/sessions/{id}/messages | 发送消息 |
| DELETE | /chat/sessions/{id} | 删除会话 |

## 相关文件

- Model: `backend/app/models/chat.py`
- API: `backend/app/api/chat.py`
