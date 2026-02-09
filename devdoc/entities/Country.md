# Country 国家

## 概述

Country 是国家/地区参考数据实体（只读系统预设），包含 ISO 3166-1 标准编码、电话区号、货币信息等。数据通过 Alembic 迁移种子导入。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name_zh | String(100) | 中文简称 |
| name_en | String(100) | 英文简称 |
| full_name_zh | String(200) | 中文全称 |
| full_name_en | String(200) | 英文全称 |
| iso_code_2 | String(2) | ISO 3166-1 alpha-2（唯一） |
| iso_code_3 | String(3) | ISO 3166-1 alpha-3 |
| numeric_code | String(3) | ISO 3166-1 数字代码 |
| phone_code | String(20) | 国际电话区号 |
| currency_name_zh | String(100) | 货币中文名称 |
| currency_name_en | String(100) | 货币英文名称 |
| currency_code | String(3) | 货币代码 (USD/CNY/EUR) |
| created_at | DateTime | 创建时间 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/countries | 国家列表（分页、搜索） |
| GET | /admin/countries/{id} | 国家详情 |

## 相关文件

- Model: `backend/app/models/country.py`
- API: `backend/app/api/countries.py`
- Migration: `backend/alembic/versions/d3e4f5g6h7i8_add_countries_table.py`
