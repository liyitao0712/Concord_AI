"""add suppliers and supplier_contacts tables

Revision ID: b1c2d3e4f5a6
Revises: 8a0ac05082a1
Create Date: 2026-02-07

创建供应商管理表：
- suppliers: 供应商（公司）信息
- supplier_contacts: 供应商联系人信息
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = '8a0ac05082a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 suppliers 表
    op.create_table('suppliers',
        sa.Column('id', sa.String(36), nullable=False, comment='供应商 ID'),
        sa.Column('name', sa.String(200), nullable=False, comment='公司全称'),
        sa.Column('short_name', sa.String(100), nullable=True, comment='简称/别名'),
        sa.Column('country', sa.String(100), nullable=True, comment='国家'),
        sa.Column('region', sa.String(100), nullable=True, comment='地区/洲'),
        sa.Column('industry', sa.String(100), nullable=True, comment='行业'),
        sa.Column('company_size', sa.String(50), nullable=True, comment='公司规模'),
        sa.Column('main_products', sa.Text(), nullable=True, comment='主营产品描述'),
        sa.Column('supplier_level', sa.String(20), nullable=False, server_default='normal', comment='供应商等级'),
        sa.Column('email', sa.String(200), nullable=True, comment='公司主邮箱'),
        sa.Column('phone', sa.String(50), nullable=True, comment='公司电话'),
        sa.Column('website', sa.String(300), nullable=True, comment='公司网站'),
        sa.Column('address', sa.Text(), nullable=True, comment='公司地址'),
        sa.Column('payment_terms', sa.String(100), nullable=True, comment='付款条款'),
        sa.Column('shipping_terms', sa.String(50), nullable=True, comment='贸易术语'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='是否活跃'),
        sa.Column('source', sa.String(50), nullable=True, comment='供应商来源'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='标签列表'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_suppliers_name', 'suppliers', ['name'])
    op.create_index('ix_suppliers_country', 'suppliers', ['country'])
    op.create_index('ix_suppliers_supplier_level', 'suppliers', ['supplier_level'])
    op.create_index('ix_suppliers_is_active', 'suppliers', ['is_active'])

    # 创建 supplier_contacts 表
    op.create_table('supplier_contacts',
        sa.Column('id', sa.String(36), nullable=False, comment='联系人 ID'),
        sa.Column('supplier_id', sa.String(36), nullable=False, comment='所属供应商 ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='联系人姓名'),
        sa.Column('title', sa.String(100), nullable=True, comment='职位/头衔'),
        sa.Column('department', sa.String(100), nullable=True, comment='部门'),
        sa.Column('email', sa.String(200), nullable=True, comment='邮箱'),
        sa.Column('phone', sa.String(50), nullable=True, comment='座机'),
        sa.Column('mobile', sa.String(50), nullable=True, comment='手机'),
        sa.Column('social_media', sa.JSON(), nullable=True, comment='社交媒体'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='是否主联系人'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='是否活跃'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_supplier_contacts_supplier_id', 'supplier_contacts', ['supplier_id'])
    op.create_index('ix_supplier_contacts_email', 'supplier_contacts', ['email'])
    op.create_index('ix_supplier_contacts_is_primary', 'supplier_contacts', ['is_primary'])
    op.create_index('ix_supplier_contacts_is_active', 'supplier_contacts', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_supplier_contacts_is_active', 'supplier_contacts')
    op.drop_index('ix_supplier_contacts_is_primary', 'supplier_contacts')
    op.drop_index('ix_supplier_contacts_email', 'supplier_contacts')
    op.drop_index('ix_supplier_contacts_supplier_id', 'supplier_contacts')
    op.drop_table('supplier_contacts')

    op.drop_index('ix_suppliers_is_active', 'suppliers')
    op.drop_index('ix_suppliers_supplier_level', 'suppliers')
    op.drop_index('ix_suppliers_country', 'suppliers')
    op.drop_index('ix_suppliers_name', 'suppliers')
    op.drop_table('suppliers')
