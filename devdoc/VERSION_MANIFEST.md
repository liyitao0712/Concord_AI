# Concord AI - 版本清单

> 记录项目中所有依赖的版本信息，确保环境一致性

---

## 一、运行环境

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.11+ | 推荐 3.11.x 或 3.12.x |
| Node.js | 18+ | 前端开发（未来） |
| Docker | 24+ | 容器运行时 |
| Docker Compose | 2.20+ | 容器编排 |

---

## 二、Docker 容器镜像

| 服务 | 镜像 | 版本 | 端口 |
|------|------|------|------|
| PostgreSQL | postgres | 18-alpine | 5432 |
| Redis | redis | 7-alpine | 6379 |

---

## 三、Python 依赖

### 核心框架

| 包名 | 版本 | 用途 |
|------|------|------|
| fastapi | >=0.109.0 | Web 框架 |
| uvicorn[standard] | >=0.27.0 | ASGI 服务器 |
| pydantic | >=2.0 | 数据验证 |
| pydantic-settings | >=2.0 | 配置管理 |

### 数据库

| 包名 | 版本 | 用途 |
|------|------|------|
| sqlalchemy | >=2.0 | ORM |
| asyncpg | >=0.29.0 | PostgreSQL 异步驱动 |
| alembic | >=1.13.0 | 数据库迁移 |

### 缓存/消息

| 包名 | 版本 | 用途 |
|------|------|------|
| redis | >=5.0 | Redis 客户端 |

### AI/LLM

| 包名 | 版本 | 用途 |
|------|------|------|
| litellm | >=1.23.0 | LLM 统一接口 |

### 调度

| 包名 | 版本 | 用途 |
|------|------|------|
| apscheduler | >=3.10.0 | 定时任务 |

### 认证

| 包名 | 版本 | 用途 |
|------|------|------|
| python-jose[cryptography] | >=3.3.0 | JWT 处理 |
| passlib[bcrypt] | >=1.7.4 | 密码哈希 |

### 邮件

| 包名 | 版本 | 用途 |
|------|------|------|
| aioimaplib | >=1.0.0 | IMAP 异步客户端 |

### HTTP 客户端

| 包名 | 版本 | 用途 |
|------|------|------|
| httpx | >=0.26.0 | 异步 HTTP 客户端 |

### 工具

| 包名 | 版本 | 用途 |
|------|------|------|
| python-dotenv | >=1.0.0 | 环境变量加载 |
| python-multipart | >=0.0.6 | 文件上传支持 |

### 测试

| 包名 | 版本 | 用途 |
|------|------|------|
| pytest | >=8.0.0 | 测试框架 |
| pytest-asyncio | >=0.23.0 | 异步测试支持 |

---

## 四、未来依赖（Phase 2+）

| 包名 | 版本 | 用途 | 阶段 |
|------|------|------|------|
| langgraph | >=0.0.26 | Agent 框架 | M5 |
| temporalio | >=1.4.0 | 工作流引擎 | Phase 2 |
| pgvector | >=0.2.0 | 向量搜索 | Phase 2 |
| oss2 | >=2.18.0 | 阿里云 OSS | Phase 2 |
| PyMuPDF | >=1.23.0 | PDF 解析 | Phase 2 |
| python-docx | >=1.1.0 | Word 解析 | Phase 2 |
| beautifulsoup4 | >=4.12.0 | HTML 解析 | Phase 2 |
| openpyxl | >=3.1.0 | Excel 解析 | Phase 2 |

---

## 五、前端依赖（未来）

| 包名 | 版本 | 用途 |
|------|------|------|
| next | >=14.0.0 | React 框架 |
| react | >=18.2.0 | UI 库 |
| typescript | >=5.0.0 | 类型支持 |
| tailwindcss | >=3.4.0 | CSS 框架 |
| zustand | >=4.5.0 | 状态管理 |
| @tanstack/react-query | >=5.0.0 | 数据请求 |

---

## 六、版本锁定文件

| 文件 | 位置 | 说明 |
|------|------|------|
| requirements.txt | backend/ | Python 依赖 |
| package.json | frontend/ | Node.js 依赖（未来） |
| docker-compose.yml | 根目录 | 容器版本 |

---

## 七、版本更新策略

### 更新频率
- **安全更新**: 立即更新
- **小版本更新**: 每月评估
- **大版本更新**: 每季度评估，需测试

### 更新流程
1. 在开发环境测试新版本
2. 更新 requirements.txt
3. 更新本文档
4. 提交代码并标注版本变更

### 版本兼容性
- Python: 保持 3.11+ 兼容
- PostgreSQL: 保持 18.x 兼容（阿里云 RDS 版本）
- Redis: 保持 7+ 兼容

---

*最后更新: 2026-01-29*
