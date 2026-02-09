"""添加权限系统：组织、部门、角色、权限表 + 改造 users 表

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-02-09

新增表：
- organizations: 组织/公司
- departments: 部门（树形）
- roles: 角色
- permissions: 功能权限定义
- role_permissions: 角色-权限关联
- role_data_scopes: 角色-数据范围
- user_departments: 用户-部门关联

改造：
- users: 新增 org_id, department_id, role_id, supervisor_id, is_super_admin

数据迁移：
- 创建默认组织
- 创建系统预置角色（超管、公司管理员、主管、业务员）
- 预置功能权限定义
- 现有 admin 用户标记为 is_super_admin
"""

from alembic import op
import sqlalchemy as sa
from uuid import uuid4


revision = "i9j0k1l2m3n4"
down_revision = "h8i9j0k1l2m3"
branch_labels = None
depends_on = None

# 预生成 ID，方便数据迁移引用
DEFAULT_ORG_ID = str(uuid4())
ROLE_SUPER_ADMIN_ID = str(uuid4())
ROLE_ORG_ADMIN_ID = str(uuid4())
ROLE_MANAGER_ID = str(uuid4())
ROLE_STAFF_ID = str(uuid4())

# 系统支持的资源和操作
RESOURCES = [
    ("customer", "客户"),
    ("supplier", "供应商"),
    ("contact", "联系人"),
    ("supplier_contact", "供应商联系人"),
    ("product", "产品"),
    ("category", "品类"),
    ("warehouse", "仓库"),
    ("inventory", "库存"),
    ("purchase_contract", "采购合同"),
    ("sales_contract", "销售合同"),
    ("inbound_order", "入仓单"),
    ("outbound_order", "出仓单"),
    ("client_rfq", "客户询价"),
    ("quotation", "报价单"),
    ("supplier_rfq", "供应商询价"),
    ("supplier_quotation", "供应商报价"),
    ("project", "项目"),
    ("task", "任务"),
    ("email", "邮件"),
    ("email_account", "邮箱配置"),
    ("worker", "Worker 配置"),
    ("work_type", "工作类型"),
    ("user", "用户管理"),
    ("setting", "系统设置"),
    ("llm_model", "LLM 模型"),
    ("prompt", "提示词"),
    ("agent", "Agent 配置"),
]

ACTIONS = ["read", "create", "update", "delete"]


