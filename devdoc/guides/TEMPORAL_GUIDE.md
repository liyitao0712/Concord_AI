# Concord AI - Temporal 工作流指南

> Temporal 工作流开发与运维完整手册
> 合并自: MANUAL.md §15 + temporal-workflows/README.md

---

## 1. 概述

使用 Temporal 实现长时间运行的业务流程，支持 Signal（外部信号）、Query（状态查询）、自动重试、持久化、可视化。

### 核心概念

| 概念 | 说明 |
|------|------|
| **Workflow** | 业务流程定义，必须是确定性代码 |
| **Activity** | 实际执行的任务，可以包含 I/O 操作 |
| **Worker** | 监听任务队列，执行 Workflow 和 Activity |
| **Client** | 与 Temporal Server 交互的客户端 |
| **Signal** | 外部发送给运行中 Workflow 的信号 |
| **Query** | 查询运行中 Workflow 的状态（只读） |

### 配置

```python
# core/config.py
TEMPORAL_HOST: str = "localhost:7233"
TEMPORAL_NAMESPACE: str = "default"
TEMPORAL_TASK_QUEUE: str = "concord-main-queue"
```

---

## 2. 架构

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
│   │   - WorkTypeSuggestionWorkflow                    │ │
│   │   - ApprovalWorkflow                              │ │
│   └───────────────────────────────────────────────────┘ │
│                                                          │
│   ┌───────────────────────────────────────────────────┐ │
│   │                    Activities                      │ │
│   │   - notify_admin_activity                         │ │
│   │   - approve_suggestion_activity                   │ │
│   │   - reject_suggestion_activity                    │ │
│   │   - send_notification                             │ │
│   │   - log_workflow_event                            │ │
│   └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构

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

---

## 4. Workflow 开发

### 4.1 Workflow 定义示例

```python
# workflows/definitions/approval.py

from temporalio import workflow
from datetime import timedelta

@workflow.defn
class ApprovalWorkflow:
    def __init__(self):
        self._status = ApprovalStatus.PENDING
        self._approver_id = None

    @workflow.run
    async def run(self, request: ApprovalRequest) -> ApprovalResult:
        """工作流主函数"""
        # 1. 发送通知
        await workflow.execute_activity(
            send_notification,
            args=[notification_request],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # 2. 等待审批或超时
        await workflow.wait_condition(
            lambda: self._status != ApprovalStatus.PENDING,
            timeout=timedelta(hours=24),
        )

        # 3. 返回结果
        return ApprovalResult(
            status=self._status,
            approver_id=self._approver_id,
        )

    @workflow.signal
    async def approve(self, approver_id: str, comment: str):
        """审批通过信号"""
        self._status = ApprovalStatus.APPROVED
        self._approver_id = approver_id

    @workflow.signal
    async def reject(self, approver_id: str, comment: str):
        """审批拒绝信号"""
        self._status = ApprovalStatus.REJECTED
        self._approver_id = approver_id

    @workflow.query
    def get_status(self) -> ApprovalStatus:
        """查询当前状态"""
        return self._status
```

### 4.2 Activity 定义示例

```python
# workflows/activities/base.py

from temporalio import activity

@activity.defn
async def send_notification(request: NotificationRequest) -> bool:
    """发送通知 Activity"""
    info = activity.info()
    logger.info(f"[Activity] 发送通知")
    logger.info(f"  Workflow ID: {info.workflow_id}")

    if request.type == NotificationType.EMAIL:
        await send_email_impl(request)
        return True

    raise ValueError(f"不支持的通知类型: {request.type}")
```

### 4.3 创建新 Workflow

1. 在 `workflows/` 目录创建文件
2. 使用 `@workflow.defn` 装饰器定义工作流类
3. 实现 `@workflow.run` 主方法
4. 定义 Signals 和 Queries
5. 在 `worker.py` 中注册工作流

### 4.4 创建新 Activity

1. 在 `activities/` 目录创建或修改文件
2. 使用 `@activity.defn` 装饰器定义活动
3. Activity 可以进行 I/O 操作（数据库、HTTP 等）
4. 在 `worker.py` 中注册活动

