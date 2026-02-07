"""add customer_suggestions table

Revision ID: c2d3e4f5g6h7
Revises: b1c2d3e4f5a6
Create Date: 2026-02-07

创建客户建议表：
- customer_suggestions: AI 提取的客户/联系人建议，待审批
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5g6h7'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('customer_suggestions',
        # 主键
        sa.Column('id', sa.String(36), nullable=False),

        # 建议类型
        sa.Column('suggestion_type', sa.String(20), nullable=False, server_default='new_customer',
                   comment='建议类型: new_customer | new_contact'),

        # AI 提取的客户信息
        sa.Column('suggested_company_name', sa.String(200), nullable=False, comment='建议的公司名称'),
        sa.Column('suggested_short_name', sa.String(100), nullable=True, comment='建议的简称'),
        sa.Column('suggested_country', sa.String(100), nullable=True, comment='建议的国家'),
        sa.Column('suggested_region', sa.String(100), nullable=True, comment='建议的地区/洲'),
        sa.Column('suggested_industry', sa.String(100), nullable=True, comment='建议的行业'),
        sa.Column('suggested_website', sa.String(300), nullable=True, comment='建议的公司网站'),
        sa.Column('suggested_email_domain', sa.String(200), nullable=True, comment='邮箱域名'),
        sa.Column('suggested_customer_level', sa.String(20), nullable=False, server_default='potential',
                   comment='建议的客户等级'),
        sa.Column('suggested_tags', sa.JSON(), nullable=True, comment='建议的标签列表'),

        # AI 提取的联系人信息
        sa.Column('suggested_contact_name', sa.String(100), nullable=True, comment='建议的联系人姓名'),
        sa.Column('suggested_contact_email', sa.String(200), nullable=True, comment='建议的联系人邮箱'),
        sa.Column('suggested_contact_title', sa.String(100), nullable=True, comment='建议的联系人职位'),
        sa.Column('suggested_contact_phone', sa.String(50), nullable=True, comment='建议的联系人电话'),
        sa.Column('suggested_contact_department', sa.String(100), nullable=True, comment='建议的联系人部门'),

        # AI 分析信息
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0', comment='AI 置信度 0-1'),
        sa.Column('reasoning', sa.Text(), nullable=True, comment='AI 推理说明'),
        sa.Column('sender_type', sa.String(20), nullable=True, comment='发件人类型'),

        # 触发来源
        sa.Column('trigger_email_id', sa.String(36), nullable=True, comment='触发的邮件 ID'),
        sa.Column('trigger_content', sa.Text(), nullable=False, server_default='', comment='触发内容摘要'),
        sa.Column('trigger_source', sa.String(20), nullable=False, server_default='email', comment='来源'),

        # 查重关联
        sa.Column('email_domain', sa.String(200), nullable=True, comment='邮箱域名用于查重'),
        sa.Column('matched_customer_id', sa.String(36), nullable=True, comment='匹配到的已有客户 ID'),

        # 审批状态
        sa.Column('status', sa.String(20), nullable=False, server_default='pending',
                   comment='状态: pending | approved | rejected'),
        sa.Column('workflow_id', sa.String(100), nullable=True, comment='Temporal Workflow ID'),
        sa.Column('reviewed_by', sa.String(36), nullable=True, comment='审批人 ID'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True, comment='审批时间'),
        sa.Column('review_note', sa.Text(), nullable=True, comment='审批备注'),

        # 结果追踪
        sa.Column('created_customer_id', sa.String(36), nullable=True, comment='创建的客户 ID'),
        sa.Column('created_contact_id', sa.String(36), nullable=True, comment='创建的联系人 ID'),

        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),

        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_customer_suggestions_status', 'customer_suggestions', ['status'])
    op.create_index('ix_customer_suggestions_email_domain', 'customer_suggestions', ['email_domain'])
    op.create_index('ix_customer_suggestions_trigger_email_id', 'customer_suggestions', ['trigger_email_id'])
    op.create_index('ix_customer_suggestions_created_at', 'customer_suggestions', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_customer_suggestions_created_at', 'customer_suggestions')
    op.drop_index('ix_customer_suggestions_trigger_email_id', 'customer_suggestions')
    op.drop_index('ix_customer_suggestions_email_domain', 'customer_suggestions')
    op.drop_index('ix_customer_suggestions_status', 'customer_suggestions')
    op.drop_table('customer_suggestions')
