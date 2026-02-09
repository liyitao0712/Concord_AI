# 权限系统设计方案

> 创建时间：2026-02-09
> 状态：Phase 1 + Phase 2 + Phase 3 已完成，待执行 Phase 4（前端适配）

---

## 一、现状诊断

| 方面 | 当前状态 | 问题 |
|------|---------|------|
| **认证** | JWT (access + refresh token)，已实现 | 没问题，可以复用 |
| **角色** | 只有 `admin` / `user` 两种 | 太粗粒度 |
| **多租户** | 完全没有，无 `org_id`/`tenant_id` | 需要从零开始 |
| **数据隔离** | 所有 admin 能看所有数据 | 完全没有行级隔离 |
| **所有权** | 11个单据模型有 `created_by`，但从不用于查询过滤 | 有基础但未启用 |
| **核心主数据** | Customer、Supplier、Product 等无任何归属字段 | 需要加字段 |

### 系统规模

| 层 | 数量 |
|----|------|
| 后端 API 文件 | 40 个 |
| API 端点总数 | 242 个 |
| 后端模型文件 | ~30 个 |
| Agent 文件 | 8 个 |
| Celery 任务文件 | 2 个 |
| Service 文件 | 5 个 |
| 前端页面 | 28 个 |
| 前端 API 客户端函数 | 100+ 个 |

### 已有 `created_by` 字段的模型（11个）

PurchaseContract, SalesContract, Quotation, ClientRFQ, SupplierQuotation, SupplierRFQ, InboundOrder, OutboundOrder, Project, Task, Prompt

### 无任何归属字段的核心模型（7个）

Customer, Supplier, Product, Category, Warehouse, Contact, SupplierContact

---

## 二、设计目标

1. **多公司隔离**：4-5 个子公司各自独立，数据互不可见
2. **动态部门**：部门可增减，树形结构
3. **动态角色**：角色可由管理员自定义，权限可配置
4. **行级数据隔离**：业务员只看自己的数据，主管看全部门
5. **上级看下属**：管理层可跨部门查看数据
6. **前端可配置**：管理员在前端定义每个角色的功能权限和数据范围
7. **开源友好**：单公司部署或多公司部署均可

---

## 三、架构设计：功能权限 + 数据权限

```
┌─────────────────────────────────────────────────┐
│                   权限系统                        │
│                                                   │
│   功能权限（能做什么）     数据权限（能看什么）       │
│   Role ←→ Permission      Role ←→ DataScope       │
│   "采购员能访问采购合同"    "采购员只看自己的数据"     │
│                            "采购主管看本部门的"       │
└─────────────────────────────────────────────────┘
```

### 不使用 Casbin 的理由

- 80% 的需求是**行级数据过滤**（SQL WHERE），Casbin 管不到这一层
- 角色和权限虽然动态，但结构清晰，自建 RBAC 表完全够用
- 前端管理界面直接 CRUD 自己的表比翻译 Casbin policy 更直观
- 部门树向下穿透是自定义逻辑，Casbin 不支持
- 少一个依赖，调试更透明

---

## 四、数据模型设计

### 4.1 组织模型

```python
class Organization(Base):
    """组织/公司"""
    __tablename__ = "organizations"

    id: str            # UUID
    name: str          # "XX贸易有限公司"
    code: str          # "company_a"，唯一标识
    logo: str          # logo 文件 key
    contact_info: JSON # 联系信息
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 4.2 部门模型（树形结构）

```python
class Department(Base):
    """部门（树形自引用）"""
    __tablename__ = "departments"

    id: str
    org_id: str        # FK → Organization
    parent_id: str     # FK → Department（自引用，NULL 表示顶级）
    name: str          # "华东销售组"
    code: str          # "sales_east"
    sort_order: int    # 排序
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 4.3 角色模型（按公司独立）

```python
class Role(Base):
    """角色（每个公司独立定义）"""
    __tablename__ = "roles"

    id: str
    org_id: str        # FK → Organization（NULL 表示系统级角色，如超管）
    name: str          # "销售主管"
    code: str          # "sales_manager"
    description: str
    is_system: bool    # 系统预置角色不可删除
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 4.4 功能权限

```python
class Permission(Base):
    """功能权限定义（全局，系统预置）"""
    __tablename__ = "permissions"

    id: str
    resource: str      # "customer", "purchase_contract", "sales_contract"
    action: str        # "read", "create", "update", "delete"
    description: str   # "查看客户"

class RolePermission(Base):
    """角色-功能权限关联"""
    __tablename__ = "role_permissions"

    role_id: str       # FK → Role
    permission_id: str # FK → Permission
```

管理员前端呈现为角色 × 资源 × 操作的勾选矩阵：

```
              客户    供应商    采购合同    销售合同
            查改删增  查改删增   查改删增    查改删增
