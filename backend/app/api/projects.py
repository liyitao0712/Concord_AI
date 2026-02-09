# app/api/projects.py
# 项目管理 API
#
# 路由：
#   GET    /admin/projects                                  列表
#   POST   /admin/projects                                  创建（含关联）
#   GET    /admin/projects/{id}                             详情（含关联+任务）
#   PUT    /admin/projects/{id}                             更新
#   DELETE /admin/projects/{id}                             删除
#   PUT    /admin/projects/{id}/status                      变更状态
#   POST   /admin/projects/{id}/associations                添加关联
#   DELETE /admin/projects/{id}/associations/{assoc_id}     移除关联
#   POST   /admin/projects/from-email/{email_id}            从邮件预填

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import require_permission, apply_data_scope, DataScope
from app.models.user import User
from app.models.project import Project, ProjectAssociation
from app.models.task import Task
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.purchase_contract import PurchaseContract
from app.models.sales_contract import SalesContract
from app.models.product import Product
from app.models.inbound_order import InboundOrder
from app.models.outbound_order import OutboundOrder
from app.models.client_rfq import ClientRFQ
from app.models.quotation import Quotation
from app.models.supplier_rfq import SupplierRFQ
from app.models.supplier_quotation import SupplierQuotation
from app.models.email_analysis import EmailAnalysis
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectDetailResponse,
    ProjectStatusUpdate,
    ProjectAssociationCreate,
    ProjectAssociationResponse,
)
from app.schemas.task import TaskResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/projects", tags=["项目管理"])

# 实体类型 → 表模型 + 名称字段的映射
ENTITY_MODEL_MAP = {
    "customer": (Customer, "name"),
    "supplier": (Supplier, "name"),
    "purchase_contract": (PurchaseContract, "contract_no"),
    "sales_contract": (SalesContract, "contract_no"),
    "product": (Product, "name"),
    "inbound_order": (InboundOrder, "order_no"),
    "outbound_order": (OutboundOrder, "order_no"),
    "client_rfq": (ClientRFQ, "rfq_no"),
    "quotation": (Quotation, "quotation_no"),
    "supplier_rfq": (SupplierRFQ, "rfq_no"),
    "supplier_quotation": (SupplierQuotation, "quotation_no"),
}


async def _resolve_entity_names(
    session: AsyncSession,
    associations: list[ProjectAssociation],
) -> dict[str, str]:
    """批量解析关联实体名称，避免 N+1"""
    # 按 entity_type 分组
    grouped: dict[str, list[str]] = {}
    for assoc in associations:
        grouped.setdefault(assoc.entity_type, []).append(assoc.entity_id)

    name_map: dict[str, str] = {}  # entity_id -> name
    for entity_type, entity_ids in grouped.items():
        model_info = ENTITY_MODEL_MAP.get(entity_type)
        if not model_info:
            continue
        model_cls, name_field = model_info
        col = getattr(model_cls, name_field)
        result = await session.execute(
            select(model_cls.id, col).where(model_cls.id.in_(entity_ids))
        )
        for row in result:
            name_map[row[0]] = row[1]

    return name_map


