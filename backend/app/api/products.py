# app/api/products.py
# 产品管理 API
#
# 功能说明：
# 1. 产品 CRUD
# 2. 产品-供应商关联管理
# 3. 搜索、筛选、分页
#
# 路由：
#   GET    /admin/products                              产品列表
#   POST   /admin/products                              创建产品
#   GET    /admin/products/{id}                         产品详情（含供应商）
#   PUT    /admin/products/{id}                         更新产品
#   DELETE /admin/products/{id}                         删除产品
#   POST   /admin/products/{id}/suppliers               添加供应商关联
#   PUT    /admin/products/{id}/suppliers/{supplier_id}  更新供应商关联
#   DELETE /admin/products/{id}/suppliers/{supplier_id}  移除供应商关联

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.category import Category
from app.models.product import Product, ProductSupplier
from app.models.supplier import Supplier
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ProductDetailResponse,
    ProductSupplierCreate,
    ProductSupplierUpdate,
    ProductSupplierResponse,
)

logger = get_logger(__name__)


# ==================== 产品 CRUD ====================

router = APIRouter(prefix="/admin/products", tags=["产品管理"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（品名/型号/HS编码）"),
    category_id: Optional[str] = Query(None, description="筛选品类"),
    status: Optional[str] = Query(None, description="筛选状态"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    获取产品列表

    支持搜索、筛选和分页
    """
    query = select(Product).order_by(Product.created_at.desc())

    # 搜索：品名、型号、HS编码
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Product.name.ilike(search_filter),
                Product.model_number.ilike(search_filter),
                Product.hs_code.ilike(search_filter),
            )
        )

    # 筛选
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if status is not None:
        query = query.where(Product.status == status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    products = list(result.scalars().all())

    # 批量查询品类名称
    category_ids = list(set(p.category_id for p in products if p.category_id))
    category_names: dict[str, str] = {}
    if category_ids:
        cat_result = await session.execute(
            select(Category.id, Category.name).where(Category.id.in_(category_ids))
        )
        for row in cat_result:
            category_names[row.id] = row.name

    # 批量查询供应商数量
    product_ids = [p.id for p in products]
    supplier_counts: dict[str, int] = {}
    if product_ids:
        sc_result = await session.execute(
            select(
                ProductSupplier.product_id,
                func.count(ProductSupplier.id).label("cnt"),
            )
            .where(ProductSupplier.product_id.in_(product_ids))
            .group_by(ProductSupplier.product_id)
        )
        for row in sc_result:
            supplier_counts[row.product_id] = row.cnt

    # 构建响应
    items = []
    for p in products:
        resp = ProductResponse.model_validate(p)
        resp.category_name = category_names.get(p.category_id) if p.category_id else None
        resp.supplier_count = supplier_counts.get(p.id, 0)
        items.append(resp)

    return ProductListResponse(items=items, total=total)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """创建产品"""
    # 验证品类存在
    if data.category_id:
        category = await session.get(Category, data.category_id)
        if not category:
            raise HTTPException(status_code=400, detail="品类不存在")

    product = Product(
        id=str(uuid4()),
        category_id=data.category_id,
        name=data.name,
        model_number=data.model_number,
        specifications=data.specifications,
        unit=data.unit,
        moq=data.moq,
        reference_price=data.reference_price,
        currency=data.currency,
        hs_code=data.hs_code,
        origin=data.origin,
        material=data.material,
        packaging=data.packaging,
        images=data.images,
        description=data.description,
        tags=data.tags,
        status=data.status,
        notes=data.notes,
    )

    session.add(product)
    await session.commit()
    await session.refresh(product)

    logger.info(f"[ProductsAPI] 创建产品: {product.name} by {admin.email}")

    # 查询品类名称
    category_name = None
    if product.category_id:
        category = await session.get(Category, product.category_id)
        if category:
            category_name = category.name

    resp = ProductResponse.model_validate(product)
    resp.category_name = category_name
    resp.supplier_count = 0
    return resp


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取产品详情（含关联供应商列表）"""
    result = await session.execute(
        select(Product)
        .options(selectinload(Product.product_suppliers))
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 查询品类名称
    category_name = None
    if product.category_id:
        category = await session.get(Category, product.category_id)
        if category:
            category_name = category.name

    # 查询供应商名称
    supplier_ids = [ps.supplier_id for ps in product.product_suppliers]
    supplier_names: dict[str, str] = {}
    if supplier_ids:
        s_result = await session.execute(
            select(Supplier.id, Supplier.name).where(Supplier.id.in_(supplier_ids))
        )
        for row in s_result:
            supplier_names[row.id] = row.name

    # 构建供应商列表
    suppliers = []
    for ps in product.product_suppliers:
        ps_resp = ProductSupplierResponse.model_validate(ps)
        ps_resp.supplier_name = supplier_names.get(ps.supplier_id)
        suppliers.append(ps_resp)

    resp = ProductDetailResponse.model_validate(product)
    resp.category_name = category_name
    resp.supplier_count = len(suppliers)
    resp.suppliers = suppliers
    return resp


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """更新产品"""
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 验证品类存在
    if "category_id" in update_data and update_data["category_id"]:
        category = await session.get(Category, update_data["category_id"])
        if not category:
            raise HTTPException(status_code=400, detail="品类不存在")

    for key, value in update_data.items():
        setattr(product, key, value)

    product.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(product)

    logger.info(f"[ProductsAPI] 更新产品: {product.name} by {admin.email}")

    # 查询品类名称和供应商数量
    category_name = None
    if product.category_id:
        category = await session.get(Category, product.category_id)
        if category:
            category_name = category.name

    supplier_count = await session.scalar(
        select(func.count(ProductSupplier.id)).where(ProductSupplier.product_id == product_id)
    ) or 0

    resp = ProductResponse.model_validate(product)
    resp.category_name = category_name
    resp.supplier_count = supplier_count
    return resp


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """删除产品（级联删除供应商关联）"""
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    product_name = product.name
    await session.delete(product)
    await session.commit()

    logger.info(f"[ProductsAPI] 删除产品: {product_name} by {admin.email}")
    return {"message": "删除成功"}


# ==================== 产品-供应商关联管理 ====================


@router.post("/{product_id}/suppliers", response_model=ProductSupplierResponse, status_code=201)
async def add_product_supplier(
    product_id: str,
    data: ProductSupplierCreate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """添加产品-供应商关联"""
    # 验证产品存在
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 验证供应商存在
    supplier = await session.get(Supplier, data.supplier_id)
    if not supplier:
        raise HTTPException(status_code=400, detail="供应商不存在")

    # 检查是否已关联
    existing = await session.execute(
        select(ProductSupplier).where(
            ProductSupplier.product_id == product_id,
            ProductSupplier.supplier_id == data.supplier_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该供应商已关联此产品")

    # 如果设为首选，清除其他首选
    if data.is_primary:
        await _clear_primary_supplier(session, product_id)

    ps = ProductSupplier(
        id=str(uuid4()),
        product_id=product_id,
        supplier_id=data.supplier_id,
        supply_price=data.supply_price,
        currency=data.currency,
        moq=data.moq,
        lead_time=data.lead_time,
        is_primary=data.is_primary,
        notes=data.notes,
    )

    session.add(ps)
    await session.commit()
    await session.refresh(ps)

    logger.info(
        f"[ProductsAPI] 产品 {product.name} 关联供应商 {supplier.name} by {admin.email}"
    )

    resp = ProductSupplierResponse.model_validate(ps)
    resp.supplier_name = supplier.name
    return resp


@router.put("/{product_id}/suppliers/{supplier_id}", response_model=ProductSupplierResponse)
async def update_product_supplier(
    product_id: str,
    supplier_id: str,
    data: ProductSupplierUpdate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """更新产品-供应商关联"""
    result = await session.execute(
        select(ProductSupplier).where(
            ProductSupplier.product_id == product_id,
            ProductSupplier.supplier_id == supplier_id,
        )
    )
    ps = result.scalar_one_or_none()
    if not ps:
        raise HTTPException(status_code=404, detail="产品-供应商关联不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 如果设为首选，清除其他首选
    if update_data.get("is_primary") is True:
        await _clear_primary_supplier(session, product_id, exclude_id=ps.id)

    for key, value in update_data.items():
        setattr(ps, key, value)

    ps.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(ps)

    # 查询供应商名称
    supplier = await session.get(Supplier, supplier_id)

    logger.info(f"[ProductsAPI] 更新产品供应商关联 by {admin.email}")

    resp = ProductSupplierResponse.model_validate(ps)
    resp.supplier_name = supplier.name if supplier else None
    return resp


@router.delete("/{product_id}/suppliers/{supplier_id}")
async def remove_product_supplier(
    product_id: str,
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """移除产品-供应商关联"""
    result = await session.execute(
        select(ProductSupplier).where(
            ProductSupplier.product_id == product_id,
            ProductSupplier.supplier_id == supplier_id,
        )
    )
    ps = result.scalar_one_or_none()
    if not ps:
        raise HTTPException(status_code=404, detail="产品-供应商关联不存在")

    await session.delete(ps)
    await session.commit()

    logger.info(f"[ProductsAPI] 移除产品供应商关联 by {admin.email}")
    return {"message": "移除成功"}


# ==================== 辅助函数 ====================

async def _clear_primary_supplier(
    session: AsyncSession,
    product_id: str,
    exclude_id: Optional[str] = None,
):
    """清除某产品的首选供应商标记"""
    query = select(ProductSupplier).where(
        ProductSupplier.product_id == product_id,
        ProductSupplier.is_primary == True,
    )
    if exclude_id:
        query = query.where(ProductSupplier.id != exclude_id)

    result = await session.execute(query)
    for ps in result.scalars().all():
        ps.is_primary = False
