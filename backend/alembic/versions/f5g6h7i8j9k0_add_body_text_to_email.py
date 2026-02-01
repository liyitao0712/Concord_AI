"""add body_text to email_raw_messages

Revision ID: f5g6h7i8j9k0
Revises: e4f5a6b7c8d9
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5g6h7i8j9k0'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 body_text 字段到 email_raw_messages 表
    op.add_column(
        'email_raw_messages',
        sa.Column('body_text', sa.Text(), nullable=True, comment='邮件纯文本正文（前 5000 字符，用于 AI 分析）')
    )

    # 插入 RouterAgent 的 Prompt 到 prompts 表
    op.execute("""
        INSERT INTO prompts (id, name, category, display_name, content, variables, description, is_active, version, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'router_agent',
            'agent',
            '路由分类 Prompt',
            '你是一个意图分类专家，负责分析消息的意图。

## 已有意图列表
{{intents_json}}

## 待分类消息
来源: {{source}}
{{subject_line}}内容:
{{content}}

## 任务
1. 判断这条消息属于哪个已有意图
2. 如果没有合适的意图匹配，请建议新增意图

## 返回格式（纯 JSON，不要 markdown）
{
  "matched_intent": "意图的name字段值" | null,
  "confidence": 0.0-1.0,
  "reasoning": "判断理由（简短）",
  "new_suggestion": {
    "name": "建议的英文名（小写下划线）",
    "label": "建议的中文名",
    "description": "这类消息的特征描述",
    "suggested_handler": "agent 或 workflow"
  } | null
}

注意：
1. confidence 表示你对匹配结果的确信程度
2. 如果 confidence < 0.6，应该考虑建议新意图
3. new_suggestion 只在没有合适匹配时提供
4. 只输出 JSON，不要添加任何其他内容',
            '{"intents_json": "已有意图列表 JSON", "source": "消息来源", "subject_line": "主题行（邮件）", "content": "消息正文"}',
            '用于 RouterAgent 进行意图分类的提示词模板',
            true,
            1,
            NOW(),
            NOW()
        )
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_column('email_raw_messages', 'body_text')
    op.execute("DELETE FROM prompts WHERE name = 'router_agent'")
