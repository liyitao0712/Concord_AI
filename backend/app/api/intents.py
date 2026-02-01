# app/api/intents.py
# 意图管理 API
#
# 功能说明：
# 1. 意图 CRUD（增删改查）
# 2. 意图建议列表和审批
# 3. 测试路由分类
#
# 路由：
#   GET    /admin/intents              列表
#   POST   /admin/intents              创建
#   GET    /admin/intents/{id}         详情
#   PUT    /admin/intents/{id}         更新
#   DELETE /admin/intents/{id}         删除
#   POST   /admin/intents/test         测试分类
#   GET    /admin/intent-suggestions   建议列表
#   POST   /admin/intent-suggestions/{id}/approve  批准建议
#   POST   /admin/intent-suggestions/{id}/reject   拒绝建议

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.intent import Intent, IntentSuggestion

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/intents", tags=["意图管理"])


# ==================== Schema ====================

class IntentCreate(BaseModel):
    """创建意图"""
    name: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=100)
    description: str
    examples: List[str] = []
    keywords: List[str] = []
    default_handler: str = "agent"
    handler_config: dict = {}
    escalation_rules: Optional[dict] = None
    escalation_workflow: Optional[str] = None
    priority: int = 0
    is_active: bool = True


class IntentUpdate(BaseModel):
    """更新意图"""
    label: Optional[str] = None
    description: Optional[str] = None
    examples: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    default_handler: Optional[str] = None
    handler_config: Optional[dict] = None
    escalation_rules: Optional[dict] = None
    escalation_workflow: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class IntentResponse(BaseModel):
    """意图响应"""
    id: str
    name: str
    label: str
    description: str
    examples: List[str]
    keywords: List[str]
    default_handler: str
    handler_config: dict
    escalation_rules: Optional[dict]
    escalation_workflow: Optional[str]
    priority: int
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntentListResponse(BaseModel):
    """意图列表响应"""
    items: List[IntentResponse]
    total: int


class RouteTestRequest(BaseModel):
    """路由测试请求"""
    content: str
    source: str = "web"
    subject: Optional[str] = None


class RouteTestResponse(BaseModel):
    """路由测试响应"""
    intent: str
    intent_label: str
    confidence: float
    reasoning: str
    action: str
    handler_config: dict
    workflow_name: Optional[str]
    needs_escalation: bool
    escalation_reason: Optional[str]
    new_suggestion: Optional[dict]


class IntentSuggestionResponse(BaseModel):
    """意图建议响应"""
    id: str
    suggested_name: str
    suggested_label: str
    suggested_description: str
    suggested_handler: str
    trigger_message: str
    trigger_source: str
    status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class IntentSuggestionListResponse(BaseModel):
    """意图建议列表响应"""
    items: List[IntentSuggestionResponse]
    total: int


class ReviewRequest(BaseModel):
    """审批请求"""
    note: Optional[str] = None


# ==================== 意图 CRUD ====================

