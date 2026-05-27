# Tenrec 排序项目阶段报告

日期：2026-05-25

本报告总结从项目初始化到第一版本地数据层 smoke 的已验证成果、问题与解决方案、简历可写边界和下一步计划。本文只写已发生事实，不把未来计划写成成果。

## 1. 当前项目定位

项目名称：

```text
Tenrec 多行为推荐排序系统
```

当前阶段：

```text
本地数据层与实验审计框架搭建
```

当前目标不是刷指标，也不是训练复杂模型，而是先把排序项目最容易出错的数据契约、split、vocab、OOV、GAUC 和日志体系做扎实，为后续服务器训练做准备。

## 2. 已完成工作

### 2.1 仓库与文档体系

已完成：

- 创建项目级 `AGENTS.md`，规定中文日志、事实边界、Git/SSH、数据安全和实验记录规则。
- 创建 canonical docs：
  - `docs/decision_log.md`
  - `docs/data_notes.md`
  - `docs/experiment_log.md`
  - `docs/issue_log.md`
  - `docs/project_summary.md`
  - `docs/daily_logs/2026-05-25.md`
- 创建 `docs/dataset_catalog.md`，整理 Tenrec 下载包内各文件用途。
- 创建 `docs/server_runbook.md` DRAFT，记录未来服务器启动顺序和未知项。

作用：

- 后续简历、面试和复盘都能追溯到真实命令、真实数据和真实限制。
- 避免把 smoke result 写成正式实验结果。

### 2.2 环境与 Git

已完成：

- 本地 `.venv` 创建，Python 为 `3.12.7`。
- 安装轻量数据层依赖：

```text
numpy==2.2.6
PyYAML==6.0.2
scikit-learn==1.6.1
```

- GitHub remote 使用 SSH：

```text
git@github.com:EddyHai57/tenrec-ranking.git
```

- `.venv/`、`data/`、`outputs/`、`checkpoints/` 等目录已被 `.gitignore` 排除。

### 2.3 Tenrec 数据探查

已完成对 `ctr_data_1M.csv` 的全量流式 inspection。

关键事实：

- 文件大小约 9.94 GiB。
- 实际有效行数为 120,342,306，不是字面 1M 行。
- unique `user_id`：999,447。
- unique `item_id`：2,310,087。
- `click=0`：91,461,446。
- `click=1`：28,880,860。
- 无显式 timestamp 字段。
- user block 连续排列，`user_id` 单调。
- 完全重复行：883,646。
- 重复 `(user_id,item_id)`：1,810,484。
- 重复 pair 中 click 冲突：560,994。

结论：

- `(user_id,item_id)` 不是唯一样本键。
- 不能机械去重。
- 不能做 timestamp-based split。
- 可以在工程上采用 user 内文件顺序 split。

### 2.4 Smoke samples

已生成两个本地 ignored sample：

| 文件 | 行数 | user 数 | 用途 |
| --- | ---: | ---: | --- |
| `data/samples/ctr_tiny_100k_head.csv` | 100,000 | 773 | reader / feature parsing / metric smoke |
| `data/samples/ctr_user_block_1m_seed20260525.csv` | 1,000,200 | 8,181 | split / GAUC / dataloader / tiny learnability smoke |

限制：

- 两者都不是正式 validation/test。
- 100k head sample 有顺序偏置。
- 1M user-block sample 只是开发样本。

### 2.5 MVP 数据契约

已确定第一版数据契约：

- 任务：点击率预测（CTR / click prediction）。
- label：`click`。
- 输入特征：
  - `user_id`
  - `item_id`
  - `video_category`
  - `gender`
  - `age`
- 暂不使用：
  - `watching_times`
  - `hist_1` 到 `hist_10`
  - `follow`
  - `like`
  - `share`

原因：

- `watching_times` 可能存在 post-exposure / post-click leakage。
- `hist_*` 构造口径未完全验证。
- `follow/like/share` 是多任务标签，不应作为单任务 click baseline 输入。

### 2.6 Split / vocab / preprocessing

已实现：

- `src/tenrec/data.py`
- `scripts/preprocess_ctr_data.py`
- `scripts/smoke_materialized_dataloader.py`

