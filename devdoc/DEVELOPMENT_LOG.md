# Concord AI - 开发记录

> 记录每次开发的内容、产出文件和验收状态

---

## 2026-01-29 - M1 基础设施搭建

### 开发内容

完成 MVP 开发计划中的 **Module 1: 基础设施**，包括：
- 项目目录结构创建
- Docker Compose 配置
- FastAPI 框架搭建
- 数据库连接配置（PostgreSQL + Alembic）
- Redis 连接配置
- 健康检查接口
- 运维脚本集合

### 产出文件清单

#### 项目根目录
```
Concord_AI/
├── .gitignore                 # Git 忽略配置
├── .env.example               # 环境变量模板
├── docker-compose.yml         # Docker 容器编排
└── README.md                  # 项目说明
```

#### 后端代码 (backend/)
```
backend/
├── requirements.txt           # Python 依赖
├── alembic.ini               # Alembic 配置
├── alembic/
│   ├── env.py                # Alembic 环境（异步支持）
│   ├── script.py.mako        # 迁移脚本模板
│   └── versions/             # 迁移版本目录
│
└── app/
    ├── __init__.py
    ├── main.py               # FastAPI 入口
    ├── api/
    │   ├── __init__.py
    │   └── health.py         # 健康检查接口
    ├── core/
    │   ├── __init__.py
    │   ├── config.py         # 配置管理（Pydantic Settings）
    │   ├── database.py       # 数据库连接（AsyncPG + SQLAlchemy）
    │   └── redis.py          # Redis 连接
    ├── models/
    │   └── __init__.py
    ├── schemas/
    │   └── __init__.py
    ├── services/
    │   ├── __init__.py
    │   └── email/
    │       └── __init__.py
    ├── agents/
    │   └── __init__.py
    └── prompts/
        └── __init__.py
```

#### 运维脚本 (scripts/)
```
scripts/
├── setup.sh                  # 一键部署
├── start.sh                  # 启动服务
├── stop.sh                   # 停止服务
├── restart.sh                # 重启服务
├── status.sh                 # 查看状态
├── logs.sh                   # 查看日志
├── migrate.sh                # 数据库迁移
└── reset-db.sh               # 清空数据库
```

#### 测试目录 (tests/)
```
tests/
├── __init__.py
├── unit/                     # 单元测试
├── e2e/                      # 端到端测试
└── fixtures/                 # 测试数据
```

### 关键代码说明

#### 1. FastAPI 入口 (app/main.py)
- 使用 `lifespan` 管理应用生命周期
- 启动时连接 Redis
- 关闭时清理资源
- 配置 CORS 中间件

#### 2. 数据库配置 (app/core/database.py)
- 使用 `asyncpg` 异步驱动
- SQLAlchemy 2.0 异步模式
- 提供 `get_db` 依赖注入

#### 3. Redis 配置 (app/core/redis.py)
- 封装 `RedisClient` 类
- 提供常用方法（get/set/delete/exists）
- 支持连接池

#### 4. 健康检查 (app/api/health.py)
- `/health` - 基础健康检查
- `/health/detailed` - 详细检查（含数据库和 Redis 状态）

### 验收标准

| 检查项 | 预期结果 | 状态 |
|--------|----------|------|
| `docker-compose up -d` | PostgreSQL 和 Redis 容器启动 | [ ] |
| `./scripts/setup.sh` | 一键完成环境配置 | [ ] |
| `./scripts/start.sh` | 服务正常启动 | [ ] |
| `http://localhost:8000/health` | 返回 `{"status": "ok"}` | [ ] |
| `http://localhost:8000/health/detailed` | 显示数据库和 Redis 连接状态 | [ ] |
| `http://localhost:8000/docs` | 显示 Swagger API 文档 | [ ] |

### 下一步计划

- [ ] M2: 认证与配置（JWT 登录）
- [ ] M3: LLM 服务（LiteLLM 集成）
- [ ] M6: 数据模型（用户、客户、订单、项目表）

---

## 开发约定

### 文件命名规范
- Python 文件：小写 + 下划线（snake_case）
- 类名：大驼峰（PascalCase）
- 函数/变量：小写 + 下划线（snake_case）

### Git 提交规范
```
feat: 新功能
fix: 修复 bug
docs: 文档更新
refactor: 重构
test: 测试相关
chore: 构建/工具相关
```

### 模块开发流程
1. 创建代码文件
2. 运行验证
3. 记录到本文档
4. 标记任务完成

---

*最后更新: 2026-01-29*
