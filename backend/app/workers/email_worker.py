# app/workers/email_worker.py
# 邮件 Worker - Celery 管理适配器
#
# 功能说明：
# 1. 适配 worker_manager 接口，管理 Celery 邮件服务
# 2. 启动/停止 Celery Beat 和 Worker
# 3. 同步邮件轮询任务
#
# 注意：
# - 邮件处理已从 APScheduler 迁移到 Celery
# - 这个 Worker 实际上是 Celery 服务的管理器
# - 不会像飞书 Worker 那样启动独立进程，而是控制 Celery 服务

import os
import subprocess
import signal
from typing import Optional, Tuple
from pathlib import Path

from app.core.logging import get_logger
from app.workers.base import BaseWorker

logger = get_logger(__name__)


class EmailWorker(BaseWorker):
    """
    邮件 Worker - Celery 服务管理器

    通过 worker_manager 接口管理 Celery 服务：
    - 启动: 调用 scripts/celery.sh start
    - 停止: 调用 scripts/celery.sh stop
    - 测试: 检查邮箱账户配置
    """

    name = "邮件服务 (Celery)"
    description = "基于 Celery 的邮件轮询服务，自动拉取和处理邮件"

    # 标记：使用自定义启动逻辑，不需要启动独立进程
    use_custom_start = True

    @classmethod
    def get_required_config_fields(cls) -> list[str]:
        """邮件 Worker 不需要额外配置（使用邮箱账户表）"""
        return []

    @classmethod
    def get_optional_config_fields(cls) -> list[str]:
        """可选配置"""
        return ["poll_interval"]  # 轮询间隔（秒），默认 60

    @classmethod
    def validate_config(cls, config: dict) -> Tuple[bool, str]:
        """验证配置"""
        poll_interval = config.get("poll_interval")
        if poll_interval is not None:
            try:
                interval = int(poll_interval)
                if interval < 10:
                    return False, "轮询间隔不能小于 10 秒"
                if interval > 3600:
                    return False, "轮询间隔不能超过 3600 秒"
            except ValueError:
                return False, "轮询间隔必须是整数"

        return True, ""

    async def start(self, config: dict) -> Tuple[bool, str]:
        """
        启动邮件 Worker (Celery 服务)

        Args:
            config: 配置字典

        Returns:
            (success, message)
        """
        try:
            # 获取项目根目录
            backend_dir = Path(__file__).parent.parent.parent
            project_root = backend_dir.parent
            celery_script = project_root / "scripts" / "celery.sh"

            if not celery_script.exists():
                return False, f"Celery 启动脚本不存在: {celery_script}"

            # 检查 Celery 是否已在运行
            status_result = subprocess.run(
                [str(celery_script), "status"],
                capture_output=True,
                text=True,
                cwd=project_root,
            )

            if "运行中" in status_result.stdout:
                logger.info("[EmailWorker] Celery 服务已在运行")
                # 同步邮件任务
                await self._sync_email_tasks()
                return True, "Celery 服务已在运行，已同步邮件任务"

            # 启动 Celery
            logger.info("[EmailWorker] 启动 Celery 服务...")
            result = subprocess.run(
                [str(celery_script), "start"],
                capture_output=True,
                text=True,
                cwd=project_root,
            )

            if result.returncode == 0:
                logger.info("[EmailWorker] Celery 服务已启动")

                # 同步邮件任务
                await self._sync_email_tasks()

                return True, "Celery 服务已启动，邮件任务已同步"
            else:
                error_msg = result.stderr or result.stdout or "启动失败"
                logger.error(f"[EmailWorker] 启动失败: {error_msg}")
                return False, f"启动失败: {error_msg}"

        except Exception as e:
            logger.error(f"[EmailWorker] 启动异常: {e}")
            return False, f"启动异常: {str(e)}"

    async def stop(self) -> Tuple[bool, str]:
        """
        停止邮件 Worker (Celery 服务)

        Returns:
            (success, message)
        """
        try:
            # 获取项目根目录
            backend_dir = Path(__file__).parent.parent.parent
            project_root = backend_dir.parent
            celery_script = project_root / "scripts" / "celery.sh"

            if not celery_script.exists():
                return False, f"Celery 停止脚本不存在: {celery_script}"

            # 停止 Celery
            logger.info("[EmailWorker] 停止 Celery 服务...")
            result = subprocess.run(
                [str(celery_script), "stop"],
                capture_output=True,
                text=True,
                cwd=project_root,
            )

            if result.returncode == 0:
                logger.info("[EmailWorker] Celery 服务已停止")
                return True, "Celery 服务已停止"
            else:
                error_msg = result.stderr or result.stdout or "停止失败"
                logger.error(f"[EmailWorker] 停止失败: {error_msg}")
                return False, f"停止失败: {error_msg}"

        except Exception as e:
            logger.error(f"[EmailWorker] 停止异常: {e}")
            return False, f"停止异常: {str(e)}"

    async def test_connection(self, config: dict) -> Tuple[bool, str]:
        """
        测试邮件服务配置

        检查：
        1. 是否有配置的邮箱账户
        2. Celery 服务状态

        Args:
            config: 配置字典

        Returns:
            (success, message)
        """
        from app.storage.email import get_active_imap_accounts

        try:
            # 检查邮箱账户
            accounts = await get_active_imap_accounts()

            if not accounts:
                return False, "没有配置邮箱账户，请先在管理后台添加邮箱账户"

            # 检查 Celery 服务
            backend_dir = Path(__file__).parent.parent.parent
            project_root = backend_dir.parent
            celery_script = project_root / "scripts" / "celery.sh"

            if celery_script.exists():
                result = subprocess.run(
                    [str(celery_script), "status"],
                    capture_output=True,
                    text=True,
                    cwd=project_root,
                )

                celery_status = "运行中" if "运行中" in result.stdout else "已停止"
            else:
                celery_status = "脚本不存在"

            message = (
                f"找到 {len(accounts)} 个邮箱账户\n"
                f"Celery 状态: {celery_status}\n"
                f"邮箱列表: {', '.join(acc.name for acc in accounts)}"
            )

            return True, message

        except Exception as e:
            logger.error(f"[EmailWorker] 测试连接失败: {e}")
            return False, f"测试失败: {str(e)}"

    async def _sync_email_tasks(self) -> None:
        """同步邮件轮询任务到 Celery Beat"""
        try:
            from app.services.email_worker_service import email_worker_service

            logger.info("[EmailWorker] 同步邮件任务...")
            stats = await email_worker_service.sync_email_tasks()

            logger.info(
                f"[EmailWorker] 任务同步完成: "
                f"新增 {stats['added']}, "
                f"删除 {stats['removed']}, "
                f"更新 {stats['updated']}, "
                f"总计 {stats['total']}"
            )

        except Exception as e:
            logger.error(f"[EmailWorker] 同步任务失败: {e}")