split 公式：

```text
N < 3:
    train = N, valid = 0, test = 0

N >= 3:
    valid = max(1, floor(0.1N))
    test  = max(1, floor(0.1N))
    train = N - valid - test
```

vocab 规则：

```text
只用 train split 建表
0 = OOV
1 = missing
2.. = train seen values
```

预处理架构：

```text
Pass 1: 流式扫描，按 user block split，只从 train 行建 vocab
Pass 2: 再次流式扫描，用冻结 vocab 编码并物化 train/valid/test
```

作用：

- 避免 valid/test 信息泄漏进 vocab。
- 避免全量 pandas load 爆内存。
- 保证本地和服务器可以走同一条 preprocessing path。

### 2.7 Metrics

已实现：

- `binary_auc`
- `binary_log_loss`
- `impression_weighted_gauc`

GAUC 口径：

```text
GAUC = sum(user_auc * user_impressions) / sum(user_impressions)
```

only-positive / only-negative user 跳过。每次 GAUC 输出必须同时报告：

- valid user count；
- total user count；
- valid row count；
- total row count；
- row coverage rate。

### 2.8 单元测试与 smoke

已新增测试：

- `tests/test_data_contract.py`
- `tests/test_metrics.py`

覆盖：

- split 整数公式；
- missing 优先于 OOV；
- train-only vocab；
- valid/test `user_id` OOV 断言；
- AUC known-answer；
- LogLoss known-answer；
- GAUC 单类用户跳过和 coverage。

已运行：

```powershell
.\.venv\Scripts\python.exe -m py_compile ...
.\.venv\Scripts\python.exe -m unittest tests.test_data_contract tests.test_metrics
```

结果：

```text
Ran 7 tests
OK
```

### 2.9 物化预处理结果

100k sample：

```text
run_id: ctr-78004c39c1dd
train/valid/test rows: 80672 / 9664 / 9664
```

1M user-block sample：

```text
run_id: ctr-454e7ccb12f7
train/valid/test rows: 807282 / 96459 / 96459
```

重构后的共享 split 函数已复现旧 oracle：

```text
807282 / 96459 / 96459
```

1M sample 物化后：

- valid `item_id` OOV rows：17,367。
- test `item_id` OOV rows：17,577。
- valid/test `user_id` OOV：0。
- `video_category` missing rows：train 10,134，valid 1,278，test 1,550。

### 2.10 sklearn LR learnability smoke

LR smoke 直接消费 `outputs/preprocessed/` 中的物化编码数据，没有绕过 preprocessing pipeline。

1M user-block sample：

```text
train rows: 100000
valid rows: 50000
train AUC: 0.8866438867118259
valid AUC: 0.6283948058203263
train LogLoss: 0.4080319738212789
valid LogLoss: 0.5718098163083559
valid GAUC: 0.6032205118880077
valid GAUC coverage: 0.89796
```

解释：

- 这证明数据管道有可学习信号。
- 这不是正式 baseline，也不能写成模型最终结果。

## 3. 遇到的问题与解决

### 问题 1：`ctr_data_1M.csv` 实际不是 1M 行

现象：

- 文件实际为 120,342,306 行。

解决：

- 所有全量探查和 preprocessing 采用流式读取。
- 本地只生成 100k 和 1M smoke sample。

### 问题 2：无显式 timestamp

现象：

- `ctr_data_1M.csv` 无 timestamp 字段。

解决：

- 不伪造 timestamp split。
- 当前采用 user 内文件顺序 split，并明确记录限制。

### 问题 3：重复与 click 冲突

现象：

- 存在完全重复行、重复 `(user_id,item_id)` 和 click 冲突。

解决：

- MVP 不去重。
- 将一行样本定义为 exposure-like row。
- 在文档中保留记忆风险和限制。

### 问题 4：valid/test OOV 泄漏风险

现象：

- 如果全文件建 vocab，会把 valid/test 未见值提前泄漏进训练特征空间。

解决：

- train-only vocab。
- valid/test 未见值映射到 OOV。
- 两遍预处理。

