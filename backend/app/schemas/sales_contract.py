# app/schemas/sales_contract.py
# 销售合同数据验证模式
#
# 命名规范：
# - XxxCreate: 创建时使用
# - XxxUpdate: 更新时使用（所有字段可选）
# - XxxResponse: 响应时使用

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ==================== 销售明细行 ====================

class SalesLineCreate(BaseModel):
    """创建销售明细行"""
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
    tax_rebate_rate: Optional[float] = Field(None, ge=0, le=100, description="退税率 %")
    amount: float = Field(default=0, ge=0, description="金额")
    amount_with_tax: float = Field(default=0, ge=0, description="含税金额")
    hs_code: Optional[str] = Field(None, max_length=20, description="HS 编码")
    notes: Optional[str] = Field(None, description="备注")


class SalesLineUpdate(BaseModel):
    """更新销售明细行"""
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
    tax_rebate_rate: Optional[float] = Field(None, ge=0, le=100, description="退税率 %")
    amount: Optional[float] = Field(None, ge=0, description="金额")
    amount_with_tax: Optional[float] = Field(None, ge=0, description="含税金额")
    hs_code: Optional[str] = Field(None, max_length=20, description="HS 编码")
    notes: Optional[str] = Field(None, description="备注")


class SalesLineResponse(BaseModel):
    """销售明细行响应"""
    id: str
    sales_contract_id: str
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
    tax_rebate_rate: Optional[float] = None
    amount: float = 0
    amount_with_tax: float = 0
    shipped_quantity: float = 0
    reserved_warehouse_id: Optional[str] = None
    reserved_quantity: float = 0
    hs_code: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 销售合同 ====================

SALES_CONTRACT_STATUSES = {
    "draft", "pending_approval", "approved", "signed",
    "in_progress", "partial_shipped", "shipped", "completed", "cancelled"
}


class SalesContractCreate(BaseModel):
    """创建销售合同"""
    contract_no: Optional[str] = Field(None, max_length=50, description="合同编号（不填则自动生成）")
    customer_id: str = Field(..., description="客户 ID")
    contact_id: Optional[str] = Field(None, description="客户联系人 ID")
    # 贸易信息
    trade_term: Optional[str] = Field(None, max_length=20, description="贸易术语")
    payment_method: Optional[str] = Field(None, max_length=50, description="付款方式")
    payment_terms: Optional[str] = Field(None, description="付款条款描述")
    currency: str = Field(default="USD", max_length=10, description="币种")
    exchange_rate: Optional[float] = Field(None, description="汇率")
    # 财务
    subtotal: float = Field(default=0, ge=0, description="小计")
    discount_amount: float = Field(default=0, ge=0, description="整单折扣")
    tax_amount: float = Field(default=0, ge=0, description="税额")
    total_amount: float = Field(default=0, ge=0, description="总金额")
    commission_rate: Optional[float] = Field(None, ge=0, le=100, description="佣金比例 %")
    commission_amount: Optional[float] = Field(None, ge=0, description="佣金金额")
    # 物流
    port_of_loading: Optional[str] = Field(None, max_length=100, description="装运港")
    port_of_discharge: Optional[str] = Field(None, max_length=100, description="目的港")
    destination: Optional[str] = Field(None, max_length=200, description="最终目的地")
    shipping_marks: Optional[str] = Field(None, description="唛头")
    # 日期
    contract_date: Optional[date] = Field(None, description="合同日期")
    delivery_date: Optional[date] = Field(None, description="交货日期")
    shipping_date: Optional[date] = Field(None, description="装运日期")
    expiry_date: Optional[date] = Field(None, description="有效期")
    # 状态和模式
    status: str = Field(default="draft", description="状态")
    is_zero_stock: bool = Field(default=False, description="是否零库存模式")
    # 其他
    notes: Optional[str] = Field(None, description="备注")
    attachments: List[dict] = Field(default=[], description="附件列表")
    tags: List[str] = Field(default=[], description="标签列表")
    # 明细行（创建合同时可同时传入）
    lines: List[SalesLineCreate] = Field(default=[], description="明细行列表")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in SALES_CONTRACT_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(SALES_CONTRACT_STATUSES))}")
        return v


