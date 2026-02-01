"""add intents table

Revision ID: e4f5a6b7c8d9
Revises: d3f4a5b6c7d8
Create Date: 2025-01-31

创建意图表：
- intents: 意图定义
- intent_suggestions: AI 建议的新意图（待审批）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from uuid import uuid4


# revision identifiers, used by Alembic.
revision = 'e4f5a6b7c8d9'
down_revision = 'd3f4a5b6c7d8'
branch_labels = None
depends_on = None


# 种子数据
SEED_INTENTS = [
    {
        "id": str(uuid4()),
        "name": "inquiry",
        "label": "询价",
        "description": "客户询问产品价格、要求报价、咨询产品信息",
        "examples": ["请问产品A多少钱？", "能给我发一份报价单吗？", "我想了解一下你们的产品价格"],
        "keywords": ["价格", "报价", "多少钱", "费用", "成本"],
        "default_handler": "agent",
        "handler_config": {"agent_name": "QuoteAgent"},
        "escalation_rules": {"amount_gt": 10000},
        "escalation_workflow": "QuoteApprovalWorkflow",
        "priority": 10,
        "is_active": True,
        "created_by": "system",
    },
    {
        "id": str(uuid4()),
        "name": "complaint",
        "label": "投诉",
        "description": "客户投诉、表达不满、问题反馈、质量问题",
        "examples": ["你们的产品质量太差了", "我要投诉", "这个问题一直没解决"],
        "keywords": ["投诉", "不满", "差", "问题", "退货", "退款"],
        "default_handler": "workflow",
        "handler_config": {"workflow_name": "ComplaintWorkflow"},
        "escalation_rules": {"always": True},
        "escalation_workflow": "ComplaintWorkflow",
        "priority": 20,
        "is_active": True,
        "created_by": "system",
    },
    {
        "id": str(uuid4()),
        "name": "order",
        "label": "订单",
        "description": "客户下单、确认采购、订购产品",
        "examples": ["我要订购100个产品A", "请帮我下单", "确认采购"],
        "keywords": ["订购", "下单", "采购", "购买", "要买"],
        "default_handler": "workflow",
        "handler_config": {"workflow_name": "OrderWorkflow"},
        "escalation_rules": None,
        "escalation_workflow": None,
        "priority": 15,
        "is_active": True,
        "created_by": "system",
    },
    {
        "id": str(uuid4()),
        "name": "follow_up",
        "label": "跟进",
        "description": "客户跟进之前的事项、询问进度、催促",
        "examples": ["上次的报价怎么样了？", "订单发货了吗？", "进度如何？"],
        "keywords": ["进度", "怎么样了", "跟进", "催", "上次"],
        "default_handler": "agent",
        "handler_config": {"agent_name": "ChatAgent", "notify": True},
        "escalation_rules": None,
        "escalation_workflow": None,
        "priority": 5,
        "is_active": True,
        "created_by": "system",
    },
    {
        "id": str(uuid4()),
        "name": "greeting",
        "label": "问候",
        "description": "打招呼、闲聊、无特定业务意图",
        "examples": ["你好", "在吗？", "早上好"],
        "keywords": ["你好", "在吗", "早上好", "下午好", "晚上好"],
        "default_handler": "agent",
        "handler_config": {"agent_name": "ChatAgent"},
        "escalation_rules": None,
        "escalation_workflow": None,
        "priority": 0,
        "is_active": True,
        "created_by": "system",
    },
    {
        "id": str(uuid4()),
        "name": "other",
        "label": "其他",
        "description": "无法分类的消息、不明确的意图",
        "examples": [],
        "keywords": [],
        "default_handler": "agent",
        "handler_config": {"agent_name": "ChatAgent", "notify": True},
        "escalation_rules": None,
        "escalation_workflow": None,
        "priority": -1,
        "is_active": True,
        "created_by": "system",
    },
]


def upgrade() -> None:
    # 创建 intents 表
    op.create_table(
        'intents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('examples', JSON, default=list),
        sa.Column('keywords', JSON, default=list),
        sa.Column('default_handler', sa.String(50), nullable=False, default='agent'),
        sa.Column('handler_config', JSON, default=dict),
        sa.Column('escalation_rules', JSON, nullable=True),
        sa.Column('escalation_workflow', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('priority', sa.Integer(), default=0),
        sa.Column('created_by', sa.String(50), default='system'),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index('ix_intents_is_active', 'intents', ['is_active'])
    op.create_index('ix_intents_priority', 'intents', ['priority'])

    # 创建 intent_suggestions 表
    op.create_table(
        'intent_suggestions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('suggested_name', sa.String(50), nullable=False),
        sa.Column('suggested_label', sa.String(100), nullable=False),
        sa.Column('suggested_description', sa.Text(), nullable=False),
        sa.Column('suggested_handler', sa.String(50), default='agent'),
        sa.Column('suggested_examples', JSON, default=list),
        sa.Column('trigger_message', sa.Text(), nullable=False),
        sa.Column('trigger_event_id', sa.String(36), nullable=True),
        sa.Column('trigger_source', sa.String(20), default='email'),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('workflow_id', sa.String(100), nullable=True),
        sa.Column('reviewed_by', sa.String(36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('created_intent_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index('ix_intent_suggestions_status', 'intent_suggestions', ['status'])
    op.create_index('ix_intent_suggestions_created_at', 'intent_suggestions', ['created_at'])

    # 插入种子数据
    intents_table = sa.table(
        'intents',
        sa.column('id', sa.String),
        sa.column('name', sa.String),
        sa.column('label', sa.String),
        sa.column('description', sa.Text),
        sa.column('examples', JSON),
        sa.column('keywords', JSON),
        sa.column('default_handler', sa.String),
        sa.column('handler_config', JSON),
        sa.column('escalation_rules', JSON),
        sa.column('escalation_workflow', sa.String),
        sa.column('priority', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_by', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    now = datetime.utcnow()
    for intent in SEED_INTENTS:
        op.execute(
            intents_table.insert().values(
                id=intent['id'],
                name=intent['name'],
                label=intent['label'],
                description=intent['description'],
                examples=intent['examples'],
                keywords=intent['keywords'],
                default_handler=intent['default_handler'],
                handler_config=intent['handler_config'],
                escalation_rules=intent['escalation_rules'],
                escalation_workflow=intent['escalation_workflow'],
                priority=intent['priority'],
                is_active=intent['is_active'],
                created_by=intent['created_by'],
                created_at=now,
                updated_at=now,
            )
        )


def downgrade() -> None:
    op.drop_index('ix_intent_suggestions_created_at', 'intent_suggestions')
    op.drop_index('ix_intent_suggestions_status', 'intent_suggestions')
    op.drop_table('intent_suggestions')

    op.drop_index('ix_intents_priority', 'intents')
    op.drop_index('ix_intents_is_active', 'intents')
    op.drop_table('intents')
