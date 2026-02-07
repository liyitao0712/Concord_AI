# app/schemas/product.py
# 产品管理数据验证模式
#
# 功能说明：
# 1. 定义产品 API 请求和响应的数据格式
# 2. 定义产品-供应商关联的数据格式
# 3. 自动验证输入数据
#
# 命名规范：
# - XxxCreate: 创建数据时使用（不包含 id）
# - XxxUpdate: 更新数据时使用（所有字段可选）
# - XxxResponse: 返回数据时使用

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ==================== Product 相关 ====================

class ProductCreate(BaseModel):
    """
    创建产品请求模式

    用于 POST /admin/products 接口
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="品名",
    )
    category_id: Optional[str] = Field(None, description="所属品类 ID")
    model_number: Optional[str] = Field(None, max_length=100, description="型号")
    specifications: Optional[str] = Field(None, description="规格")
    unit: Optional[str] = Field(None, max_length=50, description="单位，如 PCS/SET/KG")
    moq: Optional[int] = Field(None, ge=0, description="最小起订量")
    reference_price: Optional[float] = Field(None, ge=0, description="参考价格")
    currency: str = Field(default="USD", max_length=10, description="币种")
    hs_code: Optional[str] = Field(None, max_length=20, description="HS 编码")
    origin: Optional[str] = Field(None, max_length=100, description="产地")
    material: Optional[str] = Field(None, max_length=200, description="材质")
    packaging: Optional[str] = Field(None, max_length=200, description="包装方式")
    images: List[str] = Field(default=[], description="产品图片 URL 列表")
    description: Optional[str] = Field(None, description="产品描述")
    tags: List[str] = Field(default=[], description="标签列表")
    status: str = Field(default="active", description="状态: active/inactive/discontinued")
    notes: Optional[str] = Field(None, description="备注")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"active", "inactive", "discontinued"}
        if v not in allowed:
            raise ValueError(f"状态必须是: {', '.join(sorted(allowed))}")
        return v


class ProductUpdate(BaseModel):
    """
    更新产品请求模式

    用于 PUT /admin/products/{id} 接口
    所有字段都是可选的
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="品名")
    category_id: Optional[str] = Field(None, description="所属品类 ID")
    model_number: Optional[str] = Field(None, max_length=100, description="型号")
    specifications: Optional[str] = Field(None, description="规格")
    unit: Optional[str] = Field(None, max_length=50, description="单位")
    moq: Optional[int] = Field(None, ge=0, description="最小起订量")
    reference_price: Optional[float] = Field(None, ge=0, description="参考价格")
    currency: Optional[str] = Field(None, max_length=10, description="币种")
    hs_code: Optional[str] = Field(None, max_length=20, description="HS 编码")
    origin: Optional[str] = Field(None, max_length=100, description="产地")
    material: Optional[str] = Field(None, max_length=200, description="材质")
    packaging: Optional[str] = Field(None, max_length=200, description="包装方式")
    images: Optional[List[str]] = Field(None, description="产品图片 URL 列表")
    description: Optional[str] = Field(None, description="产品描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    status: Optional[str] = Field(None, description="状态")
    notes: Optional[str] = Field(None, description="备注")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"active", "inactive", "discontinued"}
            if v not in allowed:
                raise ValueError(f"状态必须是: {', '.join(sorted(allowed))}")
        return v


class ProductResponse(BaseModel):
    """产品响应模式"""
    id: str = Field(..., description="产品 ID")
    category_id: Optional[str] = Field(None, description="所属品类 ID")
    category_name: Optional[str] = Field(None, description="所属品类名称")
    name: str = Field(..., description="品名")
    model_number: Optional[str] = Field(None, description="型号")
    specifications: Optional[str] = Field(None, description="规格")
    unit: Optional[str] = Field(None, description="单位")
    moq: Optional[int] = Field(None, description="最小起订量")
    reference_price: Optional[float] = Field(None, description="参考价格")
    currency: str = Field(..., description="币种")
    hs_code: Optional[str] = Field(None, description="HS 编码")
    origin: Optional[str] = Field(None, description="产地")
    material: Optional[str] = Field(None, description="材质")
    packaging: Optional[str] = Field(None, description="包装方式")
    images: List[str] = Field(default=[], description="产品图片 URL 列表")
    description: Optional[str] = Field(None, description="产品描述")
    tags: List[str] = Field(default=[], description="标签列表")
    status: str = Field(..., description="状态")
    notes: Optional[str] = Field(None, description="备注")
    supplier_count: int = Field(default=0, description="关联供应商数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """产品列表响应"""
    items: List[ProductResponse]
    total: int


# ==================== ProductSupplier 相关 ====================

class ProductSupplierCreate(BaseModel):
    """
    添加产品-供应商关联

    用于 POST /admin/products/{id}/suppliers 接口
    """
    supplier_id: str = Field(..., description="供应商 ID")
    supply_price: Optional[float] = Field(None, ge=0, description="供应价格")
    currency: str = Field(default="USD", max_length=10, description="币种")
    moq: Optional[int] = Field(None, ge=0, description="最小起订量")
    lead_time: Optional[int] = Field(None, ge=0, description="交期（天）")
    is_primary: bool = Field(default=False, description="是否首选供应商")
    notes: Optional[str] = Field(None, description="备注")


class ProductSupplierUpdate(BaseModel):
    """
    更新产品-供应商关联

    用于 PUT /admin/products/{id}/suppliers/{supplier_id} 接口
    """
    supply_price: Optional[float] = Field(None, ge=0, description="供应价格")
    currency: Optional[str] = Field(None, max_length=10, description="币种")
    moq: Optional[int] = Field(None, ge=0, description="最小起订量")
    lead_time: Optional[int] = Field(None, ge=0, description="交期（天）")
    is_primary: Optional[bool] = Field(None, description="是否首选供应商")
    notes: Optional[str] = Field(None, description="备注")


class ProductSupplierResponse(BaseModel):
    """产品-供应商关联响应"""
    id: str = Field(..., description="关联 ID")
    product_id: str = Field(..., description="产品 ID")
    supplier_id: str = Field(..., description="供应商 ID")
    supplier_name: Optional[str] = Field(None, description="供应商名称")
    supply_price: Optional[float] = Field(None, description="供应价格")
    currency: str = Field(..., description="币种")
    moq: Optional[int] = Field(None, description="最小起订量")
    lead_time: Optional[int] = Field(None, description="交期（天）")
    is_primary: bool = Field(..., description="是否首选供应商")
    notes: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


# ==================== 产品详情（含供应商）====================

class ProductDetailResponse(ProductResponse):
    """产品详情响应（包含关联供应商列表）"""
    suppliers: List[ProductSupplierResponse] = Field(default=[], description="关联供应商列表")
