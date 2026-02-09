# app/schemas/task.py
# 任务管理数据验证模式

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# ==================== 常量 ====================

TASK_STATUSES = {"pending", "in_progress", "completed", "cancelled"}
TASK_TYPES = {"action", "milestone"}
PRIORITIES = {"low", "medium", "high", "urgent"}


# ==================== Task ====================

class TaskCreate(BaseModel):
    """创建任务"""
    project_id: str = Field(..., description="所属项目 ID")
    parent_task_id: Optional[str] = Field(None, description="父任务 ID")
    title: str = Field(..., min_length=1, max_length=300, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: str = Field(default="action", description="任务类型: action/milestone")
    phase_name: Optional[str] = Field(None, max_length=100, description="阶段名称")
    status: str = Field(default="pending", description="状态")
    priority: str = Field(default="medium", description="优先级")
    assignee_id: Optional[str] = Field(None, description="负责人 ID")
    sort_order: int = Field(default=0, description="排序序号")
    completion_percentage: int = Field(default=0, ge=0, le=100, description="完成百分比")
    due_date: Optional[date] = Field(None, description="截止日期")

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v: str) -> str:
        if v not in TASK_TYPES:
            raise ValueError(f"任务类型必须是: {', '.join(sorted(TASK_TYPES))}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in TASK_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(TASK_STATUSES))}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PRIORITIES:
            raise ValueError(f"优先级必须是: {', '.join(sorted(PRIORITIES))}")
        return v


class TaskUpdate(BaseModel):
    """更新任务"""
    title: Optional[str] = Field(None, min_length=1, max_length=300, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: Optional[str] = Field(None, description="任务类型")
    phase_name: Optional[str] = Field(None, max_length=100, description="阶段名称")
    status: Optional[str] = Field(None, description="状态")
    priority: Optional[str] = Field(None, description="优先级")
    assignee_id: Optional[str] = Field(None, description="负责人 ID")
    sort_order: Optional[int] = Field(None, description="排序序号")
    completion_percentage: Optional[int] = Field(None, ge=0, le=100, description="完成百分比")
    due_date: Optional[date] = Field(None, description="截止日期")

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in TASK_TYPES:
            raise ValueError(f"任务类型必须是: {', '.join(sorted(TASK_TYPES))}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in TASK_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(sorted(TASK_STATUSES))}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PRIORITIES:
            raise ValueError(f"优先级必须是: {', '.join(sorted(PRIORITIES))}")
        return v


class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    project_id: str
    parent_task_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    task_type: str
    phase_name: Optional[str] = None
    status: str
    priority: str
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = Field(None, description="负责人名称")
    sort_order: int = 0
    completion_percentage: int = 0
    due_date: Optional[date] = None
    created_by: Optional[str] = None
    sub_task_count: int = Field(default=0, description="子任务数量")
    progress_count: int = Field(default=0, description="进度记录数量")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应"""
    items: List[TaskResponse]
    total: int


class TaskDetailResponse(TaskResponse):
    """任务详情（含子任务和进度记录）"""
    sub_tasks: List[TaskResponse] = Field(default=[], description="子任务列表")
