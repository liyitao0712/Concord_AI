# app/schemas/trade_term.py
# 贸易术语 Schema
#
# 功能说明：
# 只读模型，只有 Response 和 ListResponse（无 Create/Update）

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TradeTermResponse(BaseModel):
    """贸易术语响应"""
    id: str
    code: str = Field(..., description="术语代码")
    name_en: str = Field(..., description="英文全称")
    name_zh: str = Field(..., description="中文名称")
    version: str = Field(..., description="Incoterms 版本")
    transport_mode: str = Field(..., description="适用运输方式")
    description_zh: Optional[str] = Field(None, description="中文说明")
    description_en: Optional[str] = Field(None, description="英文说明")
    risk_transfer: Optional[str] = Field(None, description="风险转移点")
    is_current: bool = Field(..., description="是否当前有效版本")
    sort_order: int = Field(0, description="排序序号")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TradeTermListResponse(BaseModel):
    """贸易术语列表响应"""
    items: List[TradeTermResponse]
    total: int
