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
from app.core.logging import get_logger

logger = get_logger(__name__)

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
    worker_cancel_long_running_tasks_on_connection_loss=True,  # 连接丢失时取消执行中的任务（Celery 6 默认行为）

    # Broker 连接配置（增强 Redis 断线重连能力）
    broker_connection_retry_on_startup=True,  # 启动时重试连接
    broker_connection_max_retries=None,  # 无限重试（不放弃连接）
    broker_connection_timeout=10,  # 连接超时 10 秒
    broker_transport_options={
        "visibility_timeout": 3600,   # 任务可见性超时 1 小时
        "retry_on_timeout": True,     # 超时时自动重试
        "socket_keepalive": True,     # 保持 TCP 连接活跃
        "health_check_interval": 30,  # 每 30 秒健康检查
    },

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

    在 Beat 进程启动时直接从数据库加载邮箱账户并注册轮询任务，
    确保 Beat 进程自身持有完整的调度计划。
    """
    # 添加定期同步任务（每 5 分钟，处理运行时新增/删除的账户）
    sender.add_periodic_task(
        300.0,  # 每 5 分钟
        sync_email_tasks_periodic.s(),
        name="sync-email-tasks-periodic",
    )
    logger.info("[Celery] 已添加定期邮件任务同步 (每 5 分钟)")

    # 示例：每天凌晨 2 点清理过期数据
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        cleanup_expired_data.s(),
        name="cleanup-expired-data",
    )

    # 启动时立即从数据库加载邮箱账户，注册轮询任务
    # 这样 Beat 进程自身就持有这些任务，不依赖 Worker 进程的修改
    # 注意：on_after_configure 在 Celery 信号中触发，不能使用 async 数据库连接，
    # 因此这里用同步 psycopg2 连接直接查询
    try:
        from sqlalchemy import create_engine, text

        # 将 async URL 转为 sync URL（asyncpg -> psycopg2）
        sync_url = settings.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )
        sync_engine = create_engine(sync_url)

        with sync_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id FROM email_accounts "
                "WHERE is_active = true AND imap_host IS NOT NULL AND imap_host != ''"
            )).fetchall()

        sync_engine.dispose()

        for row in rows:
            account_id = row[0]
            task_name = f"poll-email-{account_id}"
            task_sig = sender.signature(
                "app.tasks.email.poll_email_account",
                args=(account_id,),
            )
            sender.add_periodic_task(
                60.0,  # 每 60 秒
                task_sig,
                name=task_name,
                options={"queue": "email", "expires": 90},
            )
            logger.info(f"[Celery] 注册邮件轮询任务: {task_name}")
        logger.info(f"[Celery] 启动时注册了 {len(rows)} 个邮件轮询任务")
    except Exception as e:
        logger.warning(f"[Celery] 启动时注册邮件轮询任务失败（将由定期同步补充）: {e}")


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


@celery_app.task
def sync_email_tasks_periodic():
    """定期同步邮件任务"""
    from app.services.email_worker_service import email_worker_service
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        stats = loop.run_until_complete(email_worker_service.sync_email_tasks())
        logger.info(f"[Celery] 定期邮件任务同步完成: {stats}")
        return {"status": "success", "stats": stats}
    finally:
        loop.close()


# ==================== Worker 生命周期钩子 ====================

from celery.signals import worker_process_init, worker_process_shutdown
import redis.asyncio as redis_async

# 进程级全局变量（每个 Worker 子进程独立）
_process_db_engine = None
_process_redis_client = None
_process_event_loop = None


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Worker 子进程初始化钩子"""
    global _process_db_engine, _process_redis_client, _process_event_loop

    from app.core.config import settings
    from app.core.logging import get_logger
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.core import database
    import os
    import asyncio

    logger = get_logger(__name__)
    logger.info(f"[Celery Worker] 初始化子进程: PID={os.getpid()}")

    # 创建并设置持久的 event loop（所有任务共享）
    _process_event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_process_event_loop)
    logger.info(f"[Celery Worker] 创建持久 event loop")

    # 为子进程创建独立的数据库引擎
    _process_db_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

    # 替换全局 engine 和 session_maker
    database.engine = _process_db_engine
    database.async_session_maker = async_sessionmaker(
        _process_db_engine,
        class_=database.AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info(f"[Celery Worker] 数据库连接池已初始化: pool_size=5, max_overflow=10")

    # 为子进程创建独立的 Redis 连接
    _process_redis_client = redis_async.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )

    logger.info(f"[Celery Worker] Redis 连接已创建")


@worker_process_shutdown.connect
def shutdown_worker_process(**kwargs):
    """Worker 子进程关闭钩子"""
    global _process_db_engine, _process_redis_client, _process_event_loop

    import os
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info(f"[Celery Worker] 关闭子进程: PID={os.getpid()}")

    if _process_event_loop:
        try:
            if _process_db_engine:
                _process_event_loop.run_until_complete(_process_db_engine.dispose())
                logger.info("[Celery Worker] 数据库连接池已关闭")

            if _process_redis_client:
                _process_event_loop.run_until_complete(_process_redis_client.close())
                logger.info("[Celery Worker] Redis 连接已关闭")
        finally:
            _process_event_loop.close()
            logger.info("[Celery Worker] Event loop 已关闭")

    _process_db_engine = None
    _process_redis_client = None
    _process_event_loop = None


def get_worker_redis_client() -> redis_async.Redis:
    """获取 Worker 子进程的 Redis 客户端"""
    global _process_redis_client

    if _process_redis_client is None:
        raise RuntimeError(
            "Worker Redis client not initialized. "
            "This function can only be called within Celery tasks."
        )

    return _process_redis_client
