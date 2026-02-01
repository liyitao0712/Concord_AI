"""add_email_sync_config_fields

Revision ID: d0df431218d1
Revises: i8j9k0l1m2n3
Create Date: 2026-02-01 23:17:33.565117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0df431218d1'
down_revision: Union[str, None] = 'i8j9k0l1m2n3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加邮件同步配置字段
    op.add_column('email_accounts', sa.Column('imap_sync_days', sa.Integer(), nullable=True, comment='同步多少天的历史邮件（None=全部，1=1天前，30=30天前）'))
    op.add_column('email_accounts', sa.Column('imap_unseen_only', sa.Boolean(), nullable=False, server_default='false', comment='是否只同步未读邮件（False=同步全部）'))
    op.add_column('email_accounts', sa.Column('imap_fetch_limit', sa.Integer(), nullable=False, server_default='50', comment='每次拉取的邮件数量上限'))


def downgrade() -> None:
    # 回滚时删除这些字段
    op.drop_column('email_accounts', 'imap_fetch_limit')
    op.drop_column('email_accounts', 'imap_unseen_only')
    op.drop_column('email_accounts', 'imap_sync_days')