销售主管     ✓✓✓✓    ✓···     ····       ✓✓✓✓
采购员       ✓···    ✓✓✓✓     ✓✓✓✓       ····
财务        ✓···    ✓···     ✓···       ✓···
```

### 4.5 数据权限（核心）

```python
class RoleDataScope(Base):
    """角色-数据范围配置（按资源维度）"""
    __tablename__ = "role_data_scopes"

    id: str
    role_id: str        # FK → Role
    resource: str       # "customer", "purchase_contract" ...
    scope_type: str     # 数据范围类型（见下表）
    custom_dept_ids: JSON  # scope_type="custom" 时，指定的部门ID列表
```

**scope_type 取值：**

| 值 | 含义 | SQL 效果 |
|----|------|---------|
| `self` | 仅本人 | `WHERE owner_id = :user_id` |
| `department` | 本部门 | `WHERE owner_dept_id = :user_dept_id` |
| `department_tree` | 本部门及所有下级部门 | `WHERE owner_dept_id IN (:dept_and_children)` |
| `organization` | 全公司 | `WHERE org_id = :org_id` |
| `all` | 全部（超管） | 无过滤 |
| `custom` | 自定义部门列表 | `WHERE owner_dept_id IN (:custom_list)` |

管理员前端呈现为下拉选择：

```
角色：销售主管
┌──────────┬─────────────────┐
│ 资源      │ 数据范围         │
├──────────┼─────────────────┤
│ 客户      │ [本部门及下级 ▾]  │
│ 销售合同   │ [本部门及下级 ▾]  │
│ 采购合同   │ [仅本人 ▾]       │
│ 供应商    │ [全公司 ▾]       │
└──────────┴─────────────────┘
```

### 4.6 用户-部门关联（多对多，解决跨部门问题）

```python
class UserDepartment(Base):
    """用户-部门关联（支持一人多部门）"""
    __tablename__ = "user_departments"

    user_id: str          # FK → User
    department_id: str    # FK → Department
    is_primary: bool      # 主部门（新建数据时默认归属）
```

**跨部门场景示例：**

副总经理需要同时看销售部和采购部数据：

| 用户 | 部门 | 是否主部门 |
|------|------|:--------:|
| 副总 | 总经理办公室 | 是 |
| 副总 | 销售部 | 否 |
| 副总 | 采购部 | 否 |

配合角色 scope_type = `department_tree`，副总可看到：总经理办公室 + 销售部全部子部门 + 采购部全部子部门。

### 4.7 User 模型改造

```python
class User(Base):
    """用户（改造）"""
    __tablename__ = "users"

    id: str
    org_id: str           # FK → Organization（新增）
    department_id: str    # FK → Department（新增，主部门，冗余自 UserDepartment）
    role_id: str          # FK → Role（新增，替代原来的 role 字符串）
    supervisor_id: str    # FK → User（新增，直属上级，可选）
    email: str
    name: str
    password_hash: str
    is_active: bool
    is_super_admin: bool  # 新增，超管标记（不依赖角色表）
    created_at: datetime
    updated_at: datetime
```

### 4.8 业务模型统一加字段

所有业务模型加三个字段：

```python
# 示例：Customer 模型
class Customer(Base):
    # ... 原有字段 ...
    org_id: str          # 公司隔离（必填）
    owner_id: str        # 负责人/归属业务员（FK → User）
    owner_dept_id: str   # 负责人所在部门（冗余，避免 JOIN）
```

`owner_dept_id` 是冗余字段但**非常关键**——没有它，每次列表查询都要 JOIN users 表取部门 ID，性能差。

---

## 五、完整 ER 关系图

```
Organization ──1:N──▶ Department (tree: parent_id)
     │                     │
     │                     │ M:N (UserDepartment)
     │                     │
     ├──1:N──▶ Role ──M:N──▶ Permission
     │           │
     │           ├──1:N──▶ RoleDataScope (per resource)
     │           │
     └──1:N──▶ User
                 ├── department_id → Department（主部门）
                 ├── role_id → Role
                 ├── supervisor_id → User（上级）
                 │
                 └── owns ──▶ Customer, Contract, Order...
                              (via org_id + owner_id + owner_dept_id)
```

---

## 六、核心实现代码

### 6.1 数据过滤函数（最核心）

```python
# backend/app/core/data_scope.py

from sqlalchemy import select
from backend.app.models.department import Department

class DataScope:
    """数据访问范围"""
    user: User
    org_id: str | None
    is_super_admin: bool
    permissions: dict[str, set[str]]     # resource → {actions}
    data_scopes: dict[str, RoleDataScope]  # resource → scope config
    user_dept_ids: list[str]              # 用户关联的所有部门ID

def get_data_scope(user: User = Depends(get_current_user)) -> DataScope:
    """FastAPI 依赖注入：获取当前用户的数据范围"""
    # 从缓存或数据库加载角色权限和数据范围配置
    ...