def upgrade() -> None:
    # ==================== 1. 创建 organizations 表 ====================
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, comment="组织名称"),
        sa.Column("code", sa.String(50), unique=True, nullable=False, comment="组织编码"),
        sa.Column("logo", sa.String(255), nullable=True, comment="Logo 文件 key"),
        sa.Column("contact_info", sa.Text(), nullable=True, comment="联系信息（JSON）"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", comment="是否启用"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ==================== 2. 创建 departments 表 ====================
    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, comment="所属组织"),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("departments.id"), nullable=True, comment="上级部门"),
        sa.Column("name", sa.String(100), nullable=False, comment="部门名称"),
        sa.Column("code", sa.String(50), nullable=True, comment="部门编码"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="排序"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", comment="是否启用"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_departments_org_id", "departments", ["org_id"])
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"])

    # ==================== 3. 创建 roles 表 ====================
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True, comment="所属组织（NULL=系统级）"),
        sa.Column("name", sa.String(50), nullable=False, comment="角色名称"),
        sa.Column("code", sa.String(50), nullable=False, comment="角色编码"),
        sa.Column("description", sa.Text(), nullable=True, comment="角色描述"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false", comment="系统预置"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", comment="是否启用"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_roles_org_id", "roles", ["org_id"])

    # ==================== 4. 创建 permissions 表 ====================
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource", sa.String(50), nullable=False, comment="资源标识"),
        sa.Column("action", sa.String(20), nullable=False, comment="操作类型"),
        sa.Column("description", sa.String(200), nullable=True, comment="权限描述"),
    )
    op.create_index("ix_permissions_resource", "permissions", ["resource"])

    # ==================== 5. 创建 role_permissions 表 ====================
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    # ==================== 6. 创建 role_data_scopes 表 ====================
    op.create_table(
        "role_data_scopes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource", sa.String(50), nullable=False, comment="资源标识"),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="self", comment="数据范围"),
        sa.Column("custom_dept_ids", sa.JSON(), nullable=True, comment="自定义部门列表"),
    )
    op.create_index("ix_role_data_scopes_role_id", "role_data_scopes", ["role_id"])

    # ==================== 7. 创建 user_departments 表 ====================
    op.create_table(
        "user_departments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false", comment="是否主部门"),
    )
    op.create_index("ix_user_departments_user_id", "user_departments", ["user_id"])
    op.create_index("ix_user_departments_department_id", "user_departments", ["department_id"])

    # ==================== 8. 改造 users 表 ====================
    op.add_column("users", sa.Column(
        "org_id", sa.String(36), sa.ForeignKey("organizations.id"),
        nullable=True, comment="所属组织"
    ))
    op.add_column("users", sa.Column(
        "department_id", sa.String(36), sa.ForeignKey("departments.id"),
        nullable=True, comment="主部门"
    ))
    op.add_column("users", sa.Column(
        "role_id", sa.String(36), sa.ForeignKey("roles.id"),
        nullable=True, comment="角色"
    ))
    op.add_column("users", sa.Column(
        "supervisor_id", sa.String(36), sa.ForeignKey("users.id"),
        nullable=True, comment="直属上级"
    ))
    op.add_column("users", sa.Column(
        "is_super_admin", sa.Boolean(),
        nullable=False, server_default="false", comment="是否超级管理员"
    ))
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.create_index("ix_users_role_id", "users", ["role_id"])

    # ==================== 9. 数据迁移 ====================
    _seed_data()


