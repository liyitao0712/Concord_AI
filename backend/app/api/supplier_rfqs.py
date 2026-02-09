# app/api/supplier_rfqs.py
# 供应商询价单管理 API
#
# 路由：
#   GET    /admin/supplier-rfqs              列表
#   POST   /admin/supplier-rfqs              创建（含明细行）
#   GET    /admin/supplier-rfqs/{id}         详情（含明细行）
#   PUT    /admin/supplier-rfqs/{id}         更新
#   DELETE /admin/supplier-rfqs/{id}         删除
#   PUT    /admin/supplier-rfqs/{id}/status  变更状态
#   PUT    /admin/supplier-rfqs/{id}/lines   整体更新明细行

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
from app.models.supplier_rfq import SupplierRFQ, SupplierRFQLine
from app.schemas.supplier_rfq import (
    SupplierRFQCreate,
    SupplierRFQUpdate,
    SupplierRFQResponse,
    SupplierRFQListResponse,
    SupplierRFQDetailResponse,
    SupplierRFQStatusUpdate,
    SupplierRFQLineCreate,
    SupplierRFQLineResponse,
)
from app.services.contract_number import generate_contract_number

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/supplier-rfqs", tags=["供应商询价管理"])


@router.get("", response_model=SupplierRFQListResponse)
async def list_supplier_rfqs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（询价单编号）"),
    status: Optional[str] = Query(None, description="筛选状态"),
    supplier_id: Optional[str] = Query(None, description="筛选供应商"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_rfq", "read")),
):
    """获取供应商询价单列表"""
    query = select(SupplierRFQ).order_by(SupplierRFQ.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, SupplierRFQ, "supplier_rfq", scope, session)

    if search:
        query = query.where(SupplierRFQ.rfq_no.ilike(f"%{search}%"))
    if status is not None:
        query = query.where(SupplierRFQ.status == status)
    if supplier_id is not None:
        query = query.where(SupplierRFQ.supplier_id == supplier_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    rfqs = list(result.scalars().all())

    # 批量查询供应商名称和明细行数量
    rfq_ids = [r.id for r in rfqs]
    supplier_ids = list({r.supplier_id for r in rfqs})

    supplier_map: dict[str, str] = {}
    if supplier_ids:
        s_result = await session.execute(
            select(Supplier.id, Supplier.name).where(Supplier.id.in_(supplier_ids))
        )
        for row in s_result:
            supplier_map[row.id] = row.name

    line_counts: dict[str, int] = {}
    if rfq_ids:
        lc_result = await session.execute(
            select(
                SupplierRFQLine.supplier_rfq_id,
                func.count(SupplierRFQLine.id).label("cnt"),
            )
            .where(SupplierRFQLine.supplier_rfq_id.in_(rfq_ids))
            .group_by(SupplierRFQLine.supplier_rfq_id)
        )
        for row in lc_result:
            line_counts[row.supplier_rfq_id] = row.cnt

    items = []
    for r in rfqs:
        resp = SupplierRFQResponse.model_validate(r)
        resp.supplier_name = supplier_map.get(r.supplier_id)
        resp.line_count = line_counts.get(r.id, 0)
        items.append(resp)

    return SupplierRFQListResponse(items=items, total=total)


@router.post("", response_model=SupplierRFQDetailResponse, status_code=201)
async def create_supplier_rfq(
    data: SupplierRFQCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_rfq", "create")),
):
    """创建供应商询价单（含明细行）"""
    # 验证供应商
    supplier = await session.get(Supplier, data.supplier_id)
    if not supplier:
        raise HTTPException(status_code=400, detail="供应商不存在")

    # 生成询价单编号
    rfq_no = data.rfq_no
    if not rfq_no:
        rfq_no = await generate_contract_number(session, "supplier_rfq", org_id=scope.org_id)

    rfq = SupplierRFQ(
        id=str(uuid4()),
        rfq_no=rfq_no,
        supplier_id=data.supplier_id,
        contact_id=data.contact_id,
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
        rfq_date=data.rfq_date,
        deadline=data.deadline,
        expiry_date=data.expiry_date,
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
        line = SupplierRFQLine(
            id=str(uuid4()),
            supplier_rfq_id=rfq.id,
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
        rfq.lines.append(line)

    session.add(rfq)
    await session.commit()
    await session.refresh(rfq, ["lines"])

    logger.info(f"[SupplierRFQsAPI] 创建供应商询价单: {rfq.rfq_no} by {scope.user.email}")

    resp = SupplierRFQDetailResponse.model_validate(rfq)
    resp.supplier_name = supplier.name
    resp.line_count = len(rfq.lines)
    resp.lines = [SupplierRFQLineResponse.model_validate(l) for l in rfq.lines]
    return resp


@router.get("/{rfq_id}", response_model=SupplierRFQDetailResponse)
async def get_supplier_rfq(
    rfq_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_rfq", "read")),
):
    """获取供应商询价单详情（含明细行）"""
    query = (
        select(SupplierRFQ)
        .options(selectinload(SupplierRFQ.lines))
        .where(SupplierRFQ.id == rfq_id)
    )
    query = await apply_data_scope(query, SupplierRFQ, "supplier_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="供应商询价单不存在")

    # 查询供应商名称
    supplier = await session.get(Supplier, rfq.supplier_id)

    resp = SupplierRFQDetailResponse.model_validate(rfq)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = len(rfq.lines)
    resp.lines = [SupplierRFQLineResponse.model_validate(l) for l in rfq.lines]
    return resp


@router.put("/{rfq_id}", response_model=SupplierRFQResponse)
async def update_supplier_rfq(
    rfq_id: str,
    data: SupplierRFQUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_rfq", "update")),
):
    """更新供应商询价单（不含明细行，明细行通过单独接口更新）"""
    query = select(SupplierRFQ).where(SupplierRFQ.id == rfq_id)
    query = await apply_data_scope(query, SupplierRFQ, "supplier_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="供应商询价单不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rfq, key, value)

    rfq.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(rfq)

    # 查询关联信息
    supplier = await session.get(Supplier, rfq.supplier_id)
    line_count = await session.scalar(
        select(func.count(SupplierRFQLine.id)).where(SupplierRFQLine.supplier_rfq_id == rfq_id)
    ) or 0

    logger.info(f"[SupplierRFQsAPI] 更新供应商询价单: {rfq.rfq_no} by {scope.user.email}")

    resp = SupplierRFQResponse.model_validate(rfq)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = line_count
    return resp


@router.delete("/{rfq_id}")
async def delete_supplier_rfq(
    rfq_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_rfq", "delete")),
):
    """删除供应商询价单（级联删除明细行）"""
    query = select(SupplierRFQ).where(SupplierRFQ.id == rfq_id)
    query = await apply_data_scope(query, SupplierRFQ, "supplier_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="供应商询价单不存在")

    rfq_no = rfq.rfq_no
    await session.delete(rfq)
    await session.commit()

    logger.info(f"[SupplierRFQsAPI] 删除供应商询价单: {rfq_no} by {scope.user.email}")
    return {"message": "删除成功"}


@router.put("/{rfq_id}/status", response_model=SupplierRFQResponse)
async def update_supplier_rfq_status(
    rfq_id: str,
    data: SupplierRFQStatusUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_rfq", "update")),
):
    """变更供应商询价单状态"""
    query = select(SupplierRFQ).where(SupplierRFQ.id == rfq_id)
    query = await apply_data_scope(query, SupplierRFQ, "supplier_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="供应商询价单不存在")

    old_status = rfq.status
    rfq.status = data.status
    rfq.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(rfq)

    logger.info(
        f"[SupplierRFQsAPI] 状态变更: {rfq.rfq_no} "
        f"{old_status} → {data.status} by {scope.user.email}"
    )

    supplier = await session.get(Supplier, rfq.supplier_id)
    line_count = await session.scalar(
        select(func.count(SupplierRFQLine.id)).where(SupplierRFQLine.supplier_rfq_id == rfq_id)
    ) or 0

    resp = SupplierRFQResponse.model_validate(rfq)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = line_count
    return resp


@router.put("/{rfq_id}/lines", response_model=SupplierRFQDetailResponse)
async def update_supplier_rfq_lines(
    rfq_id: str,
    lines: list[SupplierRFQLineCreate],
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("supplier_rfq", "update")),
):
    """
    整体更新供应商询价单明细行

    删除旧的明细行，创建新的明细行（整体替换策略）。
    """
    query = (
        select(SupplierRFQ)
        .options(selectinload(SupplierRFQ.lines))
        .where(SupplierRFQ.id == rfq_id)
    )
    query = await apply_data_scope(query, SupplierRFQ, "supplier_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="供应商询价单不存在")

    # 删除旧明细行
    rfq.lines.clear()
    await session.flush()

    # 创建新明细行
    for idx, line_data in enumerate(lines, start=1):
        line = SupplierRFQLine(
            id=str(uuid4()),
            supplier_rfq_id=rfq.id,
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
        rfq.lines.append(line)

    rfq.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(rfq, ["lines"])

    logger.info(
        f"[SupplierRFQsAPI] 更新明细行: {rfq.rfq_no} "
        f"({len(rfq.lines)} 行) by {scope.user.email}"
    )

    supplier = await session.get(Supplier, rfq.supplier_id)
    resp = SupplierRFQDetailResponse.model_validate(rfq)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = len(rfq.lines)
    resp.lines = [SupplierRFQLineResponse.model_validate(l) for l in rfq.lines]
    return resp
