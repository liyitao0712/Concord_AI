"""add email_raw tables

Revision ID: c2e8f7d91a3b
Revises: 80a92ad83752
Create Date: 2026-01-30 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2e8f7d91a3b'
down_revision: Union[str, None] = '80a92ad83752'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建邮件原始数据表
    op.create_table(
        'email_raw_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email_account_id', sa.Integer(), nullable=True),
        sa.Column('message_id', sa.String(length=500), nullable=False, comment='邮件 Message-ID 头，用于幂等'),
        sa.Column('sender', sa.String(length=255), nullable=False, comment='发件人邮箱'),
        sa.Column('sender_name', sa.String(length=255), nullable=True, comment='发件人显示名'),
        sa.Column('recipients', sa.Text(), nullable=False, comment='收件人列表 JSON'),
        sa.Column('subject', sa.String(length=1000), nullable=False, comment='邮件主题'),
        sa.Column('received_at', sa.DateTime(), nullable=False, comment='邮件接收时间'),
        sa.Column('oss_key', sa.String(length=500), nullable=False, comment='OSS 对象键'),
        sa.Column('size_bytes', sa.Integer(), nullable=False, comment='原始邮件大小（字节）'),
        sa.Column('is_processed', sa.Boolean(), nullable=False, default=False, comment='是否已处理'),
        sa.Column('event_id', sa.String(length=36), nullable=True, comment='关联的 UnifiedEvent ID'),
        sa.Column('processed_at', sa.DateTime(), nullable=True, comment='处理完成时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['email_account_id'], ['email_accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_email_raw_messages_message_id', 'email_raw_messages', ['message_id'], unique=True)
    op.create_index('ix_email_raw_messages_email_account_id', 'email_raw_messages', ['email_account_id'], unique=False)

    # 创建邮件附件表
    op.create_table(
        'email_attachments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email_id', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False, comment='原始文件名'),
        sa.Column('content_type', sa.String(length=100), nullable=False, comment='MIME 类型'),
        sa.Column('size_bytes', sa.Integer(), nullable=False, comment='文件大小（字节）'),
        sa.Column('oss_key', sa.String(length=500), nullable=False, comment='OSS 对象键'),
        sa.Column('is_inline', sa.Boolean(), nullable=False, default=False, comment='是否为 inline 附件'),
        sa.Column('content_id', sa.String(length=255), nullable=True, comment='Content-ID'),
        sa.Column('is_signature', sa.Boolean(), nullable=False, default=False, comment='是否为签名图片'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['email_id'], ['email_raw_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_email_attachments_email_id', 'email_attachments', ['email_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_email_attachments_email_id', table_name='email_attachments')
    op.drop_table('email_attachments')
    op.drop_index('ix_email_raw_messages_email_account_id', table_name='email_raw_messages')
    op.drop_index('ix_email_raw_messages_message_id', table_name='email_raw_messages')
    op.drop_table('email_raw_messages')
