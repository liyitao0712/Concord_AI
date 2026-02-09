# app/api/suppliers.py
# 供应商管理 API
#
# 功能说明：
# 1. 供应商（公司）CRUD
# 2. 供应商联系人 CRUD
# 3. 搜索、筛选、分页
#
# 路由：
#   GET    /admin/suppliers              供应商列表
#   POST   /admin/suppliers              创建供应商
#   GET    /admin/suppliers/{id}         供应商详情（含联系人）
#   PUT    /admin/suppliers/{id}         更新供应商
#   DELETE /admin/suppliers/{id}         删除供应商（级联删除联系人）
#   GET    /admin/supplier-contacts               联系人列表
#   POST   /admin/supplier-contacts               创建联系人
#   GET    /admin/supplier-contacts/{id}          联系人详情
#   PUT    /admin/supplier-contacts/{id}          更新联系人
#   DELETE /admin/supplier-contacts/{id}          删除联系人

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
from app.core.security import get_current_admin_user, require_permission, apply_data_scope, DataScope
from app.models.user import User
from app.models.supplier import Supplier, SupplierContact
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierListResponse,
    SupplierDetailResponse,
    SupplierContactCreate,
    SupplierContactUpdate,
    SupplierContactResponse,
    SupplierContactListResponse,
)

logger = get_logger(__name__)


# ==================== 供应商 CRUD ====================

router = APIRouter(prefix="/admin/suppliers", tags=["供应商管理"])


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（公司名/简称/邮箱）"),
    country: Optional[str] = Query(None, description="筛选国家"),
    supplier_level: Optional[str] = Query(None, description="筛选等级"),
    is_active: Optional[bool] = Query(None, description="筛选状态"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier", "read")),
):
    """
    获取供应商列表

    支持搜索、筛选和分页，按数据权限过滤
    """
    query = select(Supplier).order_by(Supplier.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, Supplier, "supplier", scope, session)

    # 搜索：模糊匹配公司名、简称、邮箱
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Supplier.name.ilike(search_filter),
                Supplier.short_name.ilike(search_filter),
                Supplier.email.ilike(search_filter),
            )
        )

    # 筛选
    if country is not None:
        query = query.where(Supplier.country == country)
    if supplier_level is not None:
        query = query.where(Supplier.supplier_level == supplier_level)
    if is_active is not None:
        query = query.where(Supplier.is_active == is_active)

    # 获取总数（应用筛选条件后）
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    suppliers = list(result.scalars().all())

    # 批量查询联系人数量
    supplier_ids = [s.id for s in suppliers]
    contact_counts: dict[str, int] = {}
    if supplier_ids:
        count_result = await session.execute(
            select(
                SupplierContact.supplier_id,
                func.count(SupplierContact.id).label("cnt"),
            )
            .where(SupplierContact.supplier_id.in_(supplier_ids))
            .group_by(SupplierContact.supplier_id)
        )
        for row in count_result:
            contact_counts[row.supplier_id] = row.cnt

    # 构建响应
    items = []
    for s in suppliers:
        resp = SupplierResponse.model_validate(s)
        resp.contact_count = contact_counts.get(s.id, 0)
        items.append(resp)

    return SupplierListResponse(items=items, total=total)


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    data: SupplierCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier", "create")),
):
    """创建供应商"""
    supplier = Supplier(
        id=str(uuid4()),
        name=data.name,
        short_name=data.short_name,
        country=data.country,
        region=data.region,
        industry=data.industry,
        company_size=data.company_size,
        main_products=data.main_products,
        supplier_level=data.supplier_level,
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
        # 权限字段自动填充
        org_id=scope.org_id,
        owner_id=scope.user.id,
        owner_dept_id=scope.user.department_id,
    )

    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)

    logger.info(f"[SuppliersAPI] 创建供应商: {supplier.name} by {scope.user.email}")

    resp = SupplierResponse.model_validate(supplier)
    resp.contact_count = 0
    return resp


