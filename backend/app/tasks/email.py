# app/tasks/email.py
# 邮件相关的 Celery 任务
#
# 功能说明：
# 1. poll_email_account - 定时拉取邮箱的新邮件
# 2. process_email - 处理单封邮件（持久化、分发、启动 Workflow）
#
# 任务特点：
# - 自动重试（失败后自动重试 3 次）
# - 分布式锁（防止重复处理）
# - 任务队列隔离（email 队列）

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from celery import Task

from app.celery_app import celery_app
from app.core.logging import get_logger
from app.core.redis import redis_client

logger = get_logger(__name__)


# ==================== 异步任务包装器 ====================

class AsyncTask(Task):
    """
    支持异步函数的 Celery Task 基类

    用法：
        @celery_app.task(base=AsyncTask)
        async def my_task():
            await some_async_operation()
    """

    def __call__(self, *args, **kwargs):
        """执行任务时使用 Worker 进程的持久 event loop"""
        # 使用 Worker 进程初始化时创建的持久 event loop
        # 所有任务共享同一个 loop，避免 loop 反复创建/销毁导致的问题
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run(*args, **kwargs))

    async def run(self, *args, **kwargs):
        """子类需要实现这个方法"""
        raise NotImplementedError()


# ==================== 邮件拉取任务 ====================

@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="app.tasks.email.poll_email_account",
    max_retries=3,
    default_retry_delay=60,  # 失败后 60 秒重试
    queue="email",
)
async def poll_email_account(self, account_id: int):
    """
    拉取指定邮箱的新邮件

    Args:
        account_id: 邮箱账户 ID

    Returns:
        dict: 处理统计
            - account_id: 账户 ID
            - emails_found: 发现的新邮件数
            - emails_queued: 已加入处理队列的邮件数
            - skipped: 被跳过的邮件数（已处理或其他实例正在处理）

    Raises:
        Exception: IMAP 连接失败或其他错误（会自动重试）
    """
    from app.storage.email import get_active_imap_accounts, imap_fetch
    from app.celery_app import get_worker_redis_client

    logger.info(f"[Celery:PollEmail] 开始轮询邮箱: account_id={account_id}")

    # 使用 Worker Redis 连接
    redis_conn = get_worker_redis_client()

    try:
        # 获取分布式锁
        lock_key = f"email_worker:{account_id}:lock"
        lock_acquired = await redis_conn.set(
            lock_key,
            f"celery-{self.request.id}",  # 使用任务 ID 作为锁值
            ex=300,  # 锁过期时间 5 分钟
            nx=True,
        )

        if not lock_acquired:
            logger.debug(f"[Celery:PollEmail] 其他实例正在处理 account_id={account_id}，跳过")
            return {
                "account_id": account_id,
                "emails_found": 0,
                "emails_queued": 0,
                "skipped": True,
                "reason": "locked_by_another_instance",
            }
        # 获取账户信息
        accounts = await get_active_imap_accounts()
        account = next((acc for acc in accounts if acc.id == account_id), None)

        if not account:
            logger.warning(f"[Celery:PollEmail] 账户不存在或已禁用: {account_id}")
            return {
                "account_id": account_id,
                "emails_found": 0,
                "emails_queued": 0,
                "error": "account_not_found_or_disabled",
            }

        # 获取上次检查点（使用账户配置的同步天数）
        last_check = await _get_checkpoint(redis_conn, account_id, account.imap_sync_days)
        logger.debug(f"[Celery:PollEmail] 上次检查时间: {last_check}")

        # 拉取新邮件（使用账户配置）
        emails = await imap_fetch(
            folder=account.imap_folder,
            limit=account.imap_fetch_limit,  # 使用账户配置的拉取数量
            since=last_check,
            unseen_only=account.imap_unseen_only,  # 使用账户配置的未读策略
            account_id=account_id,
        )

        if not emails:
            logger.debug(f"[Celery:PollEmail] 没有新邮件: {account.name}")
            await _save_checkpoint(redis_conn, account_id)
            return {
                "account_id": account_id,
                "emails_found": 0,
                "emails_queued": 0,
            }

        logger.info(f"[Celery:PollEmail] 发现 {len(emails)} 封新邮件: {account.name}")

        # 将每封邮件作为独立任务加入队列
        queued = 0
        for email in emails:
            try:
                # 异步调用 process_email 任务（包含 raw_bytes 以便持久化）
                process_email.delay(
                    email_data=email.to_dict(include_raw_bytes=True),
                    account_id=account_id,
                )
                queued += 1
            except Exception as e:
                logger.error(f"[Celery:PollEmail] 加入队列失败: {email.message_id}, {e}")

        # 更新检查点
        await _save_checkpoint(redis_conn, account_id)

        logger.info(f"[Celery:PollEmail] 完成轮询: {account.name}, 发现 {len(emails)} 封，已加入队列 {queued} 封")

        return {
            "account_id": account_id,
            "emails_found": len(emails),
            "emails_queued": queued,
        }

    except Exception as exc:
        logger.error(f"[Celery:PollEmail] 轮询失败: account_id={account_id}, {exc}")
        # 自动重试
        raise self.retry(exc=exc)

    finally:
        # 释放锁
        await redis_conn.delete(lock_key)
        # 注意：不要关闭 Worker Redis 连接，它是共享的


# ==================== 邮件处理任务 ====================

