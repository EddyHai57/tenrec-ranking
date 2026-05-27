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

未来 issue 必须记录：

- 日期
- 类型：environment、data、code、training、evaluation、documentation
- 现象
- 证据
- 根因或当前假设
- 修复或 workaround
- 验证
- 状态：open、mitigated、closed
