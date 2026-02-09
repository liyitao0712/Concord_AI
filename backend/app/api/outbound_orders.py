# app/api/outbound_orders.py
# 出仓单管理 API
#
# 路由：
#   GET    /admin/outbound-orders              列表
#   POST   /admin/outbound-orders              创建
#   GET    /admin/outbound-orders/{id}         详情
#   PUT    /admin/outbound-orders/{id}         更新
#   DELETE /admin/outbound-orders/{id}         删除
#   PUT    /admin/outbound-orders/{id}/status  变更状态
#   POST   /admin/outbound-orders/{id}/confirm-ship  确认出仓

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
from app.models.customer import Customer
from app.models.sales_contract import SalesContract, SalesLine
from app.models.outbound_order import OutboundOrder, OutboundLine
from app.services.contract_number import generate_contract_number
from app.services.inventory_service import InventoryService

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/outbound-orders", tags=["出仓单"])


# ==================== Schema ====================

class OutboundLineCreate(BaseModel):
    product_id: str = Field(..., description="产品 ID")
    sales_line_id: Optional[str] = Field(None, description="关联销售明细行 ID")
    quantity: float = Field(..., gt=0, description="出仓数量")
    unit: str = Field(..., min_length=1, max_length=50, description="单位")
    notes: Optional[str] = Field(None, description="备注")


class OutboundLineResponse(BaseModel):
    id: str
    outbound_order_id: str
    product_id: str
    sales_line_id: Optional[str] = None
    quantity: float
    shipped_quantity: float = 0
    unit: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class OutboundOrderCreate(BaseModel):
    order_no: Optional[str] = Field(None, max_length=50, description="出仓单号（不填则自动生成）")
    warehouse_id: str = Field(..., description="出仓仓库 ID")
    sales_contract_id: Optional[str] = Field(None, description="关联销售合同 ID")
    customer_id: Optional[str] = Field(None, description="客户 ID")
    expected_date: Optional[date_type] = Field(None, description="预计发货日期")
    notes: Optional[str] = Field(None, description="备注")
    lines: List[OutboundLineCreate] = Field(default=[], description="明细行")


class OutboundOrderResponse(BaseModel):
    id: str
    order_no: str
    warehouse_id: str
    sales_contract_id: Optional[str] = None
    customer_id: Optional[str] = None
    status: str
    expected_date: Optional[date_type] = None
    actual_date: Optional[date_type] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    warehouse_name: Optional[str] = Field(None, description="仓库名称")
    customer_name: Optional[str] = Field(None, description="客户名称")
    sales_contract_no: Optional[str] = Field(None, description="销售合同编号")
    line_count: int = Field(default=0, description="明细行数量")
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class OutboundOrderDetailResponse(OutboundOrderResponse):
    lines: List[OutboundLineResponse] = Field(default=[], description="明细行")


class OutboundOrderListResponse(BaseModel):
    items: List[OutboundOrderResponse]
    total: int


class OutboundOrderUpdate(BaseModel):
    warehouse_id: Optional[str] = None
    sales_contract_id: Optional[str] = None
    customer_id: Optional[str] = None
    expected_date: Optional[date_type] = None
    notes: Optional[str] = None


class OutboundStatusUpdate(BaseModel):
    status: str = Field(..., description="新状态")

    @staticmethod
    def validate_status(v):
        allowed = {"draft", "confirmed", "partial_shipped", "shipped", "cancelled"}
        if v not in allowed:
            raise ValueError(f"状态必须是: {', '.join(sorted(allowed))}")
        return v


class ConfirmShipLine(BaseModel):
    outbound_line_id: str = Field(..., description="出仓明细行 ID")
    quantity: float = Field(..., gt=0, description="出仓数量")


class ConfirmShipRequest(BaseModel):
    lines: List[ConfirmShipLine] = Field(..., description="出仓明细")
    actual_date: Optional[date_type] = Field(None, description="实际发货日期")


# ==================== API ====================

