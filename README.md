# Concord AI

AI 驱动的业务自动化中台系统。

## 功能特性

- 邮件自动分析与处理
- 订单信息提取
- 项目信息管理
- 智能意图分类

## 快速开始

### 1. 环境配置

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑 .env，填入你的 API 密钥
```

### 2. 一键部署

```bash
./scripts/setup.sh
```

### 3. 启动服务

```bash
./scripts/start.sh
```

### 4. 验证

- 健康检查: http://localhost:8000/health
- API 文档: http://localhost:8000/docs

## 常用脚本

| 脚本 | 说明 |
|------|------|
| `./scripts/setup.sh` | 一键部署（首次使用） |
| `./scripts/start.sh` | 启动所有服务 |
| `./scripts/stop.sh` | 停止所有服务 |
| `./scripts/restart.sh` | 重启 Docker 容器 |
| `./scripts/status.sh` | 查看服务状态 |
| `./scripts/logs.sh` | 查看容器日志 |
| `./scripts/migrate.sh` | 数据库迁移 |
| `./scripts/reset-db.sh` | 重置数据库（危险！） |

## 项目结构

```
concord-ai/
├── docker-compose.yml      # Docker 容器编排
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic 模式
│   │   ├── services/       # 业务逻辑
│   │   └── agents/         # AI Agent
│   └── alembic/            # 数据库迁移
├── scripts/                # 运维脚本
├── tests/                  # 测试
└── devdoc/                 # 开发文档
```

## 技术栈

- **后端**: FastAPI + SQLAlchemy + PostgreSQL
- **缓存**: Redis
- **任务队列**: Celery + Redis
- **工作流**: Temporal
- **AI**: LiteLLM (Claude/GPT)
- **容器**: Docker Compose

## 文档

详细文档请查看 `devdoc/` 目录：

- `FINAL_TECHNICAL_SPEC.md` - 技术规格
- `MVP_DEVELOPMENT_PLAN.md` - 开发计划
- `DEVELOPMENT_LOG.md` - 开发记录
- `VERSION_MANIFEST.md` - 版本清单
