# 问题日志

本文件记录环境、数据、代码和实验问题。

## ISSUE-20260524-001 - `GIT_SSH_COMMAND` 反斜杠路径被 `ssh` 误解析

### 日期

2026-05-24

### 类型

environment / git

### 现象

首个 push 使用：

```powershell
$env:GIT_SSH_COMMAND='ssh -i C:\Users\Eddy\.ssh\github_key -o IdentitiesOnly=yes'
git push -u origin main
```

push 成功，但输出警告：

```text
Warning: Identity file C:UsersEddy.sshgithub_key not accessible: No such file or directory.
```

### 证据

GitHub 接受了 push，并创建了 `origin/main`；但警告说明显式 `-i` 路径没有被正确解析，实际成功依赖了 `C:\Users\Eddy\.ssh\config` 中的 `github.com` 配置。

### 根因或当前假设

`GIT_SSH_COMMAND` 传给 `ssh` 后，Windows backslash 被当作转义字符处理，导致 `C:\Users\Eddy\.ssh\github_key` 变成不可访问的 `C:UsersEddy.sshgithub_key`。

### 修复或 workaround

在 `GIT_SSH_COMMAND` 中使用 forward slash 路径：

```powershell
$env:GIT_SSH_COMMAND='ssh -i C:/Users/Eddy/.ssh/github_key -o IdentitiesOnly=yes'
```

### 验证

```powershell
ssh -i C:/Users/Eddy/.ssh/github_key -o IdentitiesOnly=yes -T git@github.com
```

输出：

```text
Hi EddyHai57! You've successfully authenticated, but GitHub does not provide shell access.
```

### 状态

Closed

## ISSUE-20260525-001 - 单遍预处理会导致 OOV 判定漂移

### 日期

2026-05-25

### 类型

data / code

### 现象

如果在扫描原始 CSV 时边 split、边建 vocab、边编码 valid/test，那么早期 user 的 valid/test 行无法知道后续 user 的 train 行中是否出现过同一 `item_id` 或类别值。

### 证据

Opus review 指出该漏洞；本地数据层设计中，valid/test OOV 必须基于完整 train vocab。`ctr_user_block_1m_seed20260525.csv` 的 valid/test 存在大量 unseen item，该问题会高频触发。

### 根因或当前假设

vocab 冻结必须发生在所有 train 行扫描完成之后。单遍编码会把“尚未看到”误当成“train 未见”。

### 修复或 workaround

采用两遍流式预处理：

```text
Pass 1: 只从 train 行构建 vocab
Pass 2: 用冻结 vocab 编码并物化 split
```

### 验证

已运行：

```powershell
.\.venv\Scripts\python.exe scripts\preprocess_ctr_data.py --config configs\ctr_user_block_1m.yaml
```

输出：

```text
run_id: ctr-454e7ccb12f7
split rows: 807282 / 96459 / 96459
valid/test user_id OOV: 0
valid item_id OOV rows: 17367
test item_id OOV rows: 17577
```

### 状态

Closed

## ISSUE-20260525-002 - GAUC 单类用户会导致 AUC 计算异常或误读

### 日期

2026-05-25

### 类型

evaluation

### 现象

GAUC 需要按 user 计算 AUC，但 valid/test 中存在 only-positive 或 only-negative user。直接对这些用户调用 AUC 会报错，跳过后如果不报告 coverage，又会误导指标解释。

### 证据

1M split feasibility：

```text
valid valid GAUC users: 5677 / 8170
valid row coverage: 0.87316891
test valid GAUC users: 5021 / 8170
test row coverage: 0.82024487
```

### 根因或当前假设

AUC 在单类 `y_true` 上没有定义。GAUC 必须跳过单类用户，并明确有效覆盖率。

### 修复或 workaround

`src/tenrec/metrics.py` 的 `impression_weighted_gauc` 跳过 only-positive / only-negative user，并返回：

- `valid_user_count`
- `only_positive_user_count`
- `only_negative_user_count`
- `valid_row_count`
- `total_row_count`
- `row_coverage_rate`