def _seed_data():
    """填充初始数据"""
    conn = op.get_bind()

    # 9.1 创建默认组织
    conn.execute(
        sa.text("""
            INSERT INTO organizations (id, name, code, is_active, created_at)
            VALUES (:id, :name, :code, true, NOW())
        """),
        {"id": DEFAULT_ORG_ID, "name": "默认组织", "code": "default"}
    )

    # 9.2 创建系统预置角色
    roles = [
        (ROLE_SUPER_ADMIN_ID, None, "超级管理员", "super_admin", "系统级超级管理员，跨组织全权限", True),
        (ROLE_ORG_ADMIN_ID, DEFAULT_ORG_ID, "公司管理员", "org_admin", "管理本公司所有数据和用户", True),
        (ROLE_MANAGER_ID, DEFAULT_ORG_ID, "主管", "manager", "查看本部门及下级数据", True),
        (ROLE_STAFF_ID, DEFAULT_ORG_ID, "业务员", "staff", "只能查看和管理自己的数据", True),
    ]
    for rid, org_id, name, code, desc, is_system in roles:
        conn.execute(
            sa.text("""
                INSERT INTO roles (id, org_id, name, code, description, is_system, is_active, created_at)
                VALUES (:id, :org_id, :name, :code, :desc, :is_system, true, NOW())
            """),
            {"id": rid, "org_id": org_id, "name": name, "code": code, "desc": desc, "is_system": is_system}
        )

    # 9.3 预置功能权限
    permission_ids = {}
    for resource, res_desc in RESOURCES:
        for action in ACTIONS:
            pid = str(uuid4())
            action_desc = {"read": "查看", "create": "新建", "update": "编辑", "delete": "删除"}[action]
            conn.execute(
                sa.text("""
                    INSERT INTO permissions (id, resource, action, description)
                    VALUES (:id, :resource, :action, :desc)
                """),
                {"id": pid, "resource": resource, "action": action, "desc": f"{action_desc}{res_desc}"}
            )
            permission_ids[(resource, action)] = pid

    # 9.4 公司管理员 = 全部权限
    for (resource, action), pid in permission_ids.items():
        conn.execute(
            sa.text("""
                INSERT INTO role_permissions (id, role_id, permission_id)
                VALUES (:id, :role_id, :pid)
            """),
            {"id": str(uuid4()), "role_id": ROLE_ORG_ADMIN_ID, "pid": pid}
        )

    # 9.5 主管 = 全部业务读写权限，无系统管理
    system_resources = {"user", "setting", "llm_model", "prompt", "agent", "worker", "email_account"}
    for (resource, action), pid in permission_ids.items():
        if resource not in system_resources:
            conn.execute(
                sa.text("""
                    INSERT INTO role_permissions (id, role_id, permission_id)
                    VALUES (:id, :role_id, :pid)
                """),
                {"id": str(uuid4()), "role_id": ROLE_MANAGER_ID, "pid": pid}
            )

    # 9.6 业务员 = 业务数据读写，无删除，无系统管理
    for (resource, action), pid in permission_ids.items():
        if resource not in system_resources and action != "delete":
            conn.execute(
                sa.text("""
                    INSERT INTO role_permissions (id, role_id, permission_id)
                    VALUES (:id, :role_id, :pid)
                """),
                {"id": str(uuid4()), "role_id": ROLE_STAFF_ID, "pid": pid}
            )
    # 业务员也需要读取权限（补充删除之外也允许 read）
    # 上面已包含 read，这里额外给 email 的 read
    email_read_pid = permission_ids.get(("email", "read"))
    if email_read_pid:
        conn.execute(
            sa.text("""
                INSERT INTO role_permissions (id, role_id, permission_id)
                VALUES (:id, :role_id, :pid)
            """),
            {"id": str(uuid4()), "role_id": ROLE_STAFF_ID, "pid": email_read_pid}
        )

    # 9.7 预置数据范围
    # 公司管理员：所有资源 = organization
    # 主管：业务资源 = department_tree
    # 业务员：业务资源 = self
    business_resources = [r for r, _ in RESOURCES if r not in system_resources]

    for resource in business_resources:
        # org_admin: organization
        conn.execute(
            sa.text("""
                INSERT INTO role_data_scopes (id, role_id, resource, scope_type)
                VALUES (:id, :role_id, :resource, :scope_type)
            """),
            {"id": str(uuid4()), "role_id": ROLE_ORG_ADMIN_ID, "resource": resource, "scope_type": "organization"}
        )
        # manager: department_tree
        conn.execute(
            sa.text("""
                INSERT INTO role_data_scopes (id, role_id, resource, scope_type)
                VALUES (:id, :role_id, :resource, :scope_type)
            """),
            {"id": str(uuid4()), "role_id": ROLE_MANAGER_ID, "resource": resource, "scope_type": "department_tree"}
        )
        # staff: self
        conn.execute(
            sa.text("""
                INSERT INTO role_data_scopes (id, role_id, resource, scope_type)
                VALUES (:id, :role_id, :resource, :scope_type)
            """),
            {"id": str(uuid4()), "role_id": ROLE_STAFF_ID, "resource": resource, "scope_type": "self"}
        )

    # 9.8 现有 admin 用户标记为 is_super_admin，并归入默认组织
    conn.execute(
        sa.text("""
            UPDATE users SET is_super_admin = true, org_id = :org_id
            WHERE role = 'admin'
        """),
        {"org_id": DEFAULT_ORG_ID}
    )
    # 普通用户也归入默认组织
    conn.execute(
        sa.text("""
            UPDATE users SET org_id = :org_id
            WHERE org_id IS NULL
        """),
        {"org_id": DEFAULT_ORG_ID}
    )


def downgrade() -> None:
    # 删除 users 表新增字段
    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_column("users", "is_super_admin")
    op.drop_column("users", "supervisor_id")
    op.drop_column("users", "role_id")
    op.drop_column("users", "department_id")
    op.drop_column("users", "org_id")

    # 删除新建的表（反序）
    op.drop_table("user_departments")
    op.drop_table("role_data_scopes")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("departments")
    op.drop_table("organizations")
