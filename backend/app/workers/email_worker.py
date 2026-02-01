# app/workers/email_worker.py
# 邮件 IMAP Worker
#
# 功能说明：
# 1. 定时拉取新邮件（IMAP）
# 2. 支持监听多个邮箱账户（从 email_accounts 表读取）
# 3. 将邮件转换为 UnifiedEvent 并分发处理
#
# 启动方式：
#   python -m app.workers.email_worker
#
# 特点：
# - 使用 APScheduler 实现定时任务
# - 支持多邮箱账户（配置在数据库中）
# - 使用 Redis 保存检查点，避免重复处理

import os
import sys
import argparse
import asyncio
from typing import Optional
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.logging import get_logger, setup_logging
from app.core.config import settings
from app.core.redis import redis_client
from app.core.database import async_session_maker
from app.storage.email import (
    imap_fetch,
    imap_mark_as_read,
    get_active_imap_accounts,
    EmailMessage,
    EmailAccountConfig,
)
from app.storage.email_persistence import persistence_service
from app.adapters.email import email_adapter
from app.messaging.streams import redis_streams
from app.messaging.dispatcher import event_dispatcher
from app.workers.base import BaseWorker, WorkerStatus

logger = get_logger(__name__)


class EmailWorker(BaseWorker):
    """
    邮件 IMAP Worker

    定时从 IMAP 服务器拉取新邮件，转换为 UnifiedEvent 后分发处理。

    特点：
    - 支持监听多个邮箱账户（从 email_accounts 表读取）
    - 使用 APScheduler 实现定时任务
    - 每个账户独立的 Redis 检查点和锁
    - 支持优雅启动/停止
    """

    worker_type = "email"
    name = "邮件 Worker"
    description = "邮件 IMAP 定时拉取，监听多个邮箱账户"

    # Redis 键名模板
    CHECKPOINT_KEY_TEMPLATE = "email_worker:{account_id}:last_check"
    LOCK_KEY_TEMPLATE = "email_worker:{account_id}:lock"

    # 默认配置
    DEFAULT_INTERVAL = 60  # 默认检查间隔（秒）
    DEFAULT_BATCH_SIZE = 50  # 每次拉取的最大邮件数

    def __init__(self):
        self.interval = self.DEFAULT_INTERVAL
        self.batch_size = self.DEFAULT_BATCH_SIZE
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._active_accounts = {}

    @classmethod
    def get_required_config_fields(cls) -> list[str]:
        # 邮件 Worker 从数据库读取账户配置，不需要在 worker_configs 中配置
        return []

    @classmethod
    def get_optional_config_fields(cls) -> list[str]:
        return ["interval", "batch_size"]

    async def start(self, config: dict) -> bool:
        """启动 Worker"""
        self.interval = config.get("interval", self.DEFAULT_INTERVAL)
        self.batch_size = config.get("batch_size", self.DEFAULT_BATCH_SIZE)

        try:
            self._status = WorkerStatus.STARTING
            logger.info("[EmailWorker] 正在启动...")

            # 获取所有启用 IMAP 的邮箱账户
            accounts = await get_active_imap_accounts()

            if not accounts:
                logger.warning("[EmailWorker] 没有配置任何邮箱账户，无法启动监听")
                self._set_error("没有配置邮箱账户")
                return False

            # 初始化 Redis Streams
            await redis_streams.initialize()

            # 创建调度器
            self.scheduler = AsyncIOScheduler()

            # 为每个账户创建监听任务
            for account in accounts:
                account_key = account.id if account.id else "env"
                self._active_accounts[account_key] = account

                self.scheduler.add_job(
                    self._poll_account,
                    trigger=IntervalTrigger(seconds=self.interval),
                    id=f"email_poll_{account_key}",
                    name=f"邮件轮询: {account.name}",
                    args=[account],
                    max_instances=1,
                    coalesce=True,
                )

                logger.info(
                    f"[EmailWorker] 添加监听任务: {account.name} ({account.imap_user})"
                )

            # 启动调度器
            self.scheduler.start()
            self._set_running(os.getpid())

            logger.info(
                f"[EmailWorker] 邮件监听已启动，"
                f"监听 {len(accounts)} 个邮箱，"
                f"间隔: {self.interval}秒"
            )

            # 立即执行一次
            for account in accounts:
                try:
                    await self._poll_account(account)
                except Exception as e:
                    logger.error(f"[EmailWorker] 初始轮询失败 ({account.name}): {e}")

            return True

        except Exception as e:
            logger.error(f"[EmailWorker] 启动失败: {e}")
            self._set_error(str(e))
            return False

    async def stop(self) -> bool:
        """停止 Worker"""
        logger.info("[EmailWorker] 正在停止...")
        self._status = WorkerStatus.STOPPING

        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=False)
                self.scheduler = None

            self._active_accounts.clear()
            self._set_stopped()
            logger.info("[EmailWorker] 邮件监听已停止")
            return True

        except Exception as e:
            logger.error(f"[EmailWorker] 停止失败: {e}")
            return False

    async def test_connection(self, config: dict) -> tuple[bool, str]:
        """测试连接（检查是否有可用的邮箱账户）"""
        try:
            accounts = await get_active_imap_accounts()
            if accounts:
                return True, f"找到 {len(accounts)} 个邮箱账户"
            else:
                return False, "没有配置邮箱账户"
        except Exception as e:
            return False, str(e)

    async def _poll_account(self, account: EmailAccountConfig) -> None:
        """轮询指定账户的新邮件"""
        account_key = account.id if account.id else "env"
        lock_key = self.LOCK_KEY_TEMPLATE.format(account_id=account_key)

        # 尝试获取分布式锁
        lock_acquired = await redis_client.set(
            lock_key,
            "1",
            ex=self.interval + 30,
            nx=True,
        )

        if not lock_acquired:
            logger.debug(f"[EmailWorker] 其他实例正在处理 {account.name}，跳过")
            return

        try:
            # 获取上次检查点
            last_check = await self._get_checkpoint(account_key)
            logger.debug(f"[EmailWorker] {account.name} 上次检查: {last_check}")

            # 拉取新邮件（使用账户配置的文件夹）
            emails = await imap_fetch(
                folder=account.imap_folder,
                limit=self.batch_size,
                since=last_check,
                unseen_only=True,
                account_id=account.id,
            )

            if not emails:
                logger.debug(f"[EmailWorker] {account.name} 没有新邮件")
                await self._save_checkpoint(account_key)
                return

            logger.info(f"[EmailWorker] {account.name} 发现 {len(emails)} 封新邮件")

            # 处理每封邮件
            processed = 0
            for email in emails:
                try:
                    await self._process_email(email, account)
                    processed += 1
                except Exception as e:
                    logger.error(
                        f"[EmailWorker] 处理邮件失败 ({account.name}): "
                        f"{email.message_id}, {e}"
                    )

            logger.info(
                f"[EmailWorker] {account.name} 处理完成: {processed}/{len(emails)}"
            )

            # 更新检查点
            await self._save_checkpoint(account_key)

        except Exception as e:
            logger.error(f"[EmailWorker] 轮询失败 ({account.name}): {e}")

        finally:
            # 释放锁
            await redis_client.delete(lock_key)

    async def _process_email(
        self,
        email: EmailMessage,
        account: EmailAccountConfig,
    ) -> None:
        """处理单封邮件"""
        logger.info(
            f"[EmailWorker] 处理邮件 ({account.name}): "
            f"{email.message_id[:50]}... "
            f"from={email.sender} subject={email.subject[:30] if email.subject else ''}"
        )

        # 1. 持久化原始邮件和附件到 OSS
        raw_record = None
        if email.raw_bytes:
            try:
                raw_record = await persistence_service.persist(email, account.id)
                logger.info(f"[EmailWorker] 已持久化: {raw_record.id}")
            except Exception as e:
                logger.error(f"[EmailWorker] 持久化失败: {e}")
                # 持久化失败不阻断处理流程

        # 2. 转换为 UnifiedEvent
        event = await email_adapter.to_unified_event(email)

        # 3. 记录来源邮箱账户和 raw_id
        if account.id:
            event.metadata["email_account_id"] = account.id
        event.metadata["email_account_name"] = account.name
        if raw_record:
            event.metadata["email_raw_id"] = raw_record.id

        # 4. 添加到 Redis Streams
        stream_id = await redis_streams.add_event(event)
        logger.debug(f"[EmailWorker] 添加到 Stream: {stream_id}")

        # 5. 分发到 Dispatcher
        workflow_id = await event_dispatcher.dispatch(event)
        if workflow_id:
            logger.info(f"[EmailWorker] 启动 Workflow: {workflow_id}")

        # 6. 更新持久化记录的处理状态
        if raw_record:
            try:
                await persistence_service.mark_processed(raw_record.id, event.event_id)
            except Exception as e:
                logger.warning(f"[EmailWorker] 更新持久化状态失败: {e}")

        # 7. 标记邮件为已读（根据配置决定是否标记）
        if account.imap_mark_as_read:
            await imap_mark_as_read(
                email.message_id,
                folder=account.imap_folder,
                account_id=account.id,
            )

    async def _get_checkpoint(self, account_key) -> Optional[datetime]:
        """获取上次检查点时间"""
        checkpoint_key = self.CHECKPOINT_KEY_TEMPLATE.format(account_id=account_key)
        timestamp = await redis_client.get(checkpoint_key)
        if timestamp:
            try:
                return datetime.fromisoformat(timestamp)
            except ValueError:
                pass
        return datetime.now() - timedelta(days=1)

    async def _save_checkpoint(self, account_key) -> None:
        """保存检查点时间"""
        checkpoint_key = self.CHECKPOINT_KEY_TEMPLATE.format(account_id=account_key)
        timestamp = datetime.now().isoformat()
        await redis_client.set(checkpoint_key, timestamp, ex=86400 * 7)

    def get_worker_status(self) -> dict:
        """获取详细状态"""
        return {
            "running": self._status == WorkerStatus.RUNNING,
            "account_count": len(self._active_accounts),
            "accounts": [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "imap_user": acc.imap_user,
                }
                for acc in self._active_accounts.values()
            ],
            "interval": self.interval,
            "batch_size": self.batch_size,
        }


