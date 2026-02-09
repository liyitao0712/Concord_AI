# app/api/inbound_orders.py
# 入仓单管理 API
#
# 路由：
#   GET    /admin/inbound-orders              列表
#   POST   /admin/inbound-orders              创建
#   GET    /admin/inbound-orders/{id}         详情
#   PUT    /admin/inbound-orders/{id}         更新
#   DELETE /admin/inbound-orders/{id}         删除
#   PUT    /admin/inbound-orders/{id}/status  变更状态
#   POST   /admin/inbound-orders/{id}/confirm-receive  确认收货

from datetime import datetime, date as date_type
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user, require_permission, apply_data_scope, DataScope
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.supplier import Supplier
from app.models.purchase_contract import PurchaseContract, PurchaseLine
from app.models.inbound_order import InboundOrder, InboundLine
from app.services.contract_number import generate_contract_number
from app.services.inventory_service import InventoryService

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/inbound-orders", tags=["入仓单"])


# ==================== Schema ====================

class InboundLineCreate(BaseModel):
    product_id: str = Field(..., description="产品 ID")
    purchase_line_id: Optional[str] = Field(None, description="关联采购明细行 ID")
    expected_quantity: float = Field(..., gt=0, description="预期数量")
    unit: str = Field(..., min_length=1, max_length=50, description="单位")
    notes: Optional[str] = Field(None, description="备注")


class InboundLineResponse(BaseModel):
    id: str
    inbound_order_id: str
    product_id: str
    purchase_line_id: Optional[str] = None
    expected_quantity: float
    received_quantity: float = 0
    unit: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class InboundOrderCreate(BaseModel):
    order_no: Optional[str] = Field(None, max_length=50, description="入仓单号（不填则自动生成）")
    warehouse_id: str = Field(..., description="目标仓库 ID")
    purchase_contract_id: Optional[str] = Field(None, description="关联采购合同 ID")
    supplier_id: Optional[str] = Field(None, description="供应商 ID")
    expected_date: Optional[date_type] = Field(None, description="预计到货日期")
    notes: Optional[str] = Field(None, description="备注")
    lines: List[InboundLineCreate] = Field(default=[], description="明细行")


class InboundOrderResponse(BaseModel):
    id: str
    order_no: str
    warehouse_id: str
    purchase_contract_id: Optional[str] = None
    supplier_id: Optional[str] = None
    status: str
    expected_date: Optional[date_type] = None
    actual_date: Optional[date_type] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    warehouse_name: Optional[str] = Field(None, description="仓库名称")
    supplier_name: Optional[str] = Field(None, description="供应商名称")
    purchase_contract_no: Optional[str] = Field(None, description="采购合同编号")
    line_count: int = Field(default=0, description="明细行数量")
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class InboundOrderDetailResponse(InboundOrderResponse):
    lines: List[InboundLineResponse] = Field(default=[], description="明细行")


class InboundOrderListResponse(BaseModel):
    items: List[InboundOrderResponse]
    total: int


class InboundOrderUpdate(BaseModel):
    warehouse_id: Optional[str] = None
    purchase_contract_id: Optional[str] = None
    supplier_id: Optional[str] = None
    expected_date: Optional[date_type] = None
    notes: Optional[str] = None


class InboundStatusUpdate(BaseModel):
    status: str = Field(..., description="新状态")

    @staticmethod
    def validate_status(v):
        allowed = {"draft", "confirmed", "partial_received", "received", "cancelled"}
        if v not in allowed:
            raise ValueError(f"状态必须是: {', '.join(sorted(allowed))}")
        return v


class ConfirmReceiveLine(BaseModel):
    inbound_line_id: str = Field(..., description="入仓明细行 ID")
    received_quantity: float = Field(..., gt=0, description="实收数量")


class ConfirmReceiveRequest(BaseModel):
    lines: List[ConfirmReceiveLine] = Field(..., description="收货明细")
    actual_date: Optional[date_type] = Field(None, description="实际到货日期")


# ==================== API ====================

