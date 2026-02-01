# app/workflows/activities/__init__.py
# Activity 模块
#
# Activity 是 Temporal 中实际执行任务的单元。
# 与 Workflow 不同，Activity 可以包含：
# - I/O 操作（数据库、文件、网络）
# - 外部 API 调用
# - 非确定性操作
#
# Activity 设计原则：
# 1. 每个 Activity 应该是幂等的（多次执行结果相同）
# 2. Activity 应该有超时设置
# 3. Activity 应该可以重试
# 4. Activity 不应该有副作用依赖（如全局状态）

from app.workflows.activities.base import (
    send_notification,
    log_workflow_event,
)
from app.workflows.types import (
    NotificationRequest,
    NotificationType,
    WorkflowEvent,
)

__all__ = [
    "send_notification",
    "log_workflow_event",
]
