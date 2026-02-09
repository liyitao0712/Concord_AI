# app/schemas/supplier_rfq.py
# 供应商询价单数据验证模式

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ==================== 明细行 ====================

class SupplierRFQLineCreate(BaseModel):
    """创建供应商询价明细行"""
    product_id: str = Field(..., description="产品 ID")
    product_name: str = Field(..., min_length=1, max_length=200, description="品名")
    specifications: Optional[str] = Field(None, description="规格")
    unit: str = Field(..., min_length=1, max_length=50, description="单位")
    quantity: float = Field(..., gt=0, description="数量")
    unit_price: float = Field(..., ge=0, description="单价")
    discount_rate: float = Field(default=0, ge=0, le=100, description="折扣率 %")
    discount_amount: float = Field(default=0, ge=0, description="折扣金额")
    tax_rate: float = Field(default=0, ge=0, le=100, description="税率 %")
    tax_amount: float = Field(default=0, ge=0, description="税额")
    amount: float = Field(default=0, ge=0, description="金额")
    amount_with_tax: float = Field(default=0, ge=0, description="含税金额")
    hs_code: Optional[str] = Field(None, max_length=20, description="HS 编码")
    notes: Optional[str] = Field(None, description="备注")


class SupplierRFQLineResponse(BaseModel):
    """供应商询价明细行响应"""
    id: str
    supplier_rfq_id: str
    line_no: int
    product_id: str
    product_name: str
    specifications: Optional[str] = None
    unit: str
    quantity: float
    unit_price: float
    discount_rate: float = 0
    discount_amount: float = 0
    tax_rate: float = 0
    tax_amount: float = 0
    amount: float = 0
    amount_with_tax: float = 0
    hs_code: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 供应商询价单 ====================

SUPPLIER_RFQ_STATUSES = {"draft", "sent", "replied", "quoted", "closed", "cancelled"}


class SupplierRFQCreate(BaseModel):
    """创建供应商询价单"""
    rfq_no: Optional[str] = Field(None, max_length=50, description="询价单编号（不填则自动生成）")
    supplier_id: str = Field(..., description="供应商 ID")
    contact_id: Optional[str] = Field(None, description="供应商联系人 ID")
    trade_term: Optional[str] = Field(None, max_length=20, description="贸易术语")
    payment_method: Optional[str] = Field(None, max_length=50, description="付款方式")
    payment_terms: Optional[str] = Field(None, description="付款条款描述")
    currency: str = Field(default="USD", max_length=10, description="币种")
    exchange_rate: Optional[float] = Field(None, description="汇率")
    subtotal: float = Field(default=0, ge=0, description="小计")
    discount_amount: float = Field(default=0, ge=0, description="整单折扣")
    tax_amount: float = Field(default=0, ge=0, description="税额")
    total_amount: float = Field(default=0, ge=0, description="总金额")
    port_of_loading: Optional[str] = Field(None, max_length=100, description="装运港")
    port_of_discharge: Optional[str] = Field(None, max_length=100, description="目的港")
    rfq_date: Optional[date] = Field(None, description="询价日期")
    deadline: Optional[date] = Field(None, description="回复截止日期")
    expiry_date: Optional[date] = Field(None, description="有效期")
    status: str = Field(default="draft", description="状态")
    notes: Optional[str] = Field(None, description="备注")
    attachments: List[dict] = Field(default=[], description="附件列表")
    tags: List[str] = Field(default=[], description="标签列表")
    lines: List[SupplierRFQLineCreate] = Field(default=[], description="明细行列表")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in SUPPLIER_RFQ_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(SUPPLIER_RFQ_STATUSES))}")
        return v


class SupplierRFQUpdate(BaseModel):
    """更新供应商询价单"""
    rfq_no: Optional[str] = Field(None, max_length=50, description="询价单编号")
    supplier_id: Optional[str] = Field(None, description="供应商 ID")
    contact_id: Optional[str] = Field(None, description="供应商联系人 ID")
    trade_term: Optional[str] = Field(None, max_length=20, description="贸易术语")
    payment_method: Optional[str] = Field(None, max_length=50, description="付款方式")
    payment_terms: Optional[str] = Field(None, description="付款条款描述")
    currency: Optional[str] = Field(None, max_length=10, description="币种")
    exchange_rate: Optional[float] = Field(None, description="汇率")
    subtotal: Optional[float] = Field(None, ge=0, description="小计")
    discount_amount: Optional[float] = Field(None, ge=0, description="整单折扣")
    tax_amount: Optional[float] = Field(None, ge=0, description="税额")
    total_amount: Optional[float] = Field(None, ge=0, description="总金额")
    port_of_loading: Optional[str] = Field(None, max_length=100, description="装运港")
    port_of_discharge: Optional[str] = Field(None, max_length=100, description="目的港")
    rfq_date: Optional[date] = Field(None, description="询价日期")
    deadline: Optional[date] = Field(None, description="回复截止日期")
    expiry_date: Optional[date] = Field(None, description="有效期")
    notes: Optional[str] = Field(None, description="备注")
    attachments: Optional[List[dict]] = Field(None, description="附件列表")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class SupplierRFQResponse(BaseModel):
    """供应商询价单响应"""
    id: str
    rfq_no: str
    supplier_id: str
    contact_id: Optional[str] = None
    trade_term: Optional[str] = None
    payment_method: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: str = "USD"
    exchange_rate: Optional[float] = None
    subtotal: float = 0
    discount_amount: float = 0
    tax_amount: float = 0
    total_amount: float = 0
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    rfq_date: Optional[date] = None
    deadline: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    notes: Optional[str] = None
    attachments: List[dict] = []
    tags: List[str] = []
    created_by: Optional[str] = None
    supplier_name: Optional[str] = Field(None, description="供应商名称")
    line_count: int = Field(default=0, description="明细行数量")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupplierRFQListResponse(BaseModel):
    """供应商询价单列表响应"""
    items: List[SupplierRFQResponse]
    total: int


class SupplierRFQDetailResponse(SupplierRFQResponse):
    """供应商询价单详情响应（含明细行）"""
    lines: List[SupplierRFQLineResponse] = Field(default=[], description="明细行列表")


class SupplierRFQStatusUpdate(BaseModel):
    """变更供应商询价单状态"""
    status: str = Field(..., description="新状态")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in SUPPLIER_RFQ_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(SUPPLIER_RFQ_STATUSES))}")
        return v
