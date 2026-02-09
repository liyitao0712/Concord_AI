# TradeTerm 贸易术语

## 概述

TradeTerm 是贸易术语（Incoterms）参考数据实体（只读系统预设），包含 Incoterms 2020 和历史版本。用于客户/供应商表单的贸易术语下拉选择。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| code | String(10) | 术语代码（唯一，如 FOB、CIF） |
| name_en | String(200) | 英文全称 |
| name_zh | String(200) | 中文名称 |
| version | String(20) | Incoterms 版本 (2020/2010/2000) |
| transport_mode | String(50) | 运输方式 (any/sea) |
| description_zh | Text | 中文详细说明 |
| description_en | Text | 英文详细说明 |
| risk_transfer | String(500) | 风险转移点描述 |
| is_current | Boolean | 是否当前版本（2020 为 true） |
| sort_order | Integer | 排序顺序 |
| created_at | DateTime | 创建时间 |

## 预设数据

### Incoterms 2020（is_current = true）

| Code | 中文名称 | 运输方式 |
|------|---------|---------|
| EXW | 工厂交货 | any |
| FCA | 货交承运人 | any |
| CPT | 运费付至 | any |
| CIP | 运费保险费付至 | any |
| DAP | 目的地交货 | any |
| DPU | 卸货地交货 | any |
| DDP | 完税后交货 | any |
| FAS | 船边交货 | sea |
| FOB | 船上交货 | sea |
| CFR | 成本加运费 | sea |
| CIF | 成本保险费加运费 | sea |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/trade-terms | 术语列表（分页、搜索、版本筛选） |
| GET | /admin/trade-terms/{id} | 术语详情 |

## 相关文件

- Model: `backend/app/models/trade_term.py`
- Schema: `backend/app/schemas/trade_term.py`
- API: `backend/app/api/trade_terms_ref.py`
- Migration: `backend/alembic/versions/e4f5g6h7i8j9_add_trade_terms_table.py`
- Frontend: `frontend/src/app/admin/trade-terms/page.tsx`
