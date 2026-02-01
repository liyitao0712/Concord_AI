# set-improvement-todo

记录对话中发现的改进点到待改进文件

## Description

从当前对话内容中提取改进建议，记录到 `devdoc/IMPROVEMENTS.md` 文件中。

## Usage

```
/set-improvement-todo
```

自动分析当前对话，提取所有改进建议，并添加到待改进文件中。

## Instructions

当用户调用此 skill 时：

1. **分析对话内容**：
   - 查看最近的对话历史
   - 识别所有提到的问题、建议、改进点
   - 提取关键信息：问题描述、建议方案、影响范围、优先级

2. **读取现有文件**：
   - 读取 `devdoc/IMPROVEMENTS.md`（如果不存在则创建）
   - 获取当前的改进项数量，用于编号

3. **格式化改进项**：
   - 使用统一的 Markdown 格式
   - 每个改进项包含：
     - 标题（简洁描述问题）
     - 问题说明（当前状态）
     - 建议方案（如何改进）
     - 优先级（P0/P1/P2）
     - 影响范围（文件列表）
     - 预期收益
     - 来源（对话时间/主题）

4. **追加到文件**：
   - 在文件末尾添加新的改进项
   - 保持格式一致
   - 自动编号

5. **确认完成**：
   - 告知用户已添加多少个改进项
   - 显示文件路径

## Template

使用以下模板记录改进项：

```markdown
## [编号]. [改进标题]

**优先级**: P0 / P1 / P2

**问题描述**:
[当前存在的问题是什么]

**建议方案**:
[如何改进，具体步骤]

**影响范围**:
- `path/to/file1.py`
- `path/to/file2.py`

**预期收益**:
- [改进后的好处]

**来源**: 对话 - [日期] - [主题]

---
```

## Example

输入：
```
/set-improvement-todo
```

输出：
```
✅ 已添加 5 个改进项到 devdoc/IMPROVEMENTS.md

1. 统一 LLM 入口为 LLMGateway (P0)
2. 创建 llm_call_logs 表 (P0)
3. 添加 LLM 调用拦截器 (P1)
4. 实时更新模型统计 (P1)
5. 添加调用链追踪 (P2)

文件路径: devdoc/IMPROVEMENTS.md
```

## File Structure

创建的文件结构：

```
devdoc/
├── IMPROVEMENTS.md        # 待改进汇总（新）
├── DEVELOPMENT_LOG.md     # 开发日志
├── MANUAL.md              # 代码手册
└── LLM_MANUAL.md          # LLM 管理手册
```

## Notes

- 自动去重：如果某个改进项已存在，不重复添加
- 智能提取：从对话中识别优先级关键词（"立即"、"紧急" -> P0，"本周" -> P1，"下周" -> P2）
- 保持格式：确保 Markdown 格式正确，便于阅读
- 来源追踪：记录改进建议的来源（日期和主题）
