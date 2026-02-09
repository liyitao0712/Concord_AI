# Category 品类

## 概述

Category 是产品品类实体，支持 Parent-Child 层级结构。品类用于组织产品分类，并关联增值税率和退税率等外贸信息。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| code | String(50) | 品类编码（唯一，层级格式 "01"、"01-01"） |
| name | String(200) | 中文名称 |
| name_en | String(200) | 英文名称 |
| description | Text | 描述 |
| parent_id | String(36) | 父级品类 ID（自引用外键） |
| vat_rate | Numeric(5,2) | 增值税率 (%) |
| tax_rebate_rate | Numeric(5,2) | 出口退税率 (%) |
| image_key | String(500) | 品类图片存储路径 |
| image_storage_type | String(10) | 存储类型 (oss/local) |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 层级结构

```
Level 1 (顶级)          Level 2 (子级)
─────────────────────────────────────
01 五金工具       ──→   01-01 手动工具
                  ──→   01-02 电动工具
02 建筑材料       ──→   02-01 水泥
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/categories | 品类列表 |
| GET | /admin/categories/tree | 树形结构 |
| POST | /admin/categories | 创建品类 |
| PUT | /admin/categories/{id} | 更新品类 |
| DELETE | /admin/categories/{id} | 删除品类 |
| POST | /admin/categories/{id}/image | 上传品类图片 |

## 相关文件

- Model: `backend/app/models/category.py`
- API: `backend/app/api/categories.py`
- Frontend: `frontend/src/app/admin/categories/page.tsx`
