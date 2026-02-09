# app/api/project_suggestions.py
# 项目建议审批 API
#
# 路由：
#   GET  /admin/project-suggestions                  列表
#   GET  /admin/project-suggestions/{id}             详情
#   POST /admin/project-suggestions/{id}/approve     批准
#   POST /admin/project-suggestions/{id}/reject      拒绝

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import require_permission, DataScope
from app.models.project import Project, ProjectAssociation
from app.models.project_suggestion import ProjectSuggestion
from app.schemas.project_suggestion import (
    ProjectSuggestionResponse,
    ProjectSuggestionListResponse,
    ProjectReviewRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/project-suggestions", tags=["项目建议审批"])


@router.get("", response_model=ProjectSuggestionListResponse)
async def list_project_suggestions(
    status: Optional[str] = Query(None, description="筛选状态"),
    search: Optional[str] = Query(None, description="搜索（建议名称）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_db),
    _: DataScope = Depends(require_permission("project", "read")),
):
    """获取项目建议列表"""
    query = select(ProjectSuggestion).order_by(ProjectSuggestion.created_at.desc())

    if status:
        query = query.where(ProjectSuggestion.status == status)
    if search:
        query = query.where(ProjectSuggestion.suggested_name.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    suggestions = list(result.scalars().all())

    return ProjectSuggestionListResponse(
        items=[ProjectSuggestionResponse.model_validate(s) for s in suggestions],
        total=total,
    )


@router.get("/{suggestion_id}", response_model=ProjectSuggestionResponse)
async def get_project_suggestion(
    suggestion_id: str,
    session: AsyncSession = Depends(get_db),
    _: DataScope = Depends(require_permission("project", "read")),
):
    """获取项目建议详情"""
    suggestion = await session.get(ProjectSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="项目建议不存在")
    return ProjectSuggestionResponse.model_validate(suggestion)


@router.post("/{suggestion_id}/approve")
async def approve_project_suggestion(
    suggestion_id: str,
    data: ProjectReviewRequest,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "create")),
):
    """
    批准项目建议

    支持管理员覆盖 AI 建议的字段后审批，
    审批通过后自动创建 Project 记录。
    """
    suggestion = await session.get(ProjectSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="项目建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议已处理: {suggestion.status}")

    # 审批时可覆盖 AI 建议的字段
    final_name = data.name or suggestion.suggested_name
    final_type = data.project_type or suggestion.suggested_type
    final_description = data.description or suggestion.suggested_description
    final_priority = data.priority or suggestion.suggested_priority
    final_owner_id = data.owner_id

    # 创建项目
    project = Project(
        id=str(uuid4()),
        name=final_name,
        project_type=final_type,
        description=final_description,
        status="active",
        priority=final_priority,
        owner_id=final_owner_id,
        created_by=scope.user.id,
        org_id=scope.org_id,
        owner_dept_id=getattr(scope.user, 'department_id', None),
    )
    session.add(project)

    # 创建建议的关联
    if suggestion.suggested_associations:
        for assoc_data in suggestion.suggested_associations:
            if isinstance(assoc_data, dict) and assoc_data.get("entity_type") and assoc_data.get("entity_id"):
                assoc = ProjectAssociation(
                    id=str(uuid4()),
                    project_id=project.id,
                    entity_type=assoc_data["entity_type"],
                    entity_id=assoc_data["entity_id"],
                )
                session.add(assoc)

    # 更新建议状态
    suggestion.status = "approved"
    suggestion.reviewed_by = scope.user.id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.review_note = data.note
    suggestion.created_project_id = project.id

    await session.commit()

    logger.info(
        f"[ProjectSuggestions] 批准建议: {final_name} "
        f"→ 项目 {project.id} by {scope.user.email}"
    )

    return {
        "message": "已批准",
        "project_id": project.id,
    }


@router.post("/{suggestion_id}/reject")
async def reject_project_suggestion(
    suggestion_id: str,
    data: ProjectReviewRequest,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "update")),
):
    """拒绝项目建议"""
    suggestion = await session.get(ProjectSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="项目建议不存在")

    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail=f"建议已处理: {suggestion.status}")

    suggestion.status = "rejected"
    suggestion.reviewed_by = scope.user.id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.review_note = data.note

    await session.commit()

    logger.info(
        f"[ProjectSuggestions] 拒绝建议: {suggestion.suggested_name} by {scope.user.email}"
    )

    return {"message": "已拒绝"}
