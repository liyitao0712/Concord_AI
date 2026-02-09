# app/schemas/purchase_contract.py
# 采购合同数据验证模式

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ==================== 采购明细行 ====================

class PurchaseLineCreate(BaseModel):
    """创建采购明细行"""
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


class PurchaseLineUpdate(BaseModel):
    """更新采购明细行"""
    product_id: Optional[str] = Field(None, description="产品 ID")
    product_name: Optional[str] = Field(None, max_length=200, description="品名")
    specifications: Optional[str] = Field(None, description="规格")
    unit: Optional[str] = Field(None, max_length=50, description="单位")
    quantity: Optional[float] = Field(None, gt=0, description="数量")
    unit_price: Optional[float] = Field(None, ge=0, description="单价")
    discount_rate: Optional[float] = Field(None, ge=0, le=100, description="折扣率 %")
    discount_amount: Optional[float] = Field(None, ge=0, description="折扣金额")
    tax_rate: Optional[float] = Field(None, ge=0, le=100, description="税率 %")
    tax_amount: Optional[float] = Field(None, ge=0, description="税额")
    amount: Optional[float] = Field(None, ge=0, description="金额")
    amount_with_tax: Optional[float] = Field(None, ge=0, description="含税金额")
    hs_code: Optional[str] = Field(None, max_length=20, description="HS 编码")
    notes: Optional[str] = Field(None, description="备注")


class PurchaseLineResponse(BaseModel):
    """采购明细行响应"""
    id: str
    purchase_contract_id: str
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
    received_quantity: float = 0
    hs_code: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 采购合同 ====================

PURCHASE_CONTRACT_STATUSES = {
    "draft", "pending_approval", "approved", "signed",
    "in_progress", "partial_received", "received", "completed", "cancelled"
}


class PurchaseContractCreate(BaseModel):
    """创建采购合同"""
    contract_no: Optional[str] = Field(None, max_length=50, description="合同编号（不填则自动生成）")
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
    contract_date: Optional[date] = Field(None, description="合同日期")
    delivery_date: Optional[date] = Field(None, description="交货日期")
    expected_arrival_date: Optional[date] = Field(None, description="预计到货日期")
    expiry_date: Optional[date] = Field(None, description="有效期")
    status: str = Field(default="draft", description="状态")
    notes: Optional[str] = Field(None, description="备注")
    attachments: List[dict] = Field(default=[], description="附件列表")
    tags: List[str] = Field(default=[], description="标签列表")
    lines: List[PurchaseLineCreate] = Field(default=[], description="明细行列表")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in PURCHASE_CONTRACT_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(PURCHASE_CONTRACT_STATUSES))}")
        return v


class PurchaseContractUpdate(BaseModel):
    """更新采购合同"""
    contract_no: Optional[str] = Field(None, max_length=50, description="合同编号")
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
    contract_date: Optional[date] = Field(None, description="合同日期")
    delivery_date: Optional[date] = Field(None, description="交货日期")
    expected_arrival_date: Optional[date] = Field(None, description="预计到货日期")
    expiry_date: Optional[date] = Field(None, description="有效期")
    notes: Optional[str] = Field(None, description="备注")
    attachments: Optional[List[dict]] = Field(None, description="附件列表")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class PurchaseContractResponse(BaseModel):
    """采购合同响应"""
    id: str
    contract_no: str
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
    contract_date: Optional[date] = None
    delivery_date: Optional[date] = None
    expected_arrival_date: Optional[date] = None
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


class PurchaseContractListResponse(BaseModel):
    """采购合同列表响应"""
    items: List[PurchaseContractResponse]
    total: int


class PurchaseContractDetailResponse(PurchaseContractResponse):
    """采购合同详情响应（含明细行）"""
    lines: List[PurchaseLineResponse] = Field(default=[], description="明细行列表")


class PurchaseContractStatusUpdate(BaseModel):
    """变更采购合同状态"""
    status: str = Field(..., description="新状态")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in PURCHASE_CONTRACT_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(PURCHASE_CONTRACT_STATUSES))}")
        return v
