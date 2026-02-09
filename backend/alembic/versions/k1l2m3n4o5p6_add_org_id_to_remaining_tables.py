"""给遗漏的业务表补充 org_id 字段 + 修正合同编号唯一约束

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-02-10

Phase 3: 为 Phase 2 遗漏的表补充 org_id：
- email_accounts
- work_types
- work_type_suggestions
- customer_suggestions

同时修正 contract_number_rules 的唯一约束：
- 旧: uq_contract_number_rule_type (rule_type)
- 新: uq_contract_number_rule_type_org (rule_type, org_id)
"""

from alembic import op
import sqlalchemy as sa


revision = "k1l2m3n4o5p6"
down_revision = "j0k1l2m3n4o5"
branch_labels = None
depends_on = None

# 需要补充 org_id 的表
TABLES = [
    "email_accounts",
    "work_types",
    "work_type_suggestions",
    "customer_suggestions",
]


def upgrade() -> None:
    # 1. 给遗漏的表加 org_id 列
    for table in TABLES:
        op.add_column(table, sa.Column(
            "org_id", sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=True, comment="所属组织"
        ))
        op.create_index(f"ix_{table}_org_id", table, ["org_id"])

    # 2. 修正 contract_number_rules 唯一约束
    op.drop_constraint("uq_contract_number_rule_type", "contract_number_rules", type_="unique")
    op.create_unique_constraint(
        "uq_contract_number_rule_type_org",
        "contract_number_rules",
        ["rule_type", "org_id"],
    )

    # 3. 数据回填
    _backfill_data()


def _backfill_data():
    """为现有数据填充 org_id"""
    conn = op.get_bind()

    # 获取默认组织 ID
    result = conn.execute(sa.text(
        "SELECT id FROM organizations WHERE code = 'default' LIMIT 1"
    ))
    row = result.fetchone()
    if not row:
        return  # 没有默认组织，跳过
    default_org_id = row[0]

    # 填充所有表的 org_id
    for table in TABLES:
        conn.execute(sa.text(f"""
            UPDATE {table} SET org_id = :org_id WHERE org_id IS NULL
        """), {"org_id": default_org_id})


def downgrade() -> None:
    # 1. 恢复 contract_number_rules 唯一约束
    op.drop_constraint("uq_contract_number_rule_type_org", "contract_number_rules", type_="unique")
    op.create_unique_constraint(
        "uq_contract_number_rule_type",
        "contract_number_rules",
        ["rule_type"],
    )

    # 2. 删除 org_id 列
    for table in reversed(TABLES):
        op.drop_index(f"ix_{table}_org_id", table_name=table)
        op.drop_column(table, "org_id")
