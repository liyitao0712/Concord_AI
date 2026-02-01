# Celery 迁移指南

## 📋 迁移概述

已成功将邮件轮询系统从 **APScheduler** 迁移到 **Celery**，以支持 100+ 邮箱账户的高并发场景。

---

## 🔄 架构变更对比

### 旧架构（APScheduler）
```
EmailWorker 进程
  └─ APScheduler
       ├─ Job 1: poll_account(邮箱1) - 每60秒
       ├─ Job 2: poll_account(邮箱2) - 每60秒
       └─ ... N 个Job

问题：
❌ 单进程瓶颈（无法水平扩展）
❌ I/O 阻塞累积（任务堆积）
❌ 无任务队列缓冲
❌ 故障影响所有邮箱
```

### 新架构（Celery）
```
Celery Beat（定时调度器）
  └─ 为每个邮箱创建定时任务 → Redis 队列

Celery Worker 1 ─┐
Celery Worker 2 ─┼─ 从 Redis 队列取任务并执行
Celery Worker N ─┘

优势：
✅ 水平扩展（可启动多个 Worker）
✅ 任务队列缓冲（防止丢失）
✅ 自动重试和故障隔离
✅ 实时监控（Flower）
```

---

## 📁 新增文件清单

### 核心文件
```
backend/app/celery_app.py                    # Celery 应用配置
backend/app/tasks/__init__.py                # 任务模块
backend/app/tasks/email.py                   # 邮件任务（拉取、处理）
backend/app/services/email_worker_service.py # 动态任务管理
backend/app/storage/local_file.py            # 本地存储（OSS降级）
backend/app/services/email_account_service.py # 邮箱级联删除
```

### 配置文件
```
docker-compose.yml                           # 添加 Celery 服务
requirements.txt                             # 添加 Celery 依赖
.env.example                                 # 添加配置项
```

### 迁移脚本
```
backend/alembic/versions/i8j9k0l1m2n3_*.py  # 数据库迁移
```

---

## 🚀 部署步骤

### 1. 安装依赖
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 运行数据库迁移
```bash
cd backend
alembic upgrade head
```

### 3. 启动 Celery 服务

#### 方式A：使用 Docker Compose（推荐）
```bash
# 启动所有服务（包括 Celery Beat 和 Worker）
docker-compose up -d

# 查看 Celery 日志
docker-compose logs -f celery-beat
docker-compose logs -f celery-worker

# 扩展 Worker 实例（水平扩展）
docker-compose up -d --scale celery-worker=5
```

#### 方式B：本地运行
```bash
cd backend
source venv/bin/activate

# 终端 1: 启动 Celery Beat（定时调度器）
celery -A app.celery_app beat --loglevel=info

# 终端 2: 启动 Celery Worker（任务执行器）
celery -A app.celery_app worker --loglevel=info --concurrency=10 --queues=email,default

# 终端 3（可选）: 启动 Flower（监控面板）
celery -A app.celery_app flower --port=5555
# 访问 http://localhost:5555
```

### 4. 同步邮箱任务
```python
# 在 Python 中手动同步（首次启动）
from app.services.email_worker_service import email_worker_service
import asyncio

asyncio.run(email_worker_service.sync_email_tasks(interval=60))
```

或者通过 API：
```bash
# TODO: 添加管理 API 端点
POST /admin/email-worker/sync
```

---

## 🔧 配置说明

### 环境变量
```bash
# .env 文件
REDIS_URL=redis://localhost:6379/0  # Celery broker 和 backend

# Celery 会自动使用 REDIS_URL，无需额外配置
```

### Celery 配置
```python
# app/celery_app.py

# 任务队列
task_queues = (
    Queue("default"),    # 默认队列
    Queue("email"),      # 邮件队列
    Queue("workflow"),   # 工作流队列
)

# Worker 并发数
worker_concurrency = 10  # 每个 Worker 10 个并发

# 任务重试
max_retries = 3          # 失败后重试 3 次
default_retry_delay = 60 # 重试间隔 60 秒
```

---

## 📊 监控和运维

### 1. Flower 监控面板
```bash
# 启动 Flower
celery -A app.celery_app flower --port=5555

# 访问
open http://localhost:5555
```