@router.get("", response_model=OutboundOrderListResponse)
async def list_outbound_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索单号"),
    status: Optional[str] = Query(None),
    warehouse_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("outbound_order", "read")),
):
    """获取出仓单列表"""
    query = select(OutboundOrder).order_by(OutboundOrder.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, OutboundOrder, "outbound_order", scope, session)

    if search:
        query = query.where(OutboundOrder.order_no.ilike(f"%{search}%"))
    if status is not None:
        query = query.where(OutboundOrder.status == status)
    if warehouse_id is not None:
        query = query.where(OutboundOrder.warehouse_id == warehouse_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    orders = list(result.scalars().all())

    # 批量查询关联信息
    order_ids = [o.id for o in orders]
    wh_ids = list({o.warehouse_id for o in orders})
    cust_ids = list({o.customer_id for o in orders if o.customer_id})
    sc_ids = list({o.sales_contract_id for o in orders if o.sales_contract_id})

    wh_map: dict[str, str] = {}
    cust_map: dict[str, str] = {}
    sc_map: dict[str, str] = {}
    line_counts: dict[str, int] = {}

    if wh_ids:
        r = await session.execute(select(Warehouse.id, Warehouse.name).where(Warehouse.id.in_(wh_ids)))
        wh_map = {row.id: row.name for row in r}
    if cust_ids:
        r = await session.execute(select(Customer.id, Customer.name).where(Customer.id.in_(cust_ids)))
        cust_map = {row.id: row.name for row in r}
    if sc_ids:
        r = await session.execute(select(SalesContract.id, SalesContract.contract_no).where(SalesContract.id.in_(sc_ids)))
        sc_map = {row.id: row.contract_no for row in r}
    if order_ids:
        r = await session.execute(
            select(OutboundLine.outbound_order_id, func.count(OutboundLine.id).label("cnt"))
            .where(OutboundLine.outbound_order_id.in_(order_ids))
            .group_by(OutboundLine.outbound_order_id)
        )
        line_counts = {row.outbound_order_id: row.cnt for row in r}

    items = []
    for o in orders:
        resp = OutboundOrderResponse.model_validate(o)
        resp.warehouse_name = wh_map.get(o.warehouse_id)
        resp.customer_name = cust_map.get(o.customer_id) if o.customer_id else None
        resp.sales_contract_no = sc_map.get(o.sales_contract_id) if o.sales_contract_id else None
        resp.line_count = line_counts.get(o.id, 0)
        items.append(resp)

    return OutboundOrderListResponse(items=items, total=total)


@router.post("", response_model=OutboundOrderDetailResponse, status_code=201)
async def create_outbound_order(
    data: OutboundOrderCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("outbound_order", "create")),
):
    """创建出仓单"""
    warehouse = await session.get(Warehouse, data.warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=400, detail="仓库不存在")

    order_no = data.order_no
    if not order_no:
        order_no = await generate_contract_number(session, "outbound_order", org_id=scope.org_id)

    order = OutboundOrder(
        id=str(uuid4()),
        order_no=order_no,
        warehouse_id=data.warehouse_id,
        sales_contract_id=data.sales_contract_id,
        customer_id=data.customer_id,
        status="draft",
        expected_date=data.expected_date,
        notes=data.notes,
        created_by=scope.user.id,
        org_id=scope.org_id,
        owner_id=scope.user.id,
        owner_dept_id=scope.user.department_id,
    )

    for line_data in data.lines:
        line = OutboundLine(
            id=str(uuid4()),
            outbound_order_id=order.id,
            product_id=line_data.product_id,
            sales_line_id=line_data.sales_line_id,
            quantity=line_data.quantity,
            unit=line_data.unit,
            notes=line_data.notes,
        )
        order.lines.append(line)

    session.add(order)
    await session.commit()
    await session.refresh(order, ["lines"])

    logger.info(f"[OutboundOrdersAPI] 创建出仓单: {order.order_no} by {scope.user.email}")

    resp = OutboundOrderDetailResponse.model_validate(order)
    resp.warehouse_name = warehouse.name
    resp.line_count = len(order.lines)
    resp.lines = [OutboundLineResponse.model_validate(l) for l in order.lines]
    return resp


@router.get("/{order_id}", response_model=OutboundOrderDetailResponse)
async def get_outbound_order(
    order_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("outbound_order", "read")),
):
    """获取出仓单详情"""
    query = (
        select(OutboundOrder)
        .options(selectinload(OutboundOrder.lines))
        .where(OutboundOrder.id == order_id)
    )
    query = await apply_data_scope(query, OutboundOrder, "outbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="出仓单不存在")

    warehouse = await session.get(Warehouse, order.warehouse_id)
    customer = await session.get(Customer, order.customer_id) if order.customer_id else None
    sc = await session.get(SalesContract, order.sales_contract_id) if order.sales_contract_id else None

    resp = OutboundOrderDetailResponse.model_validate(order)
    resp.warehouse_name = warehouse.name if warehouse else None
    resp.customer_name = customer.name if customer else None
    resp.sales_contract_no = sc.contract_no if sc else None
    resp.line_count = len(order.lines)
    resp.lines = [OutboundLineResponse.model_validate(l) for l in order.lines]
    return resp


@router.put("/{order_id}", response_model=OutboundOrderResponse)
async def update_outbound_order(
    order_id: str,
    data: OutboundOrderUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("outbound_order", "update")),
):
    """更新出仓单"""
    query = select(OutboundOrder).where(OutboundOrder.id == order_id)
    query = await apply_data_scope(query, OutboundOrder, "outbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="出仓单不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)

    order.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(order)

    logger.info(f"[OutboundOrdersAPI] 更新出仓单: {order.order_no} by {scope.user.email}")

    resp = OutboundOrderResponse.model_validate(order)
    return resp


