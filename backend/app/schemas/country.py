# app/schemas/country.py
# 国家数据库 Schema
#
# 功能说明：
# 只读模型，只有 Response 和 ListResponse（无 Create/Update）

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CountryResponse(BaseModel):
    """国家响应"""
    id: str
    name_zh: str = Field(..., description="中文简称")
    name_en: str = Field(..., description="英文简称")
    full_name_zh: Optional[str] = Field(None, description="中文全称")
    full_name_en: Optional[str] = Field(None, description="英文全称")
    iso_code_2: str = Field(..., description="ISO 3166-1 alpha-2")
    iso_code_3: Optional[str] = Field(None, description="ISO 3166-1 alpha-3")
    numeric_code: Optional[str] = Field(None, description="ISO 3166-1 数字代码")
    phone_code: Optional[str] = Field(None, description="国际电话区号")
    currency_name_zh: Optional[str] = Field(None, description="货币中文名")
    currency_name_en: Optional[str] = Field(None, description="货币英文名")
    currency_code: Optional[str] = Field(None, description="货币代码 ISO 4217")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CountryListResponse(BaseModel):
    """国家列表响应"""
    items: List[CountryResponse]
    total: int
