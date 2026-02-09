"""add project tables

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-02-08

新增表：
- projects: 项目表
- project_associations: 项目关联表（多态 junction）
- tasks: 任务/里程碑表
- progress_entries: 进度记录表
- project_suggestions: 项目建议表（AI 触发）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== projects ====================
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, comment='项目名称'),
        sa.Column('project_type', sa.String(50), nullable=False, server_default='general', comment='项目类型'),
        sa.Column('description', sa.Text(), nullable=True, comment='项目描述'),
        sa.Column('status', sa.String(20), server_default='draft', comment='状态'),
        sa.Column('priority', sa.String(10), server_default='medium', comment='优先级'),
        sa.Column('start_date', sa.Date(), nullable=True, comment='开始日期'),
        sa.Column('due_date', sa.Date(), nullable=True, comment='截止日期'),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='负责人 ID'),
        sa.Column('tags', sa.JSON(), server_default='[]', comment='标签列表'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='创建人 ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_projects_name', 'projects', ['name'])
    op.create_index('ix_projects_project_type', 'projects', ['project_type'])
    op.create_index('ix_projects_status', 'projects', ['status'])
    op.create_index('ix_projects_priority', 'projects', ['priority'])
    op.create_index('ix_projects_owner_id', 'projects', ['owner_id'])
    op.create_index('ix_projects_created_at', 'projects', ['created_at'])

    # ==================== project_associations ====================
    op.create_table(
        'project_associations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, comment='项目 ID'),
        sa.Column('entity_type', sa.String(30), nullable=False, comment='实体类型'),
        sa.Column('entity_id', sa.String(36), nullable=False, comment='实体 ID'),
        sa.Column('notes', sa.String(500), nullable=True, comment='关联备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_project_associations_project_id', 'project_associations', ['project_id'])
    op.create_index('ix_project_associations_entity_type', 'project_associations', ['entity_type'])
    op.create_index('ix_project_associations_entity_id', 'project_associations', ['entity_id'])
    op.create_index('uq_project_entity', 'project_associations', ['project_id', 'entity_type', 'entity_id'], unique=True)

    # ==================== tasks ====================
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, comment='所属项目 ID'),
        sa.Column('parent_task_id', sa.String(36), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=True, comment='父任务 ID'),
        sa.Column('title', sa.String(300), nullable=False, comment='任务标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='任务描述'),
        sa.Column('task_type', sa.String(20), server_default='action', comment='任务类型'),
        sa.Column('phase_name', sa.String(100), nullable=True, comment='阶段名称'),
        sa.Column('status', sa.String(20), server_default='pending', comment='状态'),
        sa.Column('priority', sa.String(10), server_default='medium', comment='优先级'),
        sa.Column('assignee_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='负责人 ID'),
        sa.Column('sort_order', sa.Integer(), server_default='0', comment='排序序号'),
        sa.Column('completion_percentage', sa.Integer(), server_default='0', comment='完成百分比 0-100'),
        sa.Column('due_date', sa.Date(), nullable=True, comment='截止日期'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='创建人 ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_tasks_project_id', 'tasks', ['project_id'])
    op.create_index('ix_tasks_parent_task_id', 'tasks', ['parent_task_id'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_task_type', 'tasks', ['task_type'])
    op.create_index('ix_tasks_assignee_id', 'tasks', ['assignee_id'])
    op.create_index('ix_tasks_sort_order', 'tasks', ['sort_order'])

    # ==================== progress_entries ====================
    op.create_table(
        'progress_entries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, comment='所属任务 ID'),
        sa.Column('progress_type', sa.String(20), server_default='status_update', comment='记录类型'),
        sa.Column('content', sa.Text(), nullable=True, comment='记录内容'),
        sa.Column('old_status', sa.String(20), nullable=True, comment='变更前状态'),
        sa.Column('new_status', sa.String(20), nullable=True, comment='变更后状态'),
        sa.Column('percentage', sa.Integer(), nullable=True, comment='完成百分比'),
        sa.Column('email_id', sa.String(36), sa.ForeignKey('email_raw_messages.id', ondelete='SET NULL'), nullable=True, comment='关联邮件 ID'),
        sa.Column('attachments', sa.JSON(), server_default='[]', comment='附件列表'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='创建人 ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_progress_entries_task_id', 'progress_entries', ['task_id'])
    op.create_index('ix_progress_entries_progress_type', 'progress_entries', ['progress_type'])
    op.create_index('ix_progress_entries_email_id', 'progress_entries', ['email_id'])
    op.create_index('ix_progress_entries_created_at', 'progress_entries', ['created_at'])

    # ==================== project_suggestions ====================
    op.create_table(
        'project_suggestions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('suggested_name', sa.String(200), nullable=False, comment='建议的项目名称'),
        sa.Column('suggested_type', sa.String(50), server_default='general', comment='建议的项目类型'),
        sa.Column('suggested_description', sa.Text(), nullable=True, comment='建议的项目描述'),
        sa.Column('suggested_priority', sa.String(10), server_default='medium', comment='建议的优先级'),
        sa.Column('suggested_associations', sa.JSON(), server_default='[]', comment='建议的关联实体'),
        sa.Column('confidence', sa.Float(), server_default='0.0', comment='AI 置信度'),
        sa.Column('reasoning', sa.Text(), nullable=True, comment='AI 推理说明'),
        sa.Column('trigger_email_id', sa.String(36), nullable=True, comment='触发的邮件 ID'),
        sa.Column('trigger_content', sa.Text(), nullable=False, server_default='', comment='触发内容摘要'),
        sa.Column('trigger_source', sa.String(20), server_default='email', comment='来源'),
        sa.Column('status', sa.String(20), server_default='pending', comment='审批状态'),
        sa.Column('reviewed_by', sa.String(36), nullable=True, comment='审批人 ID'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True, comment='审批时间'),
        sa.Column('review_note', sa.Text(), nullable=True, comment='审批备注'),
        sa.Column('created_project_id', sa.String(36), nullable=True, comment='创建的项目 ID'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_project_suggestions_status', 'project_suggestions', ['status'])
    op.create_index('ix_project_suggestions_trigger_email_id', 'project_suggestions', ['trigger_email_id'])
    op.create_index('ix_project_suggestions_created_at', 'project_suggestions', ['created_at'])


def downgrade() -> None:
    op.drop_table('project_suggestions')
    op.drop_table('progress_entries')
    op.drop_table('tasks')
    op.drop_table('project_associations')
    op.drop_table('projects')
