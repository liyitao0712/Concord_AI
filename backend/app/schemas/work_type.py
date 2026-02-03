# app/schemas/work_type.py
# 工作类型数据验证模式
#
# 功能说明：
# 1. 定义工作类型 API 请求和响应的数据格式
# 2. 自动验证输入数据
# 3. 自动生成 API 文档
#
# 命名规范：
# - XxxCreate: 创建数据时使用（不包含 id）
# - XxxUpdate: 更新数据时使用（所有字段可选）
# - XxxResponse: 返回数据时使用

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator
import re


# ==================== WorkType 相关 ====================

class WorkTypeBase(BaseModel):
    """工作类型基础模式"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="显示名称（中文）",
        examples=["订单", "新订单"]
    )
    description: str = Field(
        ...,
        min_length=1,
        description="工作类型描述（给 LLM 参考）",
        examples=["与订单相关的邮件，包括新订单、修改、取消等"]
    )
    examples: List[str] = Field(
        default=[],
        description="示例文本列表",
        examples=[["我想下单", "订单确认"]]
    )
    keywords: List[str] = Field(
        default=[],
        description="关键词列表",
        examples=[["订单", "order", "PO"]]
    )


class WorkTypeCreate(WorkTypeBase):
    """
    创建工作类型请求模式

    用于 POST /admin/work-types 接口
    """
    code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="唯一标识码（全大写英文+下划线）",
        examples=["ORDER", "ORDER_NEW"]
    )
    parent_id: Optional[str] = Field(
        None,
        description="父级 WorkType ID",
    )
    is_active: bool = Field(
        default=True,
        description="是否启用",
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证 code 格式：全大写英文+下划线"""
        if not re.match(r'^[A-Z][A-Z0-9_]*$', v):
            raise ValueError("code 必须是全大写英文，可包含数字和下划线，不能以数字开头")
        return v


class WorkTypeUpdate(BaseModel):
    """
    更新工作类型请求模式

    用于 PUT /admin/work-types/{id} 接口
    所有字段都是可选的
    """
    code: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="唯一标识码（全大写英文+下划线）",
    )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="显示名称",
    )
    description: Optional[str] = Field(
        None,
        description="描述",
    )
    examples: Optional[List[str]] = Field(
        None,
        description="示例文本列表",
    )
    keywords: Optional[List[str]] = Field(
        None,
        description="关键词列表",
    )
    is_active: Optional[bool] = Field(
        None,
        description="是否启用",
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        """验证 code 格式：全大写英文+下划线"""
        if v is not None and not re.match(r'^[A-Z][A-Z0-9_]*$', v):
            raise ValueError("code 必须是全大写英文，可包含数字和下划线，不能以数字开头")
        return v


class WorkTypeResponse(BaseModel):
    """
    工作类型响应模式

    API 返回的工作类型数据
    """
    id: str = Field(..., description="工作类型 ID")
    parent_id: Optional[str] = Field(None, description="父级 ID")
    code: str = Field(..., description="唯一标识码")
    name: str = Field(..., description="显示名称")
    description: str = Field(..., description="描述")
    level: int = Field(..., description="层级深度")
    path: str = Field(..., description="完整路径")
    examples: List[str] = Field(default=[], description="示例文本")
    keywords: List[str] = Field(default=[], description="关键词")
    is_active: bool = Field(..., description="是否启用")
    is_system: bool = Field(..., description="是否系统内置")
    usage_count: int = Field(..., description="使用次数")
    created_by: str = Field(..., description="创建者")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class WorkTypeTreeNode(BaseModel):
    """
    工作类型树形节点

    用于树形结构展示
    """
    id: str
    parent_id: Optional[str] = None
    code: str
    name: str
    description: str
    level: int
    is_active: bool
    is_system: bool
    usage_count: int
    children: List["WorkTypeTreeNode"] = []

    class Config:
        from_attributes = True


class WorkTypeListResponse(BaseModel):
    """工作类型列表响应"""
    items: List[WorkTypeResponse]
    total: int


class WorkTypeTreeResponse(BaseModel):
    """工作类型树形响应"""
    items: List[WorkTypeTreeNode]
    total: int


# ==================== WorkTypeSuggestion 相关 ====================

class WorkTypeSuggestionResponse(BaseModel):
    """
    工作类型建议响应模式
    """
    id: str = Field(..., description="建议 ID")
    suggested_code: str = Field(..., description="建议的 code")
    suggested_name: str = Field(..., description="建议的名称")
    suggested_description: str = Field(..., description="建议的描述")
    suggested_parent_id: Optional[str] = Field(None, description="建议的父级 ID")
    suggested_parent_code: Optional[str] = Field(None, description="建议的父级 code")
    suggested_level: int = Field(..., description="建议的层级")
    suggested_examples: List[str] = Field(default=[], description="建议的示例")
    suggested_keywords: List[str] = Field(default=[], description="建议的关键词")

    confidence: float = Field(..., description="AI 置信度 0-1")
    reasoning: Optional[str] = Field(None, description="AI 推理说明")

    trigger_email_id: Optional[str] = Field(None, description="触发的邮件 ID")
    trigger_content: str = Field(..., description="触发内容摘要")
    trigger_source: str = Field(..., description="来源")

    status: str = Field(..., description="状态: pending/approved/rejected/merged")
    workflow_id: Optional[str] = Field(None, description="Temporal Workflow ID")
    reviewed_by: Optional[str] = Field(None, description="审批人 ID")
    reviewed_at: Optional[datetime] = Field(None, description="审批时间")
    review_note: Optional[str] = Field(None, description="审批备注")
    created_work_type_id: Optional[str] = Field(None, description="创建的 WorkType ID")
    merged_to_id: Optional[str] = Field(None, description="合并到的 WorkType ID")

    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class WorkTypeSuggestionListResponse(BaseModel):
    """建议列表响应"""
    items: List[WorkTypeSuggestionResponse]
    total: int


class ReviewRequest(BaseModel):
    """审批请求"""
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="审批备注",
    )


# 解决循环引用
WorkTypeTreeNode.model_rebuild()
