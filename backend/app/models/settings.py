# app/models/settings.py
# 系统设置模型
#
# 存储系统级配置，如 LLM 设置、邮件设置等
# 使用 key-value 形式存储，便于扩展

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemSetting(Base):
    """
    系统设置表

    用于存储可动态修改的系统配置
    """
    __tablename__ = "system_settings"

    # 设置键（唯一）
    key: Mapped[str] = mapped_column(String(100), primary_key=True)

    # 设置值（JSON 格式存储复杂数据）
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # 设置分类（如 llm, email, notification 等）
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 是否敏感数据（如 API Key，前端只显示部分）
    is_sensitive: Mapped[bool] = mapped_column(default=False)

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
        return f"<SystemSetting {self.key}={self.value[:20]}...>"
