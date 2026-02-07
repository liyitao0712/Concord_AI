# app/api/categories.py
# 品类管理 API
#
# 功能说明：
# 1. 品类 CRUD
# 2. 品类树形结构查询
# 3. 品类编码自动生成
# 4. 删除保护（有子品类或产品时拒绝）
#
# 品类编码规则：
# - 根品类: 自动分配两位数字 "01", "02", ...
# - 子品类: 父编码-自动分配两位数字 "01-01", "01-02", ...
# - 也支持手动指定编码
#
# 路由：
#   GET    /admin/categories              品类列表（平铺，分页）
#   GET    /admin/categories/tree         品类树形结构
#   GET    /admin/categories/next-code    获取下一个可用编码
#   POST   /admin/categories              创建品类
#   GET    /admin/categories/{id}         品类详情
#   PUT    /admin/categories/{id}         更新品类
#   DELETE /admin/categories/{id}         删除品类

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.storage.oss import oss_client
from app.storage.local_file import local_storage
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
    CategoryTreeNode,
    CategoryTreeResponse,
)

logger = get_logger(__name__)


router = APIRouter(prefix="/admin/categories", tags=["品类管理"])


# ==================== 辅助函数 ====================

def _resolve_image_url(image_key: Optional[str], image_storage_type: Optional[str]) -> Optional[str]:
    """根据存储 key 和类型生成签名访问 URL"""
    if not image_key:
        return None
    try:
        if image_storage_type == "oss":
            return oss_client.get_signed_url(image_key, expires=3600)
        else:
            return local_storage.get_signed_url(image_key, expires=3600)
    except Exception:
        return None


async def _cleanup_image(image_key: Optional[str], image_storage_type: Optional[str]):
    """删除存储中的图片文件"""
    if not image_key:
        return
    try:
        if image_storage_type == "oss":
            await oss_client.delete(image_key)
        else:
            await local_storage.delete(image_key)
    except Exception as e:
        logger.warning(f"[CategoriesAPI] 清理图片失败 {image_key}: {e}")

async def _generate_next_code(session: AsyncSession, parent_id: Optional[str]) -> str:
    """
    自动生成下一个品类编码

    规则：
    - 根品类: "01", "02", "03", ...
    - 子品类: "{parent_code}-01", "{parent_code}-02", ...
    """
    if parent_id:
        # 查询父品类编码
        parent = await session.get(Category, parent_id)
        if not parent:
            raise HTTPException(status_code=400, detail="父品类不存在")
        parent_code = parent.code
        prefix = f"{parent_code}-"
    else:
        prefix = ""

    # 查询同级已有的编码
    if parent_id:
        query = select(Category.code).where(Category.parent_id == parent_id)
    else:
        query = select(Category.code).where(Category.parent_id.is_(None))

    result = await session.execute(query)
    existing_codes = [row[0] for row in result.all()]

    # 提取末尾数字部分，计算下一个编号
    max_num = 0
    for code in existing_codes:
        suffix = code[len(prefix):] if prefix else code
        # 只取第一段（直接子级的编号部分）
        parts = suffix.split("-")
        try:
            num = int(parts[0])
            if num > max_num:
                max_num = num
        except (ValueError, IndexError):
            continue

    next_num = max_num + 1
    return f"{prefix}{next_num:02d}"


