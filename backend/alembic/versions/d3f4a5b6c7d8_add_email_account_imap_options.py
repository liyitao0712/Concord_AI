"""add email account imap options

Revision ID: d3f4a5b6c7d8
Revises: c2e8f7d91a3b
Create Date: 2025-01-30

为 email_accounts 表添加 IMAP 配置选项：
- imap_folder: 监控的邮件文件夹（默认 INBOX）
- imap_mark_as_read: 拉取后是否标记已读（默认 False）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'd3f4a5b6c7d8'
down_revision = 'c2e8f7d91a3b'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查字段是否已存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # 添加 imap_folder 字段（如果不存在）
    if not column_exists('email_accounts', 'imap_folder'):
        op.add_column(
            'email_accounts',
            sa.Column(
                'imap_folder',
                sa.String(100),
                nullable=False,
                server_default='INBOX',
                comment='监控的邮件文件夹'
            )
        )

    # 添加 imap_mark_as_read 字段（如果不存在）
    if not column_exists('email_accounts', 'imap_mark_as_read'):
        op.add_column(
            'email_accounts',
            sa.Column(
                'imap_mark_as_read',
                sa.Boolean(),
                nullable=False,
                server_default='false',
                comment='拉取后是否标记已读'
            )
        )


def downgrade() -> None:
    if column_exists('email_accounts', 'imap_mark_as_read'):
        op.drop_column('email_accounts', 'imap_mark_as_read')
    if column_exists('email_accounts', 'imap_folder'):
        op.drop_column('email_accounts', 'imap_folder')
