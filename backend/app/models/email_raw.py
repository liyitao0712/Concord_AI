# app/models/email_raw.py
# 邮件原始数据模型
#
# 功能说明：
# 1. EmailRawMessage - 存储邮件原始 .eml 文件的元数据和 OSS 路径
# 2. EmailAttachment - 存储邮件附件的元数据和 OSS 路径
#
# 设计要点：
# - 原始邮件和附件都存储在 OSS，数据库只存元数据
# - message_id 作为幂等键，防止重复存储
# - is_signature 标识签名图片，便于过滤

import json
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class EmailRawMessage(Base):
    """
    邮件原始数据

    存储邮件的原始 .eml 文件到 OSS，数据库记录元数据。
    用于邮件追溯、重放处理、合规存档等场景。
    """
    __tablename__ = "email_raw_messages"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 关联邮箱账户（可选，环境变量配置的邮箱没有 account_id）
    email_account_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("email_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # IMAP Message-ID（幂等键，防止重复存储）
    message_id: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        index=True,
        comment="邮件 Message-ID 头，用于幂等",
    )

    # 邮件元数据（便于查询，无需解析 .eml）
    sender: Mapped[str] = mapped_column(
        String(255),
        comment="发件人邮箱",
    )
    sender_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="发件人显示名",
    )
    recipients: Mapped[str] = mapped_column(
        Text,
        comment="收件人列表 JSON",
    )
    subject: Mapped[str] = mapped_column(
        String(1000),
        comment="邮件主题",
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime,
        comment="邮件接收时间",
    )

    # 邮件正文（用于分析，不存完整 HTML）
    body_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="邮件纯文本正文（前 5000 字符，用于 AI 分析）",
    )

    # 存储信息
    oss_key: Mapped[str] = mapped_column(
        String(500),
        comment="存储路径: emails/raw/{account_id}/{date}/{uuid}.eml",
    )
    storage_type: Mapped[str] = mapped_column(
        String(20),
        default="oss",
        comment="存储类型: oss（阿里云OSS）或 local（本地文件）",
    )
    size_bytes: Mapped[int] = mapped_column(
        Integer,
        comment="原始邮件大小（字节）",
    )

    # 处理状态
    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否已处理",
    )
    event_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="关联的 UnifiedEvent ID",
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="处理完成时间",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    # 关系
    attachments: Mapped[List["EmailAttachment"]] = relationship(
        "EmailAttachment",
        back_populates="email",
        cascade="all, delete-orphan",
    )

    def set_recipients(self, recipients: list[str]) -> None:
        """设置收件人列表"""
        self.recipients = json.dumps(recipients)

    def get_recipients(self) -> list[str]:
        """获取收件人列表"""
        return json.loads(self.recipients) if self.recipients else []


class EmailAttachment(Base):
    """
    邮件附件

    存储邮件附件到 OSS，数据库记录元数据。
    支持识别签名图片（inline + Content-ID）。
    """
    __tablename__ = "email_attachments"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 关联邮件
    email_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("email_raw_messages.id", ondelete="CASCADE"),
        index=True,
    )

    # 文件信息
    filename: Mapped[str] = mapped_column(
        String(500),
        comment="原始文件名",
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        comment="MIME 类型",
    )
    size_bytes: Mapped[int] = mapped_column(
        Integer,
        comment="文件大小（字节）",
    )

    # 存储信息
    oss_key: Mapped[str] = mapped_column(
        String(500),
        comment="存储路径: emails/attachments/{account_id}/{date}/{att_id}/{filename}",
    )
    storage_type: Mapped[str] = mapped_column(
        String(20),
        default="oss",
        comment="存储类型: oss 或 local",
    )

    # 签名图片识别
    is_inline: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否为 inline 附件（Content-Disposition: inline）",
    )
    content_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Content-ID（用于 HTML 中 cid: 引用）",
    )
    is_signature: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否为签名图片（inline + Content-ID + image/*）",
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    # 关系
    email: Mapped["EmailRawMessage"] = relationship(
        "EmailRawMessage",
        back_populates="attachments",
    )
