# app/schemas/warehouse.py
# 仓库管理数据验证模式

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

class WarehouseCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=30, description="仓库编码")
    name: str = Field(..., min_length=1, max_length=100, description="仓库名称")
    address: Optional[str] = Field(None, max_length=300, description="仓库地址")
    contact_person: Optional[str] = Field(None, max_length=50, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    warehouse_type: str = Field(default="own", description="仓库类型: own/rented/bonded/virtual")
    is_active: bool = Field(default=True, description="是否启用")
    notes: Optional[str] = Field(None, description="备注")

    @field_validator("warehouse_type")
    @classmethod
    def validate_warehouse_type(cls, v):
        allowed = {"own", "rented", "bonded", "virtual"}
        if v not in allowed:
            raise ValueError(f"仓库类型必须是: {', '.join(sorted(allowed))}")
        return v

class WarehouseUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=30, description="仓库编码")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="仓库名称")
    address: Optional[str] = Field(None, max_length=300, description="仓库地址")
    contact_person: Optional[str] = Field(None, max_length=50, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    warehouse_type: Optional[str] = Field(None, description="仓库类型")
    is_active: Optional[bool] = Field(None, description="是否启用")
    notes: Optional[str] = Field(None, description="备注")

    @field_validator("warehouse_type")
    @classmethod
    def validate_warehouse_type(cls, v):
        if v is not None:
            allowed = {"own", "rented", "bonded", "virtual"}
            if v not in allowed:
                raise ValueError(f"仓库类型必须是: {', '.join(sorted(allowed))}")
        return v

class WarehouseResponse(BaseModel):
    id: str
    code: str
    name: str
    address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    warehouse_type: str
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class WarehouseListResponse(BaseModel):
    items: List[WarehouseResponse]
    total: int
