# app/workers/__init__.py
# Worker Layer - 后台服务进程
#
# Worker 是长期运行的后台进程，负责：
# 1. 监听外部消息源（飞书、邮件等）
# 2. 将消息转换为 UnifiedEvent
# 3. 调用 Agent 处理并返回响应
#
# 注意：
# - 邮件处理使用 Celery (app/tasks/email.py)
# - EmailWorker 是 Celery 服务的管理器
# - Adapter: 负责消息格式转换（飞书消息 → UnifiedEvent）
# - Worker: 负责后台运行和监听（WebSocket 长连接 / Celery 任务）

from app.workers.base import BaseWorker, WorkerStatus
from app.workers.manager import WorkerManager, worker_manager
from app.workers.feishu_worker import FeishuWorker
from app.workers.email_worker import EmailWorker

# 注册 Worker 类型
worker_manager.register_worker_type("feishu", FeishuWorker)
worker_manager.register_worker_type("email", EmailWorker)

__all__ = [
    "BaseWorker",
    "WorkerStatus",
    "WorkerManager",
    "worker_manager",
    "FeishuWorker",
    "EmailWorker",
]
