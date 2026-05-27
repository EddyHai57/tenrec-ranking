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

## 2026-05-25 - MVP 数据层采用两遍流式预处理

决策：第一版数据层不围绕 pandas 全量 DataFrame 设计，采用两遍流式预处理。

流程：

```text
Pass 1: 按 user block 流式扫描，使用唯一 split 函数，只从 train 行构建 vocab
Pass 2: 再次按 user block 流式扫描，使用冻结 vocab 编码并物化 train/valid/test
```

原因：

- `ctr_data_1M.csv` 本地实测有 120,342,306 行，约 9.94 GiB。
- valid/test 的 OOV 判定必须基于完整 train vocab；边扫边编码会导致早期 valid/test 被错误判为 OOV。
- 两遍扫描能保证本地 smoke 和服务器 full preprocessing 使用同一口径。

状态：已实现于 `src/tenrec/data.py`，并在 100k 和 1M smoke sample 上验证。

## 2026-05-25 - Vocab 采用 train-only 和统一 reserved index

决策：所有 categorical feature 的 vocab 只使用 train split 构建，并统一 reserved index。

```text
0 = OOV
1 = missing
2.. = train seen values
```

适用字段：

```text
user_id
item_id
video_category
gender
age
```

原因：

- `valid/test` 未见值不能进入 vocab，否则会造成信息泄漏。
- `item_id` 在 1M sample 中 valid/test 有大量 unseen item，必须显式 OOV。
- `video_category` 的 `\N` 是 missing 语义，不应与 unseen OOV 混淆。
- 统一 reserved index 能减少跨字段 hardcode 造成的实现错误。

状态：已实现并通过单元测试。

## 2026-05-25 - GAUC 采用 impression-weighted 并强制报告 coverage

决策：MVP 主 GAUC 口径采用 impression-weighted GAUC。

```text
GAUC = sum(user_auc * user_impressions) / sum(user_impressions)
```

only-positive / only-negative user 跳过。任何 GAUC 输出必须同时报告：

- valid GAUC user count
- total user count
- valid GAUC row count
- total row count
- row coverage rate

原因：

- Tenrec split 后存在大量单类用户，直接对每个 user 调 AUC 会报错。
- 跳过单类用户后，GAUC 覆盖率不足 100%；不报告 coverage 会误导结果解释。

状态：已实现于 `src/tenrec/metrics.py`，并通过 known-answer 单元测试。

## 2026-05-27 - torch LR 必须是标量查表线性模型

决策：torch LR baseline 使用每个 categorical field 的 `[vocab_size, 1]` scalar lookup，所有 field lookup 结果求和后加全局 bias。

原因：

- LR 是 ID 特征上的线性模型，不应使用 `embedding_dim=16` 这类 dense embedding。
- 如果 LR 使用多维 embedding 再接网络层，模型语义会变成浅层神经网络，面试和实验对比都不清楚。

状态：已实现于 `src/tenrec/models.py` 的 `FieldWiseLogisticRegression`，并由 `tests/test_torch_models.py` 验证 embedding dim 为 1。

## 2026-05-27 - CTR baseline 不做 class reweighting 或重采样

决策：LR / MLP smoke 使用普通 `BCEWithLogitsLoss`，不使用 `pos_weight`、class reweighting 或正负样本重采样。

原因：

- CTR 的 LogLoss 需要概率校准。
- 类别重加权或重采样会改变训练目标，使 LogLoss 难以解释。
- 当前 click positive rate 约 24%，不需要为了 smoke 阶段强行 reweight。

状态：已实现于 `src/tenrec/training.py`，run summary 记录 `class_reweighting=false` 和 `resampling=false`。

## 2026-05-27 - 训练前使用物化 shuffle 文件，不依赖小 shuffle buffer

决策：torch train smoke 不使用小 `shuffle_buffer_size` 在 user-ordered CSV 上做局部混洗。训练前生成 deterministic hash-bucket shuffled train CSV。

原因：

- 物化 train 文件按 user 排列，同一 user 样本会聚簇。
- 小 buffer 只能打散局部窗口，full run 可能导致 batch 梯度高度相关。
- hash-bucket shuffle 会把全文件样本按 deterministic hash 分散到 bucket，再对 bucket 和 bucket 内 rows 打乱，避免按 user 连续喂给 SGD。

状态：已实现于 `src/tenrec/torch_data.py`，本地生成：

```text
outputs/preprocessed/ctr-454e7ccb12f7/materialized/train_shuffled_seed20260525_b16.csv
```

## 2026-05-27 - metadata path 必须支持 CLI 覆盖

决策：`scripts/train.py` 支持 `--metadata` 覆盖 config 中的 `data.metadata_path`。

原因：

- `metadata_path` 指向 `outputs/preprocessed/{run_id}/metadata.json`，而 `run_id` 由输入文件、config 和版本生成。
- 服务器 full preprocessing 会产生不同 run_id，不能写死本地 smoke run。
- 服务器流程必须是先 preprocessing，读取新 metadata path，再传给 train。

状态：已实现于 `scripts/train.py`。

## 2026-05-27 - 保留 strict protocol 为主线，官方 CTR 协议作为对照

决策：本项目主线继续使用 strict auditable protocol，不改成官方 CTR benchmark 的默认协议。后续可增加 official-compatible reproduction protocol 作为对照实验。

strict protocol：

```text
不做负采样
user 内文件顺序 split
train-only vocab
valid/test unseen 映射 OOV
AUC / GAUC / LogLoss
GAUC 必须报告 coverage
```

