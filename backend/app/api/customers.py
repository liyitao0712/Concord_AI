# app/api/customers.py
# 客户管理 API
#
# 功能说明：
# 1. 客户（公司）CRUD
# 2. 联系人 CRUD
# 3. 搜索、筛选、分页
#
# 路由：
#   GET    /admin/customers              客户列表
#   POST   /admin/customers              创建客户
#   GET    /admin/customers/{id}         客户详情（含联系人）
#   PUT    /admin/customers/{id}         更新客户
#   DELETE /admin/customers/{id}         删除客户（级联删除联系人）
#   GET    /admin/contacts               联系人列表
#   POST   /admin/contacts               创建联系人
#   GET    /admin/contacts/{id}          联系人详情
#   PUT    /admin/contacts/{id}          更新联系人
#   DELETE /admin/contacts/{id}          删除联系人

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.customer import Customer, Contact
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
    CustomerDetailResponse,
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactListResponse,
)

logger = get_logger(__name__)


# ==================== 客户 CRUD ====================

router = APIRouter(prefix="/admin/customers", tags=["客户管理"])


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（公司名/简称/邮箱）"),
    country: Optional[str] = Query(None, description="筛选国家"),
    customer_level: Optional[str] = Query(None, description="筛选等级"),
    is_active: Optional[bool] = Query(None, description="筛选状态"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    获取客户列表

    支持搜索、筛选和分页
    """
    query = select(Customer).order_by(Customer.created_at.desc())

    # 搜索：模糊匹配公司名、简称、邮箱
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Customer.name.ilike(search_filter),
                Customer.short_name.ilike(search_filter),
                Customer.email.ilike(search_filter),
            )
        )

    # 筛选
    if country is not None:
        query = query.where(Customer.country == country)
    if customer_level is not None:
        query = query.where(Customer.customer_level == customer_level)
    if is_active is not None:
        query = query.where(Customer.is_active == is_active)

    # 获取总数（应用筛选条件后）
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    customers = list(result.scalars().all())

    # 批量查询联系人数量
    customer_ids = [c.id for c in customers]
    contact_counts: dict[str, int] = {}
    if customer_ids:
        count_result = await session.execute(
            select(
                Contact.customer_id,
                func.count(Contact.id).label("cnt"),
            )
            .where(Contact.customer_id.in_(customer_ids))
            .group_by(Contact.customer_id)
        )
        for row in count_result:
            contact_counts[row.customer_id] = row.cnt

    # 构建响应
    items = []
    for c in customers:
        resp = CustomerResponse.model_validate(c)
        resp.contact_count = contact_counts.get(c.id, 0)
        items.append(resp)

    return CustomerListResponse(items=items, total=total)


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    data: CustomerCreate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """创建客户"""
    customer = Customer(
        id=str(uuid4()),
        name=data.name,
        short_name=data.short_name,
        country=data.country,
        region=data.region,
        industry=data.industry,
        company_size=data.company_size,
        annual_revenue=data.annual_revenue,
        customer_level=data.customer_level,
        email=data.email,
        phone=data.phone,
        website=data.website,
        address=data.address,
        payment_terms=data.payment_terms,
        shipping_terms=data.shipping_terms,
        is_active=data.is_active,
        source=data.source,
        notes=data.notes,
        tags=data.tags,
    )

    session.add(customer)
    await session.commit()
    await session.refresh(customer)

    logger.info(f"[CustomersAPI] 创建客户: {customer.name} by {admin.email}")

    resp = CustomerResponse.model_validate(customer)
    resp.contact_count = 0
    return resp


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取客户详情（含联系人列表）"""
    # 预加载联系人
    result = await session.execute(
        select(Customer)
        .options(selectinload(Customer.contacts))
        .where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    resp = CustomerDetailResponse.model_validate(customer)
    resp.contact_count = len(customer.contacts)
    resp.contacts = [ContactResponse.model_validate(c) for c in customer.contacts]
    return resp


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """更新客户"""
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(customer, key, value)

    customer.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(customer)

    logger.info(f"[CustomersAPI] 更新客户: {customer.name} by {admin.email}")

    # 查询联系人数量
    contact_count = await session.scalar(
        select(func.count(Contact.id)).where(Contact.customer_id == customer_id)
    ) or 0

    resp = CustomerResponse.model_validate(customer)
    resp.contact_count = contact_count
    return resp


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    删除客户

    级联删除该客户的所有联系人
    """
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")

    # 统计联系人数量（用于返回信息）
    contact_count = await session.scalar(
        select(func.count(Contact.id)).where(Contact.customer_id == customer_id)
    ) or 0

    customer_name = customer.name
    await session.delete(customer)
    await session.commit()

    logger.info(f"[CustomersAPI] 删除客户: {customer_name} (联系人: {contact_count}) by {admin.email}")
    return {"message": "删除成功", "contacts_deleted": contact_count}


# ==================== AI 搜索 ====================


class AILookupRequest(BaseModel):
    """AI 搜索请求"""
    company_name: str = Field(..., min_length=1, description="公司全称")


class AILookupResponse(BaseModel):
    """AI 搜索响应"""
    short_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    confidence: float = 0.0
    error: Optional[str] = None


@router.post(
    "/ai-lookup",
    response_model=AILookupResponse,
    summary="AI 搜索公司信息",
    description="根据公司名称通过 AI 联网搜索自动填充客户信息",
)
async def ai_lookup_customer(
    request: AILookupRequest,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    AI 搜索公司信息

    调用 AddNewClientHelper Agent 通过 LLM + Web Search 搜索公司公开信息，
    返回可直接用于填充客户表单的结构化数据。
    """
    from app.llm import apply_llm_settings
    from app.agents.registry import agent_registry

    logger.info(f"[CustomersAPI] AI 搜索: {request.company_name} by {admin.email}")

    # 加载 LLM 设置
    await apply_llm_settings(session)

    # 获取 Agent 并加载配置
    agent = agent_registry.get("add_new_client_helper")
    if not agent:
        raise HTTPException(status_code=500, detail="Agent add_new_client_helper 未注册")

    await agent.load_config_from_db(session)

    # 执行搜索
    try:
        result = await agent.lookup(request.company_name)
    except Exception as e:
        logger.error(f"[CustomersAPI] AI 搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"AI 搜索失败: {str(e)}")

    return AILookupResponse(
        short_name=result.get("short_name"),
        country=result.get("country"),
        region=result.get("region"),
        industry=result.get("industry"),
        company_size=result.get("company_size"),
        website=result.get("website"),
        email=result.get("email"),
        phone=result.get("phone"),
        address=result.get("address"),
        tags=result.get("tags") or [],
        notes=result.get("notes"),
        confidence=result.get("confidence", 0),
        error=result.get("error"),
    )


# ==================== 联系人 CRUD ====================

contacts_router = APIRouter(prefix="/admin/contacts", tags=["联系人管理"])


@contacts_router.get("", response_model=ContactListResponse)
async def list_contacts(
    customer_id: Optional[str] = Query(None, description="筛选客户 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（姓名/邮箱）"),
    is_active: Optional[bool] = Query(None, description="筛选状态"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取联系人列表"""
    query = select(Contact).order_by(Contact.is_primary.desc(), Contact.created_at.desc())

    if customer_id is not None:
        query = query.where(Contact.customer_id == customer_id)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Contact.name.ilike(search_filter),
                Contact.email.ilike(search_filter),
            )
        )
    if is_active is not None:
        query = query.where(Contact.is_active == is_active)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    contacts = list(result.scalars().all())

    return ContactListResponse(
        items=[ContactResponse.model_validate(c) for c in contacts],
        total=total,
    )


@contacts_router.post("", response_model=ContactResponse, status_code=201)
async def create_contact(
    data: ContactCreate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """创建联系人"""
    # 验证客户是否存在
    customer = await session.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(status_code=400, detail="客户不存在")

    # 如果设为主联系人，先清除该客户其他主联系人
    if data.is_primary:
        await _clear_primary_contact(session, data.customer_id)

    contact = Contact(
        id=str(uuid4()),
        customer_id=data.customer_id,
        name=data.name,
        title=data.title,
        department=data.department,
        email=data.email,
        phone=data.phone,
        mobile=data.mobile,
        social_media=data.social_media,
        is_primary=data.is_primary,
        is_active=data.is_active,
        notes=data.notes,
    )

    session.add(contact)
    await session.commit()
    await session.refresh(contact)

    logger.info(f"[ContactsAPI] 创建联系人: {contact.name} @ {customer.name} by {admin.email}")
    return ContactResponse.model_validate(contact)


@contacts_router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取联系人详情"""
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return ContactResponse.model_validate(contact)


@contacts_router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: str,
    data: ContactUpdate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """更新联系人"""
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 如果设为主联系人，先清除该客户其他主联系人
    if update_data.get("is_primary") is True:
        await _clear_primary_contact(session, contact.customer_id, exclude_id=contact_id)

    for key, value in update_data.items():
        setattr(contact, key, value)

    contact.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contact)

    logger.info(f"[ContactsAPI] 更新联系人: {contact.name} by {admin.email}")
    return ContactResponse.model_validate(contact)


@contacts_router.delete("/{contact_id}")
async def delete_contact(
    contact_id: str,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """删除联系人"""
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")

    contact_name = contact.name
    await session.delete(contact)
    await session.commit()

    logger.info(f"[ContactsAPI] 删除联系人: {contact_name} by {admin.email}")
    return {"message": "删除成功"}


# ==================== 辅助函数 ====================

async def _clear_primary_contact(
    session: AsyncSession,
    customer_id: str,
    exclude_id: Optional[str] = None,
):
    """清除某客户的主联系人标记（设为 False）"""
    query = select(Contact).where(
        Contact.customer_id == customer_id,
        Contact.is_primary == True,
    )
    if exclude_id:
        query = query.where(Contact.id != exclude_id)

    result = await session.execute(query)
    for c in result.scalars().all():
        c.is_primary = False
