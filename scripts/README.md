# Concord AI - Scripts 目录

本目录包含 Concord AI 项目的运维脚本和维护工具。

---

## 📂 目录结构

```
scripts/
├── README.md                      # 本文档
├── archive/                       # 已弃用脚本
│
├── 核心运维脚本 (Shell)
├── setup.sh                       # 一键部署
├── start.sh                       # 启动服务
├── stop.sh                        # 停止服务
├── restart.sh                     # 重启服务
├── status.sh                      # 查看状态
├── logs.sh                        # 查看日志
├── migrate.sh                     # 数据库迁移
├── reset-db.sh                    # 重置数据库（危险）
│
├── 维护工具 (Python)
├── create_admin.py                # 创建管理员
├── fix_email_body.py              # 修复邮件正文
│
└── 配置文件 (SQL)
    └── init-db.sql                # PostgreSQL 初始化
```

---

## 🔧 核心运维脚本

### setup.sh - 一键部署

**用途**: 首次部署系统，完成所有初始化工作

**功能**:
- ✓ 检查系统依赖（Docker、Python 3.11+、Node.js 18+）
- ✓ 创建 `.env` 配置文件
- ✓ 启动 Docker 容器（PostgreSQL、Redis、Temporal、Celery）
- ✓ 创建 Python 虚拟环境
- ✓ 安装后端依赖（requirements.txt）
- ✓ 执行数据库迁移
- ✓ 安装前端依赖（package.json）

**使用场景**: 首次部署、重新初始化环境

**用法**:
```bash
./scripts/setup.sh
```

**后续步骤**:
1. 编辑 `.env` 文件，填入 API 密钥
2. 创建管理员：`cd backend && source venv/bin/activate && python ../scripts/create_admin.py`
3. 启动服务：`./scripts/start.sh`

---

### start.sh - 启动服务

**用途**: 启动所有或指定的服务

**功能**:
- ✓ 启动 Docker 容器
- ✓ 更新后端依赖
- ✓ 执行数据库迁移
- ✓ 启动 Temporal Worker
- ✓ 启动前端服务
- ✓ 启动 FastAPI 后端

**选项**:
```bash
./scripts/start.sh              # 启动所有服务（前台运行后端）
./scripts/start.sh --bg         # 所有服务后台运行
./scripts/start.sh --api        # 只启动后端 API
./scripts/start.sh --worker     # 只启动 Temporal Worker
./scripts/start.sh --frontend   # 只启动前端
```

**服务地址**:
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 前端: http://localhost:3000
- Temporal UI: http://localhost:8080
- Flower: http://localhost:5555 (需启动)

---

### stop.sh - 停止服务

**用途**: 停止所有或部分服务

**功能**:
- ✓ 停止 FastAPI 服务（端口 8000）
- ✓ 停止 Temporal Worker
- ✓ 停止前端服务（端口 3000）
- ✓ 停止 Docker 容器（包括 Celery）

**选项**:
```bash
./scripts/stop.sh           # 停止所有服务
./scripts/stop.sh --keep    # 保留 Docker 容器，只停止应用
```

---

### restart.sh - 重启服务

**用途**: 重启服务，常用于代码更新后

**功能**:
- ✓ 重启 Docker 容器
- ✓ 更新后端依赖
- ✓ 执行数据库迁移
- ✓ 重启应用服务

**选项**:
```bash
./scripts/restart.sh            # 重启所有服务
./scripts/restart.sh --bg       # 后台运行
./scripts/restart.sh --api      # 只重启后端 API
./scripts/restart.sh --worker   # 只重启 Temporal Worker
./scripts/restart.sh --frontend # 只重启前端
./scripts/restart.sh --celery   # 只重启 Celery 服务
```

**使用场景**:
- 代码更新后
- 配置文件修改后
- 依赖更新后

---

### status.sh - 查看状态

**用途**: 查看所有服务的运行状态

