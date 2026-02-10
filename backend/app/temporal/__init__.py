# app/temporal/__init__.py
# Temporal 工作流模块
#
# 这个模块包含：
# - client.py: Temporal Client 封装
# - worker.py: Temporal Worker 启动器
# - workflows/: 工作流定义
# - activities/: 活动定义
#
# 使用方式：
#   from app.temporal.client import get_temporal_client, start_suggestion_workflow
#   from app.temporal.workflows import WorkTypeSuggestionWorkflow

from app.temporal.client import (
    get_temporal_client,
    start_suggestion_workflow,
    approve_suggestion,
    reject_suggestion,
)

__all__ = [
    "get_temporal_client",
    "start_suggestion_workflow",
    "approve_suggestion",
    "reject_suggestion",
]
