# app/api/progress.py
# 进度记录 API
#
# 路由：
#   GET    /admin/progress              列表（task_id 必填）
#   POST   /admin/progress              创建
#   DELETE /admin/progress/{id}         删除
#
# 注意：无 PUT 接口，进度记录采用 append-only 设计

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import require_permission, apply_data_scope, DataScope
from app.models.user import User
from app.models.task import Task
from app.models.progress import Progress
from app.schemas.progress import (
    ProgressCreate,
    ProgressResponse,
    ProgressListResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/progress", tags=["进度记录"])


@router.get("", response_model=ProgressListResponse)
async def list_progress(
    task_id: str = Query(..., description="所属任务 ID"),
    progress_type: Optional[str] = Query(None, description="筛选记录类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("task", "read")),
):
    """获取进度记录列表"""
    query = (
        select(Progress)
        .where(Progress.task_id == task_id)
        .order_by(Progress.created_at.desc())
    )

    if progress_type:
        query = query.where(Progress.progress_type == progress_type)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    entries = list(result.scalars().all())

    # 批量查询创建人名称
    creator_ids = list({e.created_by for e in entries if e.created_by})
    creator_map: dict[str, str] = {}
    if creator_ids:
        c_result = await session.execute(
            select(User.id, User.email).where(User.id.in_(creator_ids))
        )
        for row in c_result:
            creator_map[row.id] = row.email

    items = []
    for e in entries:
        resp = ProgressResponse.model_validate(e)
        resp.created_by_name = creator_map.get(e.created_by) if e.created_by else None
        items.append(resp)

    return ProgressListResponse(items=items, total=total)


@router.post("", response_model=ProgressResponse, status_code=201)
async def create_progress(
    data: ProgressCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("task", "update")),
):
    """创建进度记录"""
    # 验证任务存在
    task = await session.get(Task, data.task_id)
    if not task:
        raise HTTPException(status_code=400, detail="任务不存在")

    entry = Progress(
        id=str(uuid4()),
        task_id=data.task_id,
        progress_type=data.progress_type,
        content=data.content,
        old_status=data.old_status,
        new_status=data.new_status,
        percentage=data.percentage,
        email_id=data.email_id,
        attachments=data.attachments,
        created_by=scope.user.id,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    logger.info(
        f"[ProgressAPI] 创建进度: {data.progress_type} "
        f"(任务: {task.title}) by {scope.user.email}"
    )

    resp = ProgressResponse.model_validate(entry)
    resp.created_by_name = scope.user.email
    return resp


@router.delete("/{progress_id}")
async def delete_progress(
    progress_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("task", "delete")),
):
    """删除进度记录"""
    entry = await session.get(Progress, progress_id)
    if not entry:
        raise HTTPException(status_code=404, detail="进度记录不存在")

    await session.delete(entry)
    await session.commit()

    logger.info(f"[ProgressAPI] 删除进度: {progress_id} by {scope.user.email}")
    return {"message": "删除成功"}
