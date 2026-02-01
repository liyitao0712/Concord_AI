"""add storage_type to email tables

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2026-02-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i8j9k0l1m2n3'
down_revision: Union[str, None] = 'h7i8j9k0l1m2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    添加 storage_type 字段到邮件表，支持 OSS 和本地存储

    修改内容：
    1. email_raw_messages 表添加 storage_type 字段
    2. email_attachments 表添加 storage_type 字段
    3. 更新 oss_key 字段注释（改为通用的"存储路径"）
    """
    # 添加 storage_type 字段到 email_raw_messages
    op.add_column(
        'email_raw_messages',
        sa.Column(
            'storage_type',
            sa.String(length=20),
            nullable=False,
            server_default='oss',
            comment='存储类型: oss（阿里云OSS）或 local（本地文件）'
        )
    )

    # 添加 storage_type 字段到 email_attachments
    op.add_column(
        'email_attachments',
        sa.Column(
            'storage_type',
            sa.String(length=20),
            nullable=False,
            server_default='oss',
            comment='存储类型: oss 或 local'
        )
    )


def downgrade() -> None:
    """回滚：删除 storage_type 字段"""
    op.drop_column('email_attachments', 'storage_type')
    op.drop_column('email_raw_messages', 'storage_type')
