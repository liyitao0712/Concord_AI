# User 用户

## 概述

User 是系统的用户实体，支持管理员和普通用户角色。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| email | String(255) | 邮箱（唯一） |
| name | String(100) | 用户名称 |
| password_hash | String(255) | 密码哈希 |
| is_active | Boolean | 是否启用 |
| is_admin | Boolean | 是否管理员 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| last_login_at | DateTime | 最后登录时间 |

## 认证方式

- JWT Token（Access Token + Refresh Token）
- Access Token 有效期：15 分钟
- Refresh Token 有效期：7 天

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /auth/login | 登录 |
| POST | /auth/refresh | 刷新 Token |
| GET | /auth/me | 获取当前用户 |
| POST | /admin/users | 创建用户 |
| GET | /admin/users | 用户列表 |

## 创建管理员

```bash
cd backend
source venv/bin/activate
python ../scripts/create_admin.py
```

## 相关文件

- Model: `backend/app/models/user.py`
- Schema: `backend/app/schemas/user.py`
- API: `backend/app/api/auth.py`
- Security: `backend/app/core/security.py`