---

## 5. Worker 与 Client

### Worker 启动

```python
# workflows/worker.py

from temporalio.client import Client
from temporalio.worker import Worker

async def run_worker():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client=client,
        task_queue="concord-main-queue",
        workflows=[ApprovalWorkflow],
        activities=[send_notification, log_workflow_event],
    )

    await worker.run()

# 启动：python -m app.workflows.worker
```

### Client 使用

```python
# workflows/client.py

from temporalio.client import Client

# 启动工作流
client = await Client.connect("localhost:7233")
handle = await client.start_workflow(
    ApprovalWorkflow.run,
    args=(approval_request,),
    id="approval-order-001",
    task_queue="concord-main-queue",
)

# 发送信号
await handle.signal(ApprovalWorkflow.approve, "user-001", "同意")

# 查询状态
status = await handle.query(ApprovalWorkflow.get_status)

# 等待结果
result = await handle.result()
```

---

## 6. API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/workflows/approval` | 创建审批工作流 |
| GET | `/api/workflows/{id}/status` | 查询工作流状态 |
| POST | `/api/workflows/{id}/approve` | 审批通过 |
| POST | `/api/workflows/{id}/reject` | 审批拒绝 |
| POST | `/api/workflows/{id}/cancel` | 取消工作流 |

---

## 7. Workflow 列表

| Workflow | 说明 | 文档 |
|----------|------|------|
| WorkTypeSuggestionWorkflow | 工作类型建议审批（7天超时自动拒绝） | [详细文档](../temporal-workflows/WorkTypeSuggestionWorkflow.md) |
| ApprovalWorkflow | 通用审批工作流 | 见上方示例 |

---

## 8. Workflow vs Activity 选择

| 操作 | 放在 Workflow | 放在 Activity |
|------|---------------|---------------|
| 流程控制（if/for） | O | X |
| 等待（sleep/wait） | O | X |
| 数据库读写 | X | O |
| HTTP 请求 | X | O |
| 发送邮件 | X | O |
| LLM 调用 | X | O |

---

## 9. 错误处理

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

---

## 10. 注意事项

1. **Workflow 必须是确定性的**：
   - 不能用 `random.random()`，用 `workflow.random()`
   - 不能用 `datetime.now()`，用 `workflow.now()`
   - 不能直接做 I/O，用 Activity
   - 使用 `workflow.logger` 记录日志

2. **Activity 设计原则**：
   - 每个 Activity 应该是幂等的
   - 设置合理的超时和重试策略
   - 长时间运行的 Activity 需要发送心跳

3. **Signal 注意事项**：
   - Signal 是异步的，发送后不等待处理
   - 多次发送相同 Signal 会多次触发
   - Workflow 应该检查状态避免重复处理

---

## 11. 运维

### 启动服务

```bash
# 启动 Temporal Server (Docker)
docker-compose up -d temporal temporal-ui

# 启动 Worker
cd backend && python -m app.temporal.worker

# 使用脚本
./scripts/restart.sh --worker
```

### 监控

- **Temporal UI**: http://localhost:8080 — 查看运行中的工作流、历史记录、发送 Signal、终止工作流
- **Worker 日志**: `logs/worker.log`
- **Temporal Server 日志**: `docker compose logs temporal`

### 状态查看

```bash
./scripts/status.sh     # 查看所有服务状态
./scripts/logs.sh worker  # 查看 Worker 日志
```

---

## 相关文档

- [后端开发手册](BACKEND_HANDBOOK.md)
- [Celery 指南](CELERY_GUIDE.md) — 定时任务（邮件轮询等）
- [邮件处理管线](../architecture/EMAIL_PIPELINE.md)
- [WorkTypeSuggestionWorkflow 详细文档](../temporal-workflows/WorkTypeSuggestionWorkflow.md)

---

*合并自: MANUAL.md §15 + temporal-workflows/README.md | 最后更新: 2026-02-10*