@router.delete("/{order_id}")
async def delete_outbound_order(
    order_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("outbound_order", "delete")),
):
    """删除出仓单"""
    query = select(OutboundOrder).where(OutboundOrder.id == order_id)
    query = await apply_data_scope(query, OutboundOrder, "outbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="出仓单不存在")

    order_no = order.order_no
    await session.delete(order)
    await session.commit()

    logger.info(f"[OutboundOrdersAPI] 删除出仓单: {order_no} by {scope.user.email}")
    return {"message": "删除成功"}


@router.put("/{order_id}/status", response_model=OutboundOrderResponse)
async def update_outbound_order_status(
    order_id: str,
    data: OutboundStatusUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("outbound_order", "update")),
):
    """变更出仓单状态"""
    OutboundStatusUpdate.validate_status(data.status)

    query = select(OutboundOrder).where(OutboundOrder.id == order_id)
    query = await apply_data_scope(query, OutboundOrder, "outbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="出仓单不存在")

    old_status = order.status
    order.status = data.status
    order.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(order)

    logger.info(
        f"[OutboundOrdersAPI] 状态变更: {order.order_no} {old_status} → {data.status} by {scope.user.email}"
    )

    resp = OutboundOrderResponse.model_validate(order)
    return resp


@router.post("/{order_id}/confirm-ship", response_model=OutboundOrderDetailResponse)
async def confirm_ship(
    order_id: str,
    data: ConfirmShipRequest,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("outbound_order", "update")),
):
    """
    确认出仓

    减少仓库库存，释放库存占用，
    同步更新关联销售合同的发货数量。
    """
    query = (
        select(OutboundOrder)
        .options(selectinload(OutboundOrder.lines))
        .where(OutboundOrder.id == order_id)
    )
    query = await apply_data_scope(query, OutboundOrder, "outbound_order", scope, session)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="出仓单不存在")

    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="已取消的出仓单无法出仓")

    line_map = {l.id: l for l in order.lines}

    for item in data.lines:
        line = line_map.get(item.outbound_line_id)
        if not line:
            raise HTTPException(status_code=400, detail=f"出仓明细行 {item.outbound_line_id} 不存在")

        # 更新出仓明细行的已发货数量
        line.shipped_quantity = float(line.shipped_quantity) + item.quantity
        line.updated_at = datetime.utcnow()

        # 减少库存
        try:
            await InventoryService.decrease_stock(
                session,
                warehouse_id=order.warehouse_id,
                product_id=line.product_id,
                quantity=item.quantity,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 如果有关联销售明细行，更新发货数量并释放占用
        if line.sales_line_id:
            sales_line = await session.get(SalesLine, line.sales_line_id)
            if sales_line:
                sales_line.shipped_quantity = float(sales_line.shipped_quantity) + item.quantity
                # 释放对应的库存占用
                if float(sales_line.reserved_quantity) > 0:
                    release_qty = min(item.quantity, float(sales_line.reserved_quantity))
                    await InventoryService.release_stock(
                        session,
                        warehouse_id=order.warehouse_id,
                        product_id=line.product_id,
                        quantity=release_qty,
                    )
                    sales_line.reserved_quantity = float(sales_line.reserved_quantity) - release_qty
                sales_line.updated_at = datetime.utcnow()

    # 更新出仓单
    if data.actual_date:
        order.actual_date = data.actual_date

    # 基于累计已发货数量判断状态
    all_shipped = all(
        float(l.shipped_quantity) >= float(l.quantity)
        for l in order.lines
    )
    any_shipped = any(float(l.shipped_quantity) > 0 for l in order.lines)

    if all_shipped:
        order.status = "shipped"
    elif any_shipped:
        order.status = "partial_shipped"

    order.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(order, ["lines"])

    logger.info(f"[OutboundOrdersAPI] 确认出仓: {order.order_no} by {scope.user.email}")

    warehouse = await session.get(Warehouse, order.warehouse_id)
    resp = OutboundOrderDetailResponse.model_validate(order)
    resp.warehouse_name = warehouse.name if warehouse else None
    resp.line_count = len(order.lines)
    resp.lines = [OutboundLineResponse.model_validate(l) for l in order.lines]
    return resp
