# app/tasks/__init__.py
# Celery 任务模块

from app.tasks.email import poll_email_account, process_email
from app.tasks.ai_lookup import ai_lookup_new_customer

__all__ = [
    "poll_email_account",
    "process_email",
    "ai_lookup_new_customer",
]
