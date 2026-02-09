# Organization 组织

## 概述

Organization 是多租户体系的顶层实体，代表一个公司/组织。每个子公司对应一条记录，所有业务数据通过 org_id 关联到组织，实现公司级数据隔离。组织下包含部门（Department）和角色（Role）。

## 数据模型

### 基本信息

| 项目 | 值 |
|------|------|
| 数据表名 | `organizations` |
| 模型路径 | `backend/app/models/organization.py` |

### Organization（组织）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(100) | 组织名称 |
| code | String(50) | 组织编码（唯一标识） |
| logo | String(255) | Logo 文件 key |
| contact_info | Text | 联系信息（JSON 格式） |
| is_active | Boolean | 是否启用，默认 true |
| created_at | DateTime | 创建时间（server_default） |
| updated_at | DateTime | 更新时间 |

## 关系

- **Department**: 一对多，组织下包含多个部门（selectin 加载）
- **Role**: 一对多，组织下包含多个角色（selectin 加载）
- **User**: 通过 user.org_id 间接关联用户
- **业务数据**: 所有业务单据（客户、合同、询价、项目等）通过 org_id 关联组织

## 设计说明

- **多租户核心**: Organization 是数据隔离的基础，所有业务模型都包含 org_id 字段
- **编码唯一**: code 字段全局唯一，用于组织标识和路由
- **级联体系**: Organization → Department → User，形成组织架构树

## 相关文件

- Model: `backend/app/models/organization.py`
- 权限设计: `devdoc/PERMISSION_SYSTEM_DESIGN.md`
