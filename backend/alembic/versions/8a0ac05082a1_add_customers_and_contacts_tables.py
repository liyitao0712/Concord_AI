"""add customers and contacts tables

Revision ID: 8a0ac05082a1
Revises: j9k0l1m2n3o4
Create Date: 2026-02-07 16:56:50.642374

创建客户管理表：
- customers: 客户（公司）信息
- contacts: 联系人信息
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8a0ac05082a1'
down_revision: Union[str, None] = 'j9k0l1m2n3o4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 customers 表
    op.create_table('customers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False, comment="公司全称，如 'Hyde Tools, Inc.'"),
        sa.Column('short_name', sa.String(length=100), nullable=True, comment="简称/别名，如 'Hyde'"),
        sa.Column('country', sa.String(length=100), nullable=True, comment="国家，如 'United States'"),
        sa.Column('region', sa.String(length=100), nullable=True, comment="地区/洲，如 'North America'"),
        sa.Column('industry', sa.String(length=100), nullable=True, comment="行业，如 'Tools & Hardware'"),
        sa.Column('company_size', sa.String(length=50), nullable=True, comment='公司规模: small/medium/large/enterprise'),
        sa.Column('annual_revenue', sa.String(length=50), nullable=True, comment="年营收范围，如 '<1M', '1M-10M', '10M-50M', '>50M'"),
        sa.Column('customer_level', sa.String(length=20), nullable=False, comment='客户等级: potential/normal/important/vip'),
        sa.Column('email', sa.String(length=200), nullable=True, comment='公司主邮箱'),
        sa.Column('phone', sa.String(length=50), nullable=True, comment='公司电话'),
        sa.Column('website', sa.String(length=300), nullable=True, comment='公司网站'),
        sa.Column('address', sa.Text(), nullable=True, comment='公司地址'),
        sa.Column('payment_terms', sa.String(length=100), nullable=True, comment="付款条款，如 'T/T 30 days', 'L/C at sight'"),
        sa.Column('shipping_terms', sa.String(length=50), nullable=True, comment="贸易术语（Incoterms），如 'FOB', 'CIF', 'EXW'"),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='是否活跃客户'),
        sa.Column('source', sa.String(length=50), nullable=True, comment='客户来源: email/exhibition/referral/website/other'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('tags', sa.JSON(), nullable=False, comment="标签列表，如 ['putty_knife', 'taping_knife']"),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_customers_country', 'customers', ['country'], unique=False)
    op.create_index('ix_customers_customer_level', 'customers', ['customer_level'], unique=False)
    op.create_index('ix_customers_is_active', 'customers', ['is_active'], unique=False)
    op.create_index('ix_customers_name', 'customers', ['name'], unique=False)

    # 创建 contacts 表
    op.create_table('contacts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=False, comment='所属客户 ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='联系人姓名'),
        sa.Column('title', sa.String(length=100), nullable=True, comment="职位/头衔，如 'Purchasing Manager'"),
        sa.Column('department', sa.String(length=100), nullable=True, comment='部门'),
        sa.Column('email', sa.String(length=200), nullable=True, comment='邮箱'),
        sa.Column('phone', sa.String(length=50), nullable=True, comment='座机'),
        sa.Column('mobile', sa.String(length=50), nullable=True, comment='手机'),
        sa.Column('social_media', sa.JSON(), nullable=False, comment="社交媒体，如 {'linkedin': 'url', 'whatsapp': 'number'}"),
        sa.Column('is_primary', sa.Boolean(), nullable=False, comment='是否主联系人'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='是否活跃'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contacts_customer_id', 'contacts', ['customer_id'], unique=False)
    op.create_index('ix_contacts_email', 'contacts', ['email'], unique=False)
    op.create_index('ix_contacts_is_active', 'contacts', ['is_active'], unique=False)
    op.create_index('ix_contacts_is_primary', 'contacts', ['is_primary'], unique=False)


def downgrade() -> None:
    # 删除 contacts 表
    op.drop_index('ix_contacts_is_primary', table_name='contacts')
    op.drop_index('ix_contacts_is_active', table_name='contacts')
    op.drop_index('ix_contacts_email', table_name='contacts')
    op.drop_index('ix_contacts_customer_id', table_name='contacts')
    op.drop_table('contacts')

    # 删除 customers 表
    op.drop_index('ix_customers_name', table_name='customers')
    op.drop_index('ix_customers_is_active', table_name='customers')
    op.drop_index('ix_customers_customer_level', table_name='customers')
    op.drop_index('ix_customers_country', table_name='customers')
    op.drop_table('customers')
