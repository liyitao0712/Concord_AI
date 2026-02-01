# app/workers/manager.py
# Worker 管理器
#
# 统一管理所有 Worker 进程的生命周期：
# - 启动/停止/重启
# - 状态监控
# - 配置管理

import os
import sys
import subprocess
import asyncio
from typing import Optional, Dict, Type
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.database import async_session_maker
from app.workers.base import BaseWorker, WorkerStatus, WorkerInfo

logger = get_logger(__name__)


class WorkerManager:
    """
    Worker 管理器

    负责管理所有 Worker 进程的生命周期。

    使用方法：
        from app.workers.manager import worker_manager

        # 启动所有已启用的 worker
        await worker_manager.start_all_enabled()

        # 启动单个 worker
        await worker_manager.start("worker-uuid-123")

        # 停止 worker
        await worker_manager.stop("worker-uuid-123")

        # 获取状态
        status = worker_manager.get_status("worker-uuid-123")

        # 列出所有 worker
        workers = await worker_manager.list_all()
    """

    def __init__(self):
        # 进程映射: worker_id -> subprocess.Popen
        self._processes: Dict[str, subprocess.Popen] = {}

        # 日志文件句柄: worker_id -> file handle
        self._log_handles: Dict[str, any] = {}

        # Worker 类型注册表: worker_type -> Worker 类
        self._worker_types: Dict[str, Type[BaseWorker]] = {}

        # 启动信息: worker_id -> WorkerInfo
        self._worker_info: Dict[str, WorkerInfo] = {}

    def register_worker_type(self, worker_type: str, worker_class: Type[BaseWorker]) -> None:
        """
        注册 Worker 类型

        Args:
            worker_type: 类型标识（如 'feishu', 'email'）
            worker_class: Worker 类
        """
        self._worker_types[worker_type] = worker_class
        logger.debug(f"[WorkerManager] 注册 Worker 类型: {worker_type}")

    def get_worker_types(self) -> list[str]:
        """获取所有已注册的 Worker 类型"""
        return list(self._worker_types.keys())

    async def start(self, worker_id: str, db: Optional[AsyncSession] = None) -> tuple[bool, str]:
        """
        启动指定的 Worker

        Args:
            worker_id: Worker 配置 ID
            db: 数据库会话（可选，如果没有提供会创建新的）

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        # 检查是否已在运行
        if worker_id in self._processes:
            process = self._processes[worker_id]
            if process.poll() is None:  # 进程仍在运行
                return False, "Worker 已在运行中"

        # 从数据库获取配置
        from app.models.worker import WorkerConfig

        close_session = False
        if db is None:
            db = async_session_maker()
            close_session = True

        try:
            result = await db.execute(
                select(WorkerConfig).where(WorkerConfig.id == worker_id)
            )
            config = result.scalar_one_or_none()

            if not config:
                return False, f"Worker 配置不存在: {worker_id}"

            if not config.is_enabled:
                return False, "Worker 未启用"

            # 检查 worker 类型是否支持
            if config.worker_type not in self._worker_types:
                return False, f"不支持的 Worker 类型: {config.worker_type}"

            # 启动子进程
            success, message = await self._start_process(
                worker_id=worker_id,
                worker_type=config.worker_type,
                name=config.name,
                config_data=config.config,
                agent_id=config.agent_id,
            )

            return success, message

        except Exception as e:
            logger.error(f"[WorkerManager] 启动 Worker 失败: {e}")
            return False, str(e)

        finally:
            if close_session:
                await db.close()

    async def _start_process(
        self,
        worker_id: str,
        worker_type: str,
        name: str,
        config_data: dict,
        agent_id: str,
    ) -> tuple[bool, str]:
        """
        启动 Worker 子进程

        Args:
            worker_id: Worker ID
            worker_type: Worker 类型
            name: 显示名称
            config_data: 配置数据
            agent_id: 绑定的 Agent ID

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        try:
            # 准备启动参数
            python_path = sys.executable
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

            # 日志目录
            log_dir = os.path.join(os.path.dirname(project_root), "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"worker_{worker_type}_{worker_id[:8]}.log")

            # 构建命令行参数
            cmd = [
                python_path,
                "-m",
                f"app.workers.{worker_type}_worker",
                "--worker-id", worker_id,
                "--agent-id", agent_id,
            ]

            # 添加配置参数
            for key, value in config_data.items():
                if value:  # 只添加非空值
                    cmd.extend([f"--{key.replace('_', '-')}", str(value)])

            # 打开日志文件
            log_handle = open(log_file, "a")
            self._log_handles[worker_id] = log_handle

            # 启动子进程
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

            self._processes[worker_id] = process

            # 记录信息
            self._worker_info[worker_id] = WorkerInfo(
                worker_id=worker_id,
                worker_type=worker_type,
                name=name,
                status=WorkerStatus.RUNNING,
                pid=process.pid,
                started_at=datetime.now(),
            )

            logger.info(f"[WorkerManager] Worker 已启动: {name} (PID: {process.pid})")
            logger.info(f"[WorkerManager] 日志文件: {log_file}")

            return True, f"Worker 已启动 (PID: {process.pid})"

        except Exception as e:
            logger.error(f"[WorkerManager] 启动进程失败: {e}")
            return False, str(e)

    async def stop(self, worker_id: str) -> tuple[bool, str]:
        """
        停止指定的 Worker

        Args:
            worker_id: Worker 配置 ID

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        if worker_id not in self._processes:
            return False, "Worker 未在运行"

        process = self._processes[worker_id]

        try:
            if process.poll() is None:  # 进程仍在运行
                logger.info(f"[WorkerManager] 正在停止 Worker (PID: {process.pid})...")
                process.terminate()

                # 等待进程结束
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("[WorkerManager] 进程未响应，强制终止")
                    process.kill()
                    process.wait()

            # 清理
            del self._processes[worker_id]

            if worker_id in self._log_handles:
                try:
                    self._log_handles[worker_id].close()
                except Exception:
                    pass
                del self._log_handles[worker_id]

            if worker_id in self._worker_info:
                self._worker_info[worker_id].status = WorkerStatus.STOPPED
                self._worker_info[worker_id].pid = None

            logger.info(f"[WorkerManager] Worker 已停止: {worker_id}")
            return True, "Worker 已停止"

        except Exception as e:
            logger.error(f"[WorkerManager] 停止 Worker 失败: {e}")
            return False, str(e)

    async def restart(self, worker_id: str, db: Optional[AsyncSession] = None) -> tuple[bool, str]:
        """
        重启指定的 Worker

        Args:
            worker_id: Worker 配置 ID
            db: 数据库会话

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        # 先停止
        await self.stop(worker_id)

        # 等待一下
        await asyncio.sleep(1)

        # 再启动
        return await self.start(worker_id, db)

    async def start_all_enabled(self) -> dict[str, tuple[bool, str]]:
        """
        启动所有已启用的 Worker

        Returns:
            dict: {worker_id: (success, message)}
        """
        from app.models.worker import WorkerConfig

        results = {}

        async with async_session_maker() as db:
            result = await db.execute(
                select(WorkerConfig).where(WorkerConfig.is_enabled == True)
            )
            configs = result.scalars().all()

            for config in configs:
                success, message = await self.start(config.id, db)
                results[config.id] = (success, message)
                if success:
                    logger.info(f"[WorkerManager] 已启动: {config.name}")
                else:
                    logger.warning(f"[WorkerManager] 启动失败: {config.name} - {message}")

        return results

    async def stop_all(self) -> None:
        """停止所有 Worker"""
        worker_ids = list(self._processes.keys())

        for worker_id in worker_ids:
            await self.stop(worker_id)

        logger.info(f"[WorkerManager] 已停止所有 Worker ({len(worker_ids)} 个)")

    def get_status(self, worker_id: str) -> Optional[WorkerInfo]:
        """
        获取 Worker 状态

        Args:
            worker_id: Worker ID

        Returns:
            WorkerInfo 或 None
        """
        # 检查进程是否还在运行
        if worker_id in self._processes:
            process = self._processes[worker_id]
            if process.poll() is not None:  # 进程已退出
                # 更新状态
                if worker_id in self._worker_info:
                    self._worker_info[worker_id].status = WorkerStatus.STOPPED
                    self._worker_info[worker_id].pid = None
                # 清理
                del self._processes[worker_id]

        return self._worker_info.get(worker_id)

    def get_all_status(self) -> list[WorkerInfo]:
        """获取所有 Worker 状态"""
        # 先更新状态
        for worker_id in list(self._processes.keys()):
            self.get_status(worker_id)

        return list(self._worker_info.values())

    async def list_all(self, db: Optional[AsyncSession] = None) -> list[dict]:
        """
        列出所有 Worker 配置及状态

        Returns:
            list[dict]: Worker 配置和状态列表
        """
        from app.models.worker import WorkerConfig

        close_session = False
        if db is None:
            db = async_session_maker()
            close_session = True

        try:
            result = await db.execute(select(WorkerConfig))
            configs = result.scalars().all()

            workers = []
            for config in configs:
                status = self.get_status(config.id)
                workers.append({
                    "id": config.id,
                    "worker_type": config.worker_type,
                    "name": config.name,
                    "agent_id": config.agent_id,
                    "is_enabled": config.is_enabled,
                    "status": status.status.value if status else "stopped",
                    "pid": status.pid if status else None,
                    "started_at": status.started_at.isoformat() if status and status.started_at else None,
                    "created_at": config.created_at.isoformat(),
                    "updated_at": config.updated_at.isoformat(),
                })

            return workers

        finally:
            if close_session:
                await db.close()

    async def test_connection(self, worker_type: str, config: dict) -> tuple[bool, str]:
        """
        测试 Worker 连接

        Args:
            worker_type: Worker 类型
            config: 配置

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        if worker_type not in self._worker_types:
            return False, f"不支持的 Worker 类型: {worker_type}"

        worker_class = self._worker_types[worker_type]

        # 验证配置
        valid, error = worker_class.validate_config(config)
        if not valid:
            return False, error

        # 创建临时实例测试连接
        try:
            worker = worker_class()
            return await worker.test_connection(config)
        except Exception as e:
            return False, str(e)


# 全局单例
worker_manager = WorkerManager()