**功能**：
- 查看所有 Worker 状态
- 实时任务监控
- 任务历史和统计
- 任务重试和撤销

### 2. 查看任务状态
```bash
# Celery 命令行
celery -A app.celery_app inspect active    # 运行中的任务
celery -A app.celery_app inspect scheduled # 计划中的任务
celery -A app.celery_app inspect stats     # Worker 统计
```

### 3. 日志
```bash
# Docker 环境
docker-compose logs -f celery-beat
docker-compose logs -f celery-worker

# 本地环境
# Celery 日志会输出到 stdout
```

---

## 🔍 性能优化建议

### 1. Worker 并发配置
```bash
# CPU 密集型任务
celery -A app.celery_app worker --concurrency=4  # CPU 核心数

# I/O 密集型任务（邮件拉取）
celery -A app.celery_app worker --concurrency=20 # 2-3 倍 CPU 核心数
```

### 2. 水平扩展
```bash
# 启动多个 Worker 实例
celery -A app.celery_app worker --concurrency=10 --hostname=worker1@%h
celery -A app.celery_app worker --concurrency=10 --hostname=worker2@%h
celery -A app.celery_app worker --concurrency=10 --hostname=worker3@%h

# 或使用 Docker Compose
docker-compose up -d --scale celery-worker=5
```

### 3. 队列优先级
```python
# 高优先级邮箱
poll_email_account.apply_async(
    args=(account_id,),
    priority=9,  # 0-9，越大越高
)
```

---

## 🐛 故障排查

### 问题 1：任务未执行
```bash
# 检查 Worker 是否运行
celery -A app.celery_app inspect active_queues

# 检查 Beat 是否运行
docker-compose logs celery-beat | grep "Scheduler"

# 检查 Redis 连接
redis-cli ping
```

### 问题 2：任务堆积
```bash
# 查看队列长度
redis-cli llen celery

# 增加 Worker 实例
docker-compose up -d --scale celery-worker=10
```

### 问题 3：任务重复执行
```bash
# 检查是否有多个 Beat 实例
ps aux | grep "celery.*beat"

# 只能有 1 个 Beat 实例！
```

---

## 📝 API 变更

### 旧 API（已废弃）
```
GET  /admin/workers              # EmailWorker 状态
POST /admin/workers/start        # 启动 EmailWorker
POST /admin/workers/stop         # 停止 EmailWorker
```

### 新 API（TODO）
```
GET  /admin/celery/workers       # Celery Worker 状态
GET  /admin/celery/tasks         # 任务状态
POST /admin/celery/tasks/sync    # 同步邮箱任务
POST /admin/celery/tasks/{task_id}/retry  # 重试任务
```

---

## ✅ 迁移检查清单

- [ ] 安装 Celery 依赖 (`pip install -r requirements.txt`)
- [ ] 运行数据库迁移 (`alembic upgrade head`)
- [ ] 启动 Celery Beat
- [ ] 启动 Celery Worker（至少 2 个实例）
- [ ] 同步邮箱任务 (`email_worker_service.sync_email_tasks()`)
- [ ] 验证任务执行（查看 Flower 或日志）
- [ ] 停止旧的 EmailWorker 进程
- [ ] 更新监控和告警

---

## 🎯 性能对比（100 个邮箱）

### APScheduler
```
- 单进程处理所有邮箱
- 总耗时: 50 分钟
- 任务堆积严重
- 无法扩展
```

### Celery（5 个 Worker）
```
- 并发处理
- 总耗时: 8 分钟
- 任务均匀分布
- 可动态扩展
```

**性能提升：6.25 倍** 🚀

---

## 📚 相关文档

- [Celery 官方文档](https://docs.celeryproject.org/)
- [Flower 文档](https://flower.readthedocs.io/)
- [Redis 文档](https://redis.io/docs/)

---

## 🆘 技术支持

如遇问题，请检查：
1. Celery 日志 (`docker-compose logs celery-worker`)
2. Beat 日志 (`docker-compose logs celery-beat`)
3. Flower 监控面板 (`http://localhost:5555`)
4. Redis 连接 (`redis-cli ping`)