async def _build_project_response(
    session: AsyncSession,
    project: Project,
    include_counts: bool = True,
) -> ProjectResponse:
    """构建项目响应，含负责人名称和计数"""
    resp = ProjectResponse.model_validate(project)

    # 负责人名称
    if project.owner_id:
        owner = await session.get(User, project.owner_id)
        resp.owner_name = owner.email if owner else None

    if include_counts:
        # 任务数量
        resp.task_count = await session.scalar(
            select(func.count(Task.id)).where(Task.project_id == project.id)
        ) or 0
        # 关联数量
        resp.association_count = await session.scalar(
            select(func.count(ProjectAssociation.id)).where(
                ProjectAssociation.project_id == project.id
            )
        ) or 0

    return resp


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（项目名称）"),
    status: Optional[str] = Query(None, description="筛选状态"),
    project_type: Optional[str] = Query(None, description="筛选项目类型"),
    priority: Optional[str] = Query(None, description="筛选优先级"),
    owner_id: Optional[str] = Query(None, description="筛选负责人"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "read")),
):
    """获取项目列表"""
    query = select(Project).order_by(Project.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, Project, "project", scope, session)

    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))
    if status:
        query = query.where(Project.status == status)
    if project_type:
        query = query.where(Project.project_type == project_type)
    if priority:
        query = query.where(Project.priority == priority)
    if owner_id:
        query = query.where(Project.owner_id == owner_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    projects = list(result.scalars().all())

    # 批量查询负责人名称
    owner_ids = list({p.owner_id for p in projects if p.owner_id})
    owner_map: dict[str, str] = {}
    if owner_ids:
        o_result = await session.execute(
            select(User.id, User.email).where(User.id.in_(owner_ids))
        )
        for row in o_result:
            owner_map[row.id] = row.email

    # 批量查询任务数量
    project_ids = [p.id for p in projects]
    task_counts: dict[str, int] = {}
    assoc_counts: dict[str, int] = {}
    if project_ids:
        tc_result = await session.execute(
            select(Task.project_id, func.count(Task.id).label("cnt"))
            .where(Task.project_id.in_(project_ids))
            .group_by(Task.project_id)
        )
        for row in tc_result:
            task_counts[row.project_id] = row.cnt

        ac_result = await session.execute(
            select(
                ProjectAssociation.project_id,
                func.count(ProjectAssociation.id).label("cnt"),
            )
            .where(ProjectAssociation.project_id.in_(project_ids))
            .group_by(ProjectAssociation.project_id)
        )
        for row in ac_result:
            assoc_counts[row.project_id] = row.cnt

    items = []
    for p in projects:
        resp = ProjectResponse.model_validate(p)
        resp.owner_name = owner_map.get(p.owner_id) if p.owner_id else None
        resp.task_count = task_counts.get(p.id, 0)
        resp.association_count = assoc_counts.get(p.id, 0)
        items.append(resp)

    return ProjectListResponse(items=items, total=total)


@router.post("", response_model=ProjectDetailResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "create")),
):
    """创建项目（含关联实体）"""
    project = Project(
        id=str(uuid4()),
        name=data.name,
        project_type=data.project_type,
        description=data.description,
        status=data.status,
        priority=data.priority,
        start_date=data.start_date,
        due_date=data.due_date,
        owner_id=data.owner_id,
        tags=data.tags,
        notes=data.notes,
        created_by=scope.user.id,
        org_id=scope.org_id,
        owner_dept_id=scope.user.department_id,
    )

    # 创建关联
    for assoc_data in data.associations:
        assoc = ProjectAssociation(
            id=str(uuid4()),
            project_id=project.id,
            entity_type=assoc_data.entity_type,
            entity_id=assoc_data.entity_id,
            notes=assoc_data.notes,
        )
        project.associations.append(assoc)

    session.add(project)
    await session.commit()
    await session.refresh(project, ["associations"])

    logger.info(f"[ProjectsAPI] 创建项目: {project.name} by {scope.user.email}")

    # 构建响应
    resp = ProjectDetailResponse.model_validate(project)
    if project.owner_id:
        owner = await session.get(User, project.owner_id)
        resp.owner_name = owner.email if owner else None
    resp.task_count = 0
    resp.association_count = len(project.associations)

    # 解析关联实体名称
    name_map = await _resolve_entity_names(session, project.associations)
    resp.associations = []
    for assoc in project.associations:
        a_resp = ProjectAssociationResponse.model_validate(assoc)
        a_resp.entity_name = name_map.get(assoc.entity_id)
        resp.associations.append(a_resp)

    return resp


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "read")),
):
    """获取项目详情（含关联和任务列表）"""
    query = (
        select(Project)
        .options(
            selectinload(Project.associations),
            selectinload(Project.tasks),
        )
        .where(Project.id == project_id)
    )
    query = await apply_data_scope(query, Project, "project", scope, session)
    result = await session.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    resp = await _build_project_response(session, project, include_counts=False)
    detail = ProjectDetailResponse(**resp.model_dump())
    detail.task_count = len(project.tasks)
    detail.association_count = len(project.associations)

    # 解析关联实体名称
    name_map = await _resolve_entity_names(session, project.associations)
    detail.associations = []
    for assoc in project.associations:
        a_resp = ProjectAssociationResponse.model_validate(assoc)
        a_resp.entity_name = name_map.get(assoc.entity_id)
        detail.associations.append(a_resp)

    return detail


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "update")),
):
    """更新项目"""
    query = select(Project).where(Project.id == project_id)
    query = await apply_data_scope(query, Project, "project", scope, session)
    result = await session.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(project)

    logger.info(f"[ProjectsAPI] 更新项目: {project.name} by {scope.user.email}")

    return await _build_project_response(session, project)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "delete")),
):
    """删除项目（级联删除关联、任务、进度）"""
    query = select(Project).where(Project.id == project_id)
    query = await apply_data_scope(query, Project, "project", scope, session)
    result = await session.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    name = project.name
    await session.delete(project)
    await session.commit()

    logger.info(f"[ProjectsAPI] 删除项目: {name} by {scope.user.email}")
    return {"message": "删除成功"}


