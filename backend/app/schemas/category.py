# app/schemas/category.py
# 品类管理数据验证模式
#
# 功能说明：
# 1. 定义品类 API 请求和响应的数据格式
# 2. 自动验证输入数据
# 3. 支持树形结构返回
#
# 命名规范：
# - XxxCreate: 创建数据时使用（不包含 id）
# - XxxUpdate: 更新数据时使用（所有字段可选）
# - XxxResponse: 返回数据时使用

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ==================== Category 相关 ====================

class CategoryCreate(BaseModel):
    """
    创建品类请求模式

    用于 POST /admin/categories 接口
    """
    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="品类编码，如 01、01-01",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="品类中文名",
    )
    name_en: Optional[str] = Field(None, max_length=200, description="品类英文名")
    parent_id: Optional[str] = Field(None, description="父品类 ID，不填则为根品类")
    description: Optional[str] = Field(None, description="品类描述")
    vat_rate: Optional[float] = Field(None, ge=0, le=100, description="增值税率（%）")
    tax_rebate_rate: Optional[float] = Field(None, ge=0, le=100, description="退税率（%）")
    image_key: Optional[str] = Field(None, max_length=500, description="图片存储路径 key")
    image_storage_type: Optional[str] = Field(None, max_length=10, description="图片存储类型: oss 或 local")


class CategoryUpdate(BaseModel):
    """
    更新品类请求模式

    用于 PUT /admin/categories/{id} 接口
    所有字段都是可选的
    """
    code: Optional[str] = Field(None, min_length=1, max_length=50, description="品类编码")
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="品类中文名")
    name_en: Optional[str] = Field(None, max_length=200, description="品类英文名")
    parent_id: Optional[str] = Field(None, description="父品类 ID")
    description: Optional[str] = Field(None, description="品类描述")
    vat_rate: Optional[float] = Field(None, ge=0, le=100, description="增值税率（%）")
    tax_rebate_rate: Optional[float] = Field(None, ge=0, le=100, description="退税率（%）")
    image_key: Optional[str] = Field(None, max_length=500, description="图片存储路径 key")
    image_storage_type: Optional[str] = Field(None, max_length=10, description="图片存储类型: oss 或 local")


class CategoryResponse(BaseModel):
    """品类响应模式"""
    id: str = Field(..., description="品类 ID")
    code: str = Field(..., description="品类编码")
    name: str = Field(..., description="品类中文名")
    name_en: Optional[str] = Field(None, description="品类英文名")
    parent_id: Optional[str] = Field(None, description="父品类 ID")
    parent_name: Optional[str] = Field(None, description="父品类名称")
    description: Optional[str] = Field(None, description="品类描述")
    vat_rate: Optional[float] = Field(None, description="增值税率（%）")
    tax_rebate_rate: Optional[float] = Field(None, description="退税率（%）")
    image_url: Optional[str] = Field(None, description="品类图片 URL（签名临时链接）")
    product_count: int = Field(default=0, description="产品数量")
    children_count: int = Field(default=0, description="子品类数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """品类列表响应"""
    items: List[CategoryResponse]
    total: int


class CategoryTreeNode(BaseModel):
    """品类树形节点"""
    id: str
    code: str
    name: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    vat_rate: Optional[float] = None
    tax_rebate_rate: Optional[float] = None
    image_url: Optional[str] = None
    product_count: int = 0
    children: List["CategoryTreeNode"] = []

    class Config:
        from_attributes = True


class CategoryTreeResponse(BaseModel):
    """品类树形结构响应"""
    items: List[CategoryTreeNode]
