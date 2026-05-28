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

## 2026-05-28 - 暂不对 MLP / DeepFM 添加 base-rate output bias

决策：GPU 前最后本地动作中，暂不对 MLP / DeepFM 添加 `output_bias_init: train_base_rate`。

原因：

- DCN-v2 已确认存在初始化 bug：默认 embedding 和 cross layer 初始化导致未训练预测概率偏离 train base rate，因此需要修复。
- MLP 没有暴露同类初始化问题；此前 smoke 的初始 loss 和 overfit gate 均正常。
- DeepFM 的已确认问题是 FM 二阶项初始化尺度过大，已通过小方差 FM embedding 初始化修复。
- 给 MLP / DeepFM 增加 base-rate output bias 可能加快收敛，但属于训练策略优化，不是当前 bug fix；GPU 前保持最小变更，避免改变已有 smoke baseline 的解释边界。

状态：已接受为本地收尾阶段决策。后续如果做 full / large-subset 训练配置优化，可以重新评估是否统一加入 base-rate bias。

## 2026-05-28 - 新增 opt-in tensor dataloader，保留 CSV fallback

决策：在 torch 训练数据层新增 `data.loader: tensor` 路径，用于将 materialized encoded CSV 一次性载入 tensor，并在训练期间复用内存 / GPU 显存中的张量；默认仍为 `data.loader: csv`。

边界：

- 不删除旧 CSV dataloader，旧配置未显式设置 `loader` 时继续走 `csv`。
- `tensor` loader 只改变数据读取和 shuffle 实现，不改变模型、loss、optimizer、metric、checkpoint 或 early stopping 语义。
- `tensor` loader 使用原始 `train.csv` 载入张量；训练期如启用 shuffle，则用 `torch.randperm` 生成 epoch 内索引，不再依赖预先物化的 hash-bucket shuffled train CSV。
- 等价性验证时必须用相同 seed 和相同样本顺序隔离 loader 差异；正式训练如果启用 `gpu_randperm`，其样本顺序与旧 hash-bucket shuffle 不同，不能要求逐数值一致。

原因：

- full strict 训练中，旧 CSV dataloader 每 epoch Python 逐行解析 97M 行，4090D GPU 利用率约 2%，明显 IO-bound。
- strict 当前只有 5 个 encoded feature + label，full train 载入为 int32/float32 tensor 后显存可承受。
- 保留 CSV fallback 便于回归对拍、低显存机器和问题定位。

状态：已实现并通过 LR / DeepFM loader 等价对拍。性能上已缓解 CSV 解析瓶颈，但 LR 小模型在 batch size 8192 下仍不能吃满 GPU；进一步提高 GPU 利用率需要另行评估 batch size、训练循环或模型计算量，不能混入 dataloader 语义改动。

补充决策：

- 后续 strict baseline 复跑以 `data.loader: tensor` 作为主路径，原因是 LR / DeepFM 对拍已确认 tensor loader 与 CSV loader 在相同 seed、相同样本顺序下数值完全一致。
- CSV loader 和 hash-bucket shuffled CSV 继续保留为 fallback / regression check。
- 已完成的 4 个 strict FULL baseline 指标来自 `csv` loader；不得在文档中改写成 tensor loader 产出。

## 2026-05-28 - multi-seed 作为 strict baseline 报告标准

决策：后续汇报 strict FULL baseline 时，优先使用 3 seeds × 4 models 的 mean ± std 结果，而不是单 seed run。

原因：

- 单 seed full run 已能证明训练链路跑通，但不足以判断 LR / MLP / DeepFM / DCN-v2 之间约 0.2-1.0pp 的 AUC 差距是否稳定。
- multi-seed 复跑显示 LR -> MLP -> DeepFM / DCN-v2 的 AUC 阶梯整体稳定，std 量级约为 0.0001-0.001。
- DeepFM 与 DCN-v2 的 AUC 差距小于 2 个合成 std，不应写成 DCN-v2 显著领先 DeepFM。
- GAUC 与 AUC 排序不完全一致，MLP 的 test GAUC 高于 DeepFM / DCN-v2；后续必须同时报告 AUC、GAUC 和 LogLoss，不能只挑 AUC 讲模型强弱。

