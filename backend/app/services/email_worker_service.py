# app/services/email_worker_service.py
# 邮件 Worker 服务管理
#
# 功能说明：
# 1. 动态管理 Celery Beat 定时任务
# 2. 为每个邮箱账户添加/删除轮询任务
# 3. 监控任务状态
#
# 使用方法：
#   from app.services.email_worker_service import email_worker_service
#
#   # 同步所有邮箱账户的定时任务
#   await email_worker_service.sync_email_tasks()

from datetime import timedelta
from typing import List, Dict

from celery.beat import PersistentScheduler
from celery.schedules import schedule

from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.celery_app import celery_app
from app.tasks.email import poll_email_account

logger = get_logger(__name__)


class EmailWorkerService:
    """
    邮件 Worker 服务

    负责动态管理邮件轮询任务：
    - 启动时扫描数据库，为每个邮箱账户创建定时任务
    - 账户变更时更新任务
    - 账户删除时移除任务
    """

    DEFAULT_INTERVAL = 60  # 默认轮询间隔（秒）

    async def sync_email_tasks(self, interval: int = DEFAULT_INTERVAL) -> Dict[str, int]:
        """
        同步邮箱账户的定时任务

        扫描数据库中所有启用的邮箱账户，为每个账户创建 Celery Beat 定时任务。

        Args:
            interval: 轮询间隔（秒），默认 60 秒

        Returns:
            dict: 同步统计
                - added: 新增的任务数
                - removed: 移除的任务数
                - updated: 更新的任务数
                - total: 总任务数
        """
        from app.storage.email import get_active_imap_accounts

        logger.info("[EmailWorkerService] 开始同步邮件轮询任务")

        # 获取所有启用的邮箱账户
        accounts = await get_active_imap_accounts()
        account_ids = {acc.id for acc in accounts if acc.id is not None}

        logger.info(f"[EmailWorkerService] 找到 {len(account_ids)} 个启用的邮箱账户")

        # 获取当前已注册的任务
        current_tasks = self._get_registered_email_tasks()
        current_ids = set(current_tasks.keys())

        # 计算需要添加、删除、更新的任务
        to_add = account_ids - current_ids
        to_remove = current_ids - account_ids
        to_update = account_ids & current_ids

        stats = {
            "added": 0,
            "removed": 0,
            "updated": 0,
            "total": 0,
        }

        # 添加新任务
        for account_id in to_add:
            self._add_email_task(account_id, interval)
            stats["added"] += 1
            logger.info(f"[EmailWorkerService] 添加任务: account_id={account_id}")

        # 删除过期任务
        for account_id in to_remove:
            self._remove_email_task(account_id)
            stats["removed"] += 1
            logger.info(f"[EmailWorkerService] 删除任务: account_id={account_id}")

        # 更新现有任务（如果间隔改变）
        for account_id in to_update:
            self._update_email_task(account_id, interval)
            stats["updated"] += 1

        stats["total"] = len(account_ids)

        logger.info(
            f"[EmailWorkerService] 同步完成: "
            f"新增 {stats['added']}, "
            f"删除 {stats['removed']}, "
            f"更新 {stats['updated']}, "
            f"总计 {stats['total']}"
        )

        return stats

    def _add_email_task(self, account_id: int, interval: int) -> None:
        """添加邮件轮询任务"""
        task_name = f"poll-email-{account_id}"

        celery_app.conf.beat_schedule[task_name] = {
            "task": "app.tasks.email.poll_email_account",
            "schedule": timedelta(seconds=interval),
            "args": (account_id,),
            "options": {
                "queue": "email",
                "expires": interval + 30,  # 任务过期时间
            },
        }

    def _remove_email_task(self, account_id: int) -> None:
        """删除邮件轮询任务"""
        task_name = f"poll-email-{account_id}"

        if task_name in celery_app.conf.beat_schedule:
            del celery_app.conf.beat_schedule[task_name]

    def _update_email_task(self, account_id: int, interval: int) -> None:
        """更新邮件轮询任务"""
        task_name = f"poll-email-{account_id}"

        if task_name in celery_app.conf.beat_schedule:
            celery_app.conf.beat_schedule[task_name]["schedule"] = timedelta(seconds=interval)

    def _get_registered_email_tasks(self) -> Dict[int, dict]:
        """
        获取当前已注册的邮件轮询任务

        Returns:
            dict: {account_id: task_config}
        """
        tasks = {}

        for task_name, task_config in celery_app.conf.beat_schedule.items():
            if task_name.startswith("poll-email-"):
                try:
                    account_id = int(task_name.split("-")[-1])
                    tasks[account_id] = task_config
                except (ValueError, IndexError):
                    pass

        return tasks

    async def add_account_task(self, account_id: int, interval: int = DEFAULT_INTERVAL) -> None:
        """
        为单个邮箱账户添加轮询任务

        Args:
            account_id: 邮箱账户 ID
            interval: 轮询间隔（秒）
        """
        self._add_email_task(account_id, interval)
        logger.info(f"[EmailWorkerService] 添加任务: account_id={account_id}, interval={interval}秒")

    async def remove_account_task(self, account_id: int) -> None:
        """
        删除单个邮箱账户的轮询任务

        Args:
            account_id: 邮箱账户 ID
        """
        self._remove_email_task(account_id)
        logger.info(f"[EmailWorkerService] 删除任务: account_id={account_id}")

    async def get_task_status(self) -> Dict[str, any]:
        """
        获取所有邮件轮询任务的状态

        Returns:
            dict: 任务状态统计
        """
        tasks = self._get_registered_email_tasks()

        return {
            "total_tasks": len(tasks),
            "account_ids": list(tasks.keys()),
            "tasks": [
                {
                    "account_id": account_id,
                    "interval": task_config["schedule"].total_seconds(),
                    "task_name": f"poll-email-{account_id}",
                }
                for account_id, task_config in tasks.items()
            ],
        }


# ==================== 全局单例 ====================

email_worker_service = EmailWorkerService()
