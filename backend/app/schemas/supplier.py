# app/schemas/supplier.py
# 供应商管理数据验证模式
#
# 功能说明：
# 1. 定义供应商和联系人 API 请求和响应的数据格式
# 2. 自动验证输入数据
# 3. 自动生成 API 文档
#
# 命名规范：
# - XxxCreate: 创建数据时使用（不包含 id）
# - XxxUpdate: 更新数据时使用（所有字段可选）
# - XxxResponse: 返回数据时使用

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ==================== Supplier 相关 ====================

class SupplierCreate(BaseModel):
    """
    创建供应商请求模式

    用于 POST /admin/suppliers 接口
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="公司全称",
    )
    short_name: Optional[str] = Field(
        None,
        max_length=100,
        description="简称/别名",
    )
    country: Optional[str] = Field(None, max_length=100, description="国家")
    region: Optional[str] = Field(None, max_length=100, description="地区/洲")
    industry: Optional[str] = Field(None, max_length=100, description="行业")
    company_size: Optional[str] = Field(None, max_length=50, description="公司规模")
    main_products: Optional[str] = Field(None, description="主营产品描述")
    supplier_level: str = Field(
        default="normal",
        description="供应商等级: potential/normal/important/strategic",
    )
    email: Optional[str] = Field(None, max_length=200, description="公司主邮箱")
    phone: Optional[str] = Field(None, max_length=50, description="公司电话")
    website: Optional[str] = Field(None, max_length=300, description="公司网站")
    address: Optional[str] = Field(None, description="公司地址")
    payment_terms: Optional[str] = Field(None, max_length=100, description="付款条款")
    shipping_terms: Optional[str] = Field(None, max_length=50, description="贸易术语")
    is_active: bool = Field(default=True, description="是否活跃")
    source: Optional[str] = Field(None, max_length=50, description="供应商来源")
    notes: Optional[str] = Field(None, description="备注")
    tags: List[str] = Field(default=[], description="标签列表")

    @field_validator("supplier_level")
    @classmethod
    def validate_supplier_level(cls, v: str) -> str:
        allowed = {"potential", "normal", "important", "strategic"}
        if v not in allowed:
            raise ValueError(f"供应商等级必须是: {', '.join(sorted(allowed))}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v and "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v


class SupplierUpdate(BaseModel):
    """
    更新供应商请求模式

    用于 PUT /admin/suppliers/{id} 接口
    所有字段都是可选的
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="公司全称")
    short_name: Optional[str] = Field(None, max_length=100, description="简称/别名")
    country: Optional[str] = Field(None, max_length=100, description="国家")
    region: Optional[str] = Field(None, max_length=100, description="地区/洲")
    industry: Optional[str] = Field(None, max_length=100, description="行业")
    company_size: Optional[str] = Field(None, max_length=50, description="公司规模")
    main_products: Optional[str] = Field(None, description="主营产品描述")
    supplier_level: Optional[str] = Field(None, description="供应商等级")
    email: Optional[str] = Field(None, max_length=200, description="公司主邮箱")
    phone: Optional[str] = Field(None, max_length=50, description="公司电话")
    website: Optional[str] = Field(None, max_length=300, description="公司网站")
    address: Optional[str] = Field(None, description="公司地址")
    payment_terms: Optional[str] = Field(None, max_length=100, description="付款条款")
    shipping_terms: Optional[str] = Field(None, max_length=50, description="贸易术语")
    is_active: Optional[bool] = Field(None, description="是否活跃")
    source: Optional[str] = Field(None, max_length=50, description="供应商来源")
    notes: Optional[str] = Field(None, description="备注")
    tags: Optional[List[str]] = Field(None, description="标签列表")

    @field_validator("supplier_level")
    @classmethod
    def validate_supplier_level(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"potential", "normal", "important", "strategic"}
            if v not in allowed:
                raise ValueError(f"供应商等级必须是: {', '.join(sorted(allowed))}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v and "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v


class SupplierResponse(BaseModel):
    """供应商响应模式"""
    id: str = Field(..., description="供应商 ID")
    name: str = Field(..., description="公司全称")
    short_name: Optional[str] = Field(None, description="简称/别名")
    country: Optional[str] = Field(None, description="国家")
    region: Optional[str] = Field(None, description="地区/洲")
    industry: Optional[str] = Field(None, description="行业")
    company_size: Optional[str] = Field(None, description="公司规模")
    main_products: Optional[str] = Field(None, description="主营产品描述")
    supplier_level: str = Field(..., description="供应商等级")
    email: Optional[str] = Field(None, description="公司主邮箱")
    phone: Optional[str] = Field(None, description="公司电话")
    website: Optional[str] = Field(None, description="公司网站")
    address: Optional[str] = Field(None, description="公司地址")
    payment_terms: Optional[str] = Field(None, description="付款条款")
    shipping_terms: Optional[str] = Field(None, description="贸易术语")
    is_active: bool = Field(..., description="是否活跃")
    source: Optional[str] = Field(None, description="供应商来源")
    notes: Optional[str] = Field(None, description="备注")
    tags: List[str] = Field(default=[], description="标签列表")
    contact_count: int = Field(default=0, description="联系人数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class SupplierListResponse(BaseModel):
    """供应商列表响应"""
    items: List[SupplierResponse]
    total: int


# ==================== SupplierContact 相关 ====================

class SupplierContactCreate(BaseModel):
    """
    创建供应商联系人请求模式

    用于 POST /admin/supplier-contacts 接口
    """
    supplier_id: str = Field(..., description="所属供应商 ID")
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="联系人姓名",
    )
    title: Optional[str] = Field(None, max_length=100, description="职位/头衔")
    department: Optional[str] = Field(None, max_length=100, description="部门")
    email: Optional[str] = Field(None, max_length=200, description="邮箱")
    phone: Optional[str] = Field(None, max_length=50, description="座机")
    mobile: Optional[str] = Field(None, max_length=50, description="手机")
    social_media: dict = Field(default={}, description="社交媒体")
    is_primary: bool = Field(default=False, description="是否主联系人")
    is_active: bool = Field(default=True, description="是否活跃")
    notes: Optional[str] = Field(None, description="备注")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v and "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v


class SupplierContactUpdate(BaseModel):
    """
    更新供应商联系人请求模式

    用于 PUT /admin/supplier-contacts/{id} 接口
    所有字段都是可选的，supplier_id 不可更新
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="联系人姓名")
    title: Optional[str] = Field(None, max_length=100, description="职位/头衔")
    department: Optional[str] = Field(None, max_length=100, description="部门")
    email: Optional[str] = Field(None, max_length=200, description="邮箱")
    phone: Optional[str] = Field(None, max_length=50, description="座机")
    mobile: Optional[str] = Field(None, max_length=50, description="手机")
    social_media: Optional[dict] = Field(None, description="社交媒体")
    is_primary: Optional[bool] = Field(None, description="是否主联系人")
    is_active: Optional[bool] = Field(None, description="是否活跃")
    notes: Optional[str] = Field(None, description="备注")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v and "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v


class SupplierContactResponse(BaseModel):
    """供应商联系人响应模式"""
    id: str = Field(..., description="联系人 ID")
    supplier_id: str = Field(..., description="所属供应商 ID")
    name: str = Field(..., description="联系人姓名")
    title: Optional[str] = Field(None, description="职位/头衔")
    department: Optional[str] = Field(None, description="部门")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="座机")
    mobile: Optional[str] = Field(None, description="手机")
    social_media: dict = Field(default={}, description="社交媒体")
    is_primary: bool = Field(..., description="是否主联系人")
    is_active: bool = Field(..., description="是否活跃")
    notes: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class SupplierContactListResponse(BaseModel):
    """供应商联系人列表响应"""
    items: List[SupplierContactResponse]
    total: int


# ==================== 供应商详情（含联系人）====================

class SupplierDetailResponse(SupplierResponse):
    """供应商详情响应（包含联系人列表）"""
    contacts: List[SupplierContactResponse] = Field(default=[], description="联系人列表")
