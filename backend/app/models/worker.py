# app/models/worker.py
# Worker 配置模型
#
# 存储各种渠道 Worker 的配置信息

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


class WorkerConfig(Base):
    """
    Worker 配置表

    存储各种渠道 Worker 的配置信息，如飞书、邮件等。

    支持的 worker_type:
    - feishu: 飞书机器人
    - email: 邮件监听
    - dingtalk: 钉钉（未来）
    - wecom: 企业微信（未来）

    示例数据：
    {
        "id": "uuid-1",
        "worker_type": "feishu",
        "name": "客服机器人",
        "config": {
            "app_id": "cli_xxx",
            "app_secret": "xxx",
            "encrypt_key": "",
            "verification_token": ""
        },
        "agent_id": "chat_agent",
        "is_enabled": true
    }
    """
    __tablename__ = "worker_configs"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    # Worker 类型
    worker_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Worker 类型: feishu / email / dingtalk / wecom",
    )

    # 显示名称
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="显示名称，如'客服机器人'",
    )

    # 配置数据（JSON 格式）
    # 飞书: {"app_id": "xxx", "app_secret": "xxx", "encrypt_key": "", "verification_token": ""}
    # 邮件: {"imap_host": "xxx", "imap_port": 993, "username": "xxx", "password": "xxx"}
    config: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="配置数据（JSON）",
    )

    # 绑定的 Agent ID
    agent_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="chat_agent",
        comment="绑定的 Agent ID",
    )

    # 是否启用
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否启用",
    )

    # 描述
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="描述信息",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<WorkerConfig {self.worker_type}:{self.name}>"

    def mask_sensitive_config(self) -> dict:
        """
        返回脱敏后的配置

        敏感字段（如 app_secret, password）只显示前后几个字符
        """
        sensitive_fields = ["app_secret", "password", "encrypt_key", "verification_token"]
        masked = {}

        for key, value in self.config.items():
            if key in sensitive_fields and value:
                if len(value) > 8:
                    masked[key] = f"{value[:4]}***{value[-4:]}"
                else:
                    masked[key] = "***"
            else:
                masked[key] = value

        return masked

    def to_dict(self, mask_sensitive: bool = True) -> dict:
        """
        转换为字典

        Args:
            mask_sensitive: 是否脱敏敏感字段

        Returns:
            dict: 配置字典
        """
        return {
            "id": self.id,
            "worker_type": self.worker_type,
            "name": self.name,
            "config": self.mask_sensitive_config() if mask_sensitive else self.config,
            "agent_id": self.agent_id,
            "is_enabled": self.is_enabled,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
