# app/workflows/definitions/__init__.py
# Workflow 定义模块
#
# Workflow 是 Temporal 中定义业务流程的单元。
# Workflow 代码必须是确定性的，意味着：
# - 不能使用随机数（用 workflow.random()）
# - 不能直接获取当前时间（用 workflow.now()）
# - 不能直接做 I/O 操作（用 Activity）
# - 不能使用全局可变状态
#
# Workflow 设计原则：
# 1. Workflow 是编排者，Activity 是执行者
# 2. Workflow 定义"做什么"，Activity 定义"怎么做"
# 3. Workflow 代码可以随时中断和恢复
# 4. Workflow 状态会被 Temporal 持久化

from app.workflows.definitions.approval import ApprovalWorkflow
from app.workflows.types import (
    ApprovalRequest,
    ApprovalResult,
    ApprovalStatus,
)

__all__ = [
    "ApprovalWorkflow",
    "ApprovalRequest",
    "ApprovalResult",
    "ApprovalStatus",
]