# ==================== 独立进程模式 ====================

def _load_llm_settings_sync() -> None:
    """从数据库同步加载 LLM 设置到环境变量"""
    import os
    import asyncpg
    from app.core.config import settings as app_settings

    async def _fetch_settings():
        db_url = app_settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)
        try:
            rows = await conn.fetch(
                "SELECT key, value FROM system_settings WHERE category = 'llm'"
            )
            return rows
        finally:
            await conn.close()

    try:
        loop = asyncio.new_event_loop()
        rows = loop.run_until_complete(_fetch_settings())
        loop.close()

        for row in rows:
            key, value = row['key'], row['value']
            if key == "llm.anthropic_api_key" and value:
                os.environ["ANTHROPIC_API_KEY"] = value
                logger.info("[EmailWorker] 已设置 ANTHROPIC_API_KEY")
            elif key == "llm.openai_api_key" and value:
                os.environ["OPENAI_API_KEY"] = value
                logger.info("[EmailWorker] 已设置 OPENAI_API_KEY")
            elif key == "llm.default_model" and value:
                os.environ["DEFAULT_LLM_MODEL"] = value
                logger.info(f"[EmailWorker] 已设置 DEFAULT_LLM_MODEL: {value}")

    except Exception as e:
        logger.error(f"[EmailWorker] 加载 LLM 设置失败: {e}")


