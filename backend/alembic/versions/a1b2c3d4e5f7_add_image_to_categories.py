"""add image fields to categories

Revision ID: a1b2c3d4e5f7
Revises: e4f5g6h7i8j9
Create Date: 2026-02-08

品类表增加图片字段：
- image_key: 图片存储路径 key
- image_storage_type: 存储类型（oss 或 local）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'e4f5g6h7i8j9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('categories', sa.Column('image_key', sa.String(500), nullable=True, comment='图片存储路径 key'))
    op.add_column('categories', sa.Column('image_storage_type', sa.String(10), nullable=True, comment='图片存储类型: oss 或 local'))


def downgrade() -> None:
    op.drop_column('categories', 'image_storage_type')
    op.drop_column('categories', 'image_key')