@router.get("", response_model=InboundOrderListResponse)
async def list_inbound_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索单号"),
    status: Optional[str] = Query(None),
    warehouse_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("inbound_order", "read")),
):
    """获取入仓单列表"""
    query = select(InboundOrder).order_by(InboundOrder.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, InboundOrder, "inbound_order", scope, session)

    if search:
        query = query.where(InboundOrder.order_no.ilike(f"%{search}%"))
    if status is not None:
        query = query.where(InboundOrder.status == status)
    if warehouse_id is not None:
        query = query.where(InboundOrder.warehouse_id == warehouse_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    orders = list(result.scalars().all())

    # 批量查询关联信息
    order_ids = [o.id for o in orders]
    wh_ids = list({o.warehouse_id for o in orders})
    sp_ids = list({o.supplier_id for o in orders if o.supplier_id})
    pc_ids = list({o.purchase_contract_id for o in orders if o.purchase_contract_id})

    wh_map: dict[str, str] = {}
    sp_map: dict[str, str] = {}
    pc_map: dict[str, str] = {}
    line_counts: dict[str, int] = {}

    if wh_ids:
        r = await session.execute(select(Warehouse.id, Warehouse.name).where(Warehouse.id.in_(wh_ids)))
        wh_map = {row.id: row.name for row in r}
    if sp_ids:
        r = await session.execute(select(Supplier.id, Supplier.name).where(Supplier.id.in_(sp_ids)))
        sp_map = {row.id: row.name for row in r}
    if pc_ids:
        r = await session.execute(select(PurchaseContract.id, PurchaseContract.contract_no).where(PurchaseContract.id.in_(pc_ids)))
        pc_map = {row.id: row.contract_no for row in r}
    if order_ids:
        r = await session.execute(
            select(InboundLine.inbound_order_id, func.count(InboundLine.id).label("cnt"))
            .where(InboundLine.inbound_order_id.in_(order_ids))
            .group_by(InboundLine.inbound_order_id)
        )
        line_counts = {row.inbound_order_id: row.cnt for row in r}

    items = []
    for o in orders:
        resp = InboundOrderResponse.model_validate(o)
        resp.warehouse_name = wh_map.get(o.warehouse_id)
        resp.supplier_name = sp_map.get(o.supplier_id) if o.supplier_id else None
        resp.purchase_contract_no = pc_map.get(o.purchase_contract_id) if o.purchase_contract_id else None
        resp.line_count = line_counts.get(o.id, 0)
        items.append(resp)

    return InboundOrderListResponse(items=items, total=total)


@router.post("", response_model=InboundOrderDetailResponse, status_code=201)
async def create_inbound_order(
    data: InboundOrderCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("inbound_order", "create")),
):
    """创建入仓单"""
    # 验证仓库
    warehouse = await session.get(Warehouse, data.warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=400, detail="仓库不存在")

    order_no = data.order_no
    if not order_no:
        order_no = await generate_contract_number(session, "inbound_order", org_id=scope.org_id)

    order = InboundOrder(
        id=str(uuid4()),
        order_no=order_no,
        warehouse_id=data.warehouse_id,
        purchase_contract_id=data.purchase_contract_id,
        supplier_id=data.supplier_id,
        status="draft",
        expected_date=data.expected_date,
        notes=data.notes,
        created_by=scope.user.id,
        org_id=scope.org_id,
        owner_id=scope.user.id,
        owner_dept_id=scope.user.department_id,
    )

    for line_data in data.lines:
        line = InboundLine(
            id=str(uuid4()),
            inbound_order_id=order.id,
            product_id=line_data.product_id,
            purchase_line_id=line_data.purchase_line_id,
            expected_quantity=line_data.expected_quantity,
            received_quantity=0,
            unit=line_data.unit,
            notes=line_data.notes,
        )
        order.lines.append(line)

    session.add(order)
    await session.commit()
    await session.refresh(order, ["lines"])

    logger.info(f"[InboundOrdersAPI] 创建入仓单: {order.order_no} by {scope.user.email}")

    resp = InboundOrderDetailResponse.model_validate(order)
    resp.warehouse_name = warehouse.name
    resp.line_count = len(order.lines)
    resp.lines = [InboundLineResponse.model_validate(l) for l in order.lines]
    return resp


