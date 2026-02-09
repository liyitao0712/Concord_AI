# app/schemas/project.py
# 项目管理数据验证模式

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ==================== 常量 ====================

PROJECT_STATUSES = {"draft", "active", "on_hold", "completed", "cancelled"}
PRIORITIES = {"low", "medium", "high", "urgent"}
VALID_ENTITY_TYPES = {
    "customer", "supplier", "purchase_contract", "sales_contract", "product",
    "inbound_order", "outbound_order",
    "client_rfq", "quotation", "supplier_rfq", "supplier_quotation",
}


# ==================== ProjectAssociation ====================

class ProjectAssociationCreate(BaseModel):
    """创建项目关联"""
    entity_type: str = Field(..., description="实体类型")
    entity_id: str = Field(..., description="实体 ID")
    notes: Optional[str] = Field(None, max_length=500, description="关联备注")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        if v not in VALID_ENTITY_TYPES:
            raise ValueError(f"实体类型必须是: {', '.join(sorted(VALID_ENTITY_TYPES))}")
        return v


class ProjectAssociationResponse(BaseModel):
    """项目关联响应"""
    id: str
    project_id: str
    entity_type: str
    entity_id: str
    entity_name: Optional[str] = Field(None, description="实体名称（动态查询填充）")
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Project ====================

class ProjectCreate(BaseModel):
    """创建项目"""
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    project_type: str = Field(default="general", max_length=50, description="项目类型")
    description: Optional[str] = Field(None, description="项目描述")
    status: str = Field(default="draft", description="状态")
    priority: str = Field(default="medium", description="优先级")
    start_date: Optional[date] = Field(None, description="开始日期")
    due_date: Optional[date] = Field(None, description="截止日期")
    owner_id: Optional[str] = Field(None, description="负责人 ID")
    tags: List[str] = Field(default=[], description="标签列表")
    notes: Optional[str] = Field(None, description="备注")
    associations: List[ProjectAssociationCreate] = Field(default=[], description="关联实体列表")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in PROJECT_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(PROJECT_STATUSES))}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PRIORITIES:
            raise ValueError(f"优先级必须是: {', '.join(sorted(PRIORITIES))}")
        return v


class ProjectUpdate(BaseModel):
    """更新项目"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="项目名称")
    project_type: Optional[str] = Field(None, max_length=50, description="项目类型")
    description: Optional[str] = Field(None, description="项目描述")
    status: Optional[str] = Field(None, description="状态")
    priority: Optional[str] = Field(None, description="优先级")
    start_date: Optional[date] = Field(None, description="开始日期")
    due_date: Optional[date] = Field(None, description="截止日期")
    owner_id: Optional[str] = Field(None, description="负责人 ID")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    notes: Optional[str] = Field(None, description="备注")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PROJECT_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(PROJECT_STATUSES))}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PRIORITIES:
            raise ValueError(f"优先级必须是: {', '.join(sorted(PRIORITIES))}")
        return v


class ProjectStatusUpdate(BaseModel):
    """变更项目状态"""
    status: str = Field(..., description="新状态")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in PROJECT_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(PROJECT_STATUSES))}")
        return v


class ProjectResponse(BaseModel):
    """项目响应"""
    id: str
    name: str
    project_type: str
    description: Optional[str] = None
    status: str
    priority: str
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = Field(None, description="负责人名称")
    tags: List[str] = []
    notes: Optional[str] = None
    created_by: Optional[str] = None
    task_count: int = Field(default=0, description="任务数量")
    association_count: int = Field(default=0, description="关联实体数量")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    items: List[ProjectResponse]
    total: int


class ProjectDetailResponse(ProjectResponse):
    """项目详情（含关联和任务）"""
    associations: List[ProjectAssociationResponse] = Field(default=[], description="关联实体列表")