@router.get("", response_model=IntentListResponse)
async def list_intents(
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取意图列表"""
    query = select(Intent).order_by(Intent.priority.desc(), Intent.name)

    if is_active is not None:
        query = query.where(Intent.is_active == is_active)

    result = await session.execute(query)
    intents = list(result.scalars().all())

    # 获取总数
    count_query = select(func.count(Intent.id))
    if is_active is not None:
        count_query = count_query.where(Intent.is_active == is_active)
    total = await session.scalar(count_query) or 0

    return IntentListResponse(
        items=[IntentResponse.model_validate(i) for i in intents],
        total=total,
    )


@router.post("", response_model=IntentResponse)
async def create_intent(
    data: IntentCreate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """创建意图"""
    # 检查名称是否重复
    existing = await session.scalar(
        select(Intent).where(Intent.name == data.name)
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"意图名称 '{data.name}' 已存在")

    intent = Intent(
        id=str(uuid4()),
        name=data.name,
        label=data.label,
        description=data.description,
        examples=data.examples,
        keywords=data.keywords,
        default_handler=data.default_handler,
        handler_config=data.handler_config,
        escalation_rules=data.escalation_rules,
        escalation_workflow=data.escalation_workflow,
        priority=data.priority,
        is_active=data.is_active,
        created_by="admin",
    )

    session.add(intent)
    await session.commit()
    await session.refresh(intent)


    logger.info(f"[IntentsAPI] 创建意图: {intent.name} by {admin.username}")
    return IntentResponse.model_validate(intent)


@router.get("/{intent_id}", response_model=IntentResponse)
async def get_intent(
    intent_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取意图详情"""
    intent = await session.get(Intent, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="意图不存在")
    return IntentResponse.model_validate(intent)


@router.put("/{intent_id}", response_model=IntentResponse)
async def update_intent(
    intent_id: str,
    data: IntentUpdate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """更新意图"""
    intent = await session.get(Intent, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="意图不存在")

    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(intent, key, value)

    intent.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(intent)


    logger.info(f"[IntentsAPI] 更新意图: {intent.name} by {admin.username}")
    return IntentResponse.model_validate(intent)


@router.delete("/{intent_id}")
async def delete_intent(
    intent_id: str,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """删除意图"""
    intent = await session.get(Intent, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="意图不存在")

    # 禁止删除系统意图
    if intent.created_by == "system" and intent.name in ["other", "greeting"]:
        raise HTTPException(status_code=400, detail="不能删除系统内置意图")

    await session.delete(intent)
    await session.commit()


    logger.info(f"[IntentsAPI] 删除意图: {intent.name} by {admin.username}")
    return {"message": "删除成功"}


# ==================== 测试路由 ====================

@router.post("/test", response_model=RouteTestResponse)
async def test_route(
    data: RouteTestRequest,
    _: User = Depends(get_current_admin_user),
):
    """
    测试路由分类

    输入一段文本，返回路由结果
    """
    from app.agents.registry import agent_registry

    # 使用 email_summarizer 进行意图分类
    input_text = f"Subject: {data.subject}\n\n{data.content}" if data.subject else data.content

    result = await agent_registry.run(
        "email_summarizer",
        input_text=input_text,
    )

    # 从 email_summarizer 结果中提取信息
    intent = "other"
    intent_label = "其他"
    reasoning = ""

    if result.success and result.data:
        intent = result.data.get("intent", "other")
        intent_label = result.data.get("summary", "未知意图")[:30]
        reasoning = result.data.get("business_info", {}).get("notes", "")

    return RouteTestResponse(
        intent=intent,
        intent_label=intent_label,
        confidence=0.8 if result.success else 0.0,
        reasoning=reasoning,
        action="agent",
        handler_config={},
        workflow_name=None,
        needs_escalation=False,
        escalation_reason=None,
        new_suggestion=None,
    )


# ==================== 意图建议 ====================

suggestions_router = APIRouter(prefix="/admin/intent-suggestions", tags=["意图建议"])


@suggestions_router.get("", response_model=IntentSuggestionListResponse)
async def list_suggestions(
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取意图建议列表"""
    query = select(IntentSuggestion).order_by(IntentSuggestion.created_at.desc())

    if status:
        query = query.where(IntentSuggestion.status == status)

    result = await session.execute(query)
    suggestions = list(result.scalars().all())

    # 获取总数
    count_query = select(func.count(IntentSuggestion.id))
    if status:
        count_query = count_query.where(IntentSuggestion.status == status)
    total = await session.scalar(count_query) or 0

    return IntentSuggestionListResponse(
        items=[IntentSuggestionResponse.model_validate(s) for s in suggestions],
        total=total,
    )


@suggestions_router.post("/{suggestion_id}/approve", response_model=IntentResponse)
async def approve_suggestion(
    suggestion_id: str,
    data: ReviewRequest,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    批准意图建议

    将建议转换为正式意图
    """
    suggestion = await session.get(IntentSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议已处理: {suggestion.status}")

    # 检查名称是否已存在
    existing = await session.scalar(
        select(Intent).where(Intent.name == suggestion.suggested_name)
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"意图名称 '{suggestion.suggested_name}' 已存在",
        )

    # 创建意图
    intent = Intent(
        id=str(uuid4()),
        name=suggestion.suggested_name,
        label=suggestion.suggested_label,
        description=suggestion.suggested_description,
        examples=suggestion.suggested_examples or [suggestion.trigger_message],
        keywords=[],
        default_handler=suggestion.suggested_handler,
        handler_config={},
        priority=0,
        is_active=True,
        created_by="ai",
    )
    session.add(intent)

    # 更新建议状态
    suggestion.status = "approved"
    suggestion.reviewed_by = admin.id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.review_note = data.note
    suggestion.created_intent_id = intent.id

    await session.commit()
    await session.refresh(intent)


    logger.info(
        f"[IntentsAPI] 批准建议: {suggestion.suggested_name} -> {intent.id} "
        f"by {admin.username}"
    )

    return IntentResponse.model_validate(intent)


@suggestions_router.post("/{suggestion_id}/reject")
async def reject_suggestion(
    suggestion_id: str,
    data: ReviewRequest,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """拒绝意图建议"""
    suggestion = await session.get(IntentSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议已处理: {suggestion.status}")

    suggestion.status = "rejected"
    suggestion.reviewed_by = admin.id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.review_note = data.note

    await session.commit()

    logger.info(f"[IntentsAPI] 拒绝建议: {suggestion.suggested_name} by {admin.username}")

    return {"message": "已拒绝"}
