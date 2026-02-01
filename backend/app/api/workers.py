# app/api/workers.py
# Worker 管理 API
#
# 提供 Worker 配置和管理的 HTTP 接口

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_admin_user
from app.core.database import get_db
from app.models.user import User
from app.models.worker import WorkerConfig
from app.workers import worker_manager

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/workers",
    tags=["admin-workers"],
    dependencies=[Depends(get_current_admin_user)],
)


# ==================== 请求/响应模型 ====================

class WorkerConfigCreate(BaseModel):
    """创建 Worker 配置请求"""
    worker_type: str = Field(..., description="Worker 类型: feishu / email")
    name: str = Field(..., description="显示名称")
    config: dict = Field(default_factory=dict, description="配置数据")
    agent_id: str = Field(default="chat_agent", description="绑定的 Agent ID")
    is_enabled: bool = Field(default=True, description="是否启用")
    description: Optional[str] = Field(None, description="描述")


class WorkerConfigUpdate(BaseModel):
    """更新 Worker 配置请求"""
    name: Optional[str] = Field(None, description="显示名称")
    config: Optional[dict] = Field(None, description="配置数据")
    agent_id: Optional[str] = Field(None, description="绑定的 Agent ID")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    description: Optional[str] = Field(None, description="描述")


class WorkerConfigResponse(BaseModel):
    """Worker 配置响应"""
    id: str
    worker_type: str
    name: str
    config: dict  # 已脱敏
    agent_id: str
    is_enabled: bool
    description: Optional[str]
    status: str  # stopped / running / error
    pid: Optional[int]
    started_at: Optional[str]
    created_at: str
    updated_at: str


class WorkerTypeInfo(BaseModel):
    """Worker 类型信息"""
    type: str
    name: str
    description: str
    required_fields: list[str]
    optional_fields: list[str]


class WorkerActionResponse(BaseModel):
    """Worker 操作响应"""
    success: bool
    message: str


# ==================== API 端点 ====================

@router.get("/types", response_model=list[WorkerTypeInfo])
async def list_worker_types():
    """
    列出所有支持的 Worker 类型
    """
    types = []
    for worker_type in worker_manager.get_worker_types():
        worker_class = worker_manager._worker_types.get(worker_type)
        if worker_class:
            types.append(WorkerTypeInfo(
                type=worker_type,
                name=worker_class.name,
                description=worker_class.description,
                required_fields=worker_class.get_required_config_fields(),
                optional_fields=worker_class.get_optional_config_fields(),
            ))
    return types


@router.get("", response_model=list[WorkerConfigResponse])
async def list_workers(
    db: AsyncSession = Depends(get_db),
):
    """
    列出所有 Worker 配置
    """
    result = await db.execute(select(WorkerConfig).order_by(WorkerConfig.created_at.desc()))
    configs = result.scalars().all()

    workers = []
    for config in configs:
        status = worker_manager.get_status(config.id)
        workers.append(WorkerConfigResponse(
            id=config.id,
            worker_type=config.worker_type,
            name=config.name,
            config=config.mask_sensitive_config(),
            agent_id=config.agent_id,
            is_enabled=config.is_enabled,
            description=config.description,
            status=status.status.value if status else "stopped",
            pid=status.pid if status else None,
            started_at=status.started_at.isoformat() if status and status.started_at else None,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        ))

    return workers


