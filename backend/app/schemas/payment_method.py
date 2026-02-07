# app/schemas/payment_method.py
# 付款方式 Schema
#
# 功能说明：
# 只读模型，只有 Response 和 ListResponse（无 Create/Update）

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PaymentMethodResponse(BaseModel):
    """付款方式响应"""
    id: str
    code: str = Field(..., description="付款方式代码")
    name_en: str = Field(..., description="英文全称")
    name_zh: str = Field(..., description="中文名称")
    category: str = Field(..., description="分类")
    description_zh: Optional[str] = Field(None, description="中文说明")
    description_en: Optional[str] = Field(None, description="英文说明")
    is_common: bool = Field(..., description="是否常用")
    sort_order: int = Field(0, description="排序序号")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentMethodListResponse(BaseModel):
    """付款方式列表响应"""
    items: List[PaymentMethodResponse]
    total: int
