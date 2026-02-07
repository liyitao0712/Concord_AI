# app/api/customer_suggestions.py
# 客户建议审批 API
#
# 功能说明：
# 1. 获取客户建议列表（支持状态筛选、分页）
# 2. 获取建议详情
# 3. 批准建议（支持覆盖 AI 建议字段）→ 创建 Customer + Contact
# 4. 拒绝建议

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import get_current_admin_user
from app.core.logging import get_logger
from app.models.user import User
from app.models.customer import Customer, Contact
from app.models.customer_suggestion import CustomerSuggestion
from app.schemas.customer_suggestion import (
    CustomerSuggestionResponse,
    CustomerSuggestionListResponse,
    CustomerReviewRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/customer-suggestions", tags=["客户建议审批"])


@router.get("", response_model=CustomerSuggestionListResponse)
async def list_customer_suggestions(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_admin_user),
):
    """
    获取客户建议列表

    参数：
    - status: 筛选状态（pending/approved/rejected）
    - search: 按公司名搜索
    """
    query = select(CustomerSuggestion).order_by(CustomerSuggestion.created_at.desc())

    if status:
        query = query.where(CustomerSuggestion.status == status)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            CustomerSuggestion.suggested_company_name.ilike(search_pattern)
        )

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    suggestions = list(result.scalars().all())

    # 获取总数
    count_query = select(func.count(CustomerSuggestion.id))
    if status:
        count_query = count_query.where(CustomerSuggestion.status == status)
    if search:
        search_pattern = f"%{search}%"
        count_query = count_query.where(
            CustomerSuggestion.suggested_company_name.ilike(search_pattern)
        )
    total = await session.scalar(count_query) or 0

    return CustomerSuggestionListResponse(
        items=[CustomerSuggestionResponse.model_validate(s) for s in suggestions],
        total=total,
    )


@router.get("/{suggestion_id}", response_model=CustomerSuggestionResponse)
async def get_customer_suggestion(
    suggestion_id: str,
    session: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_admin_user),
):
    """获取客户建议详情"""
    suggestion = await session.get(CustomerSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="客户建议不存在")
    return CustomerSuggestionResponse.model_validate(suggestion)


