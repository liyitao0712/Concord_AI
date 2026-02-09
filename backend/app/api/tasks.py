# app/api/tasks.py
# 任务管理 API
#
# 路由：
#   GET    /admin/tasks              列表（project_id 必填）
#   POST   /admin/tasks              创建
#   GET    /admin/tasks/{id}         详情（含子任务+进度）
#   PUT    /admin/tasks/{id}         更新（状态变更自动记录进度）
#   DELETE /admin/tasks/{id}         删除

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
from app.models.project import Project
from app.models.task import Task
from app.models.progress import Progress
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskDetailResponse,
)
from app.schemas.progress import ProgressResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/tasks", tags=["任务管理"])


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    project_id: str = Query(..., description="所属项目 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（任务标题）"),
    status: Optional[str] = Query(None, description="筛选状态"),
    task_type: Optional[str] = Query(None, description="筛选任务类型"),
    assignee_id: Optional[str] = Query(None, description="筛选负责人"),
    parent_task_id: Optional[str] = Query(None, description="筛选父任务（传 'null' 获取顶级任务）"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("task", "read")),
):
    """获取任务列表"""
    query = select(Task).where(Task.project_id == project_id).order_by(Task.sort_order, Task.created_at)

    # 数据权限过滤
    query = await apply_data_scope(query, Task, "task", scope, session)

    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))
    if status:
        query = query.where(Task.status == status)
    if task_type:
        query = query.where(Task.task_type == task_type)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    if parent_task_id == "null":
        query = query.where(Task.parent_task_id.is_(None))
    elif parent_task_id:
        query = query.where(Task.parent_task_id == parent_task_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    tasks = list(result.scalars().all())

    # 批量查询负责人名称
    assignee_ids = list({t.assignee_id for t in tasks if t.assignee_id})
    assignee_map: dict[str, str] = {}
    if assignee_ids:
        a_result = await session.execute(
            select(User.id, User.email).where(User.id.in_(assignee_ids))
        )
        for row in a_result:
            assignee_map[row.id] = row.email

    # 批量查询子任务数量和进度数量
    task_ids = [t.id for t in tasks]
    sub_counts: dict[str, int] = {}
    prog_counts: dict[str, int] = {}
    if task_ids:
        sc_result = await session.execute(
            select(Task.parent_task_id, func.count(Task.id).label("cnt"))
            .where(Task.parent_task_id.in_(task_ids))
            .group_by(Task.parent_task_id)
        )
        for row in sc_result:
            sub_counts[row.parent_task_id] = row.cnt

        pc_result = await session.execute(
            select(Progress.task_id, func.count(Progress.id).label("cnt"))
            .where(Progress.task_id.in_(task_ids))
            .group_by(Progress.task_id)
        )
        for row in pc_result:
            prog_counts[row.task_id] = row.cnt

    items = []
    for t in tasks:
        resp = TaskResponse.model_validate(t)
        resp.assignee_name = assignee_map.get(t.assignee_id) if t.assignee_id else None
        resp.sub_task_count = sub_counts.get(t.id, 0)
        resp.progress_count = prog_counts.get(t.id, 0)
        items.append(resp)

    return TaskListResponse(items=items, total=total)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("task", "create")),
):
    """创建任务"""
    # 验证项目存在
    project = await session.get(Project, data.project_id)
    if not project:
        raise HTTPException(status_code=400, detail="项目不存在")

    # 验证父任务存在
    if data.parent_task_id:
        parent = await session.get(Task, data.parent_task_id)
        if not parent:
            raise HTTPException(status_code=400, detail="父任务不存在")
        if parent.project_id != data.project_id:
            raise HTTPException(status_code=400, detail="父任务不属于该项目")

    task = Task(
        id=str(uuid4()),
        project_id=data.project_id,
        parent_task_id=data.parent_task_id,
        title=data.title,
        description=data.description,
        task_type=data.task_type,
        phase_name=data.phase_name,
        status=data.status,
        priority=data.priority,
        assignee_id=data.assignee_id,
        sort_order=data.sort_order,
        completion_percentage=data.completion_percentage,
        due_date=data.due_date,
        created_by=scope.user.id,
        org_id=scope.org_id,
        owner_id=scope.user.id,
        owner_dept_id=scope.user.department_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    logger.info(f"[TasksAPI] 创建任务: {task.title} (项目: {project.name}) by {scope.user.email}")

    resp = TaskResponse.model_validate(task)
    if task.assignee_id:
        assignee = await session.get(User, task.assignee_id)
        resp.assignee_name = assignee.email if assignee else None
    resp.sub_task_count = 0
    resp.progress_count = 0
    return resp


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("task", "read")),
):
    """获取任务详情（含子任务和进度记录）"""
    query = (
        select(Task)
        .options(
            selectinload(Task.sub_tasks),
            selectinload(Task.progress_entries),
        )
        .where(Task.id == task_id)
    )
    query = await apply_data_scope(query, Task, "task", scope, session)
    result = await session.execute(query)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    resp = TaskResponse.model_validate(task)
    if task.assignee_id:
        assignee = await session.get(User, task.assignee_id)
        resp.assignee_name = assignee.email if assignee else None
    resp.sub_task_count = len(task.sub_tasks)
    resp.progress_count = len(task.progress_entries)

    detail = TaskDetailResponse(**resp.model_dump())

    # 子任务
    detail.sub_tasks = []
    for st in task.sub_tasks:
        st_resp = TaskResponse.model_validate(st)
        st_resp.sub_task_count = 0
        st_resp.progress_count = 0
        detail.sub_tasks.append(st_resp)

    return detail


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("task", "update")),
):
    """更新任务（状态/完成度变更时自动创建进度记录）"""
    query = select(Task).where(Task.id == task_id)
    query = await apply_data_scope(query, Task, "task", scope, session)
    result = await session.execute(query)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_data = data.model_dump(exclude_unset=True)
    old_status = task.status
    old_percentage = task.completion_percentage

    for key, value in update_data.items():
        setattr(task, key, value)

    task.updated_at = datetime.utcnow()

    # 状态变更 → 自动创建进度记录
    if "status" in update_data and update_data["status"] != old_status:
        progress = Progress(
            id=str(uuid4()),
            task_id=task.id,
            progress_type="status_update",
            old_status=old_status,
            new_status=update_data["status"],
            content=f"状态变更: {old_status} → {update_data['status']}",
            created_by=scope.user.id,
        )
        session.add(progress)

    # 完成度变更 → 自动创建进度记录
    if "completion_percentage" in update_data and update_data["completion_percentage"] != old_percentage:
        progress = Progress(
            id=str(uuid4()),
            task_id=task.id,
            progress_type="completion",
            percentage=update_data["completion_percentage"],
            content=f"完成度更新: {old_percentage}% → {update_data['completion_percentage']}%",
            created_by=scope.user.id,
        )
        session.add(progress)

    await session.commit()
    await session.refresh(task)

    logger.info(f"[TasksAPI] 更新任务: {task.title} by {scope.user.email}")

    resp = TaskResponse.model_validate(task)
    if task.assignee_id:
        assignee = await session.get(User, task.assignee_id)
        resp.assignee_name = assignee.email if assignee else None

    resp.sub_task_count = await session.scalar(
        select(func.count(Task.id)).where(Task.parent_task_id == task_id)
    ) or 0
    resp.progress_count = await session.scalar(
        select(func.count(Progress.id)).where(Progress.task_id == task_id)
    ) or 0

    return resp


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("task", "delete")),
):
    """删除任务（级联删除子任务和进度记录）"""
    query = select(Task).where(Task.id == task_id)
    query = await apply_data_scope(query, Task, "task", scope, session)
    result = await session.execute(query)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    title = task.title
    await session.delete(task)
    await session.commit()

    logger.info(f"[TasksAPI] 删除任务: {title} by {scope.user.email}")
    return {"message": "删除成功"}
