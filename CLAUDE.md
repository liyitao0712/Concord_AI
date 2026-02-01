# Concord AI 项目说明

这是一个 AI 中台系统，基于 FastAPI + Next.js + Temporal + Celery + LangGraph 构建。

## 技术栈

- **后端**: FastAPI + SQLAlchemy + PostgreSQL + Redis
- **前端**: Next.js 14 + TypeScript + Tailwind CSS
- **任务队列**: Celery + Redis（邮件轮询、定时任务）
- **工作流**: Temporal（业务流程编排）
- **Agent**: LangGraph + LiteLLM
- **文档**: devdoc/ 目录

## 重要文件

- `devdoc/FINAL_TECHNICAL_SPEC.md` - 技术规格文档
- `devdoc/DEVELOPMENT_LOG.md` - 开发日志
- `devdoc/MVP_DEVELOPMENT_PLAN.md` - MVP 开发计划

---

## 自定义命令

### /log-improvement

当发现需要改进的地方时，将其记录到 `devdoc/DEVELOPMENT_LOG.md` 的 **"待改进汇总"** 部分。

**记录格式**：

```markdown
### N. 改进标题

**问题**：当前状态是什么

| 当前 | 建议改为 | 文件 |
|-----|---------|------|
| xxx | xxx | `path/to/file.py` |

**原因**：
- 为什么需要改

**改动范围**：
- 涉及的文件列表
```

记录完成后告知用户已添加。

---

### /dev-status

查看当前开发进度：
1. 读取 `devdoc/DEVELOPMENT_LOG.md` 最新的开发记录
2. 总结已完成的 Phase 和下一步计划
3. 列出"待改进汇总"中未处理的项目

---

## 开发约定

- 代码注释和文档使用中文
- Git 提交信息使用中文
- API 响应的 detail 信息使用中文
- 后台管理相关 API 统一放在 `/admin/*` 路由下
- 每次开发万需要统一更新/scripts/下关联的setup还有restart脚本