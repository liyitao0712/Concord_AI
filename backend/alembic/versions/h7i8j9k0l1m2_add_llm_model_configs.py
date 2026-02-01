"""add llm_model_configs table

Revision ID: h7i8j9k0l1m2
Revises: g6h7i8j9k0l1
Create Date: 2026-02-01 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h7i8j9k0l1m2'
down_revision: Union[str, None] = 'g6h7i8j9k0l1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 LLM 模型配置表
    op.create_table(
        'llm_model_configs',
        # 主键
        sa.Column('id', sa.String(length=36), nullable=False),

        # 模型标识
        sa.Column('model_id', sa.String(length=100), nullable=False, unique=True, comment='模型 ID，如：gemini/gemini-1.5-pro'),
        sa.Column('provider', sa.String(length=50), nullable=False, comment='提供商：gemini, qwen, anthropic 等'),
        sa.Column('model_name', sa.String(length=100), nullable=False, comment='显示名称：Gemini 1.5 Pro'),

        # API 配置
        sa.Column('api_key', sa.Text(), nullable=True, comment='该模型的 API Key（敏感）'),
        sa.Column('api_endpoint', sa.Text(), nullable=True, comment='自定义 API 端点（可选）'),

        # 使用统计
        sa.Column('total_requests', sa.Integer(), nullable=False, server_default='0', comment='总请求次数'),
        sa.Column('total_tokens', sa.BigInteger(), nullable=False, server_default='0', comment='总消耗 Token 数'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='最后使用时间'),

        # 状态
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true', comment='是否启用'),
        sa.Column('is_configured', sa.Boolean(), nullable=False, server_default='false', comment='是否已配置（有 API Key）'),

        # 元数据
        sa.Column('description', sa.Text(), nullable=True, comment='模型描述'),
        sa.Column('parameters', sa.JSON(), nullable=True, comment='默认参数（temperature, max_tokens 等）'),

        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        # 约束
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_id'),
    )

    # 创建索引
    op.create_index('ix_llm_model_configs_provider', 'llm_model_configs', ['provider'], unique=False)
    op.create_index('ix_llm_model_configs_is_enabled', 'llm_model_configs', ['is_enabled'], unique=False)
    op.create_index('ix_llm_model_configs_is_configured', 'llm_model_configs', ['is_configured'], unique=False)

    # 插入初始模型数据
    from datetime import datetime
    now = datetime.utcnow()

    # 定义表结构用于插入数据
    llm_configs_table = sa.table(
        'llm_model_configs',
        sa.column('id', sa.String),
        sa.column('model_id', sa.String),
        sa.column('provider', sa.String),
        sa.column('model_name', sa.String),
        sa.column('description', sa.Text),
        sa.column('total_requests', sa.Integer),
        sa.column('total_tokens', sa.BigInteger),
        sa.column('is_enabled', sa.Boolean),
        sa.column('is_configured', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    # 定义所有支持的模型
    models = [
        # Anthropic Claude
        {
            'id': 'anthropic-claude-3-5-sonnet',
            'model_id': 'anthropic/claude-3-5-sonnet-20241022',
            'provider': 'anthropic',
            'model_name': 'Claude 3.5 Sonnet',
            'description': 'Anthropic 最新的 Claude 3.5 Sonnet 模型，平衡性能和成本',
        },
        {
            'id': 'anthropic-claude-3-5-haiku',
            'model_id': 'anthropic/claude-3-5-haiku-20241022',
            'provider': 'anthropic',
            'model_name': 'Claude 3.5 Haiku',
            'description': 'Anthropic 轻量级模型，速度快成本低',
        },
        {
            'id': 'anthropic-claude-3-opus',
            'model_id': 'anthropic/claude-3-opus-20240229',
            'provider': 'anthropic',
            'model_name': 'Claude 3 Opus',
            'description': 'Anthropic 最强大的模型，适合复杂任务',
        },

        # OpenAI
        {
            'id': 'openai-gpt-4o',
            'model_id': 'openai/gpt-4o',
            'provider': 'openai',
            'model_name': 'GPT-4o',
            'description': 'OpenAI 最新的多模态模型',
        },
        {
            'id': 'openai-gpt-4o-mini',
            'model_id': 'openai/gpt-4o-mini',
            'provider': 'openai',
            'model_name': 'GPT-4o Mini',
            'description': 'OpenAI 轻量级模型，成本更低',
        },
        {
            'id': 'openai-gpt-4-turbo',
            'model_id': 'openai/gpt-4-turbo-preview',
            'provider': 'openai',
            'model_name': 'GPT-4 Turbo',
            'description': 'OpenAI GPT-4 Turbo 模型',
        },

        # Google Gemini
        {
            'id': 'gemini-pro',
            'model_id': 'gemini/gemini-1.5-pro',
            'provider': 'gemini',
            'model_name': 'Gemini 1.5 Pro',
            'description': 'Google 最强大的 Gemini 模型，支持长上下文',
        },
        {
            'id': 'gemini-flash',
            'model_id': 'gemini/gemini-1.5-flash',
            'provider': 'gemini',
            'model_name': 'Gemini 1.5 Flash',
            'description': 'Google 轻量级 Gemini 模型，速度快',
        },
        {
            'id': 'gemini-flash-8b',
            'model_id': 'gemini/gemini-1.5-flash-8b',
            'provider': 'gemini',
            'model_name': 'Gemini 1.5 Flash 8B',
            'description': 'Google 超轻量级模型，极低成本',
        },

        # 阿里千问（通过 Dashscope）
        {
            'id': 'qwen-max',
            'model_id': 'dashscope/qwen-max',
            'provider': 'qwen',
            'model_name': 'Qwen Max',
            'description': '千问最强大的模型',
        },
        {
            'id': 'qwen-plus',
            'model_id': 'dashscope/qwen-plus',
            'provider': 'qwen',
            'model_name': 'Qwen Plus',
            'description': '千问性能和成本平衡的模型',
        },
        {
            'id': 'qwen-turbo',
            'model_id': 'dashscope/qwen-turbo',
            'provider': 'qwen',
            'model_name': 'Qwen Turbo',
            'description': '千问快速响应模型',
        },

        # 火山引擎（可访问智谱等模型）
        {
            'id': 'volcengine-doubao',
            'model_id': 'volcengine/doubao-pro-32k',
            'provider': 'volcengine',
            'model_name': '豆包 Pro 32K',
            'description': '火山引擎豆包模型',
        },
    ]

    # 批量插入
    for model in models:
        op.execute(
            llm_configs_table.insert().values(
                id=model['id'],
                model_id=model['model_id'],
                provider=model['provider'],
                model_name=model['model_name'],
                description=model.get('description'),
                total_requests=0,
                total_tokens=0,
                is_enabled=True,
                is_configured=False,
                created_at=now,
                updated_at=now,
            )
        )


def downgrade() -> None:
    op.drop_index('ix_llm_model_configs_is_configured', table_name='llm_model_configs')
    op.drop_index('ix_llm_model_configs_is_enabled', table_name='llm_model_configs')
    op.drop_index('ix_llm_model_configs_provider', table_name='llm_model_configs')
    op.drop_table('llm_model_configs')
