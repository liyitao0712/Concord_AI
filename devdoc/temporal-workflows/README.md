# Temporal Workflows

本目录包含系统中所有 Temporal Workflow 的详细说明文档。

## Workflow 列表

| Workflow | 说明 | 文档 |
|----------|------|------|
| WorkTypeSuggestionWorkflow | 工作类型建议审批 | [WorkTypeSuggestionWorkflow.md](./WorkTypeSuggestionWorkflow.md) |

## Temporal 配置

### 环境变量

```bash
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=concord-main-queue
```

### Docker Compose

Temporal 相关服务在 `docker-compose.yml` 中定义：

- `temporal`: Temporal Server
- `temporal-ui`: Temporal Web UI (http://localhost:8080)
- `temporal-admin-tools`: 管理工具

## 架构概述

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│                                                          │
│   ┌──────────────┐        ┌──────────────────────────┐  │
│   │   API 层     │ ──────→│   Temporal Client        │  │
│   └──────────────┘        │   (app.temporal.client)  │  │
│                           └────────────┬─────────────┘  │
└────────────────────────────────────────│────────────────┘
                                         │
                              ┌──────────┴──────────┐
                              │   Temporal Server   │
                              │   (localhost:7233)  │
                              └──────────┬──────────┘
                                         │
┌────────────────────────────────────────│────────────────┐
│                    Temporal Worker                       │
│                (python -m app.temporal.worker)           │
│                                                          │
│   ┌───────────────────────────────────────────────────┐ │
│   │                    Workflows                       │ │
│   │   ┌────────────────────────────────────────────┐  │ │
│   │   │    WorkTypeSuggestionWorkflow              │  │ │
│   │   │    - 等待审批 Signal                        │  │ │
│   │   │    - 7 天超时自动拒绝                       │  │ │
│   │   └────────────────────────────────────────────┘  │ │
│   └───────────────────────────────────────────────────┘ │
│                                                          │
│   ┌───────────────────────────────────────────────────┐ │
│   │                    Activities                      │ │
│   │   - notify_admin_activity                         │ │
│   │   - approve_suggestion_activity                   │ │
│   │   - reject_suggestion_activity                    │ │
│   └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

```
backend/app/temporal/
├── __init__.py                    # 模块入口
├── client.py                      # Temporal Client 封装
├── worker.py                      # Worker 启动器
├── workflows/
│   ├── __init__.py
│   └── work_type_suggestion.py    # 审批工作流
└── activities/
    ├── __init__.py
    └── work_type.py               # 工作类型相关 Activities
```

## 启动 Worker

### 开发环境

```bash
cd backend
source venv/bin/activate
python -m app.temporal.worker
```

### 使用脚本

```bash
# 启动 Worker
./scripts/restart.sh --worker

# 查看状态
./scripts/status.sh

# 查看日志
tail -f logs/worker.log
```

## Workflow 开发指南

### 创建新 Workflow

1. 在 `workflows/` 目录创建文件
2. 使用 `@workflow.defn` 装饰器定义工作流类
3. 实现 `@workflow.run` 主方法
4. 定义 Signals 和 Queries
5. 在 `worker.py` 中注册工作流

### 创建新 Activity

1. 在 `activities/` 目录创建或修改文件
2. 使用 `@activity.defn` 装饰器定义活动
3. Activity 可以进行 I/O 操作（数据库、HTTP 等）
4. 在 `worker.py` 中注册活动

### 最佳实践

- Workflow 代码必须是确定性的（不能有随机数、时间等）
- I/O 操作放在 Activity 中
- 使用 `workflow.logger` 记录日志
- Signal 用于外部触发，Query 用于状态查询
- 设置合理的超时时间

## Temporal UI

访问 http://localhost:8080 可以：

- 查看运行中的工作流
- 查看工作流历史记录
- 发送 Signal
- 查询工作流状态
- 终止工作流

## 错误处理

### Activity 重试

```python
await workflow.execute_activity(
    my_activity,
    args=[...],
    start_to_close_timeout=timedelta(seconds=60),
    retry_policy=RetryPolicy(
        maximum_attempts=3,
        initial_interval=timedelta(seconds=1),
    ),
)
```

### Workflow 超时

```python
await workflow.wait_condition(
    lambda: self.completed,
    timeout=timedelta(days=7),
)
```

## 监控

- Temporal UI: http://localhost:8080
- Worker 日志: `logs/worker.log`
- Temporal Server 日志: `docker compose logs temporal`
