"""add broadcast to email_analyses

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-08

新增字段：
- email_analyses.broadcast: 一句话播报，用于快速浏览和语音播报
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'email_analyses',
        sa.Column('broadcast', sa.String(length=500), nullable=True,
                  comment='一句话播报，用于快速浏览和语音播报'),
    )


def downgrade() -> None:
    op.drop_column('email_analyses', 'broadcast')
