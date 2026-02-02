"""add work_types table

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
Create Date: 2025-02-02

创建工作类型表：
- work_types: 工作类型定义（支持 Parent-Child 树形结构）
- work_type_suggestions: AI 建议的新工作类型（待审批）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from uuid import uuid4


# revision identifiers, used by Alembic.
revision = 'j9k0l1m2n3o4'
down_revision = 'i8j9k0l1m2n3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建 work_types 表
    op.create_table(
        'work_types',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('work_types.id', ondelete='CASCADE'), nullable=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('level', sa.Integer(), default=1),
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('examples', JSON, default=list),
        sa.Column('keywords', JSON, default=list),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_system', sa.Boolean(), default=False),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('created_by', sa.String(50), default='system'),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index('ix_work_types_parent_id', 'work_types', ['parent_id'])
    op.create_index('ix_work_types_code', 'work_types', ['code'])
    op.create_index('ix_work_types_level', 'work_types', ['level'])
    op.create_index('ix_work_types_is_active', 'work_types', ['is_active'])

    # 2. 创建 work_type_suggestions 表
    op.create_table(
        'work_type_suggestions',
        sa.Column('id', sa.String(36), primary_key=True),
        # 建议内容
        sa.Column('suggested_code', sa.String(100), nullable=False),
        sa.Column('suggested_name', sa.String(100), nullable=False),
        sa.Column('suggested_description', sa.Text(), nullable=False),
        sa.Column('suggested_parent_id', sa.String(36), nullable=True),
        sa.Column('suggested_parent_code', sa.String(100), nullable=True),
        sa.Column('suggested_level', sa.Integer(), default=1),
        sa.Column('suggested_examples', JSON, default=list),
        sa.Column('suggested_keywords', JSON, default=list),
        # AI 分析信息
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('reasoning', sa.Text(), nullable=True),
        # 触发来源
        sa.Column('trigger_email_id', sa.String(36), nullable=True),
        sa.Column('trigger_content', sa.Text(), nullable=False, default=''),
        sa.Column('trigger_source', sa.String(20), default='email'),
        # 审批状态
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('workflow_id', sa.String(100), nullable=True),
        sa.Column('reviewed_by', sa.String(36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('created_work_type_id', sa.String(36), nullable=True),
        sa.Column('merged_to_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index('ix_work_type_suggestions_status', 'work_type_suggestions', ['status'])
    op.create_index('ix_work_type_suggestions_created_at', 'work_type_suggestions', ['created_at'])
    op.create_index('ix_work_type_suggestions_trigger_email_id', 'work_type_suggestions', ['trigger_email_id'])

    # 3. 插入种子数据
    work_types_table = sa.table(
        'work_types',
        sa.column('id', sa.String),
        sa.column('parent_id', sa.String),
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('level', sa.Integer),
        sa.column('path', sa.String),
        sa.column('examples', JSON),
        sa.column('keywords', JSON),
        sa.column('is_active', sa.Boolean),
        sa.column('is_system', sa.Boolean),
        sa.column('usage_count', sa.Integer),
        sa.column('created_by', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    now = datetime.utcnow()

    # Level 1 种子数据（先插入顶级）
    level1_data = [
        {
            "id": str(uuid4()),
            "code": "ORDER",
            "name": "订单",
            "description": "与订单相关的邮件，包括新订单、修改、取消等",
            "level": 1,
            "path": "/ORDER",
            "examples": ["我想下单", "订单确认", "采购订单", "PO"],
            "keywords": ["订单", "order", "PO", "采购", "purchase"],
        },
        {
            "id": str(uuid4()),
            "code": "INQUIRY",
            "name": "询价",
            "description": "客户询价、询盘、了解产品信息、请求报价",
            "level": 1,
            "path": "/INQUIRY",
            "examples": ["请报价", "询问价格", "product inquiry", "RFQ"],
            "keywords": ["询价", "报价", "inquiry", "quote", "RFQ", "价格"],
        },
        {
            "id": str(uuid4()),
            "code": "SHIPMENT",
            "name": "物流",
            "description": "发货、物流跟踪、运输、清关相关",
            "level": 1,
            "path": "/SHIPMENT",
            "examples": ["发货通知", "物流追踪", "shipping details", "提单"],
            "keywords": ["发货", "物流", "shipping", "delivery", "B/L", "提单"],
        },
        {
            "id": str(uuid4()),
            "code": "PAYMENT",
            "name": "付款",
            "description": "付款通知、汇款确认、财务、发票相关",
            "level": 1,
            "path": "/PAYMENT",
            "examples": ["付款通知", "汇款底单", "payment confirmation", "invoice"],
            "keywords": ["付款", "汇款", "payment", "remittance", "invoice", "发票"],
        },
        {
            "id": str(uuid4()),
            "code": "COMPLAINT",
            "name": "投诉",
            "description": "客户投诉、质量问题、售后问题",
            "level": 1,
            "path": "/COMPLAINT",
            "examples": ["产品质量问题", "投诉", "要求退款", "不满意"],
            "keywords": ["投诉", "质量", "退款", "complaint", "refund", "问题"],
        },
        {
            "id": str(uuid4()),
            "code": "OTHER",
            "name": "其他",
            "description": "无法分类的工作类型",
            "level": 1,
            "path": "/OTHER",
            "examples": [],
            "keywords": [],
        },
    ]

    # 创建 code -> id 的映射
    code_to_id = {}

    # 先插入 Level 1
    for item in level1_data:
        code_to_id[item["code"]] = item["id"]
        op.execute(
            work_types_table.insert().values(
                id=item["id"],
                parent_id=None,
                code=item["code"],
                name=item["name"],
                description=item["description"],
                level=item["level"],
                path=item["path"],
                examples=item["examples"],
                keywords=item["keywords"],
                is_active=True,
                is_system=True,
                usage_count=0,
                created_by="system",
                created_at=now,
                updated_at=now,
            )
        )

    # Level 2 种子数据
    level2_data = [
        {
            "id": str(uuid4()),
            "parent_code": "ORDER",
            "code": "ORDER_NEW",
            "name": "新订单",
            "description": "客户发起新订单、首次采购",
            "level": 2,
            "path": "/ORDER/ORDER_NEW",
            "examples": ["新订单", "首次采购", "请报价并下单", "new order"],
            "keywords": ["新订单", "new order", "首次", "下单"],
        },
        {
            "id": str(uuid4()),
            "parent_code": "ORDER",
            "code": "ORDER_CHANGE",
            "name": "订单修改",
            "description": "修改已有订单的数量、规格、交期等",
            "level": 2,
            "path": "/ORDER/ORDER_CHANGE",
            "examples": ["修改订单", "更改数量", "变更交期", "revise order"],
            "keywords": ["修改", "更改", "change", "revise", "amendment"],
        },
    ]

    # 插入 Level 2
    for item in level2_data:
        parent_id = code_to_id.get(item["parent_code"])
        op.execute(
            work_types_table.insert().values(
                id=item["id"],
                parent_id=parent_id,
                code=item["code"],
                name=item["name"],
                description=item["description"],
                level=item["level"],
                path=item["path"],
                examples=item["examples"],
                keywords=item["keywords"],
                is_active=True,
                is_system=True,
                usage_count=0,
                created_by="system",
                created_at=now,
                updated_at=now,
            )
        )


def downgrade() -> None:
    # 删除 work_type_suggestions 表
    op.drop_index('ix_work_type_suggestions_trigger_email_id', 'work_type_suggestions')
    op.drop_index('ix_work_type_suggestions_created_at', 'work_type_suggestions')
    op.drop_index('ix_work_type_suggestions_status', 'work_type_suggestions')
    op.drop_table('work_type_suggestions')

    # 删除 work_types 表
    op.drop_index('ix_work_types_is_active', 'work_types')
    op.drop_index('ix_work_types_level', 'work_types')
    op.drop_index('ix_work_types_code', 'work_types')
    op.drop_index('ix_work_types_parent_id', 'work_types')
    op.drop_table('work_types')
