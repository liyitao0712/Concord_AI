# app/workers/base.py
# Worker 基类
#
# 定义所有 Worker 的通用接口和行为

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class WorkerStatus(str, Enum):
    """Worker 状态"""
    STOPPED = "stopped"      # 已停止
    STARTING = "starting"    # 启动中
    RUNNING = "running"      # 运行中
    STOPPING = "stopping"    # 停止中
    ERROR = "error"          # 错误


@dataclass
class WorkerInfo:
    """Worker 运行信息"""
    worker_id: str                          # Worker 配置 ID
    worker_type: str                        # Worker 类型 (feishu / email)
    name: str                               # 显示名称
    status: WorkerStatus                    # 当前状态
    pid: Optional[int] = None               # 进程 PID
    started_at: Optional[datetime] = None   # 启动时间
    error_message: Optional[str] = None     # 错误信息
    extra: dict = field(default_factory=dict)  # 额外信息


class BaseWorker(ABC):
    """
    Worker 基类

    所有后台 Worker 都应继承此类并实现抽象方法。

    Worker 类型：
    - feishu: 飞书 WebSocket 长连接
    - email: 邮件 IMAP 定时拉取
    - dingtalk: 钉钉（未来）
    - wecom: 企业微信（未来）

    使用方法：
        class FeishuWorker(BaseWorker):
            worker_type = "feishu"
            name = "飞书 Worker"

            async def start(self, config: dict) -> None:
                # 启动逻辑
                ...
    """

    # 子类必须定义
    worker_type: str = ""           # Worker 类型标识
    name: str = ""                  # Worker 名称
    description: str = ""           # Worker 描述

    # 运行时状态
    _status: WorkerStatus = WorkerStatus.STOPPED
    _pid: Optional[int] = None
    _started_at: Optional[datetime] = None
    _error_message: Optional[str] = None

    @abstractmethod
    async def start(self, config: dict) -> bool:
        """
        启动 Worker

        Args:
            config: Worker 配置（如 app_id, app_secret 等）

        Returns:
            bool: 是否成功启动
        """
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """
        停止 Worker

        Returns:
            bool: 是否成功停止
        """
        pass

    @abstractmethod
    async def test_connection(self, config: dict) -> tuple[bool, str]:
        """
        测试连接

        Args:
            config: Worker 配置

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        pass

    def get_status(self) -> WorkerStatus:
        """获取当前状态"""
        return self._status

    def get_info(self, worker_id: str, name: str) -> WorkerInfo:
        """获取 Worker 信息"""
        return WorkerInfo(
            worker_id=worker_id,
            worker_type=self.worker_type,
            name=name,
            status=self._status,
            pid=self._pid,
            started_at=self._started_at,
            error_message=self._error_message,
        )

    def _set_running(self, pid: int) -> None:
        """设置为运行状态"""
        self._status = WorkerStatus.RUNNING
        self._pid = pid
        self._started_at = datetime.now()
        self._error_message = None

    def _set_stopped(self) -> None:
        """设置为停止状态"""
        self._status = WorkerStatus.STOPPED
        self._pid = None
        self._started_at = None

    def _set_error(self, message: str) -> None:
        """设置为错误状态"""
        self._status = WorkerStatus.ERROR
        self._error_message = message

    @classmethod
    def get_required_config_fields(cls) -> list[str]:
        """
        获取必需的配置字段

        子类可以重写此方法来定义必需的配置字段

        Returns:
            list[str]: 必需字段列表
        """
        return []

    @classmethod
    def get_optional_config_fields(cls) -> list[str]:
        """
        获取可选的配置字段

        Returns:
            list[str]: 可选字段列表
        """
        return []

    @classmethod
    def validate_config(cls, config: dict) -> tuple[bool, str]:
        """
        验证配置

        Args:
            config: 配置字典

        Returns:
            tuple[bool, str]: (是否有效, 错误消息)
        """
        required = cls.get_required_config_fields()
        missing = [f for f in required if not config.get(f)]

        if missing:
            return False, f"缺少必需配置: {', '.join(missing)}"

        return True, ""
