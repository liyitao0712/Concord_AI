"""add rfq and quotation tables

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-02-09

新增：
- client_rfqs: 客户询价单表
- client_rfq_lines: 客户询价单明细表
- quotations: 报价单表
- quotation_lines: 报价单明细表
- supplier_rfqs: 供应商询价单表
- supplier_rfq_lines: 供应商询价单明细表
- supplier_quotations: 供应商报价单表
- supplier_quotation_lines: 供应商报价单明细表
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== client_rfqs ====================
    op.create_table(
        'client_rfqs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('rfq_no', sa.String(50), unique=True, nullable=False),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('trade_term', sa.String(20), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('payment_terms', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(10), server_default='USD'),
        sa.Column('exchange_rate', sa.Numeric(12, 6), nullable=True),
        sa.Column('subtotal', sa.Numeric(14, 2), server_default='0'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('total_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('port_of_loading', sa.String(100), nullable=True),
        sa.Column('port_of_discharge', sa.String(100), nullable=True),
        sa.Column('destination', sa.String(200), nullable=True),
        sa.Column('rfq_date', sa.Date(), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('attachments', sa.JSON(), server_default='[]'),
        sa.Column('tags', sa.JSON(), server_default='[]'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_client_rfqs_rfq_no', 'client_rfqs', ['rfq_no'])
    op.create_index('ix_client_rfqs_customer_id', 'client_rfqs', ['customer_id'])
    op.create_index('ix_client_rfqs_status', 'client_rfqs', ['status'])
    op.create_index('ix_client_rfqs_rfq_date', 'client_rfqs', ['rfq_date'])

    # ==================== client_rfq_lines ====================
    op.create_table(
        'client_rfq_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('client_rfq_id', sa.String(36), sa.ForeignKey('client_rfqs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_no', sa.Integer(), server_default='1'),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_name', sa.String(200), nullable=False),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Numeric(14, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=False),
        sa.Column('discount_rate', sa.Numeric(5, 2), server_default='0'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('tax_rate', sa.Numeric(5, 2), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('amount_with_tax', sa.Numeric(14, 2), server_default='0'),
        sa.Column('hs_code', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_client_rfq_lines_client_rfq_id', 'client_rfq_lines', ['client_rfq_id'])
    op.create_index('ix_client_rfq_lines_product_id', 'client_rfq_lines', ['product_id'])

    # ==================== quotations ====================
    op.create_table(
        'quotations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('quotation_no', sa.String(50), unique=True, nullable=False),
        sa.Column('customer_id', sa.String(36), sa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('linked_client_rfq_id', sa.String(36), sa.ForeignKey('client_rfqs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('trade_term', sa.String(20), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('payment_terms', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(10), server_default='USD'),
        sa.Column('exchange_rate', sa.Numeric(12, 6), nullable=True),
        sa.Column('subtotal', sa.Numeric(14, 2), server_default='0'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('total_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('commission_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('commission_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('port_of_loading', sa.String(100), nullable=True),
        sa.Column('port_of_discharge', sa.String(100), nullable=True),
        sa.Column('destination', sa.String(200), nullable=True),
        sa.Column('quotation_date', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('attachments', sa.JSON(), server_default='[]'),
        sa.Column('tags', sa.JSON(), server_default='[]'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_quotations_quotation_no', 'quotations', ['quotation_no'])
    op.create_index('ix_quotations_customer_id', 'quotations', ['customer_id'])
    op.create_index('ix_quotations_status', 'quotations', ['status'])
    op.create_index('ix_quotations_quotation_date', 'quotations', ['quotation_date'])
    op.create_index('ix_quotations_linked_client_rfq_id', 'quotations', ['linked_client_rfq_id'])

    # ==================== quotation_lines ====================
    op.create_table(
        'quotation_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('quotation_id', sa.String(36), sa.ForeignKey('quotations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_no', sa.Integer(), server_default='1'),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_name', sa.String(200), nullable=False),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Numeric(14, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=False),
        sa.Column('discount_rate', sa.Numeric(5, 2), server_default='0'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('tax_rate', sa.Numeric(5, 2), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('amount_with_tax', sa.Numeric(14, 2), server_default='0'),
        sa.Column('hs_code', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_quotation_lines_quotation_id', 'quotation_lines', ['quotation_id'])
    op.create_index('ix_quotation_lines_product_id', 'quotation_lines', ['product_id'])

    # ==================== supplier_rfqs ====================
    op.create_table(
        'supplier_rfqs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('rfq_no', sa.String(50), unique=True, nullable=False),
        sa.Column('supplier_id', sa.String(36), sa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('supplier_contacts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('trade_term', sa.String(20), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('payment_terms', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(10), server_default='USD'),
        sa.Column('exchange_rate', sa.Numeric(12, 6), nullable=True),
        sa.Column('subtotal', sa.Numeric(14, 2), server_default='0'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('total_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('port_of_loading', sa.String(100), nullable=True),
        sa.Column('port_of_discharge', sa.String(100), nullable=True),
        sa.Column('rfq_date', sa.Date(), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('attachments', sa.JSON(), server_default='[]'),
        sa.Column('tags', sa.JSON(), server_default='[]'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_supplier_rfqs_rfq_no', 'supplier_rfqs', ['rfq_no'])
    op.create_index('ix_supplier_rfqs_supplier_id', 'supplier_rfqs', ['supplier_id'])
    op.create_index('ix_supplier_rfqs_status', 'supplier_rfqs', ['status'])
    op.create_index('ix_supplier_rfqs_rfq_date', 'supplier_rfqs', ['rfq_date'])

    # ==================== supplier_rfq_lines ====================
    op.create_table(
        'supplier_rfq_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('supplier_rfq_id', sa.String(36), sa.ForeignKey('supplier_rfqs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_no', sa.Integer(), server_default='1'),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_name', sa.String(200), nullable=False),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Numeric(14, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=False),
        sa.Column('discount_rate', sa.Numeric(5, 2), server_default='0'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('tax_rate', sa.Numeric(5, 2), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('amount_with_tax', sa.Numeric(14, 2), server_default='0'),
        sa.Column('hs_code', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_supplier_rfq_lines_supplier_rfq_id', 'supplier_rfq_lines', ['supplier_rfq_id'])
    op.create_index('ix_supplier_rfq_lines_product_id', 'supplier_rfq_lines', ['product_id'])

    # ==================== supplier_quotations ====================
    op.create_table(
        'supplier_quotations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('quotation_no', sa.String(50), unique=True, nullable=False),
        sa.Column('supplier_id', sa.String(36), sa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('supplier_contacts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('linked_supplier_rfq_id', sa.String(36), sa.ForeignKey('supplier_rfqs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('trade_term', sa.String(20), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('payment_terms', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(10), server_default='USD'),
        sa.Column('exchange_rate', sa.Numeric(12, 6), nullable=True),
        sa.Column('subtotal', sa.Numeric(14, 2), server_default='0'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('total_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('port_of_loading', sa.String(100), nullable=True),
        sa.Column('port_of_discharge', sa.String(100), nullable=True),
        sa.Column('quotation_date', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('attachments', sa.JSON(), server_default='[]'),
        sa.Column('tags', sa.JSON(), server_default='[]'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_supplier_quotations_quotation_no', 'supplier_quotations', ['quotation_no'])
    op.create_index('ix_supplier_quotations_supplier_id', 'supplier_quotations', ['supplier_id'])
    op.create_index('ix_supplier_quotations_status', 'supplier_quotations', ['status'])
    op.create_index('ix_supplier_quotations_quotation_date', 'supplier_quotations', ['quotation_date'])
    op.create_index('ix_supplier_quotations_linked_supplier_rfq_id', 'supplier_quotations', ['linked_supplier_rfq_id'])

    # ==================== supplier_quotation_lines ====================
    op.create_table(
        'supplier_quotation_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('supplier_quotation_id', sa.String(36), sa.ForeignKey('supplier_quotations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_no', sa.Integer(), server_default='1'),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_name', sa.String(200), nullable=False),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Numeric(14, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=False),
        sa.Column('discount_rate', sa.Numeric(5, 2), server_default='0'),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('tax_rate', sa.Numeric(5, 2), server_default='0'),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('amount', sa.Numeric(14, 2), server_default='0'),
        sa.Column('amount_with_tax', sa.Numeric(14, 2), server_default='0'),
        sa.Column('hs_code', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_supplier_quotation_lines_supplier_quotation_id', 'supplier_quotation_lines', ['supplier_quotation_id'])
    op.create_index('ix_supplier_quotation_lines_product_id', 'supplier_quotation_lines', ['product_id'])


def downgrade() -> None:
    # 按反序删除（先删有 FK 依赖的表）
    op.drop_table('supplier_quotation_lines')
    op.drop_table('supplier_quotations')
    op.drop_table('supplier_rfq_lines')
    op.drop_table('supplier_rfqs')
    op.drop_table('quotation_lines')
    op.drop_table('quotations')
    op.drop_table('client_rfq_lines')
    op.drop_table('client_rfqs')
