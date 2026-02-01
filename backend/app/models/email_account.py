# app/models/email_account.py
# 邮箱账户模型
#
# 支持多邮箱配置，不同业务使用不同邮箱
# 如：询价用 sales@，投诉用 support@，通知用 notify@

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmailPurpose:
    """邮箱用途枚举"""
    SALES = "sales"               # 销售/询价
    SUPPORT = "support"           # 客服/投诉
    NOTIFICATION = "notification" # 系统通知
    GENERAL = "general"           # 通用


class EmailAccount(Base):
    """
    邮箱账户表

    存储多个邮箱配置，支持：
    - 不同业务用途使用不同邮箱
    - SMTP 发件和 IMAP 收件独立配置
    - 设置默认邮箱
    - 启用/禁用状态

    使用方法：
        # 根据用途获取邮箱
        account = await get_account_by_purpose("sales")

        # 获取默认邮箱
        account = await get_default_account()

        # 发送邮件时指定账户
        await smtp_send(..., account_id=account.id)
    """
    __tablename__ = "email_accounts"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="账户名称")
    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="用途: sales/support/notification/general"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")

    # SMTP 发件配置
    smtp_host: Mapped[str] = mapped_column(String(200), nullable=False, comment="SMTP 服务器地址")
    smtp_port: Mapped[int] = mapped_column(Integer, default=465, comment="SMTP 端口")
    smtp_user: Mapped[str] = mapped_column(String(200), nullable=False, comment="SMTP 用户名/邮箱")
    smtp_password: Mapped[str] = mapped_column(String(500), nullable=False, comment="SMTP 密码（加密存储）")
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否使用 TLS")

    # IMAP 收件配置（可选，有些邮箱只用于发件）
    imap_host: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="IMAP 服务器地址")
    imap_port: Mapped[int] = mapped_column(Integer, default=993, comment="IMAP 端口")
    imap_user: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="IMAP 用户名/邮箱")
    imap_password: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="IMAP 密码（加密存储）")
    imap_use_ssl: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否使用 SSL")
    imap_folder: Mapped[str] = mapped_column(String(100), default="INBOX", comment="监控的邮件文件夹")
    imap_mark_as_read: Mapped[bool] = mapped_column(Boolean, default=False, comment="拉取后是否标记已读")

    # 状态
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为默认邮箱")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    def __repr__(self):
        return f"<EmailAccount {self.name} ({self.purpose})>"

    @property
    def smtp_configured(self) -> bool:
        """SMTP 是否已配置"""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def imap_configured(self) -> bool:
        """IMAP 是否已配置"""
        return bool(self.imap_host and self.imap_user and self.imap_password)

    @property
    def email_address(self) -> str:
        """获取邮箱地址（通常是 SMTP 用户名）"""
        return self.smtp_user
