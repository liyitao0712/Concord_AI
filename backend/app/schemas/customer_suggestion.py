# app/schemas/customer_suggestion.py
# 客户建议数据验证模式
#
# 功能说明：
# 1. CustomerSuggestionResponse - 建议响应（完整字段）
# 2. CustomerSuggestionListResponse - 建议列表响应（含分页）
# 3. CustomerReviewRequest - 审批请求（支持覆盖 AI 建议字段）

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class CustomerSuggestionResponse(BaseModel):
    """客户建议响应模式"""
    id: str = Field(..., description="建议 ID")
    suggestion_type: str = Field(..., description="建议类型: new_customer | new_contact")

    # AI 提取的客户信息
    suggested_company_name: str = Field(..., description="建议的公司名称")
    suggested_short_name: Optional[str] = Field(None, description="建议的简称")
    suggested_country: Optional[str] = Field(None, description="建议的国家")
    suggested_region: Optional[str] = Field(None, description="建议的地区/洲")
    suggested_industry: Optional[str] = Field(None, description="建议的行业")
    suggested_website: Optional[str] = Field(None, description="建议的公司网站")
    suggested_email_domain: Optional[str] = Field(None, description="邮箱域名")
    suggested_customer_level: str = Field(..., description="建议的客户等级")
    suggested_tags: List[str] = Field(default=[], description="建议的标签")

    # AI 提取的联系人信息
    suggested_contact_name: Optional[str] = Field(None, description="建议的联系人姓名")
    suggested_contact_email: Optional[str] = Field(None, description="建议的联系人邮箱")
    suggested_contact_title: Optional[str] = Field(None, description="建议的联系人职位")
    suggested_contact_phone: Optional[str] = Field(None, description="建议的联系人电话")
    suggested_contact_department: Optional[str] = Field(None, description="建议的联系人部门")

    # AI 分析信息
    confidence: float = Field(..., description="AI 置信度 0-1")
    reasoning: Optional[str] = Field(None, description="AI 推理说明")
    sender_type: Optional[str] = Field(None, description="发件人类型")

    # 触发来源
    trigger_email_id: Optional[str] = Field(None, description="触发的邮件 ID")
    trigger_content: str = Field(..., description="触发内容摘要")
    trigger_source: str = Field(..., description="来源")

    # 查重关联
    email_domain: Optional[str] = Field(None, description="邮箱域名")
    matched_customer_id: Optional[str] = Field(None, description="匹配到的已有客户 ID")

    # 审批状态
    status: str = Field(..., description="状态: pending/approved/rejected")
    workflow_id: Optional[str] = Field(None, description="Temporal Workflow ID")
    reviewed_by: Optional[str] = Field(None, description="审批人 ID")
    reviewed_at: Optional[datetime] = Field(None, description="审批时间")
    review_note: Optional[str] = Field(None, description="审批备注")
    created_customer_id: Optional[str] = Field(None, description="创建的客户 ID")
    created_contact_id: Optional[str] = Field(None, description="创建的联系人 ID")

    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class CustomerSuggestionListResponse(BaseModel):
    """客户建议列表响应"""
    items: List[CustomerSuggestionResponse]
    total: int


class CustomerReviewRequest(BaseModel):
    """
    客户建议审批请求

    支持覆盖 AI 建议的字段，管理员可在审批时修改。
    """
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="审批备注",
    )
    # 以下字段可选，审批时可覆盖 AI 建议的原始值
    company_name: Optional[str] = Field(None, max_length=200, description="覆盖公司名称")
    short_name: Optional[str] = Field(None, max_length=100, description="覆盖简称")
    country: Optional[str] = Field(None, max_length=100, description="覆盖国家")
    region: Optional[str] = Field(None, max_length=100, description="覆盖地区")
    industry: Optional[str] = Field(None, max_length=100, description="覆盖行业")
    website: Optional[str] = Field(None, max_length=300, description="覆盖网站")
    customer_level: Optional[str] = Field(None, description="覆盖客户等级")
    tags: Optional[List[str]] = Field(None, description="覆盖标签")

    # 联系人字段覆盖
    contact_name: Optional[str] = Field(None, max_length=100, description="覆盖联系人姓名")
    contact_email: Optional[str] = Field(None, max_length=200, description="覆盖联系人邮箱")
    contact_title: Optional[str] = Field(None, max_length=100, description="覆盖联系人职位")
    contact_phone: Optional[str] = Field(None, max_length=50, description="覆盖联系人电话")
    contact_department: Optional[str] = Field(None, max_length=100, description="覆盖联系人部门")

    @field_validator("customer_level")
    @classmethod
    def validate_customer_level(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"potential", "normal", "important", "vip"}
            if v not in allowed:
                raise ValueError(f"客户等级必须是: {', '.join(sorted(allowed))}")
        return v

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v and "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v
