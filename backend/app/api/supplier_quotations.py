# app/api/supplier_quotations.py
# 供应商报价单管理 API
#
# 路由：
#   GET    /admin/supplier-quotations              列表
#   POST   /admin/supplier-quotations              创建（含明细行）
#   GET    /admin/supplier-quotations/{id}         详情（含明细行）
#   PUT    /admin/supplier-quotations/{id}         更新
#   DELETE /admin/supplier-quotations/{id}         删除
#   PUT    /admin/supplier-quotations/{id}/status  变更状态
#   PUT    /admin/supplier-quotations/{id}/lines   整体更新明细行

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import require_permission, apply_data_scope, DataScope
from app.models.user import User
from app.models.supplier import Supplier
from app.models.supplier_quotation import SupplierQuotation, SupplierQuotationLine
from app.models.supplier_rfq import SupplierRFQ
from app.schemas.supplier_quotation import (
    SupplierQuotationCreate,
    SupplierQuotationUpdate,
    SupplierQuotationResponse,
    SupplierQuotationListResponse,
    SupplierQuotationDetailResponse,
    SupplierQuotationStatusUpdate,
    SupplierQuotationLineCreate,
    SupplierQuotationLineResponse,
)
from app.services.contract_number import generate_contract_number

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/supplier-quotations", tags=["供应商报价管理"])