@router.post("/{suggestion_id}/approve")
async def approve_customer_suggestion(
    suggestion_id: str,
    data: CustomerReviewRequest,
    session: AsyncSession = Depends(get_async_session),
    admin: User = Depends(get_current_admin_user),
):
    """
    批准客户建议

    统一在本地直接处理（支持管理员修改字段后审批），
    如果有关联的 Temporal Workflow，处理完成后发送信号通知工作流结束。

    根据 suggestion_type 处理：
    - new_customer: 创建 Customer + Contact
    - new_contact: 仅创建 Contact 关联到已有客户
    """
    suggestion = await session.get(CustomerSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="客户建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议已处理: {suggestion.status}")

    # 审批时可覆盖 AI 建议的字段
    final_company_name = data.company_name or suggestion.suggested_company_name
    final_short_name = data.short_name or suggestion.suggested_short_name
    final_country = data.country or suggestion.suggested_country
    final_region = data.region or suggestion.suggested_region
    final_industry = data.industry or suggestion.suggested_industry
    final_website = data.website or suggestion.suggested_website
    final_customer_level = data.customer_level or suggestion.suggested_customer_level
    final_tags = data.tags if data.tags is not None else (suggestion.suggested_tags or [])

    final_contact_name = data.contact_name or suggestion.suggested_contact_name
    final_contact_email = data.contact_email or suggestion.suggested_contact_email
    final_contact_title = data.contact_title or suggestion.suggested_contact_title
    final_contact_phone = data.contact_phone or suggestion.suggested_contact_phone
    final_contact_department = data.contact_department or suggestion.suggested_contact_department

    created_customer_id = None
    created_contact_id = None

    if suggestion.suggestion_type == "new_customer":
        # 创建新客户
        customer = Customer(
            id=str(uuid4()),
            name=final_company_name,
            short_name=final_short_name,
            country=final_country,
            region=final_region,
            industry=final_industry,
            website=final_website,
            customer_level=final_customer_level,
            tags=final_tags,
            source="email",
            is_active=True,
        )
        session.add(customer)
        created_customer_id = customer.id

        # 创建联系人（如有联系人信息）
        if final_contact_name or final_contact_email:
            contact = Contact(
                id=str(uuid4()),
                customer_id=customer.id,
                name=final_contact_name or "Unknown",
                email=final_contact_email,
                title=final_contact_title,
                department=final_contact_department,
                phone=final_contact_phone,
                is_primary=True,
                is_active=True,
            )
            session.add(contact)
            created_contact_id = contact.id

    elif suggestion.suggestion_type == "new_contact":
        # 仅创建联系人，关联到已有客户
        target_customer_id = suggestion.matched_customer_id
        if not target_customer_id:
            raise HTTPException(
                status_code=400,
                detail="new_contact 类型建议缺少 matched_customer_id",
            )

        # 验证客户存在
        customer = await session.get(Customer, target_customer_id)
        if not customer:
            raise HTTPException(
                status_code=400,
                detail=f"关联的客户不存在: {target_customer_id}",
            )

        if final_contact_name or final_contact_email:
            contact = Contact(
                id=str(uuid4()),
                customer_id=target_customer_id,
                name=final_contact_name or "Unknown",
                email=final_contact_email,
                title=final_contact_title,
                department=final_contact_department,
                phone=final_contact_phone,
                is_primary=False,
                is_active=True,
            )
            session.add(contact)
            created_contact_id = contact.id
            created_customer_id = target_customer_id

    # 更新建议状态
    suggestion.status = "approved"
    suggestion.reviewed_by = admin.id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.review_note = data.note
    suggestion.created_customer_id = created_customer_id
    suggestion.created_contact_id = created_contact_id

    await session.commit()

    logger.info(
        f"[CustomerSuggestions] 批准建议: {final_company_name} "
        f"(type={suggestion.suggestion_type}) by {admin.email}"
    )

    # 如果有关联的 Temporal Workflow，发送信号让工作流正常结束
    if suggestion.workflow_id:
        try:
            from app.temporal import approve_customer_suggestion as temporal_approve
            await temporal_approve(
                suggestion.workflow_id,
                str(admin.id),
                data.note or "",
            )
        except Exception as e:
            logger.warning(
                f"[CustomerSuggestions] 通知 Temporal 工作流失败（不影响审批）: {e}"
            )

    return {
        "message": "已批准",
        "customer_id": created_customer_id,
        "contact_id": created_contact_id,
    }


@router.post("/{suggestion_id}/reject")
async def reject_customer_suggestion(
    suggestion_id: str,
    data: CustomerReviewRequest,
    session: AsyncSession = Depends(get_async_session),
    admin: User = Depends(get_current_admin_user),
):
    """
    拒绝客户建议

    统一在本地直接处理，如果有关联的 Temporal Workflow，
    处理完成后发送信号通知工作流结束。
    """
    suggestion = await session.get(CustomerSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="客户建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议已处理: {suggestion.status}")

    # 直接在本地处理
    suggestion.status = "rejected"
    suggestion.reviewed_by = admin.id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.review_note = data.note

    await session.commit()

    logger.info(
        f"[CustomerSuggestions] 拒绝建议: {suggestion.suggested_company_name} "
        f"by {admin.email}"
    )

    # 如果有关联的 Temporal Workflow，发送信号让工作流正常结束
    if suggestion.workflow_id:
        try:
            from app.temporal import reject_customer_suggestion as temporal_reject
            await temporal_reject(
                suggestion.workflow_id,
                str(admin.id),
                data.note or "",
            )
        except Exception as e:
            logger.warning(
                f"[CustomerSuggestions] 通知 Temporal 工作流失败（不影响拒绝）: {e}"
            )

    return {"message": "已拒绝"}