official-compatible reproduction protocol：

```text
按官方 1:2 negative sampling
复现官方随机切分和全量 LabelEncoder 口径
标注为 official-compatible，不与 strict protocol 指标直接比较
```

原因：

- 论文 CTR 任务使用 `QK-video-1M`，保留全部正样本并按 positive:negative = 1:2 采样负样本。
- 官方 `utils.py` 的 `ctrdataset()` 对全量 df 做 `LabelEncoder().fit_transform()`，再使用 `train_test_split(df, test_size=0.1)`。
- 官方协议适合 benchmark 复现，但会改变 click base rate，并且全量编码不符合本项目 train-only vocab 的泄漏控制原则。
- 本项目目标是可审计实验工程，不是单纯复刻官方表格分数。

边界：

- 不因为官方代码使用随机 split，就改掉本项目主协议。
- 不因为官方代码使用全量 encoder，就放弃 train-only vocab。
- 不因为官方代码使用 `hist_1..hist_10`，就立即把 history 加进 MVP baseline。
- 官方 AUC / LogLoss 不能直接与本项目 strict protocol 指标比较。

状态：已接受为方向性决策。是否实现 official-compatible protocol，等待 Eddy 和 Opus 讨论后决定。

## 2026-05-27 - 多任务学习作为 Phase C 拔高方向

决策：将多任务学习（MTL / Multi-task Learning）记录为后期拔高方向，但不进入当前 MVP 阻塞项。

定位：

```text
Phase A: 单任务 CTR 主线稳定
Phase B: 特征交互 + history / user interest 完成
Phase C: 多任务学习拔高
```

前置条件：

- 单任务 click prediction pipeline 在 strict protocol 下稳定。
- LR / MLP / DeepFM / DCN-v2 至少完成可复现实验。
- Phase B 的特征和 `hist_*` 使用口径完成审计。
- 多任务 label 分布、loss 权重和 per-task metric 方差完成验证。

MTL 架构边界：

- 使用共享底座（shared backbone / shared experts）+ 多任务 head。
- 不是多个任务各自一个完整模型并联，也不是双塔（Two-Tower）召回结构。
- 多任务 head 只预测 Tenrec 当前存在的行为标签。

Tenrec 当前任务边界：

```text
click
like
share
follow
```

Tenrec 当前没有购买行为，不写 purchase / conversion / CVR 作为已存在任务。

基于 `ctr_data_1M.csv` 全量流式 inspection 的正例分布：

| task | positive rows | total rows | positive rate |
| --- | ---: | ---: | ---: |
| click | 28,880,860 | 120,342,306 | ~24.0% |
| like | 2,275,417 | 120,342,306 | ~1.9% |
| share | 250,089 | 120,342,306 | ~0.2% |
| follow | 179,788 | 120,342,306 | ~0.15% |

风险：

- `share` 和 `follow` 极稀疏。
- per-task AUC / GAUC / LogLoss 可能高方差，尤其在小样本和 user-level split 下。
- 需要报告每个任务的有效样本数、正例数、GAUC coverage 和置信解释，不能只报平均指标。

候选推进顺序：

### C1 Shared-Bottom

共享一套底层 embedding / MLP 表征，每个任务接独立 head。

解决的问题：

- 建立最小 MTL baseline。
- 验证 click / like / share / follow 是否能共享表示。
- 作为 MMOE / PLE 的对照。

主要风险：

- 所有任务强制共享底座，容易发生任务冲突（task conflict）和负迁移（negative transfer）。

### C2 MMOE

使用多个 experts 和 task-specific gates，为不同任务动态组合 expert 输出。

解决的问题：

- 缓解 Shared-Bottom 中不同任务梯度方向冲突的问题。
- 允许 click、like、share、follow 对共享专家有不同依赖。

主要风险：

- 极稀疏任务的 gate 学习不稳定。
- 需要观察每个任务的 loss 曲线和 gate 行为，避免只优化 click。

### C3 PLE

使用 shared experts 和 task-specific experts，并分层建模。

解决的问题：

- 缓解 MMOE 中任务间干扰仍然较强的问题。
- 针对多任务学习中的跷跷板现象（seesaw phenomenon）：一个任务提升时另一个任务下降。
- 更适合 Tenrec 这种 click 高频、share/follow 极低频的多行为任务结构。

主要风险：

- 架构复杂度和调参成本明显高于 Shared-Bottom / MMOE。
- 必须先有稳定单任务和 MMOE 对照，否则无法解释收益来源。

### C4 ESMM

ESMM 原始目标是处理 CTR/CVR 场景中的样本选择偏差（sample selection bias）和稀疏反馈问题。

Tenrec 边界：

- Tenrec 当前没有 purchase / conversion label。
- 不把 ESMM 写成购买转化模型。
- 若后续使用，只能作为 click -> like / share / follow 这种曝光到互动链路的条件行为建模候选。

解决的问题：

- 尝试建模“曝光后点击”和“点击后进一步互动”的链式关系。
- 在 like/share/follow 极稀疏时，探索是否能缓解稀疏标签和样本选择偏差。

主要风险：

- Tenrec 行为链路是否满足 ESMM 假设需要单独验证。
- 如果行为之间不是严格 funnel，ESMM 可能不适合，应降级为 MMOE / PLE。

状态：已确认作为 Phase C 计划方向，尚未实现，不能写成项目成果或简历已完成内容。
