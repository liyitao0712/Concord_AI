# app/schemas/inventory.py
# 库存管理数据验证模式

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class InventoryResponse(BaseModel):
    id: str
    warehouse_id: str
    product_id: str
    quantity: float = Field(description="实际库存数量")
    reserved_quantity: float = Field(description="占用数量")
    available_quantity: float = Field(description="可用库存（实际-占用）")
    unit: Optional[str] = None
    notes: Optional[str] = None
    # 关联信息（列表接口填充）
    warehouse_name: Optional[str] = Field(None, description="仓库名称")
    warehouse_code: Optional[str] = Field(None, description="仓库编码")
    product_name: Optional[str] = Field(None, description="产品名称")
    product_model: Optional[str] = Field(None, description="产品型号")
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class InventoryListResponse(BaseModel):
    items: List[InventoryResponse]
    total: int

class InventorySummaryItem(BaseModel):
    product_id: str
    product_name: Optional[str] = None
    product_model: Optional[str] = None
    total_quantity: float = Field(description="总库存（跨仓库）")
    total_reserved: float = Field(description="总占用")
    total_available: float = Field(description="总可用")
    warehouse_count: int = Field(description="分布仓库数")

class InventorySummaryResponse(BaseModel):
    items: List[InventorySummaryItem]
    total: int