### 验证

`tests/test_metrics.py` 覆盖包含 only-positive 和 only-negative user 的手写 case。

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_data_contract tests.test_metrics
```

输出：

```text
Ran 7 tests
OK
```

### 状态

Closed

## ISSUE-20260527-001 - Windows ctypes RSS 监控结果不可信

### 日期

2026-05-27

### 类型

evaluation / tooling

### 现象

第一次对 10M preprocessing 运行 `scripts/run_with_resource_monitor.py` 时，输出 peak RSS 只有 4.574 MiB。

该数值明显低于 Python 解释器、vocab dict 和 CSV preprocessing 的合理内存使用，不能作为 G1 证据。

### 证据

初次输出：

```text
peak_rss_mib: 4.574
monitor_backend: windows_ctypes
```

随后用 `psutil` 重跑同一命令：

```text
peak_rss_mib: 136.68
monitor_backend: psutil
```

### 根因或当前假设

Windows 下直接用 ctypes 查询子进程 working set 时，可能只抓到了错误进程 / launcher / 不完整工作集，导致 RSS 严重低估。

### 修复或 workaround

- 安装 `psutil==7.2.2`。
- `scripts/run_with_resource_monitor.py` 优先使用 psutil。
- psutil 统计主进程和递归子进程 RSS。

### 验证

用 psutil backend 重跑 10M preprocessing：

```powershell
.\.venv\Scripts\python.exe scripts\run_with_resource_monitor.py --output outputs\inspection\preprocess_10m_resource_monitor_psutil.json --interval 0.5 -- .\.venv\Scripts\python.exe scripts\preprocess_ctr_data.py --config configs\ctr_user_block_10m.yaml
```

结果：

```text
exit_code: 0
peak_rss_mib: 136.68
monitor_backend: psutil
```

### 状态

Closed

## ISSUE-20260528-001 - DeepFM 默认 embedding 初始化导致 FM 二阶 logit 过宽

### 日期

2026-05-28

### 类型

training / code

### 现象

第一次 DeepFM train smoke 虽然可以运行，但 valid LogLoss 明显异常：

```text
run_id: 20260528-010535-deepfm_smoke-deepfm
best valid LogLoss: 1.4114884493428632
```

进一步诊断同一 batch 上的初始化 logits：

```text
deepfm mean -1.7845935821533203
deepfm std 9.780134201049805
deepfm min -32.292457580566406
deepfm max 51.47307205200195
```

对照：

```text
mlp std 0.04044552147388458
dcnv2 std 0.9319897890090942
```

### 根因或当前假设

DeepFM 的 FM 二阶项使用 sum-square trick。PyTorch `nn.Embedding` 默认接近 `N(0,1)` 初始化，多个 field embedding 做二阶交叉后会把初始 logit 撑得过宽，导致 sigmoid 饱和和 LogLoss 异常。

### 修复或 workaround

- DeepFM 一阶 scalar embedding 初始化为 0。
- DeepFM FM embedding 使用小方差 normal 初始化：

```text
mean: 0.0
std: 0.01
```

- 增加单元测试，约束 DeepFM 初始 logits 不被 FM 二阶项撑爆。

### 验证

模型单测通过：

```text
Ran 5 tests
OK
```

DeepFM overfit 通过：

```text
initial_loss: 0.6765590310096741
final_loss: 1.746938149693733e-09
target_loss: 0.05
passed: true
```

修正后 DeepFM train smoke：

```text
run_id: 20260528-010753-deepfm_smoke-deepfm
best valid LogLoss: 0.5821876039626651
best valid AUC: 0.6712964224072929
best valid GAUC: 0.5984632023912543
GAUC coverage: 0.89796
```

### 状态

Closed

## ISSUE-20260528-002 - DCN-v2 默认初始化导致初始概率偏离 train base rate

### 日期

2026-05-28

### 类型

training / code

### 现象

DCN-v2 overfit gate 可以通过，但初始 smoke 表现接近随机：

```text
run_id: 20260528-010814-dcnv2_smoke-dcnv2
best valid AUC: 0.5340191846947128
best valid GAUC: 0.509562857013943
best valid LogLoss: 0.5963719971695486
```

复跑 `20260528-012130-dcnv2_smoke-dcnv2` 后确认：

```text
epoch 1 train AUC: 0.5596665820712516
epoch 1 valid AUC: 0.5241001837053098
epoch 4 train AUC: 0.6502114529137548
epoch 4 valid AUC: 0.549233990622756
```

### 证据

未训练模型在 50k train rows 上：

```text
batch base rate: 0.266400009393692
constant batch base LogLoss: 0.5796452164649963
init LogLoss: 0.7147810888671875
mean predicted probability: 0.40860605239868164
logit std: 1.0905441045761108
embedding std mean: 0.9925519704818726
cross weight std: ~0.111
output bias: 0.05396714061498642
```

### 根因或当前假设

DCN-v2 直接使用 PyTorch 默认 `nn.Embedding` 初始化，embedding 近似 `N(0,1)`。这些 embedding 拼接后进入矩阵式 cross layer，乘法交叉会放大初始 logit 方差。

同时 output bias 没有对齐 train base rate，导致平均预测概率明显高于训练集正例率。

注意：`scripts/train.py --overfit` 输出里的 `initial_loss` 是第 1 个 overfit epoch 之后的 loss，不是未训练 loss；未训练 loss 需要单独诊断。

### 修复或 workaround

- DCN-v2 embedding 初始化为小方差 normal：

```text
mean: 0.0
std: 0.01
```

- DCN-v2 cross layer weight 初始化为小方差 normal：

```text
mean: 0.0
std: 0.01
```

- deep / output linear bias 初始化为 0。
- `configs/dcnv2_smoke.yaml` 使用：

```yaml
output_bias_init: train_base_rate
```

- `src/tenrec/training.py` 从 `metadata["pass2"]["label_counts"]["train"]` 计算 train base logit，避免在 config 中 hardcode 当前 sample 的 base rate。

### 验证

修复后未训练模型：

```text
metadata train base logit: -1.1410586334170694
init LogLoss: 0.5812454168701172
mean predicted probability: 0.24155035614967346
logit std: 0.008613877929747105
embedding std mean: 0.009735829196870327
cross weight std: ~0.010
output bias: -1.1410586833953857
```

修复后 overfit：

```text
final_loss: 5.579277009237912e-20
target_loss: 0.05
passed: true
```

修复后 train smoke：

```text
run_id: 20260528-012603-dcnv2_smoke-dcnv2
best_epoch: 1
best valid AUC: 0.6689654983604069
best valid GAUC: 0.5930922436479876
best valid LogLoss: 0.5616743797625655
GAUC coverage: 0.89796
```

### 状态

Closed

未来 issue 必须记录：

- 日期
- 类型：environment、data、code、training、evaluation、documentation
- 现象
- 证据
- 根因或当前假设
- 修复或 workaround
- 验证
- 状态：open、mitigated、closed

## 2026-05-28 - Full training CSV dataloader IO-bound

### 类型

training / performance

### 现象

4090D 上 strict FULL 训练时，旧 dataloader 每 epoch 通过 Python `csv.DictReader` 逐行解析 materialized CSV：

- full train rows：97,146,674
- LR full epoch 1 wall-clock：约 505.385s
- GPU 显存占用：约 495 MiB
- GPU 利用率：约 2%

训练明显不是 GPU compute-bound。

### 证据

旧 CSV full run：

```text
run_id: 20260528-031610-torch_lr_full-lr
epoch 1 elapsed: 505.3850977420807s
epoch 1 valid AUC: 0.7647105088321045
epoch 1 valid GAUC: 0.7119054550320486
epoch 1 valid LogLoss: 0.49633235134902587
```

新增 tensor loader 后 LR FULL 1 epoch performance demo：

```text
run_id: 20260528-131845-perf_lr_tensor_full_1epoch-lr
preload elapsed: 27.27977681159973s
epoch 1 elapsed: 103.33020281791687s
epoch 1 valid AUC: 0.7645604166577312
epoch 1 valid GAUC: 0.7119516961953584
epoch 1 valid LogLoss: 0.49619740976391186
peak GPU util: 16%
average GPU util: 5.425373134328358%
peak memory: 7405 MiB
```

### 根因或当前假设

旧路径每 epoch 重复解析 CSV，CPU 端构造 Python dict/list，再转 tensor，导致 GPU 长时间等待。

tensor loader 消除重复 CSV 解析后，LR epoch 明显缩短，但 GPU 仍未吃满。剩余瓶颈不是 CSV parser 本身，而是：

- LR 模型和 strict 5-feature 输入计算量极小；
- batch size 8192 下 full train 仍有约 1.18 万个 optimizer step，Python training loop / optimizer step overhead 明显；
- 每 epoch full valid metric 仍需生成并搬回 11.6M rows 的 labels/scores/groups 计算 AUC/GAUC。

### 修复或 workaround

- 新增 `data.loader: tensor` opt-in 路径。
- materialized CSV 首次载入为 `int32` feature matrix + `float32` labels。
- train / valid / test 可常驻目标 device。
- tensor train shuffle 使用 `torch.randperm(..., device=device)`，取代 b64 hash-bucket shuffled CSV 文件。
- 默认仍为 `loader: csv`，保留 fallback。

### 验证

同 seed、同顺序、同 row cap 下做 CSV vs tensor loader 对拍：

LR：

```text
epoch 1 train loss: 0.6318812780380249 / 0.6318812780380249
epoch 1 valid AUC: 0.5909480469165779 / 0.5909480469165779
epoch 1 valid GAUC: 0.5824200924216459 / 0.5824200924216459
epoch 1 valid LogLoss: 0.5948254304188908 / 0.5948254304188908
epoch 2 train loss: 0.5744604323196412 / 0.5744604323196412
epoch 2 valid AUC: 0.6116213666252145 / 0.6116213666252145
epoch 2 valid GAUC: 0.5946678858627868 / 0.5946678858627868
epoch 2 valid LogLoss: 0.588292578654626 / 0.588292578654626
```

DeepFM：

```text
epoch 1 train loss: 0.6751879526138306 / 0.6751879526138306
epoch 1 valid AUC: 0.5502702944492442 / 0.5502702944492442
epoch 1 valid GAUC: 0.5636236642183162 / 0.5636236642183162
epoch 1 valid LogLoss: 0.6496039477501342 / 0.6496039477501342
epoch 2 train loss: 0.6250755997657775 / 0.6250755997657775
epoch 2 valid AUC: 0.5473344027790169 / 0.5473344027790169
epoch 2 valid GAUC: 0.5734421885685355 / 0.5734421885685355
epoch 2 valid LogLoss: 0.6027031991052973 / 0.6027031991052973
```

### 状态

Mitigated。

CSV 解析瓶颈已被 tensor loader 明显缓解，但“GPU 利用率显著吃满”尚未完成。若继续优化，必须单独设计并审计 batch size、训练循环、metric 计算或模型计算量，不能把这些改变混入 dataloader 等价优化。

## 2026-05-28 - 1M hist preprocessing 中 valid/test hist OOV 和 padding 率完全相同

### 类型

data / preprocessing diagnostic

### 现象

阶段 1A 的 `ctr_user_block_1m_seed20260525.csv` hist preprocessing smoke 中，valid 和 test 的 `hist_1..hist_10` OOV 率、padding 率逐位置完全相同。

例如 train-only `item_id` vocab 口径下的 hist OOV rate：

```text
valid: 12.188598%,12.354472%,11.629812%,13.341420%,12.678962%,13.026260%,13.219088%,12.976498%,13.565349%,12.842762%
test : 12.188598%,12.354472%,11.629812%,13.341420%,12.678962%,13.026260%,13.219088%,12.976498%,13.565349%,12.842762%
```

padding rate 也逐位置完全相同。

同时 valid/test 物化文件大小不同：

```text
valid.csv: 6,768,643 bytes
test.csv : 6,771,033 bytes
```

因此需要确认这是统计 bug，还是数据本身导致的现象。

### 证据

检查 `src/tenrec/data.py::encode_and_materialize()` 后确认：

- valid/test 使用同一个 `assignments = split_names_for_user(len(rows))` 按行分配；
- 每个 split 有独立的 `sequence_oov_counts[split]` 和 `sequence_padding_counts[split]`；
- 写 CSV 和统计计数在同一逐行循环中完成；
- 未发现 test 误读 valid counter 或共享 counter 的路径。

独立事后验证直接读取：

```text
outputs/preprocessed/ctr-610578df3be5/materialized/valid.csv
outputs/preprocessed/ctr-610578df3be5/materialized/test.csv
```

重新统计 `hist_1_idx..hist_10_idx` 中：

- OOV：`value == 0`
- padding：`value == 1`

得到的 valid/test 计数仍完全相同：

```text
valid rows: 96,459
test rows : 96,459