@router.put("/{project_id}/status", response_model=ProjectResponse)
async def update_project_status(
    project_id: str,
    data: ProjectStatusUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "update")),
):
    """变更项目状态"""
    query = select(Project).where(Project.id == project_id)
    query = await apply_data_scope(query, Project, "project", scope, session)
    result = await session.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    old_status = project.status
    project.status = data.status
    project.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(project)

    logger.info(
        f"[ProjectsAPI] 状态变更: {project.name} "
        f"{old_status} → {data.status} by {scope.user.email}"
    )

    return await _build_project_response(session, project)


@router.post("/{project_id}/associations", response_model=ProjectAssociationResponse, status_code=201)
async def add_project_association(
    project_id: str,
    data: ProjectAssociationCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "update")),
):
    """添加项目关联"""
    query = select(Project).where(Project.id == project_id)
    query = await apply_data_scope(query, Project, "project", scope, session)
    result = await session.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查重复
    existing = await session.execute(
        select(ProjectAssociation).where(
            ProjectAssociation.project_id == project_id,
            ProjectAssociation.entity_type == data.entity_type,
            ProjectAssociation.entity_id == data.entity_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该关联已存在")

    assoc = ProjectAssociation(
        id=str(uuid4()),
        project_id=project_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        notes=data.notes,
    )
    session.add(assoc)
    await session.commit()
    await session.refresh(assoc)

    logger.info(
        f"[ProjectsAPI] 添加关联: {project.name} -> "
        f"{data.entity_type}:{data.entity_id} by {scope.user.email}"
    )

    # 解析实体名称
    name_map = await _resolve_entity_names(session, [assoc])
    resp = ProjectAssociationResponse.model_validate(assoc)
    resp.entity_name = name_map.get(assoc.entity_id)
    return resp


@router.delete("/{project_id}/associations/{assoc_id}")
async def remove_project_association(
    project_id: str,
    assoc_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "update")),
):
    """移除项目关联"""
    # 先验证项目权限
    proj_query = select(Project).where(Project.id == project_id)
    proj_query = await apply_data_scope(proj_query, Project, "project", scope, session)
    proj_result = await session.execute(proj_query)
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="项目不存在")

    assoc = await session.get(ProjectAssociation, assoc_id)
    if not assoc or assoc.project_id != project_id:
        raise HTTPException(status_code=404, detail="关联不存在")

    await session.delete(assoc)
    await session.commit()

    logger.info(
        f"[ProjectsAPI] 移除关联: project={project_id} "
        f"{assoc.entity_type}:{assoc.entity_id} by {scope.user.email}"
    )
    return {"message": "删除成功"}


@router.post("/from-email/{email_id}")
async def prefill_project_from_email(
    email_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("project", "create")),
):
    """
    从邮件分析结果预填项目信息

    返回预填数据供前端表单使用，不实际创建项目。
    """
    # 查询邮件分析结果
    result = await session.execute(
        select(EmailAnalysis).where(EmailAnalysis.email_id == email_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="邮件分析结果不存在")

    # 构建预填数据
    prefill = {
        "name": f"{analysis.sender_company or '未知'} - {analysis.intent or '项目'}",
        "project_type": "order" if analysis.intent in ("order", "quotation", "inquiry") else "general",
        "description": "\n".join(analysis.key_points) if analysis.key_points else None,
        "priority": analysis.priority or "medium",
        "source_email_id": email_id,
        "suggested_associations": [],
    }

    # 尝试匹配客户
    if analysis.sender_company:
        cust_result = await session.execute(
            select(Customer.id, Customer.name).where(
                Customer.name.ilike(f"%{analysis.sender_company}%")
            ).limit(1)
        )
        cust_row = cust_result.first()
        if cust_row:
            prefill["suggested_associations"].append({
                "entity_type": "customer",
                "entity_id": cust_row.id,
                "entity_name": cust_row.name,
            })

    return prefill
