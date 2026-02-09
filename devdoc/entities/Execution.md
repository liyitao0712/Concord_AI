# Execution 执行记录

## 概述

WorkflowExecution 记录 Temporal 工作流的执行状态，AgentExecution 记录 AI Agent 的调用统计。主要用于监控和调试。

## 数据模型

### WorkflowExecution（工作流执行）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| workflow_id | String(100) | Temporal Workflow ID（唯一） |
| workflow_type | String(50) | 工作流类型 |
| status | String(20) | 状态 (pending/running/completed/failed) |
| title | String(200) | 标题 |
| input_data | JSON | 输入数据 |
| output_data | JSON | 输出数据 |
| error_message | Text | 错误信息 |
| started_at | DateTime | 开始时间 |
| completed_at | DateTime | 完成时间 |

### AgentExecution（Agent 执行记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| agent_name | String(50) | Agent 名称 |
| success | Boolean | 是否成功 |
| execution_time_ms | Integer | 执行耗时（毫秒） |
| model_used | String(100) | 使用的模型 |
| iterations | Integer | 迭代次数 |
| error_message | Text | 错误信息 |
| created_at | DateTime | 创建时间 |

## 相关文件

- Model: `backend/app/models/execution.py`
