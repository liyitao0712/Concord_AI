# Concord AI - 运维脚本与系统设置

> 运维脚本使用指南和系统设置管理
> 拆分自: MANUAL.md §16-17

---

## 1. 运维脚本

**目录**: `scripts/`

### 脚本列表

| 脚本 | 说明 |
|------|------|
| `setup.sh` | 一键部署（安装所有依赖） |
| `start.sh` | 启动所有服务 |
| `stop.sh` | 停止所有服务 |
| `restart.sh` | 重启所有服务 |
| `status.sh` | 查看服务状态 |
| `logs.sh` | 查看日志 |
| `migrate.sh` | 数据库迁移 |
| `reset-db.sh` | 重置数据库 |
| `create_admin.py` | 创建管理员账号 |

### 一键部署

```bash
./scripts/setup.sh
```

执行步骤：
1. 检查系统依赖（Docker、Python、Node.js）
2. 创建 `.env` 配置文件
3. 启动 Docker 容器（PostgreSQL、Redis、Temporal）
4. 等待容器就绪
5. 创建 Python 虚拟环境
6. 安装后端依赖
7. 执行数据库迁移
8. 安装前端依赖

### 启动服务

```bash
# 启动所有服务（API 前台运行）
./scripts/start.sh

# 所有服务后台运行
./scripts/start.sh --bg

# 只启动特定服务
./scripts/start.sh --api       # 只启动后端 API
./scripts/start.sh --worker    # 只启动 Temporal Worker
./scripts/start.sh --frontend  # 只启动前端
```

启动的服务：
- Docker 容器（PostgreSQL、Redis、Temporal、Temporal UI）
- Temporal Worker（后台运行，日志在 `logs/worker.log`）
- Next.js 前端（后台运行，日志在 `logs/frontend.log`）
- FastAPI 后端（前台或后台运行）

### 停止服务

```bash
# 停止所有服务（包括 Docker）
./scripts/stop.sh

# 只停止应用，保留 Docker 容器
./scripts/stop.sh --keep
```

### 重启服务

```bash
# 重启所有服务
./scripts/restart.sh

# 后台重启
./scripts/restart.sh --bg

# 只重启特定服务
./scripts/restart.sh --api
./scripts/restart.sh --worker
./scripts/restart.sh --frontend
```

### 查看状态

```bash
./scripts/status.sh
```

输出示例：
```
Docker 容器:
------------------------------------------
NAME                STATUS              PORTS
concord-postgres    Up 2 hours          0.0.0.0:5432->5432/tcp
concord-redis       Up 2 hours          0.0.0.0:6379->6379/tcp
concord-temporal    Up 2 hours          0.0.0.0:7233->7233/tcp

健康检查:
------------------------------------------
  PostgreSQL:     [运行中]
  Redis:          [运行中]
  Temporal:       [运行中]
  Temporal UI:    [运行中] http://localhost:8080
  FastAPI:        [运行中] http://localhost:8000 (PID: 12345)
  Temporal Worker:[运行中] (PID: 12346)
  Frontend:       [运行中] http://localhost:3000 (PID: 12347)
```

### 查看日志

```bash
# 查看所有 Docker 服务日志
./scripts/logs.sh

# 查看特定 Docker 服务
./scripts/logs.sh postgres
./scripts/logs.sh redis
./scripts/logs.sh temporal
./scripts/logs.sh temporal-ui

# 查看应用日志
./scripts/logs.sh api        # FastAPI 日志
./scripts/logs.sh worker     # Temporal Worker 日志
./scripts/logs.sh frontend   # 前端日志
./scripts/logs.sh all        # 所有应用日志
```

### 数据库操作

```bash
# 执行数据库迁移
./scripts/migrate.sh

# 创建新的迁移文件
./scripts/migrate.sh "add user table"

# 重置数据库（删除所有数据）
./scripts/reset-db.sh
```

### 创建管理员

```bash
cd backend
source venv/bin/activate
python ../scripts/create_admin.py
```

默认创建：
- 邮箱: `admin@concordai.com`
- 密码: `admin123456`

### 服务地址一览

