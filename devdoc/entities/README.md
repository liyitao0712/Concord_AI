# Entities 数据实体

本目录包含系统中所有数据实体的详细说明文档。

## 实体列表

### 核心业务实体

| 实体 | 说明 | 文档 |
|------|------|------|
| WorkType | 工作类型（层级结构） | [WorkType.md](./WorkType.md) |
| Event | 统一事件 | [Event.md](./Event.md) |
| EmailAccount | 邮箱账户 | [EmailAccount.md](./EmailAccount.md) |
| EmailRawMessage | 原始邮件 | [EmailRawMessage.md](./EmailRawMessage.md) |
| Intent | 意图定义 | [Intent.md](./Intent.md) |

### 用户与权限

| 实体 | 说明 | 文档 |
|------|------|------|
| User | 用户 | [User.md](./User.md) |

### 系统配置

| 实体 | 说明 | 文档 |
|------|------|------|
| LLMModelConfig | LLM 模型配置 | [LLMModelConfig.md](./LLMModelConfig.md) |
| SystemSetting | 系统设置 | [SystemSetting.md](./SystemSetting.md) |
| Prompt | Prompt 模板 | [Prompt.md](./Prompt.md) |
| WorkerConfig | Worker 配置 | [WorkerConfig.md](./WorkerConfig.md) |

### 执行记录

| 实体 | 说明 | 文档 |
|------|------|------|
| WorkflowExecution | 工作流执行记录 | - |
| AgentExecution | Agent 执行记录 | - |

### 聊天相关

| 实体 | 说明 | 文档 |
|------|------|------|
| ChatSession | 聊天会话 | - |
| ChatMessage | 聊天消息 | - |

## 实体关系图

```
User ─────┬───────────────────────────────────────┐
          │                                       │
          ↓                                       ↓
    EmailAccount ─────→ EmailRawMessage ─────→ Event
          │                    │                  │
          │                    ↓                  │
          │              EmailAnalysis            │
          │                                       │
          │                                       ↓
          └──────────────────────────────→ WorkType
                                               ↑
                                               │
                                    WorkTypeSuggestion
```

## 数据库迁移

所有实体对应的数据库表通过 Alembic 管理：

```bash
# 生成迁移
cd backend
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 文件位置

- Models: `backend/app/models/`
- Schemas: `backend/app/schemas/`
- Migrations: `backend/alembic/versions/`