@router.get("/{supplier_id}", response_model=SupplierDetailResponse)
async def get_supplier(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier", "read")),
):
    """获取供应商详情（含联系人列表）"""
    # 预加载联系人，并加数据权限过滤
    query = (
        select(Supplier)
        .options(selectinload(Supplier.contacts))
        .where(Supplier.id == supplier_id)
    )
    query = await apply_data_scope(query, Supplier, "supplier", scope, session)
    result = await session.execute(query)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")

    resp = SupplierDetailResponse.model_validate(supplier)
    resp.contact_count = len(supplier.contacts)
    resp.contacts = [SupplierContactResponse.model_validate(c) for c in supplier.contacts]
    return resp


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    data: SupplierUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier", "update")),
):
    """更新供应商"""
    query = select(Supplier).where(Supplier.id == supplier_id)
    query = await apply_data_scope(query, Supplier, "supplier", scope, session)
    result = await session.execute(query)
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)

    supplier.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(supplier)

    logger.info(f"[SuppliersAPI] 更新供应商: {supplier.name} by {scope.user.email}")

    # 查询联系人数量
    contact_count = await session.scalar(
        select(func.count(SupplierContact.id)).where(SupplierContact.supplier_id == supplier_id)
    ) or 0

    resp = SupplierResponse.model_validate(supplier)
    resp.contact_count = contact_count
    return resp


@router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier", "delete")),
):
    """
    删除供应商

    级联删除该供应商的所有联系人
    """
    query = select(Supplier).where(Supplier.id == supplier_id)
    query = await apply_data_scope(query, Supplier, "supplier", scope, session)
    result = await session.execute(query)
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")

    # 统计联系人数量（用于返回信息）
    contact_count = await session.scalar(
        select(func.count(SupplierContact.id)).where(SupplierContact.supplier_id == supplier_id)
    ) or 0

    supplier_name = supplier.name
    await session.delete(supplier)
    await session.commit()

    logger.info(f"[SuppliersAPI] 删除供应商: {supplier_name} (联系人: {contact_count}) by {scope.user.email}")
    return {"message": "删除成功", "contacts_deleted": contact_count}


# ==================== AI 搜索 ====================


class SupplierAILookupRequest(BaseModel):
    """供应商 AI 搜索请求"""
    company_name: str = Field(..., min_length=1, description="公司全称")


class SupplierAILookupResponse(BaseModel):
    """供应商 AI 搜索响应"""
    name: Optional[str] = None
    short_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    main_products: Optional[str] = None
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
    response_model=SupplierAILookupResponse,
    summary="AI 搜索供应商信息",
    description="根据公司名称通过 AI 联网搜索自动填充供应商信息",
)
async def ai_lookup_supplier(
    request: SupplierAILookupRequest,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier", "create")),
):
    """
    AI 搜索供应商信息

    调用 AddNewSupplierHelper Agent 通过 LLM + Web Search 搜索供应商公开信息，
    返回可直接用于填充供应商表单的结构化数据。
    """
    from app.llm import apply_llm_settings
    from app.agents.registry import agent_registry

    logger.info(f"[SuppliersAPI] AI 搜索: {request.company_name} by {scope.user.email}")

    # 加载 LLM 设置
    await apply_llm_settings(session)

    # 获取 Agent 并加载配置
    agent = agent_registry.get("add_new_supplier_helper")
    if not agent:
        raise HTTPException(status_code=500, detail="Agent add_new_supplier_helper 未注册")

    await agent.load_config_from_db(session)

    # 执行搜索
    try:
        result = await agent.lookup(request.company_name)
    except Exception as e:
        logger.error(f"[SuppliersAPI] AI 搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"AI 搜索失败: {str(e)}")

    return SupplierAILookupResponse(
        name=result.get("name"),
        short_name=result.get("short_name"),
        country=result.get("country"),
        region=result.get("region"),
        industry=result.get("industry"),
        company_size=result.get("company_size"),
        main_products=result.get("main_products"),
        website=result.get("website"),
        email=result.get("email"),
        phone=result.get("phone"),
        address=result.get("address"),
        tags=result.get("tags") or [],
        notes=result.get("notes"),
        confidence=result.get("confidence", 0),
        error=result.get("error"),
    )


# ==================== 供应商联系人 CRUD ====================

supplier_contacts_router = APIRouter(prefix="/admin/supplier-contacts", tags=["供应商联系人"])


@supplier_contacts_router.get("", response_model=SupplierContactListResponse)
async def list_supplier_contacts(
    supplier_id: Optional[str] = Query(None, description="筛选供应商 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（姓名/邮箱）"),
    is_active: Optional[bool] = Query(None, description="筛选状态"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_contact", "read")),
):
    """获取供应商联系人列表"""
    query = select(SupplierContact).order_by(
        SupplierContact.is_primary.desc(), SupplierContact.created_at.desc()
    )
    query = await apply_data_scope(query, SupplierContact, "supplier_contact", scope, session)

    if supplier_id is not None:
        query = query.where(SupplierContact.supplier_id == supplier_id)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                SupplierContact.name.ilike(search_filter),
                SupplierContact.email.ilike(search_filter),
            )
        )
    if is_active is not None:
        query = query.where(SupplierContact.is_active == is_active)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    contacts = list(result.scalars().all())

    return SupplierContactListResponse(
        items=[SupplierContactResponse.model_validate(c) for c in contacts],
        total=total,
    )


