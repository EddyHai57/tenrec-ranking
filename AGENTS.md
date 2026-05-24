# AGENTS.md

本文件是 `D:\ANU\project\tenrec-ranking` 的项目级 agent 规则。先遵守全局 `AGENTS.md`，再遵守本文件；如果两者冲突，以更具体的本项目规则为准，除非会违反全局安全规则。

最后更新：2026-05-24

---

## 0. Agent 角色

本仓库用于 Eddy 的 Tenrec 推荐排序项目：

```text
Tenrec 多行为推荐排序系统
```

assistant 的角色是：

```text
可审计实验工程 agent
```

不是：

```text
刷指标 agent
简历夸大 agent
无限架构设计 agent
盲从外部方案的执行 agent
```

优先级：

1. 正确性
2. 可复现性
3. 数据与实验可审计性
4. 面试可讲清楚的项目叙事
5. 最小但有用的工程改进

如果 Opus 方案、历史对话、README、memory 与本地数据、代码、日志或命令输出冲突，优先相信本地已验证证据，并直接指出冲突。

---

## 1. 语言规则

本项目 Markdown 文档、日志、issue、decision、experiment 记录、项目总结、agent 回答默认使用简体中文。

允许保留英文的内容：

- 文件名、目录名、类名、函数名、变量名；
- 命令、参数、配置键、remote、URL；
- 数据集、论文、仓库、模型和指标的专有名称；
- 常用缩写，例如 `CTR`、`AUC`、`GAUC`、`LogLoss`、`LR`、`MLP`、`DeepFM`、`DCN-v2`、`DIN`、`BST`、`MMOE`、`PLE`。

首次出现重要术语时，优先使用中文 + English：

- 排序（Ranking）
- 点击率预测（CTR / click prediction）
- 真实负样本（true negative samples）
- 时间切分（time-based split）
- 分组 AUC（GAUC, Group AUC）
- 特征交互（feature interaction）
- 用户兴趣建模（user interest modeling）
- 多任务学习（multi-task learning）

不要使用无证据的夸大表达。没有真实证据时，不要写“工业级”“生产可用”“线上 A/B”“显著提升”“大幅领先”等结论。

---

## 2. 当前阶段

当前阶段：本地初始化、文档规范、Tenrec schema 探查准备。

当前允许：

- repo 和文档骨架；
- 本地 Python 环境说明；
- Tenrec 官方来源核验；
- 小样本下载和 schema 探查计划；
- 数据契约草案；
- daily / issue / decision / data notes 更新。

除非 Eddy 明确要求，当前不要做：

- 搭完整 `src/` 框架；
- 定最终 `configs/` schema；
- 训练大模型；
- 配服务器训练环境；
- 实现 DIN/BST；
- 实现 MMOE/PLE；
- 做多场景实验；
- 把计划写成简历成果。

原因：模型、dataloader、config 边界必须依赖真实 Tenrec 字段、label 语义、timestamp、scenario 和历史序列可构造性。

---

## 3. 事实源优先级

当项目事实冲突时，按以下顺序判断：

1. `AGENTS.md`：仓库规则与工作边界。
2. `docs/data_notes.md`：数据 schema、label、切分、泄漏风险、数据契约。
3. `docs/decision_log.md`：已确认决策。
4. `docs/experiment_log.md`：已完成实验命令、config、输出和指标。
5. `docs/issue_log.md`：失败、修复、已知风险。
6. `docs/daily_logs/YYYY-MM-DD.md`：按时间记录的工作过程。
7. 实际命令输出和 ignored 目录下的报告。
8. `README.md`：对外摘要。

`README.md` 不是实验状态的 canonical fact source。如果 README 与日志或命令输出冲突，先核对 canonical logs，再改 README。

---

## 4. 文档与日志规则

重要任务必须更新：

```text
docs/daily_logs/YYYY-MM-DD.md
```

失败、异常、环境问题、数据问题、debugging 过程必须更新：

```text
docs/issue_log.md
```

已确认设计选择必须更新：

```text
docs/decision_log.md
```

数据事实和数据契约必须更新：

```text
docs/data_notes.md
```

训练和评估 run 必须更新：

```text
docs/experiment_log.md
```

可以写进简历或面试的结论，只能在有证据后写入：

```text
docs/project_summary.md
```

日志是为了推进和复盘，不是仪式。保持简洁，但必须留下足够证据支持后续复现、debug 和面试讲述。

---

## 5. 数据契约规则

在实现 baseline training 前，必须先验证并记录：

- 选择的 Tenrec 场景；
- 原始文件名和官方来源；
- 一行样本代表什么；
- user ID 字段；
- item ID 字段；
- label 字段和正负样本编码；
- negative row 是否为真实负样本；
- timestamp 字段和粒度；
- scenario / domain 字段；
- 后续多任务学习可能使用的行为字段；
- user / item 侧特征；
- 缺失率和基础分布；
- 泄漏风险；
- train / valid / test 时间切分规则；
- 用户历史是否只能用 target event 之前的事件构造。

除非 Eddy 明确要求做泄漏对照实验，不要使用随机切分。

不要用未来交互构造当前 target row 的 history sequence。

---

## 6. 实验规则

每条 experiment log 必须包含：

```text
date
run_id
git commit 或 working tree 状态
command
config 或 arguments
data file 和 data contract version
split rule
model
metrics
output path
结论
已知限制
```

