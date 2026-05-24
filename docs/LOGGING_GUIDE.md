# 日志指南

本指南规定 Tenrec 排序项目如何记录日志，目标是保证项目可复现、可审计、可 review，并且后续项目叙事不会把计划写成事实。

## 日志文件

```text
docs/daily_logs/YYYY-MM-DD.md
docs/decision_log.md
docs/data_notes.md
docs/experiment_log.md
docs/issue_log.md
docs/project_summary.md
```

## Daily Log 模板

```markdown
# YYYY-MM-DD

## 今日目标

## 已完成事项

## 关键命令

## 修改文件

## 产出文件

## 问题 / 风险

## 当前 Git 状态

## 今日结论

## 下一步最小动作
```

Daily log 用于按时间记录工作过程。如果已有更具体的日志，例如 experiment log 或 issue log，不要把 daily log 当成最终实验事实源。

## Decision Log 模板

```markdown
## DECISION-YYYYMMDD-NN - 标题

### 日期

### 主题

### 可选方案

### 最终选择

### 选择原因

### 证据

### 对实验可比性的影响

### 对后续工作的影响
```

只有已确认决策才能写入 decision log。仍在讨论中的想法写入 daily log 或 notes，不要写成最终决策。

## Data Notes 模板

```markdown
## Dataset / File

### 来源

### 本地路径

### 行定义

### 字段

### Label 语义

### 负样本定义

### Timestamp 与时间切分可行性

### 用户历史构造

### 泄漏风险

### 待确认问题
```

Data notes 是 schema 和数据契约的 canonical fact source。

## Experiment Log 模板

```markdown
## RUN-YYYYMMDD-HHMMSS - Model / Purpose

### 目的

### 命令

### Git 状态

### Config / Arguments

### Data Contract Version

### Split

### Output Path

### Metrics

### Diagnostics

### 结论

### 限制
```

不要把计划中的实验写成已完成实验。

## Issue Log 模板

```markdown
## ISSUE-YYYYMMDD-NN - 标题

### 日期

### 类型

environment / data / code / training / evaluation / documentation

### 严重等级

Low / Medium / High / Critical

### 状态

Open / Investigating / Mitigated / Closed / Deferred

### 现象

### 证据

### 影响

### 根因或假设

### 修复或 workaround

### 验证

### 复用建议
```

不要删除旧 issue entry。后续状态更新追加记录。

## Project Summary 规则

`docs/project_summary.md` 只写已验证成果。

允许写：

- 已确认的数据集和 schema 事实；
- 已完成实验指标；
- 已验证诊断结果；
- 有证据支撑的简历 / 面试叙事。

不允许写：

- 尚未实现的模型；
- 计划中的指标；
- 讨论中的未验证结论；
- 没有证据的 “production” 或 “online” 说法。

## 文档变更后的验证命令

文档变更后至少运行：

```powershell
Get-ChildItem -Recurse -File docs | Sort-Object FullName
git status --short
```

如果仓库还没有初始化 git，必须明确说明。
