# Scripts Archive - 已弃用脚本

此目录存放已弃用的脚本，仅作历史参考。

---

## 📦 归档脚本列表

### migrate_feishu_to_workers.py

**归档日期**: 2026-02-01

**原始用途**: 将飞书配置从 `system_settings` 表迁移到 `worker_configs` 表

**归档原因**:
- 一次性迁移脚本，已完成使命
- 系统已全面迁移到新的 Worker 配置架构
- 不再需要执行此迁移

**功能说明**:
```python
# 功能：
1. 从 system_settings 表读取飞书配置（app_id、app_secret 等）
2. 创建新的 WorkerConfig 记录
3. 删除旧的 system_settings 记录

# 使用方法（已不需要）：
cd backend && source venv/bin/activate
python ../scripts/migrate_feishu_to_workers.py
```

**替代方案**:
- 飞书配置现在直接在管理后台的 Worker 管理页面配置
- 访问: http://localhost:3000/admin/workers
- 或使用 API: `POST /admin/workers`

**相关文档**:
- Worker 架构说明: [devdoc/ARCHITECTURE.md](../../devdoc/ARCHITECTURE.md)
- Worker 管理 API: [backend/app/api/workers.py](../../backend/app/api/workers.py)

---

## 📝 归档策略

### 何时归档脚本

脚本满足以下任一条件时归档：

1. **一次性迁移脚本** - 已完成数据迁移或配置迁移
2. **架构变更** - 系统架构更新导致脚本不再适用
3. **功能替代** - 已有更好的替代方案
4. **依赖废弃** - 依赖的组件已从系统移除

### 归档而非删除的原因

保留归档脚本是为了：

- 📚 **历史参考** - 了解系统演进过程
- 🔍 **问题排查** - 回溯旧版本问题时参考
- 📖 **学习资料** - 了解过去的设计决策
- 🛡️ **数据恢复** - 极端情况下的数据迁移参考

---

## ⚠️ 使用警告

**请勿运行归档脚本！**

归档脚本可能：
- 与当前数据库结构不兼容
- 依赖已移除的模块或配置
- 产生不可预期的结果

如需参考，请仅阅读代码，不要执行。

---

*最后更新: 2026-02-01*
