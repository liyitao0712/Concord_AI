# app/workflows/__init__.py
# Temporal 工作流模块
#
# 目录结构：
# workflows/
# ├── __init__.py          # 模块初始化
# ├── worker.py            # Temporal Worker（运行 Workflow 和 Activity）
# ├── client.py            # Temporal Client（启动和查询 Workflow）
# ├── activities/          # Activity 定义（实际执行的任务）
# │   ├── __init__.py
# │   ├── base.py          # Activity 基类和工具函数
# │   ├── email.py         # 邮件相关 Activity
# │   └── notification.py  # 通知相关 Activity
# └── definitions/         # Workflow 定义（流程编排）
#     ├── __init__.py
#     ├── approval.py      # 审批工作流
#     └── order.py         # 订单处理工作流
#
# 核心概念：
# - Workflow: 定义业务流程的步骤和逻辑（必须是确定性的）
# - Activity: 实际执行的任务（可以包含 I/O 操作、外部调用）
# - Worker: 监听任务队列，执行 Workflow 和 Activity
# - Client: 与 Temporal Server 交互，启动/查询/取消 Workflow
# - Signal: 外部发送给运行中 Workflow 的信号（如审批通过）
# - Query: 查询运行中 Workflow 的状态（不影响执行）
#
# ⚠️ 重要：Temporal Sandbox 限制
# 此 __init__.py 不导入任何会触发非确定性操作的模块。
# Temporal Sandbox 在验证 Workflow 时会导入此模块，
# 如果导入链中包含 pydantic-settings、pathlib.expanduser 等操作会失败。
#
# 使用方式：
# - worker 和 client 应该直接从各自模块导入：
#   from app.workflows.worker import create_worker, run_worker
#   from app.workflows.client import get_temporal_client, start_workflow
# - 类型定义从 types 导入：
#   from app.workflows.types import ApprovalRequest, ApprovalStatus

# 只导出不触发 sandbox 限制的类型
from app.workflows.types import (
    NotificationType,
    NotificationRequest,
    WorkflowEvent,
    ApprovalStatus,
    ApprovalRequest,
    ApprovalResult,
)

__all__ = [
    # 类型定义
    "NotificationType",
    "NotificationRequest",
    "WorkflowEvent",
    "ApprovalStatus",
    "ApprovalRequest",
    "ApprovalResult",
]
