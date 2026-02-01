# tests/conftest.py
# Pytest 配置文件
#
# 功能：
# 1. 自动加载环境变量
# 2. 设置数据库连接
# 3. 提供通用 fixtures

import os
import sys
import pytest
import asyncio

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== 环境配置 ====================

def pytest_configure(config):
    """Pytest 启动时配置"""
    # 加载 .env 文件
    from dotenv import load_dotenv
    load_dotenv()

    # 确保有必要的环境变量
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("\n警告: 未设置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY，LLM 相关测试可能失败\n")


# ==================== Event Loop ====================

@pytest.fixture(scope="session")
def event_loop():
    """创建全局事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== 数据库 Fixtures ====================

@pytest.fixture
async def db_session():
    """获取数据库会话"""
    from app.core.database import async_session_maker

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def setup_intents(db_session):
    """确保数据库中有意图种子数据"""
    from sqlalchemy import select, func
    from app.models.intent import Intent, SEED_INTENTS

    # 检查是否有数据
    count = await db_session.scalar(select(func.count(Intent.id)))

    if count == 0:
        # 插入种子数据
        from uuid import uuid4
        for seed in SEED_INTENTS:
            intent = Intent(
                id=str(uuid4()),
                **seed,
                created_by="system",
            )
            db_session.add(intent)
        await db_session.commit()

    yield

    # 测试结束后不删除数据（保留种子数据）


# ==================== Redis Fixtures ====================

@pytest.fixture
async def redis_client():
    """获取 Redis 客户端"""
    from app.core.redis import redis_client as client

    await client.connect()
    yield client
    await client.disconnect()


# ==================== API 客户端 Fixtures ====================

@pytest.fixture
def api_client():
    """创建测试用 API 客户端"""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_api_client():
    """创建异步测试用 API 客户端"""
    from httpx import AsyncClient
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ==================== 认证 Fixtures ====================

@pytest.fixture
def admin_token(api_client):
    """获取管理员 Token"""
    response = api_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })

    if response.status_code != 200:
        pytest.skip("无法登录管理员账户，跳过需要认证的测试")

    return response.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    """获取带认证的请求头"""
    return {"Authorization": f"Bearer {admin_token}"}
