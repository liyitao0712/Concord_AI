# app/api/work_types.py
# 工作类型管理 API
#
# 功能说明：
# 1. 工作类型 CRUD（增删改查）
# 2. 树形结构查询
# 3. 工作类型建议列表和审批
#
# 路由：
#   GET    /admin/work-types              列表
#   GET    /admin/work-types/tree         树形结构
#   POST   /admin/work-types              创建
#   GET    /admin/work-types/{id}         详情
#   PUT    /admin/work-types/{id}         更新
#   DELETE /admin/work-types/{id}         删除
#   GET    /admin/work-type-suggestions   建议列表
#   GET    /admin/work-type-suggestions/{id}  建议详情
#   POST   /admin/work-type-suggestions/{id}/approve  批准建议
#   POST   /admin/work-type-suggestions/{id}/reject   拒绝建议

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.work_type import WorkType, WorkTypeSuggestion
from app.schemas.work_type import (
    WorkTypeCreate,
    WorkTypeUpdate,
    WorkTypeResponse,
    WorkTypeListResponse,
    WorkTypeTreeNode,
    WorkTypeTreeResponse,
    WorkTypeSuggestionResponse,
    WorkTypeSuggestionListResponse,
    ReviewRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/work-types", tags=["工作类型管理"])


# ==================== 工作类型 CRUD ====================

@router.get("", response_model=WorkTypeListResponse)
async def list_work_types(
    is_active: Optional[bool] = None,
    level: Optional[int] = None,
    parent_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    获取工作类型列表（扁平化）

    参数：
    - is_active: 筛选启用/禁用状态
    - level: 筛选层级（1=顶级，2=子级）
    - parent_id: 筛选父级 ID
    """
    query = select(WorkType).order_by(WorkType.level, WorkType.code)

    if is_active is not None:
        query = query.where(WorkType.is_active == is_active)
    if level is not None:
        query = query.where(WorkType.level == level)
    if parent_id is not None:
        query = query.where(WorkType.parent_id == parent_id)

    result = await session.execute(query)
    items = list(result.scalars().all())

    # 获取总数
    count_query = select(func.count(WorkType.id))
    if is_active is not None:
        count_query = count_query.where(WorkType.is_active == is_active)
    if level is not None:
        count_query = count_query.where(WorkType.level == level)
    total = await session.scalar(count_query) or 0

    return WorkTypeListResponse(
        items=[WorkTypeResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/tree", response_model=WorkTypeTreeResponse)
async def get_work_type_tree(
    is_active: Optional[bool] = True,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    获取工作类型树形结构

    返回嵌套的树形数据，顶级节点包含其子节点
    """
    # 查询所有工作类型（一次性加载，避免 lazy load 导致 greenlet 错误）
    query = select(WorkType).order_by(WorkType.level, WorkType.code)

    if is_active is not None:
        query = query.where(WorkType.is_active == is_active)

    result = await session.execute(query)
    all_items = list(result.scalars().all())

    # 构建 id -> 节点 和 parent_id -> children 映射
    id_to_item: dict[str, WorkType] = {item.id: item for item in all_items}
    parent_to_children: dict[Optional[str], List[WorkType]] = {}

    for item in all_items:
        parent_id = item.parent_id
        if parent_id not in parent_to_children:
            parent_to_children[parent_id] = []
        parent_to_children[parent_id].append(item)

    def build_tree(node: WorkType) -> WorkTypeTreeNode:
        """递归构建树形节点（使用预先构建的映射，无需数据库访问）"""
        children = []
        child_items = parent_to_children.get(node.id, [])
        for child in child_items:
            children.append(build_tree(child))

        return WorkTypeTreeNode(
            id=node.id,
            parent_id=node.parent_id,
            code=node.code,
            name=node.name,
            description=node.description,
            level=node.level,
            is_active=node.is_active,
            is_system=node.is_system,
            usage_count=node.usage_count,
            children=children,
        )

    # 获取顶级节点（parent_id 为 None）
    roots = parent_to_children.get(None, [])
    tree_items = [build_tree(r) for r in roots]

    return WorkTypeTreeResponse(
        items=tree_items,
        total=len(roots),
    )


@router.post("", response_model=WorkTypeResponse, status_code=201)
async def create_work_type(
    data: WorkTypeCreate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    创建工作类型

    注意：
    - code 必须是全大写英文（可含数字和下划线）
    - 如果指定 parent_id，code 必须以父级 code 为前缀
    """
    # 检查 code 唯一性
    existing = await session.scalar(
        select(WorkType).where(WorkType.code == data.code)
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"工作类型代码 '{data.code}' 已存在")

    # 处理层级
    level = 1
    path = f"/{data.code}"

    if data.parent_id:
        parent = await session.get(WorkType, data.parent_id)
        if not parent:
            raise HTTPException(status_code=400, detail="父级工作类型不存在")

        level = parent.level + 1
        path = f"{parent.path}/{data.code}"

        # 验证 code 命名规范：子级 code 必须以父级 code 开头
        if not data.code.startswith(parent.code + "_"):
            raise HTTPException(
                status_code=400,
                detail=f"子级 code 必须以父级 code 开头，如 '{parent.code}_XXX'",
            )

    work_type = WorkType(
        id=str(uuid4()),
        code=data.code,
        name=data.name,
        description=data.description,
        parent_id=data.parent_id,
        level=level,
        path=path,
        examples=data.examples,
        keywords=data.keywords,
        is_active=data.is_active,
        is_system=False,
        created_by="admin",
    )

    session.add(work_type)
    await session.commit()
    await session.refresh(work_type)

    logger.info(f"[WorkTypesAPI] 创建工作类型: {work_type.code} by {admin.email}")
    return WorkTypeResponse.model_validate(work_type)


@router.get("/{work_type_id}", response_model=WorkTypeResponse)
async def get_work_type(
    work_type_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取工作类型详情"""
    work_type = await session.get(WorkType, work_type_id)
    if not work_type:
        raise HTTPException(status_code=404, detail="工作类型不存在")
    return WorkTypeResponse.model_validate(work_type)


@router.put("/{work_type_id}", response_model=WorkTypeResponse)
async def update_work_type(
    work_type_id: str,
    data: WorkTypeUpdate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    更新工作类型

    注意：不能修改 code 和 parent_id
    """
    work_type = await session.get(WorkType, work_type_id)
    if not work_type:
        raise HTTPException(status_code=404, detail="工作类型不存在")

    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(work_type, key, value)

    work_type.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(work_type)

    logger.info(f"[WorkTypesAPI] 更新工作类型: {work_type.code} by {admin.email}")
    return WorkTypeResponse.model_validate(work_type)


@router.delete("/{work_type_id}")
async def delete_work_type(
    work_type_id: str,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    删除工作类型

    注意：
    - 不能删除系统内置类型
    - 如果有子类型，需要先删除子类型
    """
    work_type = await session.get(WorkType, work_type_id)
    if not work_type:
        raise HTTPException(status_code=404, detail="工作类型不存在")

    if work_type.is_system:
        raise HTTPException(status_code=400, detail="不能删除系统内置工作类型")

    # 检查是否有子类型
    children_count = await session.scalar(
        select(func.count(WorkType.id)).where(WorkType.parent_id == work_type_id)
    )
    if children_count and children_count > 0:
        raise HTTPException(status_code=400, detail="请先删除子工作类型")

    await session.delete(work_type)
    await session.commit()

    logger.info(f"[WorkTypesAPI] 删除工作类型: {work_type.code} by {admin.email}")
    return {"message": "删除成功"}


# ==================== 工作类型建议 ====================

suggestions_router = APIRouter(prefix="/admin/work-type-suggestions", tags=["工作类型建议"])


@suggestions_router.get("", response_model=WorkTypeSuggestionListResponse)
async def list_suggestions(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    获取工作类型建议列表

    参数：
    - status: 筛选状态（pending/approved/rejected/merged）
    """
    query = select(WorkTypeSuggestion).order_by(WorkTypeSuggestion.created_at.desc())

    if status:
        query = query.where(WorkTypeSuggestion.status == status)

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    suggestions = list(result.scalars().all())

    # 获取总数
    count_query = select(func.count(WorkTypeSuggestion.id))
    if status:
        count_query = count_query.where(WorkTypeSuggestion.status == status)
    total = await session.scalar(count_query) or 0

    return WorkTypeSuggestionListResponse(
        items=[WorkTypeSuggestionResponse.model_validate(s) for s in suggestions],
        total=total,
    )


@suggestions_router.get("/{suggestion_id}", response_model=WorkTypeSuggestionResponse)
async def get_suggestion(
    suggestion_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取建议详情"""
    suggestion = await session.get(WorkTypeSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="建议不存在")
    return WorkTypeSuggestionResponse.model_validate(suggestion)


@suggestions_router.post("/{suggestion_id}/approve")
async def approve_suggestion(
    suggestion_id: str,
    data: ReviewRequest,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    批准工作类型建议

    如果建议有关联的 Temporal Workflow，通过 Signal 处理；
    否则直接在本地执行（兼容没有工作流的建议）
    """
    suggestion = await session.get(WorkTypeSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议已处理: {suggestion.status}")

    # 如果有 workflow_id，通过 Temporal Signal 处理
    if suggestion.workflow_id:
        try:
            from app.temporal import approve_suggestion as temporal_approve
            await temporal_approve(
                suggestion.workflow_id,
                admin.id,
                data.note or "",
            )
            logger.info(
                f"[WorkTypesAPI] 发送批准信号: suggestion={suggestion_id}, "
                f"workflow={suggestion.workflow_id}, by={admin.email}"
            )
            return {"message": "审批已提交，等待工作流处理"}
        except Exception as e:
            logger.error(f"[WorkTypesAPI] 发送 Temporal 信号失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"发送审批信号失败: {str(e)}",
            )

    # 没有 workflow_id，直接在本地处理（兼容模式）
    # 检查 code 是否已存在
    existing = await session.scalar(
        select(WorkType).where(WorkType.code == suggestion.suggested_code)
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"工作类型代码 '{suggestion.suggested_code}' 已存在",
        )

    # 处理父级
    parent_id = suggestion.suggested_parent_id
    level = suggestion.suggested_level
    path = f"/{suggestion.suggested_code}"

    if suggestion.suggested_parent_code:
        parent = await session.scalar(
            select(WorkType).where(WorkType.code == suggestion.suggested_parent_code)
        )
        if parent:
            parent_id = parent.id
            level = parent.level + 1
            path = f"{parent.path}/{suggestion.suggested_code}"

    # 创建工作类型
    work_type = WorkType(
        id=str(uuid4()),
        code=suggestion.suggested_code,
        name=suggestion.suggested_name,
        description=suggestion.suggested_description,
        parent_id=parent_id,
        level=level,
        path=path,
        examples=suggestion.suggested_examples or [],
        keywords=suggestion.suggested_keywords or [],
        is_active=True,
        is_system=False,
        created_by="ai",
    )
    session.add(work_type)

    # 更新建议状态
    suggestion.status = "approved"
    suggestion.reviewed_by = admin.id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.review_note = data.note
    suggestion.created_work_type_id = work_type.id

    await session.commit()
    await session.refresh(work_type)

    logger.info(
        f"[WorkTypesAPI] 本地批准建议: {suggestion.suggested_code} -> {work_type.id} "
        f"by {admin.email}"
    )

    return WorkTypeResponse.model_validate(work_type)


@suggestions_router.post("/{suggestion_id}/reject")
async def reject_suggestion(
    suggestion_id: str,
    data: ReviewRequest,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    拒绝工作类型建议

    如果建议有关联的 Temporal Workflow，通过 Signal 处理；
    否则直接在本地执行（兼容没有工作流的建议）
    """
    suggestion = await session.get(WorkTypeSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议已处理: {suggestion.status}")

    # 如果有 workflow_id，通过 Temporal Signal 处理
    if suggestion.workflow_id:
        try:
            from app.temporal import reject_suggestion as temporal_reject
            await temporal_reject(
                suggestion.workflow_id,
                admin.id,
                data.note or "",
            )
            logger.info(
                f"[WorkTypesAPI] 发送拒绝信号: suggestion={suggestion_id}, "
                f"workflow={suggestion.workflow_id}, by={admin.email}"
            )
            return {"message": "拒绝已提交，等待工作流处理"}
        except Exception as e:
            logger.error(f"[WorkTypesAPI] 发送 Temporal 信号失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"发送拒绝信号失败: {str(e)}",
            )

    # 没有 workflow_id，直接在本地处理（兼容模式）
    suggestion.status = "rejected"
    suggestion.reviewed_by = admin.id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.review_note = data.note

    await session.commit()

    logger.info(f"[WorkTypesAPI] 本地拒绝建议: {suggestion.suggested_code} by {admin.email}")

    return {"message": "已拒绝"}
