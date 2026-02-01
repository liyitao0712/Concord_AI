"""add email_analyses table

Revision ID: g6h7i8j9k0l1
Revises: f5g6h7i8j9k0
Create Date: 2026-01-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g6h7i8j9k0l1'
down_revision: Union[str, None] = 'f5g6h7i8j9k0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建邮件分析结果表
    op.create_table(
        'email_analyses',
        # 基础关联
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email_id', sa.String(length=36), nullable=False, comment='关联的邮件 ID'),

        # 摘要与翻译
        sa.Column('summary', sa.Text(), nullable=False, comment='一句话摘要'),
        sa.Column('key_points', sa.JSON(), nullable=True, comment='关键要点列表'),
        sa.Column('original_language', sa.String(length=10), nullable=True, comment='原文语言'),

        # 发件方信息
        sa.Column('sender_type', sa.String(length=20), nullable=True, comment='发件方类型'),
        sa.Column('sender_company', sa.String(length=255), nullable=True, comment='公司名称'),
        sa.Column('sender_country', sa.String(length=50), nullable=True, comment='国家/地区'),
        sa.Column('is_new_contact', sa.Boolean(), nullable=True, comment='是否新联系人'),

        # 意图分类
        sa.Column('intent', sa.String(length=50), nullable=True, comment='主意图'),
        sa.Column('intent_confidence', sa.Float(), nullable=True, comment='意图置信度'),
        sa.Column('urgency', sa.String(length=20), nullable=True, comment='紧急程度'),
        sa.Column('sentiment', sa.String(length=20), nullable=True, comment='情感倾向'),

        # 业务信息
        sa.Column('products', sa.JSON(), nullable=True, comment='产品列表'),
        sa.Column('amounts', sa.JSON(), nullable=True, comment='金额列表'),
        sa.Column('trade_terms', sa.JSON(), nullable=True, comment='贸易条款'),
        sa.Column('deadline', sa.DateTime(), nullable=True, comment='截止/交期'),

        # 跟进建议
        sa.Column('questions', sa.JSON(), nullable=True, comment='对方问题列表'),
        sa.Column('action_required', sa.JSON(), nullable=True, comment='需要我方做的事'),
        sa.Column('suggested_reply', sa.Text(), nullable=True, comment='建议回复要点'),
        sa.Column('priority', sa.String(length=10), nullable=True, comment='处理优先级'),

        # 分析元数据
        sa.Column('cleaned_content', sa.Text(), nullable=True, comment='清洗后的正文'),
        sa.Column('llm_model', sa.String(length=100), nullable=True, comment='使用的模型'),
        sa.Column('token_used', sa.Integer(), nullable=True, comment='消耗 token'),

        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        # 约束
        sa.ForeignKeyConstraint(['email_id'], ['email_raw_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 创建索引
    op.create_index('ix_email_analyses_email_id', 'email_analyses', ['email_id'], unique=False)
    op.create_index('ix_email_analyses_intent', 'email_analyses', ['intent'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_email_analyses_intent', table_name='email_analyses')
    op.drop_index('ix_email_analyses_email_id', table_name='email_analyses')
    op.drop_table('email_analyses')
