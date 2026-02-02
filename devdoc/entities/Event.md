# Event 统一事件

## 概述

Event 是系统的统一事件实体，用于接收和处理来自不同来源的事件（邮件、飞书、API 等）。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| idempotency_key | String(200) | 幂等键（防止重复处理） |
| event_type | String(50) | 事件类型 (email/feishu/api) |
| source | String(50) | 来源标识 |
| source_id | String(200) | 来源系统中的 ID |
| content | Text | 事件内容 |
| content_type | String(50) | 内容类型 (text/html) |
| intent | String(50) | 意图分类结果 |
| user_id | String(36) | 关联用户 ID |
| user_external_id | String(200) | 外部用户 ID |
| session_id | String(36) | 会话 ID |
| thread_id | String(200) | 线程 ID |
| status | Enum | pending/processing/completed/failed |
| metadata | JSON | 元数据 |
| response_content | Text | 响应内容 |
| error_message | Text | 错误信息 |
| created_at | DateTime | 创建时间 |
| completed_at | DateTime | 完成时间 |

## 事件类型 (event_type)

| 值 | 说明 |
|-----|------|
| email | 邮件事件 |
| feishu | 飞书消息 |
| api | API 调用 |

## 状态流转

```
PENDING → PROCESSING → COMPLETED
                    ↘ FAILED
```

## 处理流程

```
来源 (邮件/飞书/API)
    ↓
UnifiedEvent Schema
    ↓
EventDispatcher.dispatch()
    ├─ 幂等性检查
    ├─ 保存到数据库
    ├─ 并行分析 (EmailSummarizer + WorkTypeAnalyzer)
    └─ 更新状态
```

## 相关文件

- Model: `backend/app/models/event.py`
- Schema: `backend/app/schemas/event.py`
- Dispatcher: `backend/app/messaging/dispatcher.py`