报告标准：

- 表格必须包含 mean ± std、每个 seed 的 run_id、best_epoch 分布、test AUC / GAUC / LogLoss。
- 结论必须写明当前仅使用 5 个 ID/profile 特征，未使用 `hist_*`，未做统计特征和系统超参调优。
- `project_summary.md` 只写高层工程事实，不嵌入具体 AUC 数字。

状态：已接受为 strict Phase A baseline 报告口径。

## 2026-05-28 - hist_1..hist_10 泄漏闸门 PASS，可进入 DIN/DIEN

决策：`hist_1..hist_10` 在当前 strict user-order split 下通过泄漏闸门验证，可作为后续 DIN / DIEN 序列建模输入的前置条件。

验证方法：

- 新增 `scripts/check_hist_leakage.py`，对 `data/Tenrec/ctr_data_1M.csv` 全量 120,342,306 行做流式扫描。
- 按 user block 处理，每个 block 使用 `src/tenrec/data.py` 中唯一 split 函数 `split_counts_for_user()`，不重写 split 逻辑。
- Check 1 检查每个 user 的 train 行 `hist_1..hist_10` 并集是否包含该 user 后续 valid/test target `item_id`。
- Check 2 抽取 1,000,000 个非 padding hist 取值，检查其是否存在于全文件 `item_id` universe。

证据：

- Check 1：valid / test 的 mean、p99、max overlap rate 全部为 0%。
- Check 1：combined valid+test global overlap 为 `0 / 23,187,926` target items。
- Check 2：full-file unique `item_id` 为 2,310,087；hist sample 中 987,324 / 1,000,000 个取值在该 universe 内，覆盖率 98.7324%。
- 相对 full file item universe，约 1.2676% hist sample 取值不在 `item_id` universe 内，后续 DIN 编码时必须走 OOV。

限制：

- 该检查不能证明 Tenrec 原始 `hist_*` 构造严格时间正确；它只能证明在本项目当前 strict user-order split 下，train hist 没有直接包含同 user 后续 valid/test target item。
- Check 2 的 98.7324% 是相对 full file item universe 的 sample coverage，不等价于 train-only vocab coverage；正式 DIN 数据管道仍必须使用 train-only item vocab，train 未见 hist item 也映射 OOV。

状态：已接受为 Phase B history / DIN 前置闸门。DIN/DIEN 实现仍需复用 strict split、train-only vocab 和 OOV/missing 规则。

## 2026-05-28 - DIEN 移出当前路线图

决策：DIEN 暂时移出当前 Phase B 路线图，Phase B history 方向先只推进 DIN。

原因：

- 阶段 1A 复核发现，`ctr_user_block_1m_seed20260525.csv` 中 100% user 的 `hist_1..hist_10` 跨 rows 静态不变。
- 这说明 `hist_*` 在当前 `ctr_data_1M.csv` 中更像 user-level static history snapshot，而不是随 target impression 演化的动态行为序列。
- DIEN 的核心价值依赖 GRU / interest evolution 对历史兴趣随时间演化的建模；如果输入历史本身在同一 user 内不演化，GRU 时序建模没有明确可学信号。
- DIN 的 target-dependent attention 仍然成立：同一静态 history snapshot 面对不同 target item 时，attention 权重可以不同。

边界：

- 该决策不否定 DIEN 模型本身，只是不适合当前 `ctr_data_1M.csv` 的 `hist_*` 语义。
- 如果后续从 raw `QK-video.csv` 自建 per-event rolling history，或找到能反映行为演化的序列输入，可以重新评估 DIEN。
- 此决策覆盖上一节中“DIN/DIEN 实现前置闸门”的宽口径：hist leakage gate 继续解锁 DIN，但不再解锁 DIEN。