@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="app.tasks.email.process_email",
    max_retries=3,
    default_retry_delay=120,  # 失败后 2 分钟重试
    queue="email",
)
async def process_email(self, email_data: dict, account_id: int):
    """
    处理单封邮件

    流程：
    1. 持久化邮件和附件到 OSS/本地存储
    2. 转换为 UnifiedEvent
    3. 添加到 Redis Streams
    4. 分发到 Dispatcher（意图分类 + 启动 Workflow）
    5. 标记邮件已读（可选）

    Args:
        email_data: 邮件数据字典（EmailMessage.to_dict() 的结果）
        account_id: 邮箱账户 ID

    Returns:
        dict: 处理结果
            - message_id: 邮件 Message-ID
            - raw_record_id: 持久化记录 ID
            - event_id: UnifiedEvent ID
            - workflow_id: 启动的 Workflow ID

    Raises:
        Exception: 处理失败（会自动重试）
    """
    from app.storage.email import EmailMessage, get_active_imap_accounts, imap_mark_as_read
    from app.storage.email_persistence import persistence_service
    from app.adapters.email import email_adapter
    from app.messaging.streams import RedisStreams
    from app.messaging.dispatcher import event_dispatcher
    from app.celery_app import get_worker_redis_client

    # 反序列化邮件数据
    email = EmailMessage.from_dict(email_data)

    logger.info(
        f"[Celery:ProcessEmail] 处理邮件: "
        f"message_id={email.message_id[:50]}..., "
        f"from={email.sender}, "
        f"subject={email.subject[:30] if email.subject else ''}"
    )

    try:
        # 1. 获取并缓存账户信息（避免重复查询）
        accounts = await get_active_imap_accounts()
        account = next((acc for acc in accounts if acc.id == account_id), None)

        if not account:
            logger.warning(f"[Celery:ProcessEmail] 账户不存在: {account_id}")
            return {"status": "error", "error": "account_not_found"}

        # 2. 持久化原始邮件和附件
        raw_record = None
        if email.raw_bytes:
            try:
                raw_record = await persistence_service.persist(email, account_id)
                logger.info(f"[Celery:ProcessEmail] 已持久化: {raw_record.id}")
            except Exception as e:
                logger.error(f"[Celery:ProcessEmail] 持久化失败: {e}")
                # 持久化失败不阻断流程（可能是重复邮件）

        # 3. 转换为 UnifiedEvent
        event = await email_adapter.to_unified_event(email)

        # 4. 添加元数据（使用缓存的 account）
        event.metadata["email_account_id"] = account_id
        event.metadata["email_account_name"] = account.name

        if raw_record:
            event.metadata["email_raw_id"] = raw_record.id

        # 5. 添加到 Redis Streams（使用 Worker Redis 连接）
        worker_redis_streams = RedisStreams(redis_client_override=get_worker_redis_client())
        stream_id = await worker_redis_streams.add_event(event)
        logger.debug(f"[Celery:ProcessEmail] 添加到 Stream: {stream_id}")

        # 6. 分发到 Dispatcher（意图分类 + 启动 Workflow）
        workflow_id = await event_dispatcher.dispatch(event)
        if workflow_id:
            logger.info(f"[Celery:ProcessEmail] 启动 Workflow: {workflow_id}")

        # 7. 更新持久化记录状态
        if raw_record:
            try:
                await persistence_service.mark_processed(raw_record.id, event.event_id)
            except Exception as e:
                logger.warning(f"[Celery:ProcessEmail] 更新持久化状态失败: {e}")

        # 8. 标记邮件为已读（使用缓存的 account）
        if account.imap_mark_as_read:
            await imap_mark_as_read(
                email.message_id,
                folder=account.imap_folder,
                account_id=account_id,
            )

        logger.info(f"[Celery:ProcessEmail] 处理完成: {email.message_id[:50]}...")

        return {
            "message_id": email.message_id,
            "raw_record_id": raw_record.id if raw_record else None,
            "event_id": event.event_id,
            "workflow_id": workflow_id,
            "status": "success",
        }

    except Exception as exc:
        logger.error(f"[Celery:ProcessEmail] 处理失败: {email.message_id}, {exc}")
        # 自动重试
        raise self.retry(exc=exc)


# ==================== 辅助函数 ====================

async def _get_checkpoint(redis_conn, account_id: int, sync_days: Optional[int] = None) -> Optional[datetime]:
    """
    获取邮箱的上次检查时间

    Args:
        redis_conn: Redis 连接
        account_id: 账户 ID
        sync_days: 同步天数配置（None=全部历史，1=1天前，30=30天前）

    Returns:
        上次检查时间或根据配置计算的起始时间
    """
    checkpoint_key = f"email_worker:{account_id}:last_check"
    timestamp = await redis_conn.get(checkpoint_key)

    if timestamp:
        try:
            return datetime.fromisoformat(timestamp)
        except ValueError:
            pass

    # 首次运行：根据配置决定同步范围
    if sync_days is None:
        # None 表示同步全部历史邮件（从很久以前开始）
        return datetime(2000, 1, 1)  # 从 2000 年开始，基本覆盖所有邮件
    else:
        # 同步指定天数的邮件
        return datetime.now() - timedelta(days=sync_days)


async def _save_checkpoint(redis_conn, account_id: int) -> None:
    """保存邮箱的检查时间"""
    checkpoint_key = f"email_worker:{account_id}:last_check"
    timestamp = datetime.now().isoformat()
    await redis_conn.set(checkpoint_key, timestamp, ex=86400 * 7)  # 保存 7 天