@supplier_contacts_router.post("", response_model=SupplierContactResponse, status_code=201)
async def create_supplier_contact(
    data: SupplierContactCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_contact", "create")),
):
    """创建供应商联系人"""
    # 验证供应商是否存在
    supplier = await session.get(Supplier, data.supplier_id)
    if not supplier:
        raise HTTPException(status_code=400, detail="供应商不存在")

    # 如果设为主联系人，先清除该供应商其他主联系人
    if data.is_primary:
        await _clear_primary_contact(session, data.supplier_id)

    contact = SupplierContact(
        id=str(uuid4()),
        supplier_id=data.supplier_id,
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
        org_id=scope.org_id,
        owner_id=scope.user.id,
        owner_dept_id=scope.user.department_id,
    )

    session.add(contact)
    await session.commit()
    await session.refresh(contact)

    logger.info(f"[SupplierContactsAPI] 创建联系人: {contact.name} @ {supplier.name} by {scope.user.email}")
    return SupplierContactResponse.model_validate(contact)


@supplier_contacts_router.get("/{contact_id}", response_model=SupplierContactResponse)
async def get_supplier_contact(
    contact_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_contact", "read")),
):
    """获取供应商联系人详情"""
    query = select(SupplierContact).where(SupplierContact.id == contact_id)
    query = await apply_data_scope(query, SupplierContact, "supplier_contact", scope, session)
    result = await session.execute(query)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return SupplierContactResponse.model_validate(contact)


@supplier_contacts_router.put("/{contact_id}", response_model=SupplierContactResponse)
async def update_supplier_contact(
    contact_id: str,
    data: SupplierContactUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_contact", "update")),
):
    """更新供应商联系人"""
    query = select(SupplierContact).where(SupplierContact.id == contact_id)
    query = await apply_data_scope(query, SupplierContact, "supplier_contact", scope, session)
    result = await session.execute(query)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 如果设为主联系人，先清除该供应商其他主联系人
    if update_data.get("is_primary") is True:
        await _clear_primary_contact(session, contact.supplier_id, exclude_id=contact_id)

    for key, value in update_data.items():
        setattr(contact, key, value)

    contact.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contact)

    logger.info(f"[SupplierContactsAPI] 更新联系人: {contact.name} by {scope.user.email}")
    return SupplierContactResponse.model_validate(contact)


@supplier_contacts_router.delete("/{contact_id}")
async def delete_supplier_contact(
    contact_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_contact", "delete")),
):
    """删除供应商联系人"""
    query = select(SupplierContact).where(SupplierContact.id == contact_id)
    query = await apply_data_scope(query, SupplierContact, "supplier_contact", scope, session)
    result = await session.execute(query)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")

    contact_name = contact.name
    await session.delete(contact)
    await session.commit()

    logger.info(f"[SupplierContactsAPI] 删除联系人: {contact_name} by {scope.user.email}")
    return {"message": "删除成功"}


# ==================== 辅助函数 ====================

async def _clear_primary_contact(
    session: AsyncSession,
    supplier_id: str,
    exclude_id: Optional[str] = None,
):
    """清除某供应商的主联系人标记（设为 False）"""
    query = select(SupplierContact).where(
        SupplierContact.supplier_id == supplier_id,
        SupplierContact.is_primary == True,
    )
    if exclude_id:
        query = query.where(SupplierContact.id != exclude_id)

    result = await session.execute(query)
    for c in result.scalars().all():
        c.is_primary = False
