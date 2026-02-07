"""add categories, products, product_suppliers tables

Revision ID: c2d3e4f5a6b7
Revises: c2d3e4f5g6h7
Create Date: 2026-02-07

创建产品管理相关表：
- categories: 品类表（支持多级树形结构）
- products: 产品表（外贸产品完整信息）
- product_suppliers: 产品-供应商关联表（多对多）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'c2d3e4f5g6h7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 categories 表
    op.create_table('categories',
        sa.Column('id', sa.String(36), nullable=False, comment='品类 ID'),
        sa.Column('code', sa.String(50), nullable=False, unique=True, comment='品类编码，如 01、01-01'),
        sa.Column('name', sa.String(200), nullable=False, comment='品类中文名'),
        sa.Column('name_en', sa.String(200), nullable=True, comment='品类英文名'),
        sa.Column('parent_id', sa.String(36), nullable=True, comment='父品类 ID，根品类为 NULL'),
        sa.Column('description', sa.Text(), nullable=True, comment='品类描述'),
        sa.Column('vat_rate', sa.Numeric(5, 2), nullable=True, comment='增值税率（%）'),
        sa.Column('tax_rebate_rate', sa.Numeric(5, 2), nullable=True, comment='退税率（%）'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_categories_code', 'categories', ['code'])
    op.create_index('ix_categories_parent_id', 'categories', ['parent_id'])

    # 创建 products 表
    op.create_table('products',
        sa.Column('id', sa.String(36), nullable=False, comment='产品 ID'),
        sa.Column('category_id', sa.String(36), nullable=True, comment='所属品类 ID'),
        sa.Column('name', sa.String(200), nullable=False, comment='品名'),
        sa.Column('model_number', sa.String(100), nullable=True, comment='型号'),
        sa.Column('specifications', sa.Text(), nullable=True, comment='规格'),
        sa.Column('unit', sa.String(50), nullable=True, comment='单位'),
        sa.Column('moq', sa.Integer(), nullable=True, comment='最小起订量'),
        sa.Column('reference_price', sa.Numeric(12, 2), nullable=True, comment='参考价格'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD', comment='币种'),
        sa.Column('hs_code', sa.String(20), nullable=True, comment='HS 编码'),
        sa.Column('origin', sa.String(100), nullable=True, comment='产地'),
        sa.Column('material', sa.String(200), nullable=True, comment='材质'),
        sa.Column('packaging', sa.String(200), nullable=True, comment='包装方式'),
        sa.Column('images', sa.JSON(), nullable=True, comment='产品图片 URL 列表'),
        sa.Column('description', sa.Text(), nullable=True, comment='产品描述'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='标签列表'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active', comment='状态'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_products_category_id', 'products', ['category_id'])
    op.create_index('ix_products_status', 'products', ['status'])
    op.create_index('ix_products_name', 'products', ['name'])
    op.create_index('ix_products_hs_code', 'products', ['hs_code'])

    # 创建 product_suppliers 表
    op.create_table('product_suppliers',
        sa.Column('id', sa.String(36), nullable=False, comment='关联 ID'),
        sa.Column('product_id', sa.String(36), nullable=False, comment='产品 ID'),
        sa.Column('supplier_id', sa.String(36), nullable=False, comment='供应商 ID'),
        sa.Column('supply_price', sa.Numeric(12, 2), nullable=True, comment='供应价格'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD', comment='币种'),
        sa.Column('moq', sa.Integer(), nullable=True, comment='最小起订量'),
        sa.Column('lead_time', sa.Integer(), nullable=True, comment='交期（天）'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='是否首选供应商'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('product_id', 'supplier_id', name='uq_product_supplier'),
    )
    op.create_index('ix_product_suppliers_product_id', 'product_suppliers', ['product_id'])
    op.create_index('ix_product_suppliers_supplier_id', 'product_suppliers', ['supplier_id'])


def downgrade() -> None:
    # 按依赖关系反向删除
    op.drop_index('ix_product_suppliers_supplier_id', 'product_suppliers')
    op.drop_index('ix_product_suppliers_product_id', 'product_suppliers')
    op.drop_table('product_suppliers')

    op.drop_index('ix_products_hs_code', 'products')
    op.drop_index('ix_products_name', 'products')
    op.drop_index('ix_products_status', 'products')
    op.drop_index('ix_products_category_id', 'products')
    op.drop_table('products')

    op.drop_index('ix_categories_parent_id', 'categories')
    op.drop_index('ix_categories_code', 'categories')
    op.drop_table('categories')