@router.post("", response_model=WorkerConfigResponse, status_code=201)
async def create_worker(
    request: WorkerConfigCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    创建新的 Worker 配置
    """
    # 检查 Worker 类型是否支持
    if request.worker_type not in worker_manager.get_worker_types():
        raise HTTPException(
            status_code=400,
            detail=f"不支持的 Worker 类型: {request.worker_type}",
        )

    # 验证配置
    worker_class = worker_manager._worker_types[request.worker_type]
    valid, error = worker_class.validate_config(request.config)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    # 创建配置
    config = WorkerConfig(
        worker_type=request.worker_type,
        name=request.name,
        config=request.config,
        agent_id=request.agent_id,
        is_enabled=request.is_enabled,
        description=request.description,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    logger.info(f"[WorkerAPI] 管理员 {admin.email} 创建 Worker: {config.name}")

    return WorkerConfigResponse(
        id=config.id,
        worker_type=config.worker_type,
        name=config.name,
        config=config.mask_sensitive_config(),
        agent_id=config.agent_id,
        is_enabled=config.is_enabled,
        description=config.description,
        status="stopped",
        pid=None,
        started_at=None,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.get("/{worker_id}", response_model=WorkerConfigResponse)
async def get_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取单个 Worker 配置
    """
    result = await db.execute(
        select(WorkerConfig).where(WorkerConfig.id == worker_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Worker 不存在")

    status = worker_manager.get_status(config.id)

    return WorkerConfigResponse(
        id=config.id,
        worker_type=config.worker_type,
        name=config.name,
        config=config.mask_sensitive_config(),
        agent_id=config.agent_id,
        is_enabled=config.is_enabled,
        description=config.description,
        status=status.status.value if status else "stopped",
        pid=status.pid if status else None,
        started_at=status.started_at.isoformat() if status and status.started_at else None,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.put("/{worker_id}", response_model=WorkerConfigResponse)
async def update_worker(
    worker_id: str,
    request: WorkerConfigUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    更新 Worker 配置
    """
    result = await db.execute(
        select(WorkerConfig).where(WorkerConfig.id == worker_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Worker 不存在")

    # 更新字段
    if request.name is not None:
        config.name = request.name
    if request.config is not None:
        # 合并配置（保留未更新的字段）
        new_config = {**config.config, **request.config}
        config.config = new_config
    if request.agent_id is not None:
        config.agent_id = request.agent_id
    if request.is_enabled is not None:
        config.is_enabled = request.is_enabled
    if request.description is not None:
        config.description = request.description

    await db.commit()
    await db.refresh(config)

    logger.info(f"[WorkerAPI] 管理员 {admin.email} 更新 Worker: {config.name}")

    status = worker_manager.get_status(config.id)

    return WorkerConfigResponse(
        id=config.id,
        worker_type=config.worker_type,
        name=config.name,
        config=config.mask_sensitive_config(),
        agent_id=config.agent_id,
        is_enabled=config.is_enabled,
        description=config.description,
        status=status.status.value if status else "stopped",
        pid=status.pid if status else None,
        started_at=status.started_at.isoformat() if status and status.started_at else None,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.delete("/{worker_id}")
async def delete_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    删除 Worker 配置
    """
    result = await db.execute(
        select(WorkerConfig).where(WorkerConfig.id == worker_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Worker 不存在")

    # 如果正在运行，先停止
    status = worker_manager.get_status(worker_id)
    if status and status.status.value == "running":
        await worker_manager.stop(worker_id)

    name = config.name
    await db.delete(config)
    await db.commit()

    logger.info(f"[WorkerAPI] 管理员 {admin.email} 删除 Worker: {name}")

    return {"message": f"Worker '{name}' 已删除"}


@router.post("/{worker_id}/start", response_model=WorkerActionResponse)
async def start_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    启动 Worker
    """
    success, message = await worker_manager.start(worker_id, db)

    if success:
        logger.info(f"[WorkerAPI] 管理员 {admin.email} 启动 Worker: {worker_id}")

    return WorkerActionResponse(success=success, message=message)


@router.post("/{worker_id}/stop", response_model=WorkerActionResponse)
async def stop_worker(
    worker_id: str,
    admin: User = Depends(get_current_admin_user),
):
    """
    停止 Worker
    """
    success, message = await worker_manager.stop(worker_id)

    if success:
        logger.info(f"[WorkerAPI] 管理员 {admin.email} 停止 Worker: {worker_id}")

    return WorkerActionResponse(success=success, message=message)


@router.post("/{worker_id}/restart", response_model=WorkerActionResponse)
async def restart_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """
    重启 Worker
    """
    success, message = await worker_manager.restart(worker_id, db)

    if success:
        logger.info(f"[WorkerAPI] 管理员 {admin.email} 重启 Worker: {worker_id}")

    return WorkerActionResponse(success=success, message=message)


@router.post("/{worker_id}/test", response_model=WorkerActionResponse)
async def test_worker_connection(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    测试 Worker 连接
    """
    result = await db.execute(
        select(WorkerConfig).where(WorkerConfig.id == worker_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Worker 不存在")

    success, message = await worker_manager.test_connection(
        config.worker_type,
        config.config,
    )

    return WorkerActionResponse(success=success, message=message)


@router.post("/test")
async def test_new_worker_connection(
    request: WorkerConfigCreate,
):
    """
    测试新 Worker 配置的连接（创建前测试）
    """
    if request.worker_type not in worker_manager.get_worker_types():
        raise HTTPException(
            status_code=400,
            detail=f"不支持的 Worker 类型: {request.worker_type}",
        )

    success, message = await worker_manager.test_connection(
        request.worker_type,
        request.config,
    )

    return WorkerActionResponse(success=success, message=message)