| 服务 | 地址 | 说明 |
|------|------|------|
| 后端 API | http://localhost:8000 | FastAPI 服务 |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| 前端 | http://localhost:3000 | Next.js 应用 |
| Temporal UI | http://localhost:8080 | 工作流管理界面 |
| PostgreSQL | localhost:5432 | 数据库 |
| Redis | localhost:6379 | 缓存 |
| Temporal | localhost:7233 | 工作流引擎（gRPC） |

### 日志文件位置

| 文件 | 说明 |
|------|------|
| `logs/api.log` | FastAPI 后端日志 |
| `logs/worker.log` | Temporal Worker 日志 |
| `logs/frontend.log` | Next.js 前端日志 |

---

## 2. 系统设置

管理员可以在后台界面配置系统设置，无需修改环境变量或重启服务。

### 2.1 访问设置页面

1. 登录管理后台: http://localhost:3000/admin
2. 点击侧边栏 "系统设置"

### 2.2 LLM 配置

#### 选择默认模型

系统支持以下 LLM 模型：

| 模型 ID | 名称 | 提供商 | 说明 |
|---------|------|--------|------|
| claude-sonnet-4-20250514 | Claude Sonnet 4 | Anthropic | 推荐，性能均衡 |
| claude-3-5-sonnet-20241022 | Claude 3.5 Sonnet | Anthropic | 高性能通用模型 |
| claude-3-opus-20240229 | Claude 3 Opus | Anthropic | 最强大，适合复杂任务 |
| claude-3-haiku-20240307 | Claude 3 Haiku | Anthropic | 最快速，适合简单任务 |
| gpt-4o | GPT-4o | OpenAI | 多模态模型 |
| gpt-4-turbo | GPT-4 Turbo | OpenAI | 更快更便宜 |
| gpt-3.5-turbo | GPT-3.5 Turbo | OpenAI | 性价比高 |

#### 配置 API Key

1. **Anthropic API Key**: 从 https://console.anthropic.com 获取
2. **OpenAI API Key**: 从 https://platform.openai.com 获取

输入 API Key 后点击 "保存配置"。系统会安全存储（只显示部分字符）。

#### 测试连接

点击 "测试连接" 按钮验证配置是否正确。成功会显示模型名称，失败会显示错误信息。

### 2.3 邮件配置

#### SMTP 发件服务器

| 字段 | 说明 | 示例 |
|------|------|------|
| 服务器地址 | SMTP 主机名 | smtp.qq.com |
| 端口 | 通常 465 (SSL) 或 587 (STARTTLS) | 465 |
| 用户名 | 发件邮箱地址 | your@qq.com |
| 密码 | 授权码（不是登录密码） | 从邮箱设置获取 |

#### IMAP 收件服务器

| 字段 | 说明 | 示例 |
|------|------|------|
| 服务器地址 | IMAP 主机名 | imap.qq.com |
| 端口 | 通常 993 (SSL) | 993 |
| 用户名 | 收件邮箱地址 | your@qq.com |
| 密码 | 授权码 | 从邮箱设置获取 |

### 2.4 配置优先级

设置按以下优先级生效：

1. **数据库设置**（最高）- 通过管理后台配置
2. **环境变量** - `.env` 文件中的配置
3. **代码默认值**（最低）- 代码中的默认值

这意味着管理员在后台修改设置后立即生效，无需重启服务。

### 2.5 设置 API

开发者可以通过 API 管理设置（注意：所有设置 API 都在 `/admin/settings` 下）：

```bash
# 获取 LLM 配置
curl http://localhost:8000/admin/settings/llm \
  -H "Authorization: Bearer <token>"

# 更新 LLM 配置
curl -X PUT http://localhost:8000/admin/settings/llm \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"default_model": "claude-3-haiku-20240307"}'

# 测试 LLM 连接
curl -X POST http://localhost:8000/admin/settings/llm/test \
  -H "Authorization: Bearer <token>"

# 获取邮件配置
curl http://localhost:8000/admin/settings/email \
  -H "Authorization: Bearer <token>"
```

---

*拆分自 MANUAL.md | 最后更新: 2026-02-01*
