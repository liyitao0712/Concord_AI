"""add order related tables

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-08

新增表：
- warehouses: 仓库表
- inventories: 库存表
- contract_number_rules: 合同编号规则表
- purchase_contracts: 采购合同表
- purchase_lines: 采购合同明细表
- sales_contracts: 销售合同表
- sales_lines: 销售合同明细表
- inbound_orders: 入仓单表
- inbound_lines: 入仓明细表
- outbound_orders: 出仓单表
- outbound_lines: 出仓明细表
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== 仓库表 ====================
    op.create_table(
        'warehouses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(30), unique=True, nullable=False, comment='仓库编码'),
        sa.Column('name', sa.String(100), nullable=False, comment='仓库名称'),
        sa.Column('address', sa.String(300), nullable=True, comment='仓库地址'),
        sa.Column('contact_person', sa.String(50), nullable=True, comment='联系人'),
        sa.Column('contact_phone', sa.String(50), nullable=True, comment='联系电话'),
        sa.Column('warehouse_type', sa.String(20), server_default='own', comment='仓库类型'),
        sa.Column('is_active', sa.Boolean(), server_default='true', comment='是否启用'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_warehouses_code', 'warehouses', ['code'])
    op.create_index('ix_warehouses_is_active', 'warehouses', ['is_active'])

    # ==================== 库存表 ====================
    op.create_table(
        'inventories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('warehouse_id', sa.String(36), sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False, comment='仓库 ID'),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, comment='产品 ID'),
        sa.Column('quantity', sa.Numeric(14, 4), server_default='0', comment='实际库存数量'),
        sa.Column('reserved_quantity', sa.Numeric(14, 4), server_default='0', comment='占用数量'),
        sa.Column('unit', sa.String(50), nullable=True, comment='单位'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('warehouse_id', 'product_id', name='uq_inventory_warehouse_product'),
    )
    op.create_index('ix_inventories_warehouse_id', 'inventories', ['warehouse_id'])
    op.create_index('ix_inventories_product_id', 'inventories', ['product_id'])

    # ==================== 合同编号规则表 ====================
    op.create_table(
        'contract_number_rules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('rule_type', sa.String(30), nullable=False, comment='规则类型'),
        sa.Column('prefix', sa.String(20), nullable=False, comment='前缀'),
        sa.Column('date_format', sa.String(20), server_default='%Y%m%d', comment='日期格式'),
        sa.Column('separator', sa.String(5), server_default='-', comment='分隔符'),
        sa.Column('sequence_length', sa.Integer(), server_default='3', comment='序号位数'),
        sa.Column('current_sequence', sa.Integer(), server_default='0', comment='当前序号'),
        sa.Column('last_date', sa.String(20), nullable=True, comment='上次生成日期'),
        sa.Column('is_active', sa.Boolean(), server_default='true', comment='是否启用'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('rule_type', name='uq_contract_number_rule_type'),
    )
    op.create_index('ix_contract_number_rules_rule_type', 'contract_number_rules', ['rule_type'])

    # ==================== 采购合同表 ====================
    op.create_table(
        'purchase_contracts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('contract_no', sa.String(50), unique=True, nullable=False, comment='合同编号'),
        sa.Column('supplier_id', sa.String(36), sa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False, comment='供应商 ID'),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('supplier_contacts.id', ondelete='SET NULL'), nullable=True, comment='联系人 ID'),
        sa.Column('trade_term', sa.String(20), nullable=True, comment='贸易术语'),
        sa.Column('payment_method', sa.String(50), nullable=True, comment='付款方式'),
        sa.Column('payment_terms', sa.Text(), nullable=True, comment='付款条款'),
        sa.Column('currency', sa.String(10), server_default='USD', comment='币种'),
        sa.Column('exchange_rate', sa.Numeric(12, 6), nullable=True, comment='汇率'),
        sa.Column('subtotal', sa.Numeric(14, 2), server_default='0', comment='小计'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0', comment='折扣'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0', comment='税额'),
        sa.Column('total_amount', sa.Numeric(14, 2), server_default='0', comment='总金额'),
        sa.Column('port_of_loading', sa.String(100), nullable=True, comment='装运港'),
        sa.Column('port_of_discharge', sa.String(100), nullable=True, comment='目的港'),
        sa.Column('contract_date', sa.Date(), nullable=True, comment='合同日期'),
        sa.Column('delivery_date', sa.Date(), nullable=True, comment='交货日期'),
        sa.Column('expected_arrival_date', sa.Date(), nullable=True, comment='预计到货'),
        sa.Column('expiry_date', sa.Date(), nullable=True, comment='有效期'),
        sa.Column('status', sa.String(20), server_default='draft', comment='状态'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('attachments', sa.JSON(), server_default='[]', comment='附件列表'),
        sa.Column('tags', sa.JSON(), server_default='[]', comment='标签列表'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='创建人'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_purchase_contracts_contract_no', 'purchase_contracts', ['contract_no'])
    op.create_index('ix_purchase_contracts_supplier_id', 'purchase_contracts', ['supplier_id'])
    op.create_index('ix_purchase_contracts_status', 'purchase_contracts', ['status'])
    op.create_index('ix_purchase_contracts_contract_date', 'purchase_contracts', ['contract_date'])

    # ==================== 采购明细行表 ====================
    op.create_table(
        'purchase_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('purchase_contract_id', sa.String(36), sa.ForeignKey('purchase_contracts.id', ondelete='CASCADE'), nullable=False, comment='采购合同 ID'),
        sa.Column('line_no', sa.Integer(), server_default='1', comment='行号'),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, comment='产品 ID'),
        sa.Column('product_name', sa.String(200), nullable=False, comment='品名'),
        sa.Column('specifications', sa.Text(), nullable=True, comment='规格'),
        sa.Column('unit', sa.String(50), nullable=False, comment='单位'),
        sa.Column('quantity', sa.Numeric(14, 4), nullable=False, comment='数量'),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=False, comment='单价'),
        sa.Column('discount_rate', sa.Numeric(5, 2), server_default='0', comment='折扣率'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0', comment='折扣金额'),
        sa.Column('tax_rate', sa.Numeric(5, 2), server_default='0', comment='税率'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0', comment='税额'),
        sa.Column('amount', sa.Numeric(14, 2), server_default='0', comment='金额'),
        sa.Column('amount_with_tax', sa.Numeric(14, 2), server_default='0', comment='含税金额'),
        sa.Column('received_quantity', sa.Numeric(14, 4), server_default='0', comment='已收货数量'),
        sa.Column('hs_code', sa.String(20), nullable=True, comment='HS 编码'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_purchase_lines_purchase_contract_id', 'purchase_lines', ['purchase_contract_id'])
    op.create_index('ix_purchase_lines_product_id', 'purchase_lines', ['product_id'])

    # ==================== 销售合同表 ====================
    op.create_table(
        'sales_contracts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('contract_no', sa.String(50), unique=True, nullable=False, comment='合同编号'),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False, comment='客户 ID'),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True, comment='联系人 ID'),
        sa.Column('trade_term', sa.String(20), nullable=True, comment='贸易术语'),
        sa.Column('payment_method', sa.String(50), nullable=True, comment='付款方式'),
        sa.Column('payment_terms', sa.Text(), nullable=True, comment='付款条款'),
        sa.Column('currency', sa.String(10), server_default='USD', comment='币种'),
        sa.Column('exchange_rate', sa.Numeric(12, 6), nullable=True, comment='汇率'),
        sa.Column('subtotal', sa.Numeric(14, 2), server_default='0', comment='小计'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0', comment='折扣'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0', comment='税额'),
        sa.Column('total_amount', sa.Numeric(14, 2), server_default='0', comment='总金额'),
        sa.Column('commission_rate', sa.Numeric(5, 2), nullable=True, comment='佣金比例'),
        sa.Column('commission_amount', sa.Numeric(14, 2), nullable=True, comment='佣金金额'),
        sa.Column('port_of_loading', sa.String(100), nullable=True, comment='装运港'),
        sa.Column('port_of_discharge', sa.String(100), nullable=True, comment='目的港'),
        sa.Column('destination', sa.String(200), nullable=True, comment='最终目的地'),
        sa.Column('shipping_marks', sa.Text(), nullable=True, comment='唛头'),
        sa.Column('contract_date', sa.Date(), nullable=True, comment='合同日期'),
        sa.Column('delivery_date', sa.Date(), nullable=True, comment='交货日期'),
        sa.Column('shipping_date', sa.Date(), nullable=True, comment='装运日期'),
        sa.Column('expiry_date', sa.Date(), nullable=True, comment='有效期'),
        sa.Column('status', sa.String(20), server_default='draft', comment='状态'),
        sa.Column('is_zero_stock', sa.Boolean(), server_default='false', comment='零库存模式'),
        sa.Column('linked_purchase_contract_id', sa.String(36), sa.ForeignKey('purchase_contracts.id', ondelete='SET NULL'), nullable=True, unique=True, comment='关联采购合同'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('attachments', sa.JSON(), server_default='[]', comment='附件列表'),
        sa.Column('tags', sa.JSON(), server_default='[]', comment='标签列表'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='创建人'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_sales_contracts_contract_no', 'sales_contracts', ['contract_no'])
    op.create_index('ix_sales_contracts_customer_id', 'sales_contracts', ['customer_id'])
    op.create_index('ix_sales_contracts_status', 'sales_contracts', ['status'])
    op.create_index('ix_sales_contracts_contract_date', 'sales_contracts', ['contract_date'])
    op.create_index('ix_sales_contracts_is_zero_stock', 'sales_contracts', ['is_zero_stock'])

    # ==================== 销售明细行表 ====================
    op.create_table(
        'sales_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('sales_contract_id', sa.String(36), sa.ForeignKey('sales_contracts.id', ondelete='CASCADE'), nullable=False, comment='销售合同 ID'),
        sa.Column('line_no', sa.Integer(), server_default='1', comment='行号'),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, comment='产品 ID'),
        sa.Column('product_name', sa.String(200), nullable=False, comment='品名'),
        sa.Column('specifications', sa.Text(), nullable=True, comment='规格'),
        sa.Column('unit', sa.String(50), nullable=False, comment='单位'),
        sa.Column('quantity', sa.Numeric(14, 4), nullable=False, comment='数量'),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=False, comment='单价'),
        sa.Column('discount_rate', sa.Numeric(5, 2), server_default='0', comment='折扣率'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0', comment='折扣金额'),
        sa.Column('tax_rate', sa.Numeric(5, 2), server_default='0', comment='税率'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0', comment='税额'),
        sa.Column('tax_rebate_rate', sa.Numeric(5, 2), nullable=True, comment='退税率'),
        sa.Column('amount', sa.Numeric(14, 2), server_default='0', comment='金额'),
        sa.Column('amount_with_tax', sa.Numeric(14, 2), server_default='0', comment='含税金额'),
        sa.Column('shipped_quantity', sa.Numeric(14, 4), server_default='0', comment='已发货数量'),
        sa.Column('reserved_warehouse_id', sa.String(36), sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True, comment='占用仓库'),
        sa.Column('reserved_quantity', sa.Numeric(14, 4), server_default='0', comment='占用数量'),
        sa.Column('hs_code', sa.String(20), nullable=True, comment='HS 编码'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_sales_lines_sales_contract_id', 'sales_lines', ['sales_contract_id'])
    op.create_index('ix_sales_lines_product_id', 'sales_lines', ['product_id'])

    # ==================== 入仓单表 ====================
    op.create_table(
        'inbound_orders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_no', sa.String(50), unique=True, nullable=False, comment='入仓单号'),
        sa.Column('warehouse_id', sa.String(36), sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False, comment='仓库 ID'),
        sa.Column('purchase_contract_id', sa.String(36), sa.ForeignKey('purchase_contracts.id', ondelete='SET NULL'), nullable=True, comment='采购合同 ID'),
        sa.Column('supplier_id', sa.String(36), sa.ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True, comment='供应商 ID'),
        sa.Column('status', sa.String(20), server_default='draft', comment='状态'),
        sa.Column('expected_date', sa.Date(), nullable=True, comment='预计到货'),
        sa.Column('actual_date', sa.Date(), nullable=True, comment='实际到货'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='创建人'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_inbound_orders_order_no', 'inbound_orders', ['order_no'])
    op.create_index('ix_inbound_orders_warehouse_id', 'inbound_orders', ['warehouse_id'])
    op.create_index('ix_inbound_orders_purchase_contract_id', 'inbound_orders', ['purchase_contract_id'])
    op.create_index('ix_inbound_orders_status', 'inbound_orders', ['status'])

    # ==================== 入仓明细行表 ====================
    op.create_table(
        'inbound_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('inbound_order_id', sa.String(36), sa.ForeignKey('inbound_orders.id', ondelete='CASCADE'), nullable=False, comment='入仓单 ID'),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, comment='产品 ID'),
        sa.Column('purchase_line_id', sa.String(36), sa.ForeignKey('purchase_lines.id', ondelete='SET NULL'), nullable=True, comment='采购明细行 ID'),
        sa.Column('expected_quantity', sa.Numeric(14, 4), nullable=False, comment='预期数量'),
        sa.Column('received_quantity', sa.Numeric(14, 4), server_default='0', comment='实收数量'),
        sa.Column('unit', sa.String(50), nullable=False, comment='单位'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_inbound_lines_inbound_order_id', 'inbound_lines', ['inbound_order_id'])
    op.create_index('ix_inbound_lines_product_id', 'inbound_lines', ['product_id'])

    # ==================== 出仓单表 ====================
    op.create_table(
        'outbound_orders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_no', sa.String(50), unique=True, nullable=False, comment='出仓单号'),
        sa.Column('warehouse_id', sa.String(36), sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False, comment='仓库 ID'),
        sa.Column('sales_contract_id', sa.String(36), sa.ForeignKey('sales_contracts.id', ondelete='SET NULL'), nullable=True, comment='销售合同 ID'),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True, comment='客户 ID'),
        sa.Column('status', sa.String(20), server_default='draft', comment='状态'),
        sa.Column('expected_date', sa.Date(), nullable=True, comment='预计发货'),
        sa.Column('actual_date', sa.Date(), nullable=True, comment='实际发货'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='创建人'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_outbound_orders_order_no', 'outbound_orders', ['order_no'])
    op.create_index('ix_outbound_orders_warehouse_id', 'outbound_orders', ['warehouse_id'])
    op.create_index('ix_outbound_orders_sales_contract_id', 'outbound_orders', ['sales_contract_id'])
    op.create_index('ix_outbound_orders_status', 'outbound_orders', ['status'])

    # ==================== 出仓明细行表 ====================
    op.create_table(
        'outbound_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('outbound_order_id', sa.String(36), sa.ForeignKey('outbound_orders.id', ondelete='CASCADE'), nullable=False, comment='出仓单 ID'),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, comment='产品 ID'),
        sa.Column('sales_line_id', sa.String(36), sa.ForeignKey('sales_lines.id', ondelete='SET NULL'), nullable=True, comment='销售明细行 ID'),
        sa.Column('quantity', sa.Numeric(14, 4), nullable=False, comment='出仓数量'),
        sa.Column('shipped_quantity', sa.Numeric(14, 4), server_default='0', comment='已发货数量（累计）'),
        sa.Column('unit', sa.String(50), nullable=False, comment='单位'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_outbound_lines_outbound_order_id', 'outbound_lines', ['outbound_order_id'])
    op.create_index('ix_outbound_lines_product_id', 'outbound_lines', ['product_id'])


def downgrade() -> None:
    op.drop_table('outbound_lines')
    op.drop_table('outbound_orders')
    op.drop_table('inbound_lines')
    op.drop_table('inbound_orders')
    op.drop_table('sales_lines')
    op.drop_table('sales_contracts')
    op.drop_table('purchase_lines')
    op.drop_table('purchase_contracts')
    op.drop_table('contract_number_rules')
    op.drop_table('inventories')
    op.drop_table('warehouses')
