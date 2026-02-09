"""给业务模型添加 org_id/owner_id/owner_dept_id 字段

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-02-09

为所有业务表添加权限相关字段：
- org_id: 组织隔离
- owner_id: 负责人（数据归属）
- owner_dept_id: 负责人部门（冗余，避免 JOIN）

现有数据填充：
- org_id → 默认组织
- owner_id → 第一个 admin 用户
- owner_dept_id → NULL（待用户手动分配部门后自动填充）
"""

from alembic import op
import sqlalchemy as sa


revision = "j0k1l2m3n4o5"
down_revision = "i9j0k1l2m3n4"
branch_labels = None
depends_on = None

# 需要 org_id + owner_id + owner_dept_id 的表
FULL_OWNERSHIP_TABLES = [
    "customers",
    "contacts",
    "suppliers",
    "supplier_contacts",
    "products",
    "purchase_contracts",
    "sales_contracts",
    "inbound_orders",
    "outbound_orders",
    "client_rfqs",
    "quotations",
    "supplier_rfqs",
    "supplier_quotations",
    "projects",
    "tasks",
]

# 只需要 org_id 的表
ORG_ONLY_TABLES = [
    "categories",
    "warehouses",
    "inventories",
    "contract_number_rules",
    "email_analyses",
    "product_suppliers",
]


def upgrade() -> None:
    # projects 表已在 f6g7h8i9j0k1 中创建了 owner_id 列和索引，需跳过
    SKIP_OWNER_ID = {"projects"}

    # 1. 给所有需要完整权限字段的表加列
    for table in FULL_OWNERSHIP_TABLES:
        op.add_column(table, sa.Column(
            "org_id", sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=True, comment="所属组织"
        ))
        if table not in SKIP_OWNER_ID:
            op.add_column(table, sa.Column(
                "owner_id", sa.String(36),
                sa.ForeignKey("users.id"),
                nullable=True, comment="负责人"
            ))
        op.add_column(table, sa.Column(
            "owner_dept_id", sa.String(36),
            sa.ForeignKey("departments.id"),
            nullable=True, comment="负责人部门"
        ))
        op.create_index(f"ix_{table}_org_id", table, ["org_id"])
        if table not in SKIP_OWNER_ID:
            op.create_index(f"ix_{table}_owner_id", table, ["owner_id"])
        op.create_index(f"ix_{table}_owner_dept_id", table, ["owner_dept_id"])

    # 2. 给只需要 org_id 的表加列
    for table in ORG_ONLY_TABLES:
        op.add_column(table, sa.Column(
            "org_id", sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=True, comment="所属组织"
        ))
        op.create_index(f"ix_{table}_org_id", table, ["org_id"])

    # 3. 数据迁移：现有数据填充默认组织和负责人
    _backfill_data()


def _backfill_data():
    """为现有数据填充 org_id 和 owner_id"""
    conn = op.get_bind()

    # 获取默认组织 ID
    result = conn.execute(sa.text(
        "SELECT id FROM organizations WHERE code = 'default' LIMIT 1"
    ))
    row = result.fetchone()
    if not row:
        return  # 没有默认组织，跳过（不应该发生）
    default_org_id = row[0]

    # 获取第一个 admin 用户作为默认 owner
    result = conn.execute(sa.text(
        "SELECT id FROM users WHERE is_super_admin = true LIMIT 1"
    ))
    row = result.fetchone()
    default_owner_id = row[0] if row else None

    # 查询哪些表有 created_by 列（PostgreSQL 事务内不能用 try/except 探测列是否存在）
    result = conn.execute(sa.text("""
        SELECT table_name FROM information_schema.columns
        WHERE column_name = 'created_by'
          AND table_name = ANY(:tables)
    """), {"tables": FULL_OWNERSHIP_TABLES})
    tables_with_created_by = {row[0] for row in result}

    # 填充完整权限字段的表
    for table in FULL_OWNERSHIP_TABLES:
        conn.execute(sa.text(f"""
            UPDATE {table} SET org_id = :org_id WHERE org_id IS NULL
        """), {"org_id": default_org_id})

        if default_owner_id:
            if table in tables_with_created_by:
                # 用 created_by 作为 owner_id
                conn.execute(sa.text(f"""
                    UPDATE {table}
                    SET owner_id = COALESCE(created_by, :default_owner)
                    WHERE owner_id IS NULL
                """), {"default_owner": default_owner_id})
            else:
                # 没有 created_by 列，直接用默认 admin
                conn.execute(sa.text(f"""
                    UPDATE {table} SET owner_id = :owner_id WHERE owner_id IS NULL
                """), {"owner_id": default_owner_id})

    # 填充仅 org_id 的表
    for table in ORG_ONLY_TABLES:
        conn.execute(sa.text(f"""
            UPDATE {table} SET org_id = :org_id WHERE org_id IS NULL
        """), {"org_id": default_org_id})


def downgrade() -> None:
    # projects 表的 owner_id 属于 f6g7h8i9j0k1，不在这里删除
    SKIP_OWNER_ID = {"projects"}

    # 删除完整权限字段
    for table in reversed(FULL_OWNERSHIP_TABLES):
        op.drop_index(f"ix_{table}_owner_dept_id", table_name=table)
        if table not in SKIP_OWNER_ID:
            op.drop_index(f"ix_{table}_owner_id", table_name=table)
        op.drop_index(f"ix_{table}_org_id", table_name=table)
        op.drop_column(table, "owner_dept_id")
        if table not in SKIP_OWNER_ID:
            op.drop_column(table, "owner_id")
        op.drop_column(table, "org_id")

    # 删除仅 org_id 字段
    for table in reversed(ORG_ONLY_TABLES):
        op.drop_index(f"ix_{table}_org_id", table_name=table)
        op.drop_column(table, "org_id")
