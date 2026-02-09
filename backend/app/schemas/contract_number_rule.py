# app/schemas/contract_number_rule.py
# 合同编号规则数据验证模式

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

class ContractNumberRuleUpdate(BaseModel):
    prefix: Optional[str] = Field(None, max_length=20, description="前缀")
    date_format: Optional[str] = Field(None, max_length=20, description="日期格式")
    separator: Optional[str] = Field(None, max_length=5, description="分隔符")
    sequence_length: Optional[int] = Field(None, ge=1, le=10, description="序号位数")
    is_active: Optional[bool] = Field(None, description="是否启用")

class ContractNumberRuleResponse(BaseModel):
    id: str
    rule_type: str
    prefix: str
    date_format: str
    separator: str
    sequence_length: int
    current_sequence: int
    last_date: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class ContractNumberRuleListResponse(BaseModel):
    items: List[ContractNumberRuleResponse]
    total: int

class ContractNumberPreviewRequest(BaseModel):
    prefix: str = Field(default="SC", max_length=20, description="前缀")
    date_format: str = Field(default="%Y%m%d", max_length=20, description="日期格式")
    separator: str = Field(default="-", max_length=5, description="分隔符")
    sequence_length: int = Field(default=3, ge=1, le=10, description="序号位数")

class ContractNumberPreviewResponse(BaseModel):
    preview: str = Field(description="预览编号")
