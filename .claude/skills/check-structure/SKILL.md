---
name: check-structure
description: 检查代码库结构，发现框架混乱、文件组织不一致、Agent 功能重叠等问题
disable-model-invocation: true
context: fork
agent: Explore
---

# 代码库结构检查

从根目录开始，全面检查项目结构是否有混乱或不一致。

## 检查步骤

### 1. 目录结构概览
- 列出所有顶级目录
- 检查是否符合项目约定（backend/, frontend/, devdoc/, scripts/）
- 发现任何不应存在的文件或目录

### 2. Agent 体系检查
- 列出 backend/app/agents/ 下所有 Agent
- 检查功能是否有重叠
- 检查哪些 Agent 实际被调用，哪些是死代码

### 3. Model 层检查
- 列出 backend/app/models/ 下所有模型
- 检查是否有未使用的模型
- 检查表名和类名是否一致

### 4. API 路由检查
- 列出 backend/app/api/ 下所有路由文件
- 检查命名是否一致（admin_* vs admin/*）
- 检查是否有重复的端点

### 5. Workflow 检查
- 列出 backend/app/workflows/ 下所有工作流
- 检查与 Agent 的关系是否清晰

## 输出格式

### 目录结构
```
<列出目录树>
```

### 发现的问题

| 类别 | 位置 | 问题 | 严重程度 | 建议 |
|------|------|------|----------|------|
| Agent | agents/xxx.py | 描述问题 | 高/中/低 | 建议操作 |

### 建议的改进
1. ...
2. ...
