# Role 角色与权限

## 概述

Role 是角色实体，每个组织可独立定义角色。角色通过 RolePermission 关联功能权限，通过 RoleDataScope 配置数据可见范围。Permission 是全局预置的功能权限定义。三者组合构成完整的 RBAC + 数据权限体系。

## 数据模型

### 基本信息

| 项目 | 值 |
|------|------|
| 数据表名 | `roles` / `permissions` / `role_permissions` / `role_data_scopes` |
| 模型路径 | `backend/app/models/role.py` |

### Role（角色）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| org_id | String(36) | 所属组织（外键 → organizations，NULL = 系统级角色） |
| name | String(50) | 角色名称 |
| code | String(50) | 角色编码 |
| description | Text | 角色描述 |
| is_system | Boolean | 是否系统预置（不可删除），默认 false |
| is_active | Boolean | 是否启用，默认 true |
| created_at | DateTime | 创建时间（server_default） |
| updated_at | DateTime | 更新时间 |

### Permission（功能权限定义）

全局预置，由系统初始化时创建，管理员不直接增删。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| resource | String(50) | 资源标识（如 customer, purchase_contract） |
| action | String(20) | 操作类型: read / create / update / delete |
| description | String(200) | 权限描述 |

### RolePermission（角色-功能权限关联）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| role_id | String(36) | 角色 ID（外键 → roles，级联删除） |
| permission_id | String(36) | 权限 ID（外键 → permissions，级联删除） |

### RoleDataScope（角色-数据范围配置）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| role_id | String(36) | 角色 ID（外键 → roles，级联删除） |
| resource | String(50) | 资源标识（如 customer, purchase_contract） |
| scope_type | String(20) | 数据范围（见下方枚举） |
| custom_dept_ids | JSON | scope_type=custom 时的自定义部门 ID 列表 |

**scope_type 取值**：

| 值 | 说明 |
|------|------|
| self | 仅自己的数据 |
| department | 本部门数据 |
| department_tree | 本部门及下级部门数据 |
| organization | 本组织所有数据 |
| all | 全部数据（超管） |
| custom | 自定义部门范围 |

## 关系

- **Organization**: 多对一，角色可属于某个组织（NULL 表示系统级）
- **RolePermission**: 一对多，角色关联多个功能权限（级联删除）
- **RoleDataScope**: 一对多，角色配置多个资源的数据范围（级联删除）
- **User**: 通过 user.role_id 间接关联用户

## 设计说明

- **RBAC**: 基于角色的访问控制，Permission 定义"能做什么"，RolePermission 关联角色和权限
- **数据权限**: RoleDataScope 定义"能看什么"，控制数据可见范围
- **组织隔离**: 每个组织可独立定义角色，org_id=NULL 的角色为系统级角色（如超管）
- **系统预置**: is_system=true 的角色不可删除，确保基础角色始终存在

## 相关文件

- Model: `backend/app/models/role.py`
- 权限设计: `devdoc/PERMISSION_SYSTEM_DESIGN.md`