async def run_worker(interval: int = 60, batch_size: int = 50):
    """运行邮件 Worker"""
    logger.info("=" * 60)
    logger.info("邮件 IMAP Worker 启动中...")
    logger.info("=" * 60)

    # 连接 Redis
    await redis_client.connect()
    logger.info("[EmailWorker] Redis 连接成功")

    # 创建并启动 Worker
    worker = EmailWorker()
    config = {
        "interval": interval,
        "batch_size": batch_size,
    }

    success = await worker.start(config)
    if not success:
        logger.error("[EmailWorker] 启动失败")
        return

    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("[EmailWorker] 收到中断信号")
    finally:
        await worker.stop()
        await redis_client.disconnect()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="邮件 IMAP Worker")
    parser.add_argument("--worker-id", help="Worker 配置 ID")
    parser.add_argument("--interval", type=int, default=60, help="检查间隔（秒）")
    parser.add_argument("--batch-size", type=int, default=50, help="每次拉取数量")
    parser.add_argument("--agent-id", default="email_analyzer", help="绑定的 Agent ID（兼容 WorkerManager）")
    args = parser.parse_args()

    # 初始化日志
    setup_logging()

    logger.info("=" * 60)
    logger.info("邮件 IMAP Worker 启动")
    logger.info(f"  Worker ID: {args.worker_id or '(未指定)'}")
    logger.info(f"  Agent: {args.agent_id}")
    logger.info(f"  间隔: {args.interval}秒")
    logger.info(f"  批量大小: {args.batch_size}")
    logger.info("=" * 60)

    # 加载 LLM 设置（在 asyncio.run 之前）
    _load_llm_settings_sync()

    # 运行
    asyncio.run(run_worker(args.interval, args.batch_size))


if __name__ == "__main__":
    main()
