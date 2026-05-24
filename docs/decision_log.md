# 决策日志

本文件记录稳定项目决策及其证据。

## 2026-05-24 - 使用 Tenrec 作为主数据集

决策：使用 Tenrec 作为排序项目主数据集。

原因：

- Tenrec 比匿名广告 CTR benchmark 更接近腾讯 / 字节类内容流推荐场景。
- Tenrec 支持 click prediction，并为后续 multi-behavior / multi-task 扩展留空间。
- 官方描述说明它包含真实负反馈、多场景、多种正向反馈，以及 user / item ID 之外的额外特征。
- 它与已有 Amazon Two-Tower retrieval 项目互补，覆盖排序层（Ranking）。

证据：

- Official Tenrec website: https://tenrec0.github.io/
- Official code repository: https://github.com/yuangh-x/2022-NIPS-Tenrec
- NeurIPS 2022 paper entry: https://arxiv.org/abs/2210.10629

状态：作为项目方向已接受。真实 schema 仍需本地验证。

## 2026-05-24 - MVP 从单场景 click prediction 开始

决策：MVP 从一个 Tenrec 场景上的 click prediction 开始。

原因：

- 任务聚焦，指标清晰：AUC、GAUC、LogLoss。
- 有利于形成可复现、可被面试追问的第一里程碑。
- 避免在 label 和 history 字段验证前，过早承诺 multi-task 或 sequence model。

状态：作为 MVP 规划已接受。具体场景尚未选择。

## 2026-05-24 - schema inspection 前不创建 `src/` 和 `configs/`

决策：检查真实 Tenrec 字段前，不搭模型 / 数据模块和最终 config schema。

原因：

- 模型和 config 边界依赖真实字段、timestamp、label 语义、scenario 字段，以及用户历史是否能稳定构造。
- 过早 scaffold 容易把错误假设编码进项目结构。

状态：作为初始化阶段规则已接受。

## 2026-05-24 - 使用仓库 docs 作为 canonical fact sources

决策：使用仓库文档和日志作为项目 canonical fact sources，`README.md` 只作为对外摘要。

事实源优先级：

1. `AGENTS.md`：仓库规则与工作边界。
2. `docs/data_notes.md`：数据事实与数据契约。
3. `docs/decision_log.md`：已确认决策。
4. `docs/experiment_log.md`：已完成 run 和指标。
5. `docs/issue_log.md`：失败、修复和已知风险。
6. `docs/daily_logs/YYYY-MM-DD.md`：按时间记录的工作历史。
7. 实际命令输出和生成报告。
8. `README.md`：对外摘要。

原因：

- 项目目标是可审计实验工程。
- 排序实验容易出现 label leakage、split drift 和 metric provenance 不清。
- Amazon Two-Tower 的经验说明，README 摘要可能变旧，而日志能保留决策和证据历史。

状态：作为项目 workflow 已接受。

## 2026-05-24 - 使用 SSH remote 和显式 push 命令

决策：本仓库使用 SSH remote `git@github.com:EddyHai57/tenrec-ranking.git`。

原因：

- 本机已有 GitHub SSH key：`C:\Users\Eddy\.ssh\github_key`。
- `ssh -T git@github.com` 已成功认证为 `EddyHai57`。
- 显式 `GIT_SSH_COMMAND` 可以减少 Codex shell session 不共享 agent 状态导致的 push 失败。

本地 Codex session 的 push 命令：

```powershell
$env:GIT_SSH_COMMAND='ssh -i C:/Users/Eddy/.ssh/github_key -o IdentitiesOnly=yes'
git push -u origin main
```

边界：

- 没有 Eddy 明确要求，不 commit / push。
- push 前必须检查 staged files。
- 不假设后续训练服务器有这把 Windows SSH key；服务器 GitHub access 需要单独验证。
- `GIT_SSH_COMMAND` 中使用 forward slash 路径，避免 Windows backslash 被 `ssh` 解释成转义字符。

状态：作为仓库 workflow 已接受。

## 2026-05-24 - 项目 Markdown 默认使用中文

决策：本项目 Markdown 文档、日志、issue、decision、experiment 记录、project summary 和 agent 回答默认使用简体中文。

允许保留英文的内容：

- 文件名、目录名、代码标识符、命令、配置键；
- URL、remote、数据集、论文、仓库、模型和指标专有名称；
- 常用缩写，例如 CTR、AUC、GAUC、LogLoss、LR、MLP、DeepFM、DCN-v2、DIN、BST、MMOE、PLE。

原因：

- 本项目主要用于 Eddy 自己学习、复盘、面试准备和简历叙事，中文日志更利于快速回看。
- 专有名词保留英文可减少歧义，也便于后续代码、论文和面试材料对齐。

状态：已接受，并已同步到 `AGENTS.md`。