### 问题 5：GAUC 单类用户

现象：

- valid/test 中有 only-positive 或 only-negative user，AUC 对单类 label 无定义。

解决：

- GAUC 跳过单类用户。
- 每次报告 coverage。
- 加 known-answer 单元测试。

### 问题 6：`hist_*` 泄漏无法完全排除

现象：

- target item 没有出现在同一行 history 中，但 sampled history item 也没有出现在该文件此前同 user 行里。

解决：

- MVP baseline 暂不使用 `hist_*`。
- 后续如果做 DIN/BST，必须重新验证 history 构造口径或从 raw sequence 构造历史。

## 4. 简历可写边界

现在可以写的方向性描述：

```text
基于 Tenrec 构建推荐排序实验工程，完成 1.2 亿行 CTR 数据的流式 schema inspection，识别无 timestamp、重复曝光、click 冲突和 OOV item 等数据契约风险；设计并实现 train-only vocab、OOV/missing 编码、user-order split、impression-weighted GAUC 与两遍流式预处理 pipeline，并通过 100k/1M smoke sample 验证数据链路可学习。
```

目前不能写：

- 不能写 DeepFM / DCN-v2 已完成。
- 不能写 DIN / BST 已完成。
- 不能写 MMOE / PLE 已完成。
- 不能写线上 A/B。
- 不能写正式 AUC 提升。
- 不能把 sklearn LR smoke 指标写成正式模型指标。

更稳妥的简历 bullet 需要等至少 LR / MLP / DeepFM / DCN-v2 baseline 在服务器或 large subset 上完成后再定。

## 5. 当前代码入口

数据预处理：

```powershell
.\.venv\Scripts\python.exe scripts\preprocess_ctr_data.py --config configs\ctr_user_block_1m.yaml
```

dataloader smoke：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_materialized_dataloader.py --metadata outputs\preprocessed\ctr-454e7ccb12f7\metadata.json --batch-size 32
```

LR learnability smoke：

```powershell
.\.venv\Scripts\python.exe scripts\run_sklearn_lr_smoke.py --metadata outputs\preprocessed\ctr-454e7ccb12f7\metadata.json --max-train-rows 100000 --max-valid-rows 50000 --output outputs\inspection\sklearn_lr_smoke_ctr_user_block_1m.json
```

测试：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_data_contract tests.test_metrics
```

## 6. 下一步

租服务器前建议继续完成：

1. 创建 full data config 草案 `configs/ctr_full.yaml`，但先不运行。
2. 实现 torch LR / MLP tiny baseline，仍先在 100k / 1M sample 上跑。
3. 明确服务器 Python、CUDA、Torch wheel 版本。
4. 租服务器后先跑 unit test 和 smoke preprocessing，再跑 full preprocessing。
5. full preprocessing 完成后，再进入正式 baseline 训练。

## 7. 2026-05-27 本地训练前收尾补充

已完成：

- 安装本地 CPU torch：`torch==2.12.0+cpu`。
- 新增 torch LR / MLP 训练入口。
- LR 明确为 scalar lookup sum，不使用 dense embedding。
- 训练前生成 deterministic hash-bucket shuffled train CSV，避免按 user 聚簇顺序训练。
- `metadata_path` 支持 CLI 覆盖，服务器 full preprocessing 后可传入新的 metadata。
- CTR baseline 不使用 class reweighting / resampling。
- LR / MLP overfit gate 均通过。
- LR / MLP train smoke 均完成 checkpoint 和 metrics 落盘。

关键 smoke 结果：

| model | overfit final loss | best valid LogLoss | valid AUC | valid GAUC | GAUC coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| torch LR | 0.02680760808289051 | 0.5508678869033629 | 0.677162416436456 | 0.599984004757329 | 0.89796 |
| torch MLP | 0.00024013200891204178 | 0.5926276149280864 | 0.5641194888327414 | 0.5185113647677471 | 0.89796 |

注意：

- 上述数字仍是 smoke，不是正式 baseline。
- 数据来自 1M user-block sample 的 head-truncated train/valid。
- MLP 未调参，不能据此得出模型强弱结论。