async def apply_data_scope(
    query,
    model,
    resource: str,
    scope: DataScope,
    db: AsyncSession
):
    """给查询自动加上组织和归属过滤"""

    # 超管看所有
    if scope.is_super_admin:
        return query

    # 公司隔离（永远生效）
    query = query.where(model.org_id == scope.org_id)

    # 获取该资源的数据范围配置
    ds = scope.data_scopes.get(resource)
    if not ds:
        # 没有配置 = 无权限，返回空
        query = query.where(False)
        return query

    if ds.scope_type == "self":
        query = query.where(model.owner_id == scope.user.id)

    elif ds.scope_type == "department":
        query = query.where(model.owner_dept_id.in_(scope.user_dept_ids))

    elif ds.scope_type == "department_tree":
        # 用户关联的所有部门 + 各自的子部门
        all_dept_ids = set()
        for dept_id in scope.user_dept_ids:
            subtree = await get_department_subtree(db, dept_id)
            all_dept_ids.update(subtree)
        query = query.where(model.owner_dept_id.in_(all_dept_ids))

    elif ds.scope_type == "organization":
        pass  # org_id 已经过滤了

    elif ds.scope_type == "custom":
        query = query.where(model.owner_dept_id.in_(ds.custom_dept_ids))

    elif ds.scope_type == "all":
        pass  # 无额外过滤

    return query


async def get_department_subtree(db: AsyncSession, dept_id: str) -> list[str]:
    """获取部门及所有下级部门的 ID 列表（递归）"""
    # 可以用 CTE 递归查询，也可以用物化路径优化
    result = [dept_id]
    children = await db.execute(
        select(Department.id).where(Department.parent_id == dept_id)
    )
    for child_id in children.scalars():
        result.extend(await get_department_subtree(db, child_id))
    return result
```

### 6.2 功能权限检查

```python
def check_permission(scope: DataScope, resource: str, action: str) -> bool:
    """检查用户是否有某资源的某操作权限"""
    if scope.is_super_admin:
        return True
    actions = scope.permissions.get(resource, set())
    return action in actions

def require_permission(resource: str, action: str):
    """FastAPI 依赖：要求特定权限"""
    def checker(scope: DataScope = Depends(get_data_scope)):
        if not check_permission(scope, resource, action):
            raise HTTPException(403, detail="无权限执行此操作")
        return scope
    return checker
```

### 6.3 API 端点改造示例

```python
# ===== 改造前 =====
@router.get("")
async def list_customers(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await session.execute(select(Customer))
    return result.scalars().all()

# ===== 改造后 =====
@router.get("")
async def list_customers(
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("customer", "read")),
):
    query = select(Customer)
    query = await apply_data_scope(query, Customer, "customer", scope, session)
    result = await session.execute(query)
    return result.scalars().all()

@router.post("")
async def create_customer(
    data: CustomerCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("customer", "create")),
):
    customer = Customer(
        **data.dict(),
        org_id=scope.org_id,                    # 自动填充
        owner_id=scope.user.id,                 # 自动填充
        owner_dept_id=scope.user.department_id,  # 自动填充
    )
    session.add(customer)
    await session.commit()