**功能**:
- ✓ 显示 Docker 容器状态
- ✓ 显示端口映射
- ✓ 健康检查（PostgreSQL、Redis、Temporal、Celery）
- ✓ 显示应用服务状态（FastAPI、Temporal Worker、前端）
- ✓ 列出日志文件

**用法**:
```bash
./scripts/status.sh
```

**输出示例**:
```
Docker 容器:
  PostgreSQL:     [运行中]
  Redis:          [运行中]
  Celery Beat:    [运行中] (定时调度器)
  Celery Worker:  [运行中] (2 个实例)
  Flower:         [运行中] http://localhost:5555

健康检查:
  FastAPI:        [运行中] http://localhost:8000 (PID: 12345)
  Temporal Worker:[运行中] (PID: 12346)
  Frontend:       [运行中] http://localhost:3000 (PID: 12347)
```

---

### logs.sh - 查看日志

**用途**: 查看各服务的日志输出

**功能**:
- ✓ 查看 Docker 服务日志
- ✓ 查看 Celery 服务日志
- ✓ 查看应用服务日志

**用法**:
```bash
./scripts/logs.sh                # 查看所有 Docker 服务日志
./scripts/logs.sh postgres       # 查看 PostgreSQL 日志
./scripts/logs.sh redis          # 查看 Redis 日志
./scripts/logs.sh temporal       # 查看 Temporal Server 日志
./scripts/logs.sh temporal-ui    # 查看 Temporal UI 日志

./scripts/logs.sh celery-beat    # 查看 Celery Beat 日志
./scripts/logs.sh celery-worker  # 查看 Celery Worker 日志
./scripts/logs.sh flower         # 查看 Flower 日志
./scripts/logs.sh celery         # 查看所有 Celery 服务日志

./scripts/logs.sh api            # 查看 FastAPI 日志
./scripts/logs.sh worker         # 查看 Temporal Worker 日志
./scripts/logs.sh frontend       # 查看前端日志
./scripts/logs.sh all            # 查看所有应用日志
```

---

### migrate.sh - 数据库迁移

**用途**: 管理数据库迁移（使用 Alembic）

**功能**:
- ✓ 执行迁移（upgrade）
- ✓ 回滚迁移（downgrade）
- ✓ 创建新迁移（create）
- ✓ 查看迁移历史
- ✓ 查看当前版本

**用法**:
```bash
./scripts/migrate.sh              # 执行所有待处理的迁移
./scripts/migrate.sh upgrade      # 同上
./scripts/migrate.sh down         # 回滚上一次迁移
./scripts/migrate.sh create "描述" # 创建新迁移
./scripts/migrate.sh history      # 查看迁移历史
./scripts/migrate.sh current      # 查看当前版本
```

**注意事项**:
- 创建迁移前需确保数据库模型已更新
- 回滚操作需谨慎，可能导致数据丢失
- 生产环境迁移前应先备份数据库

---

### reset-db.sh - 重置数据库

**用途**: 完全重置数据库（⚠️ 危险操作）

**功能**:
- ✓ 停止所有容器
- ✓ 删除数据库卷
- ✓ 重启容器
- ✓ 执行数据库迁移

**用法**:
```bash
./scripts/reset-db.sh
```

**警告**:
- ⚠️ 会删除所有数据
- ⚠️ 不可恢复
- ⚠️ 仅用于开发环境
- ⚠️ 需要输入 `yes` 确认

**使用场景**: 开发环境重置、测试环境初始化

---

## 🛠️ 维护工具

### create_admin.py - 创建管理员

**用途**: 创建系统管理员账户

**功能**:
- ✓ 创建第一个管理员账户
- ✓ 检查是否已有管理员
- ✓ 验证邮箱唯一性
- ✓ 密码哈希存储

**默认账户**:
```
邮箱: admin@concordai.com
密码: admin123456
名称: 系统管理员
```

