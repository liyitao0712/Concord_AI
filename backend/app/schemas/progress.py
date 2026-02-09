# app/schemas/progress.py
# 进度记录数据验证模式

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ==================== 常量 ====================

PROGRESS_TYPES = {"status_update", "completion", "communication"}


# ==================== Progress ====================

class ProgressCreate(BaseModel):
    """创建进度记录"""
    task_id: str = Field(..., description="所属任务 ID")
    progress_type: str = Field(default="status_update", description="记录类型")
    content: Optional[str] = Field(None, description="记录内容")
    old_status: Optional[str] = Field(None, max_length=20, description="变更前状态")
    new_status: Optional[str] = Field(None, max_length=20, description="变更后状态")
    percentage: Optional[int] = Field(None, ge=0, le=100, description="完成百分比")
    email_id: Optional[str] = Field(None, description="关联邮件 ID")
    attachments: List[dict] = Field(default=[], description="附件列表")

    @field_validator("progress_type")
    @classmethod
    def validate_progress_type(cls, v: str) -> str:
        if v not in PROGRESS_TYPES:
            raise ValueError(f"记录类型必须是: {', '.join(sorted(PROGRESS_TYPES))}")
        return v


class ProgressResponse(BaseModel):
    """进度记录响应"""
    id: str
    task_id: str
    progress_type: str
    content: Optional[str] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    percentage: Optional[int] = None
    email_id: Optional[str] = None
    attachments: List[dict] = []
    created_by: Optional[str] = None
    created_by_name: Optional[str] = Field(None, description="创建人名称")
    created_at: datetime

    class Config:
        from_attributes = True


class ProgressListResponse(BaseModel):
    """进度记录列表响应"""
    items: List[ProgressResponse]
    total: int
