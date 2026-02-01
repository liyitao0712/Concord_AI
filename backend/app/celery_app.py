# app/celery_app.py
# Celery 应用配置
#
# 功能说明：
# 1. Celery 实例创建和配置
# 2. 任务自动发现
# 3. 定时任务管理（Celery Beat）
#
# 启动方式：
#   # Celery Beat（定时调度器）
#   celery -A app.celery_app beat --loglevel=info
#
#   # Celery Worker（任务执行器，可启动多个）
#   celery -A app.celery_app worker --loglevel=info --concurrency=10
#
#   # Flower（监控面板，可选）
#   celery -A app.celery_app flower --port=5555

from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

from app.core.config import settings

# ==================== 创建 Celery 应用 ====================

celery_app = Celery(
    "concord",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# ==================== Celery 配置 ====================

celery_app.conf.update(
    # 时区配置
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # 结果后端配置
    result_backend=settings.REDIS_URL,
    result_expires=3600,  # 结果保存 1 小时

    # 任务执行配置
    task_acks_late=True,  # 任务执行完才确认（防止任务丢失）
    task_reject_on_worker_lost=True,  # Worker 丢失时重新排队
    task_track_started=True,  # 跟踪任务开始状态

    # Worker 配置
    worker_prefetch_multiplier=1,  # 每次只取 1 个任务（公平分发）
    worker_max_tasks_per_child=1000,  # 每个 Worker 进程处理 1000 个任务后重启（防止内存泄漏）

    # 任务路由
    task_routes={
        "app.tasks.email.*": {"queue": "email"},  # 邮件任务专用队列
        "app.tasks.workflow.*": {"queue": "workflow"},  # Workflow 任务专用队列
    },

    # 队列定义
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("email", Exchange("email"), routing_key="email"),
        Queue("workflow", Exchange("workflow"), routing_key="workflow"),
    ),

    # Beat 调度器配置
    beat_schedule={},  # 动态任务，在运行时添加
    beat_max_loop_interval=60,  # Beat 最大循环间隔（秒）

    # 日志配置
    worker_hijack_root_logger=False,  # 不劫持根日志

    # 任务限流（防止雪崩）
    task_annotations={
        "*": {"rate_limit": "100/s"},  # 全局限流：每秒最多 100 个任务
    },
)

# ==================== 任务自动发现 ====================

# 自动发现 app/tasks/ 目录下的所有任务
celery_app.autodiscover_tasks(["app.tasks"])

# ==================== 启动时钩子 ====================

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    启动时设置定时任务

    注意：邮件轮询任务是动态添加的，由 EmailWorkerService 管理
    这里只设置系统级别的定时任务
    """
    # 示例：每天凌晨 2 点清理过期数据
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        cleanup_expired_data.s(),
        name="cleanup-expired-data",
    )


# ==================== 系统任务 ====================

@celery_app.task
def cleanup_expired_data():
    """清理过期数据（示例任务）"""
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("[Celery] 执行定期清理任务")
    # TODO: 实现清理逻辑
    return {"status": "success", "message": "清理完成"}


# ==================== 健康检查 ====================

@celery_app.task
def health_check():
    """健康检查任务"""
    return {"status": "healthy", "message": "Celery is running"}
