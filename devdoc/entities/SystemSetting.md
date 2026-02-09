# SystemSetting 系统设置

## 概述

SystemSetting 是键值对形式的系统设置实体，支持按分类管理，敏感数据标记，用于存储全局配置项。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| key | String(100) | 设置键名（主键） |
| value | Text | 设置值 |
| category | String(50) | 分类（索引） |
| description | Text | 描述 |
| is_sensitive | Boolean | 是否敏感数据（API 返回时脱敏） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/settings | 获取所有设置（敏感值脱敏） |
| PUT | /admin/settings/{key} | 更新设置 |

## 相关文件

- Model: `backend/app/models/settings.py`
- API: `backend/app/api/settings.py`
