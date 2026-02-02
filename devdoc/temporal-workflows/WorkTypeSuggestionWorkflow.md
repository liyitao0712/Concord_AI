# WorkTypeSuggestionWorkflow

## 概述

WorkTypeSuggestionWorkflow 是工作类型建议审批工作流，是项目第一个正式的 Temporal Workflow 实践。

负责：
- 接收 AI 生成的工作类型建议
- 通知管理员审批
- 等待审批信号
- 执行批准/拒绝操作

## 工作流信息

| 属性 | 值 |
|------|-----|
| Task Queue | concord-main-queue |
| Workflow ID 格式 | work-type-suggestion-{suggestion_id} |
| 超时时间 | 7 天 |
| 命名空间 | default |

## 执行流程

```
启动工作流
    ↓
发送通知给管理员（Activity）
    ↓
等待审批信号（最长 7 天）
    │
    ├─ 收到 approve Signal
    │       ↓
    │   执行 approve_suggestion_activity
    │       ↓
    │   创建 WorkType
    │
    ├─ 收到 reject Signal
    │       ↓
    │   执行 reject_suggestion_activity
    │       ↓
    │   更新状态为 rejected
    │
    └─ 超时（7 天）
            ↓
        自动拒绝
```

## Signals

### approve

批准建议，创建新的 WorkType。

```python
@workflow.signal
def approve(self, reviewer_id: str, note: str = ""):
    """批准信号"""
```

### reject

拒绝建议。

```python
@workflow.signal
def reject(self, reviewer_id: str, note: str = ""):
    """拒绝信号"""
```

## Queries

### get_status

查询当前工作流状态。

```python
@workflow.query
def get_status(self) -> dict:
    """
    返回:
    {
        "approved": bool | None,
        "reviewer_id": str | None,
        "review_note": str | None,
        "waiting_for_approval": bool,
    }
    """
```

## Activities

### notify_admin_activity

发送审批通知给管理员。

```python
@activity.defn
async def notify_admin_activity(suggestion_id: str) -> bool:
    """
    TODO: 实现通知逻辑（邮件/飞书/站内信）
    目前只记录日志
    """
```

### approve_suggestion_activity

批准建议，创建 WorkType。

```python
@activity.defn
async def approve_suggestion_activity(
    suggestion_id: str,
    reviewer_id: str,
    note: str
) -> dict:
    """
    返回:
    {
        "success": True,
        "work_type_id": "xxx",
        "work_type_code": "ORDER_URGENT",
        "suggestion_id": "xxx",
    }
    """
```

### reject_suggestion_activity

拒绝建议。

```python
@activity.defn
async def reject_suggestion_activity(
    suggestion_id: str,
    reviewer_id: str,
    note: str
) -> dict:
    """
    返回:
    {
        "success": True,
        "suggestion_id": "xxx",
        "rejected_reason": "xxx",
    }
    """
```

## 配置

在 `backend/app/core/config.py` 中：

```python
TEMPORAL_HOST: str = "localhost:7233"
TEMPORAL_NAMESPACE: str = "default"
TEMPORAL_TASK_QUEUE: str = "concord-main-queue"
```

## 使用方式

### 启动工作流

```python
from app.temporal import start_suggestion_workflow

workflow_id = await start_suggestion_workflow(suggestion_id)
```

### 发送审批信号

```python
from app.temporal import approve_suggestion, reject_suggestion

# 批准
await approve_suggestion(workflow_id, reviewer_id, "同意添加此类型")

# 拒绝
await reject_suggestion(workflow_id, reviewer_id, "类型定义不够清晰")
```

### 查询状态

```python
from app.temporal import get_workflow_status

status = await get_workflow_status(workflow_id)
# {"approved": None, "waiting_for_approval": True, ...}
```

## Worker 启动

```bash
cd backend
source venv/bin/activate
python -m app.temporal.worker
```

或使用脚本：

```bash
./scripts/restart.sh --worker
```

## 相关文件

| 文件 | 说明 |
|------|------|
| `backend/app/temporal/__init__.py` | 模块入口 |
| `backend/app/temporal/client.py` | Temporal Client 封装 |
| `backend/app/temporal/worker.py` | Worker 启动器 |
| `backend/app/temporal/workflows/work_type_suggestion.py` | 工作流定义 |
| `backend/app/temporal/activities/work_type.py` | Activity 实现 |

## Temporal UI

访问 http://localhost:8080 查看工作流执行状态。

## 错误处理

- Activity 失败会自动重试（最多 3 次）
- 工作流超时（7 天）自动拒绝
- 信号发送失败会抛出异常，API 层需要捕获

## 扩展计划

未来可能添加：
- 邮件通知 Activity
- 飞书机器人通知 Activity
- 审批提醒（定时 Activity）
