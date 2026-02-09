"""add ai_status and ai_confidence to customers

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-02-09

新增：
- customers.ai_status: AI 搜索状态（searching/completed/failed）
- customers.ai_confidence: AI 搜索置信度
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "h8i9j0k1l2m3"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column(
            "ai_status",
            sa.String(20),
            nullable=True,
            comment="AI 搜索状态: searching/completed/failed, null=非AI创建",
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "ai_confidence",
            sa.Float(),
            nullable=True,
            comment="AI 搜索置信度 0.0-1.0",
        ),
    )


def downgrade() -> None:
    op.drop_column("customers", "ai_confidence")
    op.drop_column("customers", "ai_status")