class SalesContractUpdate(BaseModel):
    """更新销售合同"""
    contract_no: Optional[str] = Field(None, max_length=50, description="合同编号")
    customer_id: Optional[str] = Field(None, description="客户 ID")
    contact_id: Optional[str] = Field(None, description="客户联系人 ID")
    trade_term: Optional[str] = Field(None, max_length=20, description="贸易术语")
    payment_method: Optional[str] = Field(None, max_length=50, description="付款方式")
    payment_terms: Optional[str] = Field(None, description="付款条款描述")
    currency: Optional[str] = Field(None, max_length=10, description="币种")
    exchange_rate: Optional[float] = Field(None, description="汇率")
    subtotal: Optional[float] = Field(None, ge=0, description="小计")
    discount_amount: Optional[float] = Field(None, ge=0, description="整单折扣")
    tax_amount: Optional[float] = Field(None, ge=0, description="税额")
    total_amount: Optional[float] = Field(None, ge=0, description="总金额")
    commission_rate: Optional[float] = Field(None, ge=0, le=100, description="佣金比例 %")
    commission_amount: Optional[float] = Field(None, ge=0, description="佣金金额")
    port_of_loading: Optional[str] = Field(None, max_length=100, description="装运港")
    port_of_discharge: Optional[str] = Field(None, max_length=100, description="目的港")
    destination: Optional[str] = Field(None, max_length=200, description="最终目的地")
    shipping_marks: Optional[str] = Field(None, description="唛头")
    contract_date: Optional[date] = Field(None, description="合同日期")
    delivery_date: Optional[date] = Field(None, description="交货日期")
    shipping_date: Optional[date] = Field(None, description="装运日期")
    expiry_date: Optional[date] = Field(None, description="有效期")
    is_zero_stock: Optional[bool] = Field(None, description="是否零库存模式")
    notes: Optional[str] = Field(None, description="备注")
    attachments: Optional[List[dict]] = Field(None, description="附件列表")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class SalesContractResponse(BaseModel):
    """销售合同响应"""
    id: str
    contract_no: str
    customer_id: str
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
    commission_rate: Optional[float] = None
    commission_amount: Optional[float] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    destination: Optional[str] = None
    shipping_marks: Optional[str] = None
    contract_date: Optional[date] = None
    delivery_date: Optional[date] = None
    shipping_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    is_zero_stock: bool = False
    linked_purchase_contract_id: Optional[str] = None
    notes: Optional[str] = None
    attachments: List[dict] = []
    tags: List[str] = []
    created_by: Optional[str] = None
    # 关联信息
    customer_name: Optional[str] = Field(None, description="客户名称")
    line_count: int = Field(default=0, description="明细行数量")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SalesContractListResponse(BaseModel):
    """销售合同列表响应"""
    items: List[SalesContractResponse]
    total: int


class SalesContractDetailResponse(SalesContractResponse):
    """销售合同详情响应（含明细行）"""
    lines: List[SalesLineResponse] = Field(default=[], description="明细行列表")
    linked_purchase_contract_no: Optional[str] = Field(None, description="关联采购合同编号")


class SalesContractStatusUpdate(BaseModel):
    """变更销售合同状态"""
    status: str = Field(..., description="新状态")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in SALES_CONTRACT_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(SALES_CONTRACT_STATUSES))}")
        return v


class LinkPurchaseRequest(BaseModel):
    """绑定采购合同请求"""
    purchase_contract_id: str = Field(..., description="采购合同 ID")


class ReserveInventoryRequest(BaseModel):
    """占用库存请求"""
    warehouse_id: str = Field(..., description="仓库 ID")
    quantity: float = Field(..., gt=0, description="占用数量")
