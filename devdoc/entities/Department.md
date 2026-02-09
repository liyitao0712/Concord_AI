# Department 部门

## 概述

Department 是部门实体，通过 parent_id 自引用构成部门树结构。用于数据权限中的 department_tree 范围查询。UserDepartment 是用户与部门的多对多关联表，支持一个用户关联多个部门。

## 数据模型

### 基本信息

| 项目 | 值 |
|------|------|
| 数据表名 | `departments` / `user_departments` |
| 模型路径 | `backend/app/models/department.py`, `backend/app/models/user_department.py` |

### Department（部门）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| org_id | String(36) | 所属组织（外键 → organizations） |
| parent_id | String(36) | 上级部门 ID（自引用外键，NULL 表示顶级部门） |
| name | String(100) | 部门名称 |
| code | String(50) | 部门编码 |
| sort_order | Integer | 排序，默认 0 |
| is_active | Boolean | 是否启用，默认 true |
| created_at | DateTime | 创建时间（server_default） |
| updated_at | DateTime | 更新时间 |

### UserDepartment（用户-部门关联）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| user_id | String(36) | 用户 ID（外键 → users，级联删除） |
| department_id | String(36) | 部门 ID（外键 → departments，级联删除） |
| is_primary | Boolean | 是否主部门，默认 false |

## 关系

### Department
- **Organization**: 多对一，每个部门属于一个组织
- **Department (parent)**: 自引用多对一，构成部门树
- **Department (children)**: 自引用一对多，包含下级部门

### UserDepartment
- **User**: 多对一，关联用户
- **Department**: 多对一，关联部门

## 设计说明

- **树形结构**: 通过 parent_id 自引用构成无限层级部门树
- **主部门**: UserDepartment.is_primary 标记主部门，新建数据时默认归属到主部门
- **多部门支持**: 用户可关联多个部门（如副总同时管理销售部和采购部）
- **数据权限**: 部门树用于 RoleDataScope 中 department_tree 类型的数据范围查询

## 相关文件

- Model: `backend/app/models/department.py`, `backend/app/models/user_department.py`
- 权限设计: `devdoc/PERMISSION_SYSTEM_DESIGN.md`