@router.get("/next-code")
async def get_next_code(
    parent_id: Optional[str] = Query(None, description="父品类 ID，不填则生成根品类编码"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取下一个可用的品类编码"""
    code = await _generate_next_code(session, parent_id)
    return {"code": code}


@router.get("/tree", response_model=CategoryTreeResponse)
async def get_category_tree(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    获取品类树形结构

    一次性查出所有品类，在 Python 层构建树形结构，按编码排序
    """
    query = select(Category).order_by(Category.code)

    result = await session.execute(query)
    categories = list(result.scalars().all())

    # 查询每个品类的产品数量
    product_counts: dict[str, int] = {}
    if categories:
        cat_ids = [c.id for c in categories]
        count_result = await session.execute(
            select(
                Product.category_id,
                func.count(Product.id).label("cnt"),
            )
            .where(Product.category_id.in_(cat_ids))
            .group_by(Product.category_id)
        )
        for row in count_result:
            product_counts[row.category_id] = row.cnt

    # 构建树形结构
    nodes: dict[str, CategoryTreeNode] = {}
    for cat in categories:
        nodes[cat.id] = CategoryTreeNode(
            id=cat.id,
            code=cat.code,
            name=cat.name,
            name_en=cat.name_en,
            description=cat.description,
            vat_rate=float(cat.vat_rate) if cat.vat_rate is not None else None,
            tax_rebate_rate=float(cat.tax_rebate_rate) if cat.tax_rebate_rate is not None else None,
            image_url=_resolve_image_url(cat.image_key, cat.image_storage_type),
            product_count=product_counts.get(cat.id, 0),
            children=[],
        )

    root_nodes: list[CategoryTreeNode] = []
    for cat in categories:
        node = nodes[cat.id]
        if cat.parent_id and cat.parent_id in nodes:
            nodes[cat.parent_id].children.append(node)
        else:
            root_nodes.append(node)

    return CategoryTreeResponse(items=root_nodes)


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索品类名称/编码"),
    parent_id: Optional[str] = Query(None, description="筛选父品类 ID"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取品类列表（平铺，分页）"""
    query = select(Category).order_by(Category.code)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Category.name.ilike(search_filter),
                Category.name_en.ilike(search_filter),
                Category.code.ilike(search_filter),
            )
        )
    if parent_id is not None:
        query = query.where(Category.parent_id == parent_id)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    categories = list(result.scalars().all())

    # 批量查询产品数量和子品类数量
    cat_ids = [c.id for c in categories]
    product_counts: dict[str, int] = {}
    children_counts: dict[str, int] = {}

    if cat_ids:
        pc_result = await session.execute(
            select(
                Product.category_id,
                func.count(Product.id).label("cnt"),
            )
            .where(Product.category_id.in_(cat_ids))
            .group_by(Product.category_id)
        )
        for row in pc_result:
            product_counts[row.category_id] = row.cnt

        cc_result = await session.execute(
            select(
                Category.parent_id,
                func.count(Category.id).label("cnt"),
            )
            .where(Category.parent_id.in_(cat_ids))
            .group_by(Category.parent_id)
        )
        for row in cc_result:
            children_counts[row.parent_id] = row.cnt

    # 批量查询父品类名称
    parent_ids = list(set(c.parent_id for c in categories if c.parent_id))
    parent_names: dict[str, str] = {}
    if parent_ids:
        parent_result = await session.execute(
            select(Category.id, Category.name).where(Category.id.in_(parent_ids))
        )
        for row in parent_result:
            parent_names[row.id] = row.name

    # 构建响应
    items = []
    for cat in categories:
        resp = CategoryResponse.model_validate(cat)
        resp.product_count = product_counts.get(cat.id, 0)
        resp.children_count = children_counts.get(cat.id, 0)
        resp.parent_name = parent_names.get(cat.parent_id) if cat.parent_id else None
        resp.image_url = _resolve_image_url(cat.image_key, cat.image_storage_type)
        if cat.vat_rate is not None:
            resp.vat_rate = float(cat.vat_rate)
        if cat.tax_rebate_rate is not None:
            resp.tax_rebate_rate = float(cat.tax_rebate_rate)
        items.append(resp)

    return CategoryListResponse(items=items, total=total)


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """创建品类"""
    # 验证父品类存在
    if data.parent_id:
        parent = await session.get(Category, data.parent_id)
        if not parent:
            raise HTTPException(status_code=400, detail="父品类不存在")

    # 检查编码唯一性
    existing = await session.execute(
        select(Category).where(Category.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"品类编码 '{data.code}' 已存在")

    category = Category(
        id=str(uuid4()),
        code=data.code,
        name=data.name,
        name_en=data.name_en,
        parent_id=data.parent_id,
        description=data.description,
        vat_rate=data.vat_rate,
        tax_rebate_rate=data.tax_rebate_rate,
        image_key=data.image_key,
        image_storage_type=data.image_storage_type,
    )

    session.add(category)
    await session.commit()
    await session.refresh(category)

    logger.info(f"[CategoriesAPI] 创建品类: {category.code} {category.name} by {admin.email}")

    resp = CategoryResponse.model_validate(category)
    resp.product_count = 0
    resp.children_count = 0
    resp.image_url = _resolve_image_url(category.image_key, category.image_storage_type)
    if category.vat_rate is not None:
        resp.vat_rate = float(category.vat_rate)
    if category.tax_rebate_rate is not None:
        resp.tax_rebate_rate = float(category.tax_rebate_rate)
    return resp


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取品类详情"""
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="品类不存在")

    product_count = await session.scalar(
        select(func.count(Product.id)).where(Product.category_id == category_id)
    ) or 0

    children_count = await session.scalar(
        select(func.count(Category.id)).where(Category.parent_id == category_id)
    ) or 0

    parent_name = None
    if category.parent_id:
        parent = await session.get(Category, category.parent_id)
        if parent:
            parent_name = parent.name

    resp = CategoryResponse.model_validate(category)
    resp.product_count = product_count
    resp.children_count = children_count
    resp.parent_name = parent_name
    resp.image_url = _resolve_image_url(category.image_key, category.image_storage_type)
    if category.vat_rate is not None:
        resp.vat_rate = float(category.vat_rate)
    if category.tax_rebate_rate is not None:
        resp.tax_rebate_rate = float(category.tax_rebate_rate)
    return resp


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """更新品类"""
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="品类不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 编码唯一性检查
    if "code" in update_data and update_data["code"] != category.code:
        existing = await session.execute(
            select(Category).where(Category.code == update_data["code"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"品类编码 '{update_data['code']}' 已存在")

    # 验证不能设自己为父品类
    if "parent_id" in update_data:
        new_parent_id = update_data["parent_id"]
        if new_parent_id == category_id:
            raise HTTPException(status_code=400, detail="不能将品类设为自己的子品类")
        if new_parent_id:
            parent = await session.get(Category, new_parent_id)
            if not parent:
                raise HTTPException(status_code=400, detail="父品类不存在")
            # 检查循环引用
            current = parent
            while current.parent_id:
                if current.parent_id == category_id:
                    raise HTTPException(status_code=400, detail="不能将品类设为其后代的子品类（会形成循环）")
                current = await session.get(Category, current.parent_id)
                if not current:
                    break

    # 如果图片 key 变了，清理旧图片
    old_image_key = category.image_key
    old_image_storage_type = category.image_storage_type
    new_image_key = update_data.get("image_key")
    if "image_key" in update_data and new_image_key != old_image_key:
        await _cleanup_image(old_image_key, old_image_storage_type)

    for key, value in update_data.items():
        setattr(category, key, value)

    category.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(category)

    logger.info(f"[CategoriesAPI] 更新品类: {category.code} {category.name} by {admin.email}")

    product_count = await session.scalar(
        select(func.count(Product.id)).where(Product.category_id == category_id)
    ) or 0
    children_count = await session.scalar(
        select(func.count(Category.id)).where(Category.parent_id == category_id)
    ) or 0
    parent_name = None
    if category.parent_id:
        parent = await session.get(Category, category.parent_id)
        if parent:
            parent_name = parent.name

    resp = CategoryResponse.model_validate(category)
    resp.product_count = product_count
    resp.children_count = children_count
    resp.parent_name = parent_name
    resp.image_url = _resolve_image_url(category.image_key, category.image_storage_type)
    if category.vat_rate is not None:
        resp.vat_rate = float(category.vat_rate)
    if category.tax_rebate_rate is not None:
        resp.tax_rebate_rate = float(category.tax_rebate_rate)
    return resp


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    删除品类

    如果有子品类或产品关联，拒绝删除
    """
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="品类不存在")

    children_count = await session.scalar(
        select(func.count(Category.id)).where(Category.parent_id == category_id)
    ) or 0
    if children_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该品类下有 {children_count} 个子品类，请先删除或移动子品类",
        )

    product_count = await session.scalar(
        select(func.count(Product.id)).where(Product.category_id == category_id)
    ) or 0
    if product_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该品类下有 {product_count} 个产品，请先删除或移动产品",
        )

    # 清理图片
    await _cleanup_image(category.image_key, category.image_storage_type)

    category_name = category.name
    category_code = category.code
    await session.delete(category)
    await session.commit()

    logger.info(f"[CategoriesAPI] 删除品类: {category_code} {category_name} by {admin.email}")
    return {"message": "删除成功"}