@router.get("", response_model=SupplierQuotationListResponse)
async def list_supplier_quotations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（报价单编号）"),
    status: Optional[str] = Query(None, description="筛选状态"),
    supplier_id: Optional[str] = Query(None, description="筛选供应商"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_quotation", "read")),
):
    """获取供应商报价单列表"""
    query = select(SupplierQuotation).order_by(SupplierQuotation.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, SupplierQuotation, "supplier_quotation", scope, session)

    if search:
        query = query.where(SupplierQuotation.quotation_no.ilike(f"%{search}%"))
    if status is not None:
        query = query.where(SupplierQuotation.status == status)
    if supplier_id is not None:
        query = query.where(SupplierQuotation.supplier_id == supplier_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    quotations = list(result.scalars().all())

    # 批量查询供应商名称和明细行数量
    quotation_ids = [q.id for q in quotations]
    supplier_ids = list({q.supplier_id for q in quotations})

    supplier_map: dict[str, str] = {}
    if supplier_ids:
        s_result = await session.execute(
            select(Supplier.id, Supplier.name).where(Supplier.id.in_(supplier_ids))
        )
        for row in s_result:
            supplier_map[row.id] = row.name

    line_counts: dict[str, int] = {}
    if quotation_ids:
        lc_result = await session.execute(
            select(
                SupplierQuotationLine.supplier_quotation_id,
                func.count(SupplierQuotationLine.id).label("cnt"),
            )
            .where(SupplierQuotationLine.supplier_quotation_id.in_(quotation_ids))
            .group_by(SupplierQuotationLine.supplier_quotation_id)
        )
        for row in lc_result:
            line_counts[row.supplier_quotation_id] = row.cnt

    items = []
    for q in quotations:
        resp = SupplierQuotationResponse.model_validate(q)
        resp.supplier_name = supplier_map.get(q.supplier_id)
        resp.line_count = line_counts.get(q.id, 0)
        items.append(resp)

    return SupplierQuotationListResponse(items=items, total=total)


@router.post("", response_model=SupplierQuotationDetailResponse, status_code=201)
async def create_supplier_quotation(
    data: SupplierQuotationCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_quotation", "create")),
):
    """创建供应商报价单（含明细行）"""
    # 验证供应商
    supplier = await session.get(Supplier, data.supplier_id)
    if not supplier:
        raise HTTPException(status_code=400, detail="供应商不存在")

    # 生成报价单编号
    quotation_no = data.quotation_no
    if not quotation_no:
        quotation_no = await generate_contract_number(session, "supplier_quotation", org_id=scope.org_id)

    quotation = SupplierQuotation(
        id=str(uuid4()),
        quotation_no=quotation_no,
        supplier_id=data.supplier_id,
        contact_id=data.contact_id,
        linked_supplier_rfq_id=data.linked_supplier_rfq_id,
        trade_term=data.trade_term,
        payment_method=data.payment_method,
        payment_terms=data.payment_terms,
        currency=data.currency,
        exchange_rate=data.exchange_rate,
        subtotal=data.subtotal,
        discount_amount=data.discount_amount,
        tax_amount=data.tax_amount,
        total_amount=data.total_amount,
        port_of_loading=data.port_of_loading,
        port_of_discharge=data.port_of_discharge,
        quotation_date=data.quotation_date,
        valid_until=data.valid_until,
        status=data.status,
        notes=data.notes,
        attachments=data.attachments,
        tags=data.tags,
        created_by=scope.user.id,
        # 权限字段自动填充
        org_id=scope.org_id,
        owner_id=scope.user.id,
        owner_dept_id=scope.user.department_id,
    )

    # 创建明细行
    for idx, line_data in enumerate(data.lines, start=1):
        line = SupplierQuotationLine(
            id=str(uuid4()),
            supplier_quotation_id=quotation.id,
            line_no=idx,
            product_id=line_data.product_id,
            product_name=line_data.product_name,
            specifications=line_data.specifications,
            unit=line_data.unit,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            discount_rate=line_data.discount_rate,
            discount_amount=line_data.discount_amount,
            tax_rate=line_data.tax_rate,
            tax_amount=line_data.tax_amount,
            amount=line_data.amount,
            amount_with_tax=line_data.amount_with_tax,
            hs_code=line_data.hs_code,
            notes=line_data.notes,
        )
        quotation.lines.append(line)

    session.add(quotation)
    await session.commit()
    await session.refresh(quotation, ["lines"])

    logger.info(f"[SupplierQuotationsAPI] 创建供应商报价单: {quotation.quotation_no} by {scope.user.email}")

    resp = SupplierQuotationDetailResponse.model_validate(quotation)
    resp.supplier_name = supplier.name
    resp.line_count = len(quotation.lines)
    resp.lines = [SupplierQuotationLineResponse.model_validate(l) for l in quotation.lines]

    # 如果关联了询价单，查询询价单编号
    if quotation.linked_supplier_rfq_id:
        rfq = await session.get(SupplierRFQ, quotation.linked_supplier_rfq_id)
        if rfq:
            resp.linked_supplier_rfq_no = rfq.rfq_no

    return resp


@router.get("/{quotation_id}", response_model=SupplierQuotationDetailResponse)
async def get_supplier_quotation(
    quotation_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_quotation", "read")),
):
    """获取供应商报价单详情（含明细行）"""
    query = (
        select(SupplierQuotation)
        .options(selectinload(SupplierQuotation.lines))
        .where(SupplierQuotation.id == quotation_id)
    )
    query = await apply_data_scope(query, SupplierQuotation, "supplier_quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="供应商报价单不存在")

    # 查询供应商名称
    supplier = await session.get(Supplier, quotation.supplier_id)

    resp = SupplierQuotationDetailResponse.model_validate(quotation)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = len(quotation.lines)
    resp.lines = [SupplierQuotationLineResponse.model_validate(l) for l in quotation.lines]

    # 如果关联了询价单，查询询价单编号
    if quotation.linked_supplier_rfq_id:
        rfq = await session.get(SupplierRFQ, quotation.linked_supplier_rfq_id)
        if rfq:
            resp.linked_supplier_rfq_no = rfq.rfq_no

    return resp


@router.put("/{quotation_id}", response_model=SupplierQuotationResponse)
async def update_supplier_quotation(
    quotation_id: str,
    data: SupplierQuotationUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_quotation", "update")),
):
    """更新供应商报价单（不含明细行，明细行通过单独接口更新）"""
    query = select(SupplierQuotation).where(SupplierQuotation.id == quotation_id)
    query = await apply_data_scope(query, SupplierQuotation, "supplier_quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="供应商报价单不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(quotation, key, value)

    quotation.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(quotation)

    # 查询关联信息
    supplier = await session.get(Supplier, quotation.supplier_id)
    line_count = await session.scalar(
        select(func.count(SupplierQuotationLine.id)).where(
            SupplierQuotationLine.supplier_quotation_id == quotation_id
        )
    ) or 0

    logger.info(f"[SupplierQuotationsAPI] 更新供应商报价单: {quotation.quotation_no} by {scope.user.email}")

    resp = SupplierQuotationResponse.model_validate(quotation)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = line_count
    return resp


@router.delete("/{quotation_id}")
async def delete_supplier_quotation(
    quotation_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_quotation", "delete")),
):
    """删除供应商报价单（级联删除明细行）"""
    query = select(SupplierQuotation).where(SupplierQuotation.id == quotation_id)
    query = await apply_data_scope(query, SupplierQuotation, "supplier_quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="供应商报价单不存在")

    quotation_no = quotation.quotation_no
    await session.delete(quotation)
    await session.commit()

    logger.info(f"[SupplierQuotationsAPI] 删除供应商报价单: {quotation_no} by {scope.user.email}")
    return {"message": "删除成功"}


@router.put("/{quotation_id}/status", response_model=SupplierQuotationResponse)
async def update_supplier_quotation_status(
    quotation_id: str,
    data: SupplierQuotationStatusUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_quotation", "update")),
):
    """变更供应商报价单状态"""
    query = select(SupplierQuotation).where(SupplierQuotation.id == quotation_id)
    query = await apply_data_scope(query, SupplierQuotation, "supplier_quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="供应商报价单不存在")

    old_status = quotation.status
    quotation.status = data.status
    quotation.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(quotation)

    logger.info(
        f"[SupplierQuotationsAPI] 状态变更: {quotation.quotation_no} "
        f"{old_status} → {data.status} by {scope.user.email}"
    )

    supplier = await session.get(Supplier, quotation.supplier_id)
    line_count = await session.scalar(
        select(func.count(SupplierQuotationLine.id)).where(
            SupplierQuotationLine.supplier_quotation_id == quotation_id
        )
    ) or 0

    resp = SupplierQuotationResponse.model_validate(quotation)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = line_count
    return resp


@router.put("/{quotation_id}/lines", response_model=SupplierQuotationDetailResponse)
async def update_supplier_quotation_lines(
    quotation_id: str,
    lines: list[SupplierQuotationLineCreate],
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_quotation", "update")),
):
    """
    整体更新供应商报价单明细行

    删除旧的明细行，创建新的明细行（整体替换策略）。
    """
    query = (
        select(SupplierQuotation)
        .options(selectinload(SupplierQuotation.lines))
        .where(SupplierQuotation.id == quotation_id)
    )
    query = await apply_data_scope(query, SupplierQuotation, "supplier_quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="供应商报价单不存在")

    # 删除旧明细行
    quotation.lines.clear()
    await session.flush()

    # 创建新明细行
    for idx, line_data in enumerate(lines, start=1):
        line = SupplierQuotationLine(
            id=str(uuid4()),
            supplier_quotation_id=quotation.id,
            line_no=idx,
            product_id=line_data.product_id,
            product_name=line_data.product_name,
            specifications=line_data.specifications,
            unit=line_data.unit,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            discount_rate=line_data.discount_rate,
            discount_amount=line_data.discount_amount,
            tax_rate=line_data.tax_rate,
            tax_amount=line_data.tax_amount,
            amount=line_data.amount,
            amount_with_tax=line_data.amount_with_tax,
            hs_code=line_data.hs_code,
            notes=line_data.notes,
        )
        quotation.lines.append(line)

    quotation.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(quotation, ["lines"])

    logger.info(
        f"[SupplierQuotationsAPI] 更新明细行: {quotation.quotation_no} "
        f"({len(quotation.lines)} 行) by {scope.user.email}"
    )

    supplier = await session.get(Supplier, quotation.supplier_id)
    resp = SupplierQuotationDetailResponse.model_validate(quotation)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = len(quotation.lines)
    resp.lines = [SupplierQuotationLineResponse.model_validate(l) for l in quotation.lines]

    # 如果关联了询价单，查询询价单编号
    if quotation.linked_supplier_rfq_id:
        rfq = await session.get(SupplierRFQ, quotation.linked_supplier_rfq_id)
        if rfq:
            resp.linked_supplier_rfq_no = rfq.rfq_no

    return resp
