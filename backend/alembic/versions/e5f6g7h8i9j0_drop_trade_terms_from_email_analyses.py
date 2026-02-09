"""drop trade_terms from email_analyses

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-02-08

移除字段：
- email_analyses.trade_terms: 贸易条款 JSON 字段（已不再由 EmailSummarizer 提取）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('email_analyses', 'trade_terms')


def downgrade() -> None:
    op.add_column(
        'email_analyses',
        sa.Column('trade_terms', sa.JSON(), nullable=True,
                  comment='贸易条款 {incoterm, payment_terms, destination}'),
    )