```

---

## 七、数据访问场景验证

### 场景 1：销售员小王

- 关联部门：`[华东销售组(主)]`
- 角色：销售员，客户 scope_type = `self`
- 效果：只看自己负责的客户
- SQL：`WHERE org_id='company_a' AND owner_id='xiaowang'`

### 场景 2：销售主管老李

- 关联部门：`[销售部(主)]`
- 角色：销售主管，客户 scope_type = `department_tree`
- 效果：看到销售部 + 华东组 + 华南组所有人的客户
- SQL：`WHERE org_id='company_a' AND owner_dept_id IN ('sales', 'sales_east', 'sales_south')`

### 场景 3：副总经理

- 关联部门：`[总经理办公室(主), 销售部, 采购部]`
- 角色：副总，scope_type = `department_tree`
- 效果：看到销售部全部 + 采购部全部 + 各自下级部门
- SQL：`WHERE org_id='company_a' AND owner_dept_id IN ('gm_office', 'sales', 'sales_east', 'sales_south', 'purchase')`

### 场景 4：CEO / 公司管理员

- 关联部门：`[总经理办公室(主)]`
- 角色：总经理/org_admin，scope_type = `organization`
- 效果：看到全公司所有数据
- SQL：`WHERE org_id='company_a'`

### 场景 5：超级管理员

- is_super_admin = True
- 效果：看到所有公司所有数据
- SQL：无 WHERE 过滤

### 场景 6：临时跨部门协作

- 给某个采购员额外关联销售部（UserDepartment 加一条记录）
- 不用改角色、不用改权限配置
- 撤销时移除关联即可

---

## 八、模型改动清单

### 需加 `org_id` + `owner_id` + `owner_dept_id`（核心业务，20个）

| 模型 | 文件 |
|------|------|
| Customer | `backend/app/models/customer.py` |
| Supplier | `backend/app/models/supplier.py` |
| Contact | `backend/app/models/customer.py` |
| SupplierContact | `backend/app/models/supplier.py` |
| PurchaseContract | `backend/app/models/purchase_contract.py` |
| PurchaseLine | 跟随 PurchaseContract |
| SalesContract | `backend/app/models/sales_contract.py` |
| SalesLine | 跟随 SalesContract |
| Quotation | `backend/app/models/quotation.py` |
| ClientRFQ | `backend/app/models/client_rfq.py` |
| SupplierRFQ | `backend/app/models/supplier_rfq.py` |
| SupplierQuotation | `backend/app/models/supplier_quotation.py` |
| InboundOrder | `backend/app/models/inbound_order.py` |
| OutboundOrder | `backend/app/models/outbound_order.py` |
| Project | `backend/app/models/project.py` |
| Task | `backend/app/models/task.py` |
| EmailAnalysis | `backend/app/models/email_analysis.py` |
| Product | `backend/app/models/product.py` |
| Category | `backend/app/models/category.py` |
| Warehouse | `backend/app/models/warehouse.py` |

### 需加 `org_id`（配置/关联数据）

| 模型 | 文件 |
|------|------|
| Inventory | `backend/app/models/inventory.py` |
| ProductSupplier | `backend/app/models/product.py` |
| ContractNumberRule | `backend/app/models/contract_number_rule.py` |
| EmailAccount (如有) | 邮箱配置 |
| ChatSession | 聊天会话 |

### 不需要改（全局参考数据）

Country, TradeTerm, PaymentMethod, LLMModelConfig, Prompt（或可选加 org_id）

---

## 九、后端改动量详细清单

### API 文件改造（~35 个）

| 文件 | 端点数 | 改动内容 |
|------|:------:|---------|
| `customers.py` | 12 | 查询加 data_scope，创建加 org_id/owner_id |
| `suppliers.py` | 11 | 同上 |
| `purchase_contracts.py` | 7 | 同上 |
| `sales_contracts.py` | 7 | 同上 |
| `quotations.py` | 7 | 同上 |
| `client_rfqs.py` | 7 | 同上 |
| `supplier_rfqs.py` | 7 | 同上 |
| `supplier_quotations.py` | 7 | 同上 |
| `inbound_orders.py` | 7 | 同上 |
| `outbound_orders.py` | 7 | 同上 |
| `projects.py` | 9 | 同上 |
| `tasks.py` | 5 | 同上 |
| `progress.py` | 3 | 同上 |
| `products.py` | 8 | 同上 |
| `categories.py` | 7 | 同上 |
| `warehouses.py` | 5 | 同上 |
| `inventories.py` | 2 | 同上 |
| `emails.py` | 11 | 查询加 org_id 过滤 |
| `email_accounts.py` | 9 | 同上 |
| `chat.py` | 7 | session 隔离 |
| `admin.py` | 8 | 用户管理适配新角色 |
| `settings.py` | 12 | 部分配置按 org 隔离 |
| `workers.py` | 11 | worker 按 org 隔离 |
| `work_types.py` | 10 | 同上 |
| `agents.py` | 8 | 传递 org_id 到 agent |
| `prompts.py` | 7 | 可选按 org 隔离 |
| `llm_models.py` | 7 | 可选按 org 隔离 |
| `contract_numbers.py` | 3 | 按 org 隔离编号规则 |
| `project_suggestions.py` | 4 | 同上 |
| `auth.py` | 4 | 登录返回完整角色信息 |
| `countries.py` | 2 | 不改（全局数据） |
| `trade_terms_ref.py` | 2 | 不改 |
| `payment_methods_ref.py` | 2 | 不改 |

### Agent 改造（5 个）

| Agent | 复杂度 | 改动 |
|-------|--------|------|
| BaseAgent | 中 | AgentState 加 org_id, user_id |
| EmailSummarizerAgent | 小 | input_data 传 org_id |
| ChatAgent | 小 | Redis key 按 org 隔离 |
| CustomerExtractorAgent | 中 | 查询加 org_id 过滤 |
| WorkTypeAnalyzerAgent | 中 | 查询加 org_id 过滤 |

### Celery 任务改造（2 个）

| 任务 | 复杂度 | 改动 |
|------|--------|------|
| email.py | 大 | poll/process 加 org_id |
| ai_lookup.py | 中 | 验证 customer 归属 |

### Service 改造（3 个）

| Service | 复杂度 | 改动 |
|---------|--------|------|
| email_account_service | 中 | 删除验证 org_id |
| email_worker_service | 中 | 按 org 过滤账号 |
| contract_number | 小 | 按 org 隔离编号序列 |

---

## 十、前端改动量详细清单

### 基础改造

| 文件 | 改动内容 |
|------|---------|
| `contexts/AuthContext.tsx` | user 加 org_id, role, department, permissions |
| `lib/api.ts` | 新增组织/部门/角色 API 模块 |
| `app/admin/layout.tsx` | 角色判断从 isAdmin 改为基于功能权限 |
| `lib/navigation.ts` | 菜单项加 requiredPermission，动态显示/隐藏 |

### 新增页面（3 个）

| 页面 | 说明 |
|------|------|
| 组织管理 `/admin/organizations` | 超管用，CRUD 公司 |
| 部门管理 `/admin/departments` | 树形结构增删改拖拽 |
| 角色管理 `/admin/roles` | 功能权限矩阵 + 数据范围下拉 |

### 改造用户管理页

- 加部门选择（树形下拉）
- 加角色选择
- 加上级选择
- 加关联部门多选

### 现有 28 个页面改造

每个页面的改动：
- 创建表单：自动带 org_id、owner_id（后端处理，前端不感知）
- 列表页：可能加"负责人"列显示（manager 及以上角色才显示）
- 部分页面：根据功能权限隐藏创建/编辑/删除按钮

### 角色管理页 UI（最复杂的新页面）

```
┌─ 角色管理 ─────────────────────────────────────────┐
│                                                      │
│  角色名称：[销售主管        ]                         │
│                                                      │
│  ┌─ 功能权限 ──────────────────────────────────────┐ │
│  │          查看  新建  编辑  删除                   │ │
│  │  客户     ☑    ☑    ☑    ☐                      │ │
│  │  供应商   ☑    ☐    ☐    ☐                      │ │
│  │  销售合同  ☑    ☑    ☑    ☑                      │ │
│  │  采购合同  ☐    ☐    ☐    ☐                      │ │
│  └──────────────────────────────────────────────────┘ │
│                                                      │
│  ┌─ 数据范围 ──────────────────────────────────────┐ │
│  │  客户     [本部门及下级 ▾]                        │ │
│  │  销售合同  [本部门及下级 ▾]                        │ │
│  │  供应商   [全公司 ▾]                              │ │
│  └──────────────────────────────────────────────────┘ │
│                                                      │
│                           [保存]  [取消]              │
└──────────────────────────────────────────────────────┘
```

---

## 十一、实施计划

### Phase 1：地基（~2-3天）

**目标：** 建立组织/部门/角色数据结构，User 改造，不改现有业务逻辑

**改动内容：**
1. 新建模型：Organization, Department, Role, Permission, RolePermission, RoleDataScope, UserDepartment
2. 改造 User 模型：加 org_id, department_id, role_id, supervisor_id, is_super_admin
3. 数据库 migration：创建新表 + 改造 users 表
4. 改造 security.py：JWT 加 org_id，新增 DataScope 依赖注入
5. 改造 auth API：登录返回完整角色信息
6. 数据迁移脚本：创建默认组织、默认角色，现有用户归入

**验证标准：** 登录后能拿到 org_id、role、department 信息，现有功能不受影响

### Phase 2：后端数据隔离（~3-4天）

**目标：** 所有业务数据加上 org_id/owner_id，API 加上数据过滤

**改动内容：**
1. ~20 个业务模型加 org_id + owner_id + owner_dept_id 字段
2. 数据库 migration + 数据填充（默认 org_id 和 owner_id）
3. 新增 `apply_data_scope` 核心过滤函数
4. 新增 `check_permission` + `require_permission` 功能权限检查
5. ~35 个 API 文件改造：查询加过滤，创建自动填充归属
6. Schema 改造：返回值加 owner_name 等

**验证标准：** staff 登录只看自己数据，manager 看本部门，org_admin 看全公司

### Phase 3：Agent + 任务改造（~1-2天）

**目标：** 后台异步流程遵循数据隔离

**改动内容：**
1. BaseAgent 的 AgentState 加 org_id, user_id
2. CustomerExtractor、WorkTypeAnalyzer 查询加 org_id 过滤
3. Celery email 任务加 org_id 参数
4. ai_lookup 任务加归属验证
5. Redis chat context key 按 org 隔离
6. celery_app.py 任务注册加 org_id

**验证标准：** 邮件轮询、AI 分析、客户提取只操作本组织数据

### Phase 4：前端适配（~3-4天）

**Phase 4a - 基础适配（1-2天）：**
1. AuthContext 加完整角色/权限信息
2. layout + navigation 按权限动态显示菜单
3. 现有 28 个页面表单适配（创建时后端自动带 org_id）
4. 列表页加"负责人"列显示
5. 按钮级权限控制（无编辑权限则隐藏编辑按钮）

**Phase 4b - 管理页面（1-2天）：**
1. 新增组织管理页（超管用）
2. 新增部门管理页（树形拖拽）
3. 新增角色管理页（权限矩阵勾选 + 数据范围下拉）
4. 改造用户管理页（部门/角色/上级选择）

**验证标准：** 不同角色登录看到不同菜单，数据范围正确

---

## 十二、总工作量估算

| Phase | 文件数 | 估计时间 | 优先级 |
|-------|:------:|---------|--------|
| Phase 1 地基 | ~10 | 2-3 天 | 最高 |
| Phase 2 后端隔离 | ~55 | 3-4 天 | 最高 |
| Phase 3 Agent/任务 | ~10 | 1-2 天 | 高 |
| Phase 4 前端 | ~35 | 3-4 天 | 高 |
| **总计** | **~110** | **~10-13 天** | - |

Phase 1 + 2 是关键路径，做完后系统即具备完整数据隔离能力。
Phase 3 + 4 可并行或灵活安排。

---

## 十三、注意事项

1. **数据迁移**：现有数据需要填充 org_id 和 owner_id 默认值，migration 要带 default
2. **向后兼容**：Phase 1 完成后现有功能不能broken，新字段先 nullable
3. **性能**：`owner_dept_id` 冗余字段必须加，避免列表查询 JOIN users
4. **部门树查询**：考虑用物化路径（materialized path）优化递归查询
5. **缓存**：用户权限信息应缓存（Redis），角色配置变更时清除
6. **超管标记**：`is_super_admin` 放在 User 上而非依赖角色表，因为超管是系统级概念
7. **开源适配**：单公司部署时只创建一个 Organization，super_admin = org_admin

---

## 十四、Phase 1 实施记录

> 完成时间：2026-02-09

### 新建文件

| 文件 | 内容 |
|------|------|
| `backend/app/models/organization.py` | Organization 组织模型（id, name, code, logo, contact_info, is_active） |
| `backend/app/models/department.py` | Department 部门模型（树形自引用 parent_id，org_id 关联组织） |
| `backend/app/models/role.py` | Role 角色 + Permission 权限定义 + RolePermission 关联 + RoleDataScope 数据范围 |
| `backend/app/models/user_department.py` | UserDepartment 用户-部门多对多（is_primary 标记主部门） |
| `backend/alembic/versions/i9j0k1l2m3n4_add_permission_system.py` | 完整 migration |

### 改造文件

| 文件 | 改动要点 |
|------|---------|
| `backend/app/models/user.py` | 新增 org_id, department_id, role_id, supervisor_id, is_super_admin；保留旧 role 字段兼容；is_admin 属性改为 `is_super_admin or role=="admin"` |
| `backend/app/core/security.py` | 新增 DataScope 数据类；新增 get_data_scope（加载角色权限+数据范围+关联部门）；新增 check_permission / require_permission（功能权限检查）；新增 apply_data_scope（行级数据过滤核心函数）；新增 get_department_subtree（递归 CTE 查部门子树） |
| `backend/app/api/auth.py` | `/me` 接口改为返回 UserMeResponse，包含 org_name, department_name, role_name, permissions 列表, data_scopes 列表 |
| `backend/app/schemas/user.py` | UserResponse 新增 org_id, department_id, role_id, supervisor_id, is_super_admin；新增 UserMeResponse（附带权限上下文） |
| `backend/app/models/__init__.py` | 注册 Organization, Department, Role, Permission, RolePermission, RoleDataScope, UserDepartment |

### Migration 预置数据

- **默认组织**：name="默认组织"，code="default"
- **4 个系统角色**：super_admin, org_admin, manager, staff（is_system=true）
- **108 条功能权限**：27 资源 × 4 操作（read/create/update/delete）
- **角色权限分配**：
  - org_admin = 全部 108 条
  - manager = 全部业务权限（排除 user/setting/llm_model/prompt/agent/worker/email_account）
  - staff = 业务读写（排除 delete + 系统管理）
- **数据范围预置**：
  - org_admin: 所有业务资源 scope_type=organization
  - manager: 所有业务资源 scope_type=department_tree
  - staff: 所有业务资源 scope_type=self
- **用户迁移**：现有 admin 用户 → is_super_admin=true + org_id=默认组织；普通用户 → org_id=默认组织

### 向后兼容验证

- `get_current_admin_user` 不变，依赖 `user.is_admin` 属性 → 返回 `is_super_admin or role=="admin"` ✓
- 现有 admin API（用户管理等）全部正常 ✓
- 前端 AuthContext 的 `isAdmin = user?.role === 'admin'` 仍可用 ✓
- 所有新字段 nullable，不影响现有数据 ✓

### 下一步：Phase 2

执行 `alembic upgrade head` 后，开始 Phase 2：
1. ~20 个业务模型加 org_id + owner_id + owner_dept_id
2. apply_data_scope 已就绪（security.py），Phase 2 直接在 API 端点中调用
3. 重点改造：customers.py, suppliers.py, 各合同/询价/报价/订单 API

### apply_data_scope 使用方式（Phase 2 参考）

```python
# 改造前
@router.get("")
async def list_customers(
    session=Depends(get_db),
    _=Depends(get_current_admin_user),
):
    query = select(Customer)
    result = await session.execute(query)
    return result.scalars().all()

