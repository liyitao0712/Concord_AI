# Workers Archive

此目录存放已弃用的 Worker 实现，仅作参考。

## email_worker_apscheduler.py

**归档日期**: 2026-02-01

**原因**: 系统已从 APScheduler 迁移到 Celery，实现高并发邮件处理。

**替代方案**:
- 新实现：`app/tasks/email.py` (Celery Tasks)
- 调度服务：`app/services/email_worker_service.py`
- Celery 配置：`app/celery_app.py`

**架构变更**:
```
旧架构: APScheduler (单进程) → Email Worker → IMAP
新架构: Celery Beat → Redis Queue → Celery Workers (多实例) → IMAP
```

**性能提升**:
- 100 个邮箱：从 50 分钟降低到 8 分钟
- 支持水平扩展（可启动多个 Worker 实例）
- 任务隔离和自动重试

详见：[CELERY_MIGRATION.md](../../../../devdoc/CELERY_MIGRATION.md)