@router.get("/{order_id}", response_model=InboundOrderDetailResponse)
async def get_inbound_order(
    order_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("inbound_order", "read")),
):
    """获取入仓单详情"""
    query = (
        select(InboundOrder)
        .options(selectinload(InboundOrder.lines))
        .where(InboundOrder.id == order_id)
    )
    query = await apply_data_scope(query, InboundOrder, "inbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="入仓单不存在")

    warehouse = await session.get(Warehouse, order.warehouse_id)
    supplier = await session.get(Supplier, order.supplier_id) if order.supplier_id else None
    pc = await session.get(PurchaseContract, order.purchase_contract_id) if order.purchase_contract_id else None

    resp = InboundOrderDetailResponse.model_validate(order)
    resp.warehouse_name = warehouse.name if warehouse else None
    resp.supplier_name = supplier.name if supplier else None
    resp.purchase_contract_no = pc.contract_no if pc else None
    resp.line_count = len(order.lines)
    resp.lines = [InboundLineResponse.model_validate(l) for l in order.lines]
    return resp


@router.put("/{order_id}", response_model=InboundOrderResponse)
async def update_inbound_order(
    order_id: str,
    data: InboundOrderUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("inbound_order", "update")),
):
    """更新入仓单"""
    query = select(InboundOrder).where(InboundOrder.id == order_id)
    query = await apply_data_scope(query, InboundOrder, "inbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="入仓单不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)

    order.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(order)

    logger.info(f"[InboundOrdersAPI] 更新入仓单: {order.order_no} by {scope.user.email}")

    resp = InboundOrderResponse.model_validate(order)
    return resp


@router.delete("/{order_id}")
async def delete_inbound_order(
    order_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("inbound_order", "delete")),
):
    """删除入仓单"""
    query = select(InboundOrder).where(InboundOrder.id == order_id)
    query = await apply_data_scope(query, InboundOrder, "inbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="入仓单不存在")

    order_no = order.order_no
    await session.delete(order)
    await session.commit()

    logger.info(f"[InboundOrdersAPI] 删除入仓单: {order_no} by {scope.user.email}")
    return {"message": "删除成功"}


@router.put("/{order_id}/status", response_model=InboundOrderResponse)
async def update_inbound_order_status(
    order_id: str,
    data: InboundStatusUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("inbound_order", "update")),
):
    """变更入仓单状态"""
    InboundStatusUpdate.validate_status(data.status)

    query = select(InboundOrder).where(InboundOrder.id == order_id)
    query = await apply_data_scope(query, InboundOrder, "inbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="入仓单不存在")

    old_status = order.status
    order.status = data.status
    order.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(order)

    logger.info(
        f"[InboundOrdersAPI] 状态变更: {order.order_no} {old_status} → {data.status} by {scope.user.email}"
    )

    resp = InboundOrderResponse.model_validate(order)
    return resp


@router.post("/{order_id}/confirm-receive", response_model=InboundOrderDetailResponse)
async def confirm_receive(
    order_id: str,
    data: ConfirmReceiveRequest,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("inbound_order", "update")),
):
    """
    确认收货

    更新入仓明细行的实收数量，增加仓库库存，
    同步更新关联采购合同的收货数量。
    """
    query = (
        select(InboundOrder)
        .options(selectinload(InboundOrder.lines))
        .where(InboundOrder.id == order_id)
    )
    query = await apply_data_scope(query, InboundOrder, "inbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="入仓单不存在")

    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="已取消的入仓单无法收货")

    # 构建入仓明细行映射
    line_map = {l.id: l for l in order.lines}

    for item in data.lines:
        line = line_map.get(item.inbound_line_id)
        if not line:
            raise HTTPException(status_code=400, detail=f"入仓明细行 {item.inbound_line_id} 不存在")

        # 更新实收数量
        line.received_quantity = float(line.received_quantity) + item.received_quantity
        line.updated_at = datetime.utcnow()

        # 增加库存
        await InventoryService.increase_stock(
            session,
            warehouse_id=order.warehouse_id,
            product_id=line.product_id,
            quantity=item.received_quantity,
            unit=line.unit,
        )

        # 同步采购合同收货数量
        if line.purchase_line_id:
            purchase_line = await session.get(PurchaseLine, line.purchase_line_id)
            if purchase_line:
                purchase_line.received_quantity = float(purchase_line.received_quantity) + item.received_quantity
                purchase_line.updated_at = datetime.utcnow()

    # 更新入仓单状态和日期
    if data.actual_date:
        order.actual_date = data.actual_date

    # 判断是否全部收货
    all_received = all(
        float(l.received_quantity) >= float(l.expected_quantity)
        for l in order.lines
    )
    any_received = any(float(l.received_quantity) > 0 for l in order.lines)

    if all_received:
        order.status = "received"
    elif any_received:
        order.status = "partial_received"

    order.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(order, ["lines"])

    logger.info(f"[InboundOrdersAPI] 确认收货: {order.order_no} by {scope.user.email}")

    warehouse = await session.get(Warehouse, order.warehouse_id)
    resp = InboundOrderDetailResponse.model_validate(order)
    resp.warehouse_name = warehouse.name if warehouse else None
    resp.line_count = len(order.lines)
    resp.lines = [InboundLineResponse.model_validate(l) for l in order.lines]
    return resp