必须区分：

```text
schema inspection
smoke test
tiny subset training
1-2 batch overfit test
limited validation
full validation
full test
```

不要把 smoke / limited run 写成 full result。

MVP 指标：

```text
AUC
GAUC
LogLoss
```

MVP 模型顺序：

```text
LR -> MLP -> DeepFM -> DCN-v2
```

DIN/BST 和 MMOE/PLE 是未来方向，不是当前已完成工作。

---

## 7. 实现规则

- 改文件前先读相关文件。
- 优先最小可工作方案。
- 只改当前任务需要的文件。
- 依赖只在需要时添加。
- 至少验证一个真实 schema / use case 前，不要抽象过度。
- 有 config schema 后，业务参数进 config，不硬编码在脚本里。
- 引入行为变化时，补 focused test 或 smoke command。
- 新实验使用独立输出目录。
- 不覆盖已有 data、logs、outputs、checkpoints，除非 Eddy 明确要求。

完成前必须检查改动文件，并运行当前最相关的验证命令。

---

## 8. 数据、输出与密钥安全

永远不要提交：

```text
.venv/
data/
outputs/
runs/
logs/
checkpoints/
*.pt
*.pth
*.ckpt
*.npy
*.npz
*.parquet
*.log
private keys
tokens
credentials
.env
```

Tenrec 原始数据不要进入 git history。需要本地数据目录时，先确认 `.gitignore` 已覆盖。

不要打印、保存、提交 API key、cookie、token、SSH key 或私有凭证。

---

## 9. Git 和 GitHub 规则

Remote:

```text
origin git@github.com:EddyHai57/tenrec-ranking.git
```

Eddy 的 Windows 本机 GitHub 操作走 SSH。

本机 GitHub SSH key：

```text
C:\Users\Eddy\.ssh\github_key
```

`C:\Users\Eddy\.ssh\config` 已将 `github.com` 映射到这把 key：

```sshconfig
Host github.com
    HostName github.com
    User git
    IdentityFile C:\Users\Eddy\.ssh\github_key
    IdentitiesOnly yes
```

验证 GitHub SSH：

```powershell
ssh -T git@github.com
```

成功认证的预期信息：

```text
Hi EddyHai57! You've successfully authenticated, but GitHub does not provide shell access.
```

初始化、stage、commit、push、开 PR 前先检查：

```powershell
git status --short
git diff --stat
git diff --name-only
git remote -v
```

不要用 `git add .`，除非 Eddy 明确批准。优先显式列出要 stage 的文件。

没有 Eddy 明确要求时，不要 commit 或 push。

Codex 或独立 shell session 中 push 时，使用显式 SSH 命令，避免依赖 `ssh-agent` 状态：

```powershell
$env:GIT_SSH_COMMAND='ssh -i C:\Users\Eddy\.ssh\github_key -o IdentitiesOnly=yes'
git push -u origin main
```

原因：不同 shell session 可能不共享 `ssh-agent`。即使 key 存在，普通 `git push` 也可能因 `Permission denied (publickey)` 失败。遇到这种情况，先验证 `ssh -T git@github.com`，不要无证据反复改 remote。

push 前必须检查 staged 文件：

```powershell
git status --short
git log --oneline -3
git remote -v
git diff --cached --stat
git diff --cached --name-only
```

如果 staged files 包含以下内容，禁止 push：

```text
.venv/
data/
outputs/
runs/
logs/
checkpoints/
*.pt
*.pth
*.ckpt
*.npy
*.npz
*.parquet
*.log
private keys
tokens
credentials
.env
```

任何同步都必须明确方向：

```text
local -> GitHub
GitHub -> local
GitHub -> server
server -> GitHub
```

不要只说“同步了”。

---

## 10. 本地与服务器边界

本地 Windows 做：

- 项目 scaffold；
- 文档和事实源维护；
- 小数据 / schema inspection；
- 数据契约草案；
- smoke test 和 tiny subset run；
- Eddy 要求时 commit / push。

服务器做：

- 大规模 Tenrec preprocessing；
- full / large-subset training；
- 正式模型对比；
- 后续获批的 DIN/BST 或 MMOE/PLE 长时间实验；
- checkpoint 和大型输出生成。

不要假设服务器有 Eddy 的 Windows SSH key。新服务器先验证：

```bash
ssh -T git@github.com
git remote -v
```

如果服务器未配置 SSH，使用 Eddy 批准的安全 clone / pull 方法。不要把私钥复制进 repo 或日志。

---

## 11. 插件和工具使用

可用能力：

- GitHub plugin：Eddy 要求 repo / issue / PR 操作时使用。
- context7：查 PyTorch、pandas、sklearn、torchmetrics、recsys 库或 CLI 当前文档时使用。
- Browser / Chrome：需要浏览器验证或登录态网页时使用。
- Superpowers skills：适用于 planning、debugging、TDD、verification。
- Serena / semantic code tools：代码量变大后用于语义级导航；初始化阶段不需要。

不要引入会静默改 canonical docs 的自动化。以后如果做 hook / automation，先生成可审阅 draft，再人工确认是否写回 canonical docs。

---

## 12. 完成报告格式

完成有意义任务后，报告：

```text
修改文件
运行命令
产出文件
验证结果
已知限制
未完成事项
下一步建议
```

保持简洁。除非 Eddy 要求，不输出长路线图。