# 改造后
@router.get("")
async def list_customers(
    session=Depends(get_db),
    scope=Depends(require_permission("customer", "read")),
):
    query = select(Customer)
    query = await apply_data_scope(query, Customer, "customer", scope, session)
    result = await session.execute(query)
    return result.scalars().all()

# 创建时自动填充归属
@router.post("")
async def create_customer(
    data: CustomerCreate,
    session=Depends(get_db),
    scope=Depends(require_permission("customer", "create")),
):
    customer = Customer(
        **data.dict(),
        org_id=scope.org_id,
        owner_id=scope.user.id,
        owner_dept_id=scope.user.department_id,
    )
    session.add(customer)
    await session.commit()
```

---

## 十五、Phase 2 实施记录

> 完成时间：2026-02-09

### 新建文件

| 文件 | 内容 |
|------|------|
| `backend/alembic/versions/j0k1l2m3n4o5_add_ownership_fields.py` | 给 ~21 个业务表添加 org_id/owner_id/owner_dept_id 字段 + 数据回填 |

### 业务模型改造（20 个模型加字段）

**完整权限字段（org_id + owner_id + owner_dept_id）— 14 个表：**

customers, contacts, suppliers, supplier_contacts, products, purchase_contracts, sales_contracts, inbound_orders, outbound_orders, client_rfqs, quotations, supplier_rfqs, supplier_quotations, projects, tasks

**仅 org_id — 6 个表：**

categories, warehouses, inventories, contract_number_rules, email_analyses, product_suppliers

### API 端点改造（35 个文件，~180 个端点）

#### 业务 API（18 文件）— 使用 require_permission + apply_data_scope

| 文件 | 端点数 | 权限资源 | 改动要点 |
|------|:------:|---------|---------|
| `customers.py` | 12 | customer | 查询加 data_scope，创建加 org_id/owner_id/owner_dept_id |
| `suppliers.py` | 11 | supplier | 同上 |
| `purchase_contracts.py` | 7 | purchase_contract | 同上 |
| `sales_contracts.py` | 7 | sales_contract | 同上 |
| `client_rfqs.py` | 7 | client_rfq | 同上 |
| `quotations.py` | 7 | quotation | 同上 |
| `supplier_rfqs.py` | 7 | supplier_rfq | 同上 |
| `supplier_quotations.py` | 7 | supplier_quotation | 同上 |
| `inbound_orders.py` | 7 | inbound_order | 同上 |
| `outbound_orders.py` | 7 | outbound_order | 同上 |
| `products.py` | 8 | product | 同上 |
| `categories.py` | 7 | category | org_id 过滤 |
| `warehouses.py` | 5 | warehouse | org_id 过滤 |
| `inventories.py` | 2 | inventory | org_id 过滤 |
| `projects.py` | 9 | project | 完整 data_scope |
| `tasks.py` | 5 | task | 完整 data_scope |
| `emails.py` | 11 | email | org_id 过滤 |
| `progress.py` | 3 | project | org_id 过滤 |

#### 系统管理 API（10 文件）— 使用 require_permission（无 data_scope）

| 文件 | 端点数 | 权限资源 | 改动要点 |
|------|:------:|---------|---------|
| `admin.py` | 8 | user | org_id 过滤用户列表，创建用户自动填充 org_id |
| `settings.py` | 12 | setting | read/update 权限 |
| `workers.py` | 12 | worker | read/create/update/delete，移除 router 级依赖 |
| `prompts.py` | 7 | prompt | read/update 权限 |
| `llm_models.py` | 7 | llm_model | read/create/update/delete |
| `email_accounts.py` | 10 | email_account | read/create/update/delete，移除 router 级依赖 |
| `admin_monitor.py` | 4 | setting | read 权限 |
| `work_types.py` | 10 | work_type | read/create/update/delete |
| `contract_numbers.py` | 3 | setting | read/update + org_id 过滤 |
| `agents.py` | 3(admin) | agent | read/update（用户端端点保持 get_current_user） |

#### 参考数据/工具 API（7 文件）— 使用 require_permission（只读）

| 文件 | 端点数 | 权限资源 | 改动要点 |
|------|:------:|---------|---------|
| `trade_terms_ref.py` | 2 | setting | read |
| `payment_methods_ref.py` | 2 | setting | read |
| `countries.py` | 2 | setting | read |
| `tts.py` | 1 | setting | read |
| `upload.py` | 1 | setting | update |
| `customer_suggestions.py` | 4 | customer | 审批时自动填充 org_id/owner_id/owner_dept_id |
| `project_suggestions.py` | 4 | project | 审批时自动填充 org_id/owner_id/owner_dept_id |

#### 不需要改造的 API（4 文件）

| 文件 | 原因 |
|------|------|
| `chat.py` | 使用 get_current_user，会话已按 user_id 隔离 |
| `llm.py` | 使用 get_current_user，工具端点 |
| `health.py` | 无鉴权 |
| `storage.py` | 文件服务，无鉴权 |

### Migration 数据回填策略

- **org_id**：所有表填充为默认组织（`organizations.code = 'default'`）
- **owner_id**：优先用 `created_by` 字段（如果存在），否则用第一个 super_admin 用户
- **owner_dept_id**：设为 NULL，待用户手动分配部门后自动填充

### 向后兼容验证

- 旧 `get_current_admin_user` 仍可用，新系统通过 `require_permission` 替代 ✓
- 所有新字段 nullable，不影响现有数据 ✓
- 前端暂无改动需要，后端完全透明升级 ✓
- super_admin 用户自动拥有所有权限，行为不变 ✓
- 老 admin 用户通过 `check_permission` 向后兼容逻辑获得完整权限 ✓

### 下一步：Phase 3 → 已完成，见第十六节

---

## 十六、Phase 3 实施记录

### 改动范围

Phase 3 目标：让后台异步流程（Agent 分析、Celery 邮件任务、AI 搜索任务）遵守 org 边界。

核心挑战：Agent 是全局单例，不能在实例变量上存 org_id。org_id 必须通过函数参数/状态字典流转。

### 新增 Migration

| Migration | 说明 |
|-----------|------|
| `k1l2m3n4o5p6` | 给 email_accounts/work_types/work_type_suggestions/customer_suggestions 补充 org_id；修正 contract_number_rules 唯一约束为 (rule_type, org_id) |

### Model 改动（4 个文件）

| 文件 | 改动 |
|------|------|
| `models/email_account.py` | 加 `org_id` 列（FK → organizations.id） |
| `models/work_type.py` | WorkType + WorkTypeSuggestion 各加 `org_id` 列 |
| `models/customer_suggestion.py` | 加 `org_id` 列 |
| `models/contract_number_rule.py` | UniqueConstraint 改为 `(rule_type, org_id)` |

### Agent 改动（4 个文件）

| 文件 | 改动 |
|------|------|
| `agents/base.py` | AgentState 加 `org_id`/`user_id` 字段；`run()` 从 input_data 提取并写入 initial_state |
| `agents/work_type_analyzer.py` | `_get_work_types_list()` 加 `WHERE org_id = :org_id OR org_id IS NULL`；`_get_pending_suggestions_list()` 加 `WHERE org_id = :org_id`；`_create_suggestion()` 设 org_id |
| `agents/customer_extractor.py` | `_get_existing_customers_context()` 加 org_id 过滤；`_get_pending_suggestions_context()` 加 org_id 过滤；`_create_suggestion()` 设 org_id |
| `agents/chat_agent.py` | Redis key 改为 `chat:context:{org_id}:{session_id}`；新旧 key 双读兼容（旧 key 24h 自然过期）；`chat()`/`chat_stream()`/`clear_context()` 均加 org_id 参数 |

### Celery/Dispatcher 改动（3 个文件）

| 文件 | 改动 |
|------|------|
| `tasks/email.py` | `poll_email_account` 从 account 取 org_id 传给 `process_email.delay()`；`process_email` 新增 org_id 参数并写入 event.metadata |
| `tasks/ai_lookup.py` | `ai_lookup_new_customer` 新增 org_id 参数；Customer 查询加 org_id 过滤 |
| `messaging/dispatcher.py` | `_classify_intent()` 和 `_classify_parallel()` 的 input_data 加 `org_id` 字段 |

### API/Service 改动（11 个文件）

| 文件 | 改动 |
|------|------|
| `api/chat.py` | `chat()`/`chat_stream()`/`clear_context()` 传 `org_id=current_user.org_id` |
| `api/customers.py` | `ai_lookup_new_customer.delay()` 加 `org_id=scope.org_id` |
| `services/contract_number.py` | `generate_contract_number()` 加 org_id 参数；查询按 org_id 过滤；新建规则设 org_id |
| `storage/email.py` | `EmailAccountConfig` 加 org_id 字段 |
| 8 个 API 文件 | `client_rfqs`/`supplier_quotations`/`inbound_orders`/`supplier_rfqs`/`outbound_orders`/`purchase_contracts`/`sales_contracts`/`quotations` — 每个的 `generate_contract_number()` 调用加 `org_id=scope.org_id` |

### org_id 流转路径

```
EmailAccount.org_id
  → poll_email_account (从 DB 读取)
    → process_email.delay(org_id=...)
      → event.metadata["org_id"] = org_id
        → EventDispatcher.input_data["org_id"]
          → BaseAgent.run() → AgentState["org_id"]
            → WorkTypeAnalyzer 查询过滤
            → CustomerExtractor 查询过滤
            → EmailSummarizer（不查 DB，自动透传）
```

### 向后兼容

- 所有新参数默认 `None`，老任务/老数据照常运行 ✓
- ChatAgent Redis key：双 key 读取（新 key → 旧 key fallback），旧 key 24h 自然过期 ✓
- Agent 查询：`if org_id:` 守卫，None 时不过滤（等同当前行为） ✓
- Celery 队列中的老任务（无 org_id 参数）正常执行，只是不做 org 过滤 ✓

### 下一步：Phase 4（前端适配）

1. 前端登录后获取用户权限列表
2. 根据权限动态渲染菜单/按钮
3. API 调用统一携带 org_id（已由后端 JWT 自动解析，前端无需额外传递）