阶段 1B full 120M 复核：

```text
rows: 120,342,306
users: 999,447
static hist users: 999,447
dynamic hist users: 0
static hist user rate: 100.0000000000%
```

结论：full `ctr_data_1M.csv` 上 static hist user rate 仍为 100%。DIN 按“static hist snapshot + target-dependent attention”语义推进；DIEN 不进入当前路线图。

状态：已接受为 Phase B 路线图调整。

## 2026-05-29 - DIN full 结果支持“特征空间 > 模型复杂度”

决策：Phase B DIN multi-seed full 结果接受为进入 Phase C 的证据；下一阶段必须优先做 dual-protocol 对照和低泄漏统计特征设计，而不是继续单纯堆叠更复杂模型。

原因：

- strict Phase A 中 DeepFM -> DCN-v2 的 AUC 差距处于 seed 噪声内，说明在 5 个 ID/profile 特征上继续增加交叉网络复杂度收益有限。
- DIN 引入 `hist_item` 后，AUC / GAUC / LogLoss 均稳定优于 4 模型 strict baseline，且 DCN-v2 -> DIN 的差距明显在噪声外。
- 当前提升来自特征空间加入 static history snapshot 和 target-dependent attention，而不是 DIEN 式动态兴趣演化；因此后续叙事必须继续保持 DIN 语义边界。

后续约束：

- Phase C 需要把 strict mainline、同数据契约下的 hist ablation、official-compatible reproduction 分开，不混写结论。
- Phase D 统计特征必须先通过泄漏风险审查，再进入 full run。
- `project_summary.md` 只写高层工程事实，不写具体 AUC / GAUC / LogLoss 数字。

状态：已接受为 Phase C / Phase D 方向约束。

## 2026-05-29 - Phase C official-compatible 使用复用 vocab 的简化协议

决策：Phase C official-compatible preprocessing 复用 `ctr-972e0dcb2b8d` 的 train-only vocab，不重新从 official sampled train split 建表。

原因：

- 本阶段目标是比较 strict protocol 与 official-compatible 1:2 negative sampling + random split 对 AUC / GAUC / PCOC 的影响，而不是重新评估 vocab 构建策略。
- 复用 vocab 可以控制 ID 映射差异，避免 full 预处理额外 pass 和多套 vocab 带来的解释噪声。
- 该做法是工程简化，不等价于论文 exact replication；必须在 experiment log 和 summary 中明确标注 `vocab_source=ctr-972e0dcb2b8d (reuse)`。

约束：

- official-compatible 结果只能写成 reproduction-style 对照，不能写成 exact paper replication。
- LogLoss 跨 strict / official 协议不可直接比较，因为 label base rate 已被 1:2 negative sampling 改变。
- PCOC 是 Phase C 校准对照的核心指标，必须与 AUC / GAUC 一起报告。

状态：已接受为 Phase C official-compatible 预处理边界。

## 2026-05-29 - PCOC 只衡量当前评估分布内校准

决策：当前 PCOC 定义固定为 `mean(pred) / mean(label)`，只解释为当前 evaluation distribution 内的校准比值。

原因：

- 在 strict valid/test 上，PCOC 使用 strict label base rate。
- 在 official-compatible sampled valid/test 上，PCOC 使用采样后的 label base rate；如果模型校准到采样分布，PCOC 仍会接近 1。
- 因此不能仅凭当前 PCOC 定义证明 1:2 negative sampling 相对原始 CTR 分布的概率校准失真。

后续约束：

- Phase C dual-protocol summary 可以报告 strict PCOC 与 official sampled PCOC，但必须注明它们各自相对于对应评估分布。
- 如需证明 official 协议牺牲原始概率校准，需要新增 original-base-rate PCOC、采样率校正后的 PCOC，或单独做 de-biased calibration 分析。

状态：已接受为 Phase C 指标解释边界。