**用法**:
```bash
cd backend
source venv/bin/activate

# 使用默认值创建
python ../scripts/create_admin.py

# 自定义账户信息
python ../scripts/create_admin.py \
  --email admin@example.com \
  --password mypassword \
  --name "管理员"

# 简写形式
python ../scripts/create_admin.py -e admin@example.com -p mypass -n Admin
```

**注意事项**:
- 密码至少 6 位
- 如已有管理员会跳过创建
- 首次登录后建议修改密码

---

### fix_email_body.py - 修复邮件正文

**用途**: 修复没有 body_text 的历史邮件

**功能**:
- ✓ 从 OSS 重新解析邮件正文（推荐，快速）
- ✓ 从 IMAP 重新获取邮件（备选）
- ✓ 批量修复历史数据
- ✓ HTML 转纯文本

**用法**:
```bash
cd backend
source venv/bin/activate

# 从 OSS 解析（推荐）
python ../scripts/fix_email_body.py --limit 100

# 从 IMAP 获取
python ../scripts/fix_email_body.py --from-imap --limit 100

# 只处理指定账户
python ../scripts/fix_email_body.py --account-id 1

# 预览模式（不实际更新）
python ../scripts/fix_email_body.py --dry-run
```

**选项说明**:
- `--limit N` - 最大处理数量
- `--account-id ID` - 只处理指定邮箱账户
- `--dry-run` - 仅显示，不实际更新
- `--from-oss` - 从 OSS 解析（默认，更快）
- `--from-imap` - 从 IMAP 重新获取

**使用场景**:
- 邮件正文解析失败
- 数据迁移后修复
- 历史数据补全

---

## 📝 配置文件

### init-db.sql

**用途**: PostgreSQL 容器初始化脚本

**功能**:
- ✓ 创建 Temporal 数据库
- ✓ 创建 Temporal Visibility 数据库

**说明**:
- 由 Docker Compose 自动挂载到 PostgreSQL 容器
- 容器首次启动时自动执行
- 不需要手动运行

---

## 📦 已弃用脚本

已弃用的脚本移至 `scripts/archive/` 目录，详见 [archive/README.md](./archive/README.md)

---

## 🚀 快速参考

### 首次部署流程
```bash
# 1. 一键部署
./scripts/setup.sh

# 2. 编辑配置
vim .env

# 3. 创建管理员
cd backend && source venv/bin/activate
python ../scripts/create_admin.py

# 4. 启动服务
cd ..
./scripts/start.sh
```

### 日常开发流程
```bash
# 查看状态
./scripts/status.sh

# 重启服务（代码更新后）
./scripts/restart.sh

# 查看日志
./scripts/logs.sh api
./scripts/logs.sh celery

# 数据库迁移
./scripts/migrate.sh create "添加新字段"
./scripts/migrate.sh upgrade
```

### 常见问题排查
```bash
# 服务无法启动
./scripts/status.sh              # 检查状态
./scripts/logs.sh                # 查看日志
docker compose ps                # 检查容器

# 数据库问题
./scripts/migrate.sh current     # 查看迁移版本
./scripts/migrate.sh history     # 查看迁移历史
./scripts/reset-db.sh            # 重置数据库（开发环境）

# Celery 问题
./scripts/logs.sh celery         # 查看 Celery 日志
./scripts/restart.sh --celery    # 重启 Celery 服务
```

---

## 📞 获取帮助

每个脚本都支持查看帮助信息：

```bash
./scripts/setup.sh --help
./scripts/logs.sh              # 不带参数显示用法
python scripts/create_admin.py --help
```

---

## ⚠️ 安全提示

1. **生产环境**:
   - 修改默认管理员密码
   - 不使用 `reset-db.sh`
   - 迁移前备份数据库

2. **API 密钥**:
   - 不要将 `.env` 文件提交到版本控制
   - 定期轮换 API 密钥

3. **权限管理**:
   - 限制管理员账户数量
   - 使用强密码

---

*最后更新: 2026-02-01*
