"""add_events_table

Revision ID: a1b2c3d4e5f6
Revises: 79b66ba4fa2c
Create Date: 2026-01-30 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '79b66ba4fa2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 events 表
    op.create_table('events',
    sa.Column('id', sa.String(length=36), nullable=False, comment='事件唯一标识'),
    sa.Column('idempotency_key', sa.String(length=255), nullable=False, comment='幂等键，防止重复处理'),
    sa.Column('event_type', sa.String(length=50), nullable=False, comment='事件类型：email/chat/webhook/command/approval/schedule'),
    sa.Column('source', sa.String(length=50), nullable=False, comment='来源渠道：web/chatbox/feishu/email/webhook/schedule'),
    sa.Column('source_id', sa.String(length=255), nullable=True, comment='原始消息ID'),
    sa.Column('content', sa.Text(), nullable=False, comment='事件内容'),
    sa.Column('content_type', sa.String(length=20), nullable=False, comment='内容类型：text/html/markdown'),
    sa.Column('user_id', sa.String(length=36), nullable=True, comment='系统用户ID'),
    sa.Column('user_external_id', sa.String(length=255), nullable=True, comment='外部用户ID（邮箱/open_id等）'),
    sa.Column('session_id', sa.String(length=36), nullable=True, comment='会话ID'),
    sa.Column('thread_id', sa.String(length=255), nullable=True, comment='线程ID（邮件回复链）'),
    sa.Column('status', sa.String(length=20), nullable=False, comment='处理状态：pending/processing/completed/failed/skipped'),
    sa.Column('intent', sa.String(length=50), nullable=True, comment='分类后的意图'),
    sa.Column('workflow_id', sa.String(length=255), nullable=True, comment='关联的Workflow ID'),
    sa.Column('response_content', sa.Text(), nullable=True, comment='响应内容'),
    sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
    sa.Column('event_metadata', sa.JSON(), nullable=True, comment='额外元数据'),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
    sa.Column('processed_at', sa.DateTime(), nullable=True, comment='开始处理时间'),
    sa.Column('completed_at', sa.DateTime(), nullable=True, comment='完成时间'),
    sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index(op.f('ix_events_idempotency_key'), 'events', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_events_event_type'), 'events', ['event_type'], unique=False)
    op.create_index(op.f('ix_events_source'), 'events', ['source'], unique=False)
    op.create_index(op.f('ix_events_user_id'), 'events', ['user_id'], unique=False)
    op.create_index(op.f('ix_events_session_id'), 'events', ['session_id'], unique=False)
    op.create_index(op.f('ix_events_status'), 'events', ['status'], unique=False)
    op.create_index(op.f('ix_events_intent'), 'events', ['intent'], unique=False)
    op.create_index(op.f('ix_events_workflow_id'), 'events', ['workflow_id'], unique=False)

    # 创建复合索引
    op.create_index('ix_events_status_created', 'events', ['status', 'created_at'], unique=False)
    op.create_index('ix_events_source_created', 'events', ['source', 'created_at'], unique=False)
    op.create_index('ix_events_user_external_id', 'events', ['user_external_id'], unique=False)


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_events_user_external_id', table_name='events')
    op.drop_index('ix_events_source_created', table_name='events')
    op.drop_index('ix_events_status_created', table_name='events')
    op.drop_index(op.f('ix_events_workflow_id'), table_name='events')
    op.drop_index(op.f('ix_events_intent'), table_name='events')
    op.drop_index(op.f('ix_events_status'), table_name='events')
    op.drop_index(op.f('ix_events_session_id'), table_name='events')
    op.drop_index(op.f('ix_events_user_id'), table_name='events')
    op.drop_index(op.f('ix_events_source'), table_name='events')
    op.drop_index(op.f('ix_events_event_type'), table_name='events')
    op.drop_index(op.f('ix_events_idempotency_key'), table_name='events')

    # 删除表
    op.drop_table('events')