OOV counts:
valid: [11757, 11917, 11218, 12869, 12230, 12565, 12751, 12517, 13085, 12388]
test : [11757, 11917, 11218, 12869, 12230, 12565, 12751, 12517, 13085, 12388]

padding counts:
valid: [13, 25, 80, 130, 226, 438, 767, 1087, 1504, 1909]
test : [13, 25, 80, 130, 226, 438, 767, 1087, 1504, 1909]
```

进一步按 `user_id_idx` 对 valid/test 做定量检查：

```text
valid users: 8,170
test users : 8,170
valid/test user row-count maps equal: True
users with same valid/test hist sequence multiset: 8,170 / 8,170
users with static valid hist sequence: 8,170 / 8,170
users with static test hist sequence : 8,170 / 8,170
```

直接扫描 raw 1M sample：

```text
raw rows: 1,000,200
users: 8,181
users with one distinct hist_1..hist_10 sequence across all rows: 8,181 / 8,181
static hist user rate: 100.000000%
```

### 根因或当前假设

这不是统计代码 bug，而是当前 Tenrec `ctr_data_1M.csv` / 1M user-block sample 的数据特性：

- 同一 user 的 `hist_1..hist_10` 在所有 rows 中保持静态不变；
- strict split 中每个 `N >= 3` user 的 valid 行数和 test 行数由同一公式产生，且二者相等；
- 因此 valid 和 test 覆盖的是同一批 user，且每个 user 在 valid/test 中贡献相同次数的同一条 hist sequence；
- 所以 hist OOV/padding 统计在 valid/test 间精确相同。

valid/test 物化文件大小不同，是因为 target `item_id_idx`、label 和其他列值不同；hist 统计相同不代表 valid/test 文件内容相同。

### 修复或 workaround

不需要修复。

后续解读 hist 统计时必须明确：

- valid/test hist OOV/padding 完全相同是由静态 per-user hist + valid/test 同用户同计数导致的；
- 这不影响 train-only item vocab、hist OOV/padding 编码或 dataloader batch shape 的正确性；
- 但它说明 `hist_*` 更像论文预处理好的 user-level recent-click feature，而不是每条 target row 动态变化的 event-level rolling history。

### 验证

独立 CSV 重算与 metadata 中的 `sequence_oov_counts` / `sequence_padding_counts` 完全一致。

### 状态

Closed。非 bug，但 Phase B / DIN 解释时必须保留该数据语义边界。

## 2026-05-29 - Phase C 本地 smoke 被 Codex Windows sandbox 外部进程问题阻断

### 现象

Phase C 已完成 PCOC 和 official-compatible preprocessing 的初版实现后，继续执行本地 smoke 时，Codex shell 对外部进程开始失败：

```text
windows sandbox: runner error: CreateProcessAsUserW failed: 1312
```

已受影响命令包括：

```text
.\.venv\Scripts\python.exe scripts\preprocess_ctr_data_official.py ...
git status --short
where.exe python
```

尝试提权执行 preprocessing smoke 时，Codex approval 层返回 usage limit 拦截，无法继续通过该 session 跑外部命令。

### 影响

- PCOC / official preprocessing 的 focused tests 曾在实现后通过：`Ran 6 tests OK`。
- 但 1M official preprocessing smoke、LR overfit gate、后续 commit / push 尚未在当前 session 完成。
- 该问题属于本地 Codex 执行环境问题，不是已定位的项目代码逻辑失败。

### 下一步

恢复方式任选其一：

- 重启 Codex / 重开本地 shell session 后继续跑 smoke；
- 或 Eddy 在本机 PowerShell 直接执行 smoke 命令并把输出贴回。

恢复后首先执行：

```powershell
.\.venv\Scripts\python.exe scripts\preprocess_ctr_data_official.py --config configs\official_ctr_smoke.yaml
.\.venv\Scripts\python.exe scripts\train.py --config configs\torch_lr_smoke.yaml --metadata <official-smoke-metadata.json> --overfit --device cpu
```

### 更新

重启 Codex 后，普通 sandbox 仍会触发 `CreateProcessAsUserW failed: 1312`，但提权执行路径恢复可用。本任务已通过提权路径继续完成本地 focused tests、official 1M preprocessing smoke 和 LR overfit gate。

### 状态

Mitigated。普通 sandbox 仍不稳定；本轮使用提权执行路径继续工作。

## 2026-05-29 - Phase D OOF stats preprocessing 首版在 1M 上超时

### 现象

首版 `scripts/preprocess_ctr_stats.py` 在本地 1M hist run 上生成 OOF stats features 时超过 20 分钟仍未完成，命令超时：

```text
scripts/preprocess_ctr_stats.py --source-metadata outputs/preprocessed/ctr-610578df3be5/metadata.json --mode oof
```

### 根因

首版实现对每个 train row 都执行一次：

```text
full_count_table.subtract(current_fold_table)
```

这会按行重复遍历 item/user/category/user_category 的全量 key space，复杂度接近 `O(rows * keys)`，在 807k train rows 上不可接受。

### 修复

将每个 fold 的 OOF lookup tables 预先计算一次：

```text
oof_tables[fold][feature] = full_tables[feature] - fold_tables[fold][feature]
```

逐行编码时只查 `oof_tables[fold]`，避免重复构造全量差分表。

### 验证

修复后同一 OOF preprocessing 在本地 1M run 上完成：

```text
run_id: ctr-5c68a971db3a-stats
elapsed_seconds: 26.007
split rows: 807,282 / 96,459 / 96,459
```

focused test 通过：

```text
python -m unittest tests.test_phase_d_stats
Ran 3 tests OK
```

### 状态

Fixed for local 1M prototype。Full run 前仍需改成 streaming / chunked 版本，当前脚本会把 train/valid/test rows 读入内存。

---

## ISSUE-20260530-001 — Phase D stats features 引入 test PCOC 偏移（OOF-vs-full-train shift）

### 日期

2026-05-30

### 类型

calibration / feature engineering

### 现象

Phase D ablation 三模型 test PCOC 全部 > 1.0：

- LR +stats：1.1079、1.0921、1.0883（mean ≈ 1.096）
- DCN-v2 +stats：1.0974、1.0604、1.0754（mean ≈ 1.078）
- DIN +stats：1.1160、1.1015、1.0978（mean ≈ 1.105）

模型系统性高估真实 CTR 约 8–11%。

### 证据

- 三模型 9 个 run 的 summary.json test 段（完整数字见 docs/experiment_log.md Phase D ablation 章节）
- LR 在 Phase D 没有 output_bias_init，但 PCOC 仍 ≈ 1.09 → 偏移来源不是 bias init，而是统计特征本身
- Phase B baseline 无 PCOC 数据（PCOC 指标在 Phase C 才实现，Phase B 运行时未记录）；无法直接对照定性

### 根因或当前假设

**OOF-vs-full-train 特征分布偏移（假设）**：

- train 统计特征：5-fold OOF（扣除自己 fold），每个特征值系统性"偏低"
- valid/test 统计特征：全量 train 统计（包含所有 train 行），系统性"偏高"
- 模型学到"低统计值 → 输出约 24%"，到 test 看到偏高统计值 → 输出 > 24% → PCOC > 1
- 这是 Kaggle / 工业 target encoding 的已知副作用（"OOF shift"）

### 影响

- AUC / GAUC 不受影响（ranking 仍正确）
- LogLoss 在 +stats 下仍下降（可解释：整体校准虽偏，但条件预测仍更准）
- **直接部署会高估 CTR 约 8–11%**，下游出价 / 融合需修正（常见做法：训练后做 isotonic regression 或 Platt scaling 校准头）
- 与 Phase C 的 cross-protocol PCOC ≈ 1.45 是不同机制（C 是负采样导致，D 是 OOF shift 导致）

### 修复或 workaround（未实施）

候选方案：

1. valid/test 也用 K-fold OOF（对齐 train，代价是评估一致性）
2. 训练时也用 full-train 统计（放弃 OOF，接受微弱泄漏）
3. 训练后加 isotonic regression 校准头，只调整概率不影响 ranking
4. 显式建模：把 fold 标记当 train 特征喂给模型

### 验证（待做）

- Phase B baseline 没有 PCOC 数据，无法直接对照定性
- 后续如果实施任一修复方案，需 ablation 验证 PCOC 是否回到 ≈ 1.0
- 同时验证 AUC / LogLoss 不被修复方案显著破坏

### 2026-05-31 分布判定（不训练，直接对比 materialized 数据）

方法：对 6 个 numeric 特征用 stride 均匀采样，对比 train（OOF）/ valid / test（full-train lookup）的标准化 mean（train 基准≈0，valid/test 偏离量即 shift）。

| 特征 | valid | test | 偏移 |
|---|---:|---:|---|
| user_hist_ctr | 0.000 | 0.000 | 无 |
| user_category_hist_ctr | 0.007 | 0.001 | 无 |
| item_log_impressions | 0.007 | -0.028 | 小 |
| category_hist_ctr | -0.024 | -0.051 | 小 |
| item_hist_ctr | 0.064 | -0.010 | 小 |
| user_log_impressions | 0.316 | 0.316 | **大 +0.32σ** |

判定：

- **OOF-vs-full-train shift 假设证伪**：CTR 类 target-encoded 特征（含 user_hist_ctr）的 train OOF 与 valid/test full-train lookup 分布几乎一致（mean 偏移 < 0.07σ），不存在假设中"train 系统偏低、valid/test 系统偏高"的现象。
- **真正的单一显著偏移是 user_log_impressions（count 类，非 target-encoded）**，valid/test 系统高 0.32σ。根因是 user-order time-split：valid/test 是每个 user 的时间后段，累计曝光自然更多 → log_impressions 偏高，与 OOF 无关。
- 判别证据：同为 user 侧，`user_hist_ctr`（比率）无偏、`user_log_impressions`（计数）偏高，干净区分"时间累积"vs"OOF 编码"。

重新定性：

- PCOC 8–11% 高估**不是 OOF target encoding bug**，而是 time-split 下 count 特征的结构性偏移（叠加模型对其依赖）。
- 仍是校准问题非排序问题（AUC/GAUC 不受影响），部署加 isotonic / Platt 校准头即可。
- 边界："PCOC 完全由 user_log_impressions 解释"是强假设，要完全坐实需 reliability 图或对该特征消融（可选，非收口必需）。

### 状态

Downgraded / 机制已查清（2026-05-31）：非 OOF 编码 bug，是 user-order time-split 的 count 特征结构性偏移。不阻塞收口。未来做 stats 特征**无需**特别处理 OOF；若需部署级概率校准，加校准头或对 count 特征做时间稳健处理即可。
