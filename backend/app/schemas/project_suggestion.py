# app/schemas/project_suggestion.py
# 项目建议数据验证模式

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ==================== ProjectSuggestion ====================

class ProjectSuggestionResponse(BaseModel):
    """项目建议响应"""
    id: str
    suggested_name: str
    suggested_type: str
    suggested_description: Optional[str] = None
    suggested_priority: str
    suggested_associations: List[dict] = []
    confidence: float
    reasoning: Optional[str] = None
    trigger_email_id: Optional[str] = None
    trigger_content: str
    trigger_source: str
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    created_project_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectSuggestionListResponse(BaseModel):
    """项目建议列表响应"""
    items: List[ProjectSuggestionResponse]
    total: int


class ProjectReviewRequest(BaseModel):
    """项目建议审批请求（支持覆盖 AI 建议的字段）"""
    note: Optional[str] = Field(None, max_length=500, description="审批备注")
    name: Optional[str] = Field(None, max_length=200, description="覆盖项目名称")
    project_type: Optional[str] = Field(None, max_length=50, description="覆盖项目类型")
    description: Optional[str] = Field(None, description="覆盖项目描述")
    priority: Optional[str] = Field(None, description="覆盖优先级")
    owner_id: Optional[str] = Field(None, description="指定负责人")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"low", "medium", "high", "urgent"}
            if v not in allowed:
                raise ValueError(f"优先级必须是: {', '.join(sorted(allowed))}")
        return v
