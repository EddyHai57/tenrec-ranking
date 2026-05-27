# 数据笔记

本文件记录已验证的数据集事实、schema 观察、label 定义、切分规则和数据契约决策。

## 已检查官方来源

- Tenrec official website: https://tenrec0.github.io/
- Tenrec official GitHub repository: https://github.com/yuangh-x/2022-NIPS-Tenrec
- Official dataset download page: https://static.qblv.qq.com/qblv/h5/algo-frontend/tenrec_dataset.html
- Paper: https://arxiv.org/abs/2210.10629

## 来源层面事实

根据 Tenrec 官方网站和官方仓库描述，Tenrec：

- 来自两个腾讯 feed recommendation app；
- 覆盖四个场景；
- 约包含 5 million users 和 140 million interactions；
- 包含真实负样本（true negative feedback）；
- 包含多种正向反馈，例如 clicks、likes、shares、follows；
- 包含 user ID / item ID 之外的额外特征。

根据论文 / 官方材料截图，Tenrec 可用于多种推荐系统任务，包括：

- CTR prediction；
- Session-based Recommendation；
- Transfer Learning；
- Cold-start Recommendation；
- Lifelong User Representation Learning；
- Model Compression / Training Speedup / Inference Speedup。

论文 / 官方材料总结的五个特点：

1. 大规模：超过 5 million users 和约 140 million interactions。
2. 同时包含正向用户反馈和真实负反馈。
3. 四个不同场景中存在部分 user overlap 和 item overlap。
4. 包含多种用户反馈：click、like、share、follow 等。
5. 包含额外 user features 和 item features。

用户隐私保护：

- 数据来自真实推荐场景。
- 为保护用户个人隐私，数据已做匿名化处理。

官方仓库列出的 raw scenario files：

- `QK-video.csv`
- `QB-video.csv`
- `QK-article.csv`
- `QB-artilce.csv`

注意：`QB-artilce.csv` 是官方 README 中的拼写。引用原始文件名时保留上游拼写。

## 论文 / 官方材料统计

以下统计来自用户提供的论文 / 官方材料截图，用于背景理解；尚未由本地全量脚本重算。

| Name | QK-video | QK-article | QB-video | QB-article |
| --- | ---: | ---: | ---: | ---: |
| #users | 5,022,750 | 1,325,838 | 34,240 | 24,516 |
| #items | 3,753,436 | 220,122 | 130,637 | 7,355 |
| #click | 142,321,193 | 46,111,728 | 1,701,171 | 348,736 |
| #like | 10,141,195 | 821,888 | 20,687 | / |
| #share | 1,128,312 | 591,834 | 2,541 | / |
| #follow | 857,678 | 62,239 | 2,487 | / |
| #read | / | 44,228,593 | / | / |
| #favorite | / | 316,627 | / | / |
| #exposure | 493,458,970 | / | 2,442,299 | / |
| avg #clicks | 28.34 | 34.78 | 49.69 | 14.22 |

解释：

- `avg #clicks` 表示每个 user 平均 click 数。
- `#exposure` 包括正反馈和负反馈曝光。
- 这些数字适合用于项目背景和数据规模说明，不直接作为本项目实验结果。


## 本地验证状态

Tenrec 数据已下载并解压到：

```text
D:\ANU\project\tenrec-ranking\data\Tenrec
```

`data/` 已被 `.gitignore` 排除，不进入 git。

## 官方最小子集确认

已确认官方材料中存在 1M 级别子集口径：

- 官方 GitHub 的 CTR benchmark 命令使用 `data/ctr_data_1M.csv`。
- 官方 GitHub 的 session-based recommendation 命令使用 `data/sbr_data_1M.csv`。
- 官方官网 leaderboard 标注 `CTR-1M`。
- 论文和官方材料将该采样数据称为 `QK-video-1M`。

当前判断：

- `ctr_data_1M.csv` 是第一轮 click prediction schema inspection 的优先候选。
- 本地已存在 `data/Tenrec/ctr_data_1M.csv`，后续 inspection 以该文件为准。

当前不能写成事实的内容：

- 不能说下载链接已解析出来。
- 不能说 `ctr_data_1M.csv` 的 timestamp、split 口径或 `hist_1` 到 `hist_10` 构造口径已经验证。

本地 schema inspection 后仍未知：

- true negative label 编码；
- scenario / domain 字段；
- user / item 侧特征；
- 是否能稳定构造用户历史序列；
- 官方预处理 CTR 文件是否保留时间顺序。

## 本地文件清单

只读文件清单，未做全表扫描：

| 文件 | 大小 | 初步用途 |
| --- | ---: | --- |
| `QK-video.csv` | 14.08 GB | raw video scenario |
| `ctr_data_1M.csv` | 9.94 GB | CTR task / Multi-Task Learning |
| `QK-article.csv` | 4.47 GB | raw article scenario |
| `sbr_data_1M.csv` | 1.04 GB | Session-based Recommendation 等序列任务 |
| `task_0.csv` | 603.4 MB | Lifelong Learning |
| `cold_data_0.3.csv` | 247.5 MB | Cold-start task |
| `cold_data_0.7.csv` | 115.6 MB | Cold-start task |
| `QB-video.csv` | 73.9 MB | raw video scenario / transfer target |
| `task_1.csv` | 67.7 MB | Lifelong Learning |
| `cold_data.csv` | 31.5 MB | Cold-start task |
| `QB-article.csv` | 19.7 MB | raw article scenario |
| `cold_data_1.csv` | 19.0 MB | Cold-start task |
| `task_2.csv` | 8.7 MB | Lifelong Learning |
| `task_3.csv` | 13.9 KB | Lifelong Learning |

## Readme 事实

本地 `data/Tenrec/Readme.txt` 说明：

- 四个 raw datasets 是 `QK-video`、`QK-article`、`QB-video`、`QB-article.csv`。
- `ctr_data_1M.csv` 用于 CTR task 和 Multi-Task Learning。
- `sbr_data_1M.csv` 用于 Session-based Recommendation、Transfer Learning pre-training、User Profile Prediction、Model Compression、Model Training Speedup。
- item 在 user level 按 click time 排序，因此时间信息隐含在 item 顺序中。

关键影响：

- 当前数据没有显式 timestamp 字段；时间切分不能直接按 timestamp 做。
- 如果采用官方预处理 CTR 表，需要确认 `hist_1` 到 `hist_10` 是否只使用 target event 之前的历史，避免未来信息泄漏。
- 如果要自己构造严格时间切分，可能需要从 raw sequence order 出发，而不是直接依赖 `ctr_data_1M.csv`。

## 头部 schema 观察

`ctr_data_1M.csv` 表头：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age,hist_1,hist_2,hist_3,hist_4,hist_5,hist_6,hist_7,hist_8,hist_9,hist_10
```

前两行样例：

```text
1,4,0,0,0,0,1,0,1,4,2,3,80936,781,111774,1230,26403,991,2362,1202
1,1201,1,0,0,0,1,1,1,4,2,3,80936,781,111774,1230,26403,991,2362,1202
```

`sbr_data_1M.csv` 和 `QK-video.csv` 表头：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age
```

`QK-article.csv` 表头：

```text
user_id,item_id,click,gender,age,exposure_count,click_count,like_count,comment_count,read_percentage,item_score1,item_score2,category_second,category_first,item_score3,read,read_time,share,like,follow,favorite
```

## 轻量抽样观察

使用 Python 标准库读取每个文件前 100,000 行；这不是全量统计，不能当最终指标。

| 文件 | 抽样行数 | 抽样 unique users | 抽样 unique items | click 分布 |
| --- | ---: | ---: | ---: | --- |
| `ctr_data_1M.csv` | 100,000 | 773 | 55,764 | `0`: 71,756；`1`: 28,244 |
| `sbr_data_1M.csv` | 100,000 | 2,162 | 49,572 | `1`: 100,000 |
| `QK-video.csv` | 100,000 | 8,012 | 46,964 | `0`: 57,152；`1`: 42,848 |
| `QB-video.csv` | 100,000 | 639 | 28,226 | `0`: 54,997；`1`: 45,003 |
| `QK-article.csv` | 100,000 | 4,189 | 22,631 | `1.0`: 100,000 |
| `QB-article.csv` | 100,000 | 5,722 | 4,496 | `1.0`: 100,000 |

初步判断：

- `ctr_data_1M.csv` 明确包含 click 0/1，且已有 `hist_1` 到 `hist_10`，适合作为第一轮 click prediction schema inspection 优先对象。
- `QK-video.csv` / `QB-video.csv` raw video 文件也包含 click 0/1，但没有预生成 history columns。
- `sbr_data_1M.csv` 头部 click 全为 1，更偏序列正反馈任务，不适合作为 CTR MVP 起点。
- article 文件头部 click 全为 1，第一阶段不优先。

仍需验证：

- `hist_1` 到 `hist_10` 的构造口径。
- `watching_times=0` 是否与 negative exposure 对齐。
- `ctr_data_1M.csv` 是否有官方固定 train/valid/test split，或需要自行构造切分。
- 如果没有显式 timestamp，如何定义“时间切分”或是否需要改为“顺序切分 / user-level chronological split”。

## `ctr_data_1M.csv` 全量流式 inspection

日期：2026-05-25

命令：

```powershell
.\.venv\Scripts\python.exe scripts\inspect_ctr_data.py --input data\Tenrec\ctr_data_1M.csv --output-dir outputs\inspection
```

输出文件：

```text
outputs/inspection/ctr_data_1M_summary.json
outputs/inspection/ctr_data_1M_report.md
```

文件基础信息：

| 项 | 值 |
| --- | ---: |
| size bytes | 10,670,097,636 |
| size GB decimal | 10.6701 |
| size GiB | 9.9373 |
| total rows | 120,342,306 |
| bad width rows | 0 |
| elapsed seconds | 614.431 |

字段：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age,hist_1,hist_2,hist_3,hist_4,hist_5,hist_6,hist_7,hist_8,hist_9,hist_10
```

Label / behavior 分布：

| 字段 | 分布 |
| --- | --- |
| `click` | `0`: 91,461,446；`1`: 28,880,860 |
| `follow` | `0`: 120,162,518；`1`: 179,788 |
| `like` | `0`: 118,066,889；`1`: 2,275,417 |
| `share` | `0`: 120,092,217；`1`: 250,089 |
| `gender` | `0`: 22,618,864；`1`: 69,808,045；`2`: 27,915,397 |
| `age` | `0`: 22,393,960；`1`: 2,382,927；`2`: 59,148,517；`3`: 25,562,860；`4`: 7,943,550；`5`: 2,158,742；`6`: 656,496；`7`: 95,254 |
| `video_category` | `0`: 64,475,979；`1`: 54,277,815；`\N`: 1,588,512 |

`watching_times` top values：

| value | count |
| ---: | ---: |
| 1 | 69,388,757 |
| 0 | 39,522,741 |
| 2 | 8,987,366 |
| 3 | 1,570,537 |
| 4 | 510,529 |
| 5 | 168,241 |

ID 统计：

| 项 | 值 |
| --- | ---: |
| unique `user_id` | 999,447 |
| unique `item_id` | 2,310,087 |
| user row count min | 1 |
| user row count p50 | 82 |
| user row count p90 | 265 |
| user row count p99 | 590 |
| user row count max | 5,995 |
| item row count min | 1 |
| item row count p50 | 3 |
| item row count p90 | 51 |
| item row count p99 | 799 |
| item row count max | 153,434 |

History 字段检查：

| 字段 | empty | zero | nonzero |
| --- | ---: | ---: | ---: |
| `hist_1` | 0 | 25,382 | 120,316,924 |
| `hist_2` | 0 | 60,340 | 120,281,966 |
| `hist_3` | 0 | 111,798 | 120,230,508 |
| `hist_4` | 0 | 192,460 | 120,149,846 |
| `hist_5` | 0 | 336,534 | 120,005,772 |
| `hist_6` | 0 | 578,022 | 119,764,284 |
| `hist_7` | 0 | 940,260 | 119,402,046 |
| `hist_8` | 0 | 1,456,568 | 118,885,738 |
| `hist_9` | 0 | 2,072,059 | 118,270,247 |
| `hist_10` | 0 | 2,771,110 | 117,571,196 |

每行非零 history 长度分布：

| 非零长度 | 行数 |
| ---: | ---: |
| 0 | 25,382 |
| 1 | 34,958 |
| 2 | 51,458 |
| 3 | 80,662 |
| 4 | 144,074 |
| 5 | 241,488 |
| 6 | 362,238 |
| 7 | 516,308 |
| 8 | 615,491 |
| 9 | 699,051 |
| 10 | 117,571,196 |

Target item history 检查：

- `target item in history count`: 0
- `target item in history rate`: 0.0

初步风险判断：

- 没有显式 timestamp 字段，不能直接做 timestamp-based split。
- 后续需要验证是否可使用 user-level chronological / order-based split。
- `hist_1` 到 `hist_10` 是否只来自 target event 之前的行为仍未验证；当前结果只能说明 target `item_id` 没有直接出现在同一行 history 中。
- `video_category` 存在 `\N`，后续 dataloader 需要明确 missing category 编码。

## `ctr_data_1M.csv` 数据契约 probe

日期：2026-05-25

命令：

```powershell
.\.venv\Scripts\python.exe scripts\probe_ctr_data_contract.py --input data\Tenrec\ctr_data_1M.csv --output-dir outputs\inspection
```

输出文件：

```text
outputs/inspection/ctr_data_1M_contract_probe.json
outputs/inspection/ctr_data_1M_contract_probe.md
```

### user 顺序检查

| 项 | 值 |
| --- | ---: |
| user block count | 999,447 |
| seen closed users | 999,447 |
| non-contiguous user count | 0 |
| user id monotonic violations | 0 |
| user id numeric parse failures | 0 |
| user block row count min | 1 |
| user block row count p50 | 82 |
| user block row count p90 | 265 |
| user block row count p99 | 590 |
| user block row count max | 5,995 |

结论：

- `ctr_data_1M.csv` 按 `user_id` 连续分块排列。
- `user_id` 数值单调递增。
- user block 数与上一轮 inspection 的 unique `user_id` 一致。
- 这使 user-level order-based split 和 user-block sample 在工程上可行。

### 重复与冲突检查

统计口径：user block 内精确统计。本次 probe 确认 user 连续排列，因此同一 user 内的完全重复行、重复 `(user_id,item_id)` 和 click 冲突可以视为本文件全量精确统计。

| 项 | 值 |
| --- | ---: |
| 完全重复行 | 883,646 |
| 重复 `(user_id,item_id)` | 1,810,484 |
| 重复 pair 中 click 冲突 | 560,994 |

解释：

- 重复 `(user_id,item_id)` 可能代表多次曝光，也可能来自预处理重复；当前不能直接删除。
- 同一 `(user_id,item_id)` 同时出现 `click=0` 和 `click=1`，说明 `(user_id,item_id)` 不是唯一样本键。
- 后续数据契约应把“一行样本”定义为一次曝光 / one exposure-like row，而不是唯一 user-item pair。

### history 合理性检查

| 项 | 值 |
| --- | ---: |
| target item in same-row history count | 0 |
| target item in same-row history rate | 0.0 |
| sampled user blocks | 200 |
| sampled history items | 257,099 |
| sampled history items not in previous rows of same file | 257,099 |

解释：

- target `item_id` 没有直接出现在同一行 `hist_1` 到 `hist_10`，这是一个正向信号。
- 但 200 个 sampled user blocks 中，history item 没有出现在该文件此前行的同 user item 集合里。
- 这更可能说明 `ctr_data_1M.csv` 是 task-specific 文件，没有保留完整原始历史，而不是直接证明未来泄漏。
- 当前仍不能证明 `hist_1` 到 `hist_10` 严格只使用 target event 之前行为；后续需要结合 raw `QK-video.csv` 或官方预处理逻辑继续确认。

### split 策略判断

| 策略 | 当前建议 | 原因 | 风险 |
| --- | --- | --- | --- |
| timestamp-based split | 不建议 | 无显式 timestamp | 伪造时间口径会导致实验不可审计 |
| user-level order-based split | MVP 候选，但需谨慎 | user block 连续，Readme 说明 user-level item order 隐含时间 | 仍需确认 `hist_1` 到 `hist_10` 无未来信息 |
| user-block split | 可作稳健性 / 冷启动式对照 | user 连续，工程实现简单 | 评估变成 unseen-user 泛化，不一定是常规 CTR ranking |
| official / random split baseline | 只作官方复现或对照 | 可能贴近官方 benchmark | 同一 user/item 跨 split，泄漏风险更高 |

### smoke sample 策略建议

下一步建议生成两个本地 ignored sample：

| 文件 | 用途 | 边界 |
| --- | --- | --- |
| `ctr_tiny_100k_head.csv` | 代码 smoke / debug，验证 reader、feature parsing、batch shape 和最小 metric 流程 | head sample 有偏，不能当正式实验结果 |
| `ctr_user_block_1m_seed20260525.csv` | dataloader、GAUC、order-based split 和 history 检查 | 需要保留完整 user blocks；不能当 full validation/test |

## Smoke samples

日期：2026-05-25

命令：

```powershell
.\.venv\Scripts\python.exe scripts\make_ctr_smoke_samples.py --input data\Tenrec\ctr_data_1M.csv --sample-dir data\samples --output-dir outputs\inspection --tiny-rows 100000 --target-rows 1000000 --seed 20260525
```

输出 sample：

```text
data/samples/ctr_tiny_100k_head.csv
data/samples/ctr_user_block_1m_seed20260525.csv
```

输出报告：

```text
outputs/inspection/ctr_smoke_samples_summary.json
outputs/inspection/ctr_smoke_samples_report.md
```

### `ctr_tiny_100k_head.csv`

生成方式：

- 保留原始 header。
- 取 `ctr_data_1M.csv` 前 100,000 行数据。
- 不打乱。
- 不去重。

统计：

| 项 | 值 |
| --- | ---: |
| rows | 100,000 |
| user count | 773 |
| file size bytes | 7,767,741 |
| `click=0` | 71,756 |
| `click=1` | 28,244 |

用途：

- CSV reader smoke test。
- feature parsing。
- batch shape。
- 最小 metric 流程 debug。

不能用于：

- 正式实验结果。
- 模型指标报告。
- 代表性数据分布判断。

原因：head sample 有明显顺序 / user 偏置。

### `ctr_user_block_1m_seed20260525.csv`

生成方式：

- 保留原始 header。
- 使用 seed `20260525` 对 `user_id` 做 stable hash，选择完整 user blocks。
- 目标约 1,000,000 行，最后一个 user block 不截断。
- 写出时保留原始行顺序。
- 不打乱。
- 不去重。

统计：

| 项 | 值 |
| --- | ---: |
| target rows | 1,000,000 |
| actual rows | 1,000,200 |
| user count | 8,181 |
| file size bytes | 88,850,808 |
| `click=0` | 758,425 |
| `click=1` | 241,775 |
| user row count min | 1 |
| user row count p50 | 84 |
| user row count p90 | 269 |
| user row count p99 | 607 |
| user row count max | 1,810 |

用途：

- dataloader 原型。
- GAUC 计算验证。
- user-level split / order-based split 验证。
- tiny training / overfit smoke test。

不能用于：

- full validation。
- full test。
- 正式实验结果。

注意：

- 该 sample 保留完整 user blocks，适合调试 group-level metric 和按 user 的切分逻辑。
- 该 sample 仍是开发样本，不代表全量评估。

## Split feasibility check

日期：2026-05-25

命令：

```powershell
.\.venv\Scripts\python.exe scripts\check_ctr_split_feasibility.py --input data\samples\ctr_user_block_1m_seed20260525.csv --output-dir outputs\inspection
```

输出文件：

```text
outputs/inspection/ctr_user_block_1m_split_feasibility.json
outputs/inspection/ctr_user_block_1m_split_feasibility.md
```

### split 规则

输入：`data/samples/ctr_user_block_1m_seed20260525.csv`

规则：

- 每个 user 内按文件顺序切分。
- user rows `< 3`：全部进入 train。
- user rows `>= 3`：按 80/10/10 切成 train / valid / test，valid 和 test 至少各 1 行。
- 不打乱。
- 不去重。
- 保留原始 row order。

短 user 分布：

| user row count bucket | user count |
| --- | ---: |
| `1` | 8 |
| `2` | 3 |
| `>=3` | 8,170 |

### split 基础统计

| split | rows | users | items | `click=0` | `click=1` | positive rate | `follow=1` | `like=1` | `share=1` | missing `video_category` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 807,282 | 8,181 | 222,829 | 611,818 | 195,464 | 0.24212605 | 1,172 | 16,418 | 1,816 | 10,134 |
| valid | 96,459 | 8,170 | 54,212 | 70,725 | 25,734 | 0.26678693 | 101 | 1,547 | 129 | 1,278 |
| test | 96,459 | 8,170 | 55,095 | 75,882 | 20,577 | 0.2133238 | 59 | 1,091 | 79 | 1,550 |

`video_category` top values：

| split | top values |
| --- | --- |
| train | `0`: 427,448；`1`: 369,700；`\N`: 10,134 |
| valid | `0`: 54,492；`1`: 40,689；`\N`: 1,278 |
| test | `0`: 54,266；`1`: 40,643；`\N`: 1,550 |

### GAUC 可行性

GAUC 只对同一 split 内同时有 click 正负样本的 user 有意义。

| split | total users | valid GAUC users | only positive users | only negative users | rows `< 2` users | valid GAUC rows | row coverage rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| valid | 8,170 | 5,677 | 312 | 2,181 | 590 | 84,225 | 0.87316891 |
| test | 8,170 | 5,021 | 212 | 2,937 | 590 | 79,120 | 0.82024487 |

判断：

- valid / test 的 GAUC row coverage 分别约 87.3% 和 82.0%，smoke 阶段可用。
- 仍有不少 only negative users，正式 full run 需要重新验证 GAUC 覆盖率。
- 该结果只能支持 GAUC implementation / dataloader smoke，不能作为正式模型指标依据。

### cold item / unseen item 风险

| 检查 | count | rate |
| --- | ---: | ---: |
| valid item 未出现在 train | 16,805 | 0.30998672 |
| test item 未出现在 train | 16,911 | 0.30694255 |
| test item 未出现在 train + valid | 15,784 | 0.28648698 |

判断：

- unseen item 比例约 29%-31%，后续 embedding / feature mapping 必须支持 OOV item。
- 如果第一版 baseline 直接用 ID embedding，需要显式定义 unknown item 处理。

### feature 使用建议

第一阶段 click baseline 可用：

```text
user_id
item_id
video_category
gender
age
```

暂时不要作为输入特征：

```text
watching_times
hist_1 ... hist_10
follow
like
share
```

原因：

- `watching_times` 可能是 post-exposure / post-click 行为，有 leakage 风险。
- `hist_1` 到 `hist_10` 构造口径未完全验证，第一版 click baseline 暂不使用。
- `follow`、`like`、`share` 是多任务标签，不应作为 click baseline 输入特征，除非明确做多任务或 label leakage 对照。

### 当前结论

- `ctr_user_block_1m_seed20260525.csv` 适合 dataloader smoke。
- `ctr_user_block_1m_seed20260525.csv` 适合 tiny LR / MLP overfit test。
- `ctr_user_block_1m_seed20260525.csv` 不适合报告正式指标。
- 当前可以进入最小 `src/` / `configs/` 设计，但范围应限制为 dataloader、split、feature mapping 和 metric smoke。
- 下一步不应做 full training；应先设计最小数据契约、OOV 编码、GAUC 计算和 tiny baseline smoke。

## 初始数据契约草案

第一版本地数据契约需要回答：

1. MVP 使用哪一个单场景？
2. 一行样本代表什么？
3. 哪一列是 click label？
4. 哪个值是正样本，哪个值是真实负样本？
5. 哪个 timestamp 字段支持时间切分？
6. train / valid / test 如何切分？
7. 可用的 categorical / numerical features 有哪些？
8. 哪些字段适合 MVP，哪些字段有泄漏风险？
9. 用户历史是否能只用 target event 之前的事件构造？
10. 哪些字段可为后续 multi-task learning 预留？

## MVP 数据契约 v0.1

日期：2026-05-25

本节是第一版 click prediction 数据层实现的事实契约。后续 `data.py`、preprocessing、metric 和 server runbook 必须以本节为准。

### 任务与输入字段

- 主任务：点击率预测（CTR / click prediction）。
- label：`click`，`1` 为 click positive，`0` 为真实曝光负样本。
- 一行样本：一次 exposure-like row，不是唯一 `(user_id,item_id)` pair。
- 第一阶段输入特征：
  - `user_id`
  - `item_id`
  - `video_category`
  - `gender`
  - `age`
- 暂不作为输入：
  - `watching_times`：可能是 post-exposure / post-click 行为。
  - `hist_1` 到 `hist_10`：构造口径仍未完全验证，暂不进入 MVP baseline。
  - `follow`、`like`、`share`：多任务标签，不作为单任务 click baseline 输入。

`gender` 和 `age` 已在全量 inspection 中确认没有 `\N` 缺失；第一版仍按 categorical vocab 编码，并保留统一 missing 槽，避免后续字段扩展时出现编码分叉。

### Split 整数公式

每个 user block 保持原始文件内顺序，不 shuffle、不去重。

```text
如果 N < 3:
    train = N
    valid = 0
    test = 0

如果 N >= 3:
    valid = max(1, floor(0.1 * N))
    test  = max(1, floor(0.1 * N))
    train = N - valid - test
```

边界：

```text
train: [0, train)
valid: [train, train + valid)
test : [train + valid, N)
```

示例：

| N | train | valid | test |
| ---: | ---: | ---: | ---: |
| 1 | 1 | 0 | 0 |
| 2 | 2 | 0 | 0 |
| 3 | 1 | 1 | 1 |
| 7 | 5 | 1 | 1 |
| 10 | 8 | 1 | 1 |
| 99 | 81 | 9 | 9 |
| 100 | 80 | 10 | 10 |

实现约束：

- split 逻辑只在 `src/tenrec/data.py` 中实现。
- `scripts/check_ctr_split_feasibility.py` 已改为调用同一个 split 函数。
- 重构后在 `ctr_user_block_1m_seed20260525.csv` 上复现 oracle：
  - train：807,282
  - valid：96,459
  - test：96,459

注意：上述 oracle 是重构后重新运行得到的验证结果，不是为了匹配旧脚本而调整新函数。

### Vocab 与编码

词表构建规则：

- 只使用 train split 的行构建 vocab。
- valid/test 未见值映射到 OOV。
- 不允许用全文件建表。
- vocab 是派生产物，落盘到 `outputs/preprocessed/{run_id}/vocabs/`。

统一 reserved index：

```text
0 = OOV
1 = missing
2.. = train 中出现过的正常取值
```

适用于全部 categorical features，包括 `user_id`、`item_id`、`video_category`、`gender`、`age`。

missing 判定优先于 OOV 判定：

```text
如果原始值是 "" 或 "\N"，编码为 1。
否则如果值不在 train vocab 中，编码为 0。
否则使用 vocab 中的 seen index。
```

`video_category` 的 `\N` 编码为 missing，而不是 OOV。

回归断言：

- 由于 split 是 user 内顺序切分，`valid/test` 的 `user_id` OOV 率理论上必须为 0。
- 如果 `valid/test` 出现 `user_id` OOV，说明 split 或 vocab 实现存在错误，应直接失败。
- `item_id` OOV 是预期现象，1M sample 中 valid/test 均存在较高 unseen item。

### 两遍流式预处理

全量 `ctr_data_1M.csv` 有 120,342,306 行，不能围绕一次性 DataFrame load 设计。

采用两遍流式预处理：

```text
Pass 1:
    流式扫描原始 CSV
    按 user block 使用同一 split 函数
    只累积 train 行中的 feature value 进入 vocab
    冻结 vocab

Pass 2:
    再次流式扫描原始 CSV
    使用同一 split 函数
    用冻结 vocab 编码 train/valid/test
    物化为 split CSV 文件
```

物化输出：

```text
outputs/preprocessed/{run_id}/metadata.json
outputs/preprocessed/{run_id}/vocabs/*.json
outputs/preprocessed/{run_id}/materialized/train.csv
outputs/preprocessed/{run_id}/materialized/valid.csv
outputs/preprocessed/{run_id}/materialized/test.csv
```

`run_id` 由输入文件名、输入文件大小、config、数据契约版本和预处理版本生成确定性 hash。`metadata.json` 记录输入、config、split、reserved index、vocab size、OOV/missing 统计和 git commit。

### GAUC 口径

采用 impression-weighted GAUC：

```text
GAUC = sum(user_auc * user_impressions) / sum(user_impressions)
```

只对同一 split 内同时有 positive 和 negative label 的 user 计算 user AUC。only-positive / only-negative user 跳过。

任何 GAUC 输出必须同时报告：

- GAUC
- valid GAUC user count
- total user count
- valid GAUC row count
- total row count
- row coverage rate

原因：跳过单类用户后，GAUC 的有效行覆盖率会低于 100%。例如 1M sample 的 valid/test GAUC row coverage 分别约为 87.3% 和 82.0%，单独报告 GAUC 数值会误导。

### 不去重限制

MVP 不去重。

原因：

- 全量 probe 发现完全重复行 883,646 条。
- 重复 `(user_id,item_id)` 为 1,810,484 条。
- 重复 pair 中 click 冲突为 560,994 条。
- `(user_id,item_id)` 不是唯一曝光键，机械去重会改变样本语义。

已知限制：

- 完全重复行可能跨 train/valid/test 分裂，带来轻微记忆风险。
- 该限制必须在实验日志和项目总结中保留，不能把 smoke / limited result 写成正式结论。

### Seed 作用域

`20260525` 只用于生成 smoke sample 时选择 user blocks。

split 本身是确定性 user-order split，不依赖 seed。

### 本地验证结果

已实现：

- `src/tenrec/data.py`：split、train-only vocab、OOV/missing 编码、两遍流式预处理和物化输出。
- `src/tenrec/metrics.py`：AUC、LogLoss、impression-weighted GAUC。
- `tests/test_data_contract.py`：split 整数公式、missing 优先于 OOV、train-only vocab 和 `user_id` OOV 断言。
- `tests/test_metrics.py`：AUC / LogLoss known-answer，GAUC 单类用户跳过和 coverage。

100k smoke sample 预处理：

```text
run_id: ctr-78004c39c1dd
train/valid/test rows: 80672 / 9664 / 9664
```

1M user-block smoke sample 预处理：

```text
run_id: ctr-454e7ccb12f7
train/valid/test rows: 807282 / 96459 / 96459
```

1M sample 物化后 OOV/missing 摘要：

- `valid item_id` OOV rows：17,367。
- `test item_id` OOV rows：17,577。
- `valid/test user_id` OOV：0。
- `video_category` missing rows：
  - train：10,134
  - valid：1,278
  - test：1,550

sklearn LR learnability smoke 只消费物化后的编码数据，不绕过 preprocessing pipeline。1M sample 上使用前 100,000 train rows 和前 50,000 valid rows：

- train AUC：0.8866438867118259
- train LogLoss：0.4080319738212789
- train GAUC：0.9012071068750077，coverage 0.99388
- valid AUC：0.6283948058203263
- valid LogLoss：0.5718098163083559
- valid GAUC：0.6032205118880077，coverage 0.89796

该结果只证明数据管道可学习，不是正式模型结果。

### torch baseline 训练契约

日期：2026-05-27

本地 CPU smoke 已加入 torch LR / MLP。训练层继续遵守 MVP 数据契约：

- 只消费 `outputs/preprocessed/{run_id}/materialized/*.csv`。
- vocab size、feature list 和 split path 从 `metadata.json` 读取。
- 不直接读取 raw CSV。
- 不重新构建 vocab。
- 不绕过 OOV/missing 编码。

LR 参数化：

```text
logit = bias + sum(field_scalar_lookup[field_value])
```

即每个 categorical field 使用 `[vocab_size, 1]` 的 scalar lookup。`embedding_dim` 只对 MLP 生效。

CTR baseline 训练目标：

- 使用普通 `BCEWithLogitsLoss`。
- 不使用 `pos_weight`。
- 不做 class reweighting。
- 不做正负样本重采样。

原因：LogLoss 需要概率校准，重加权或重采样会改变目标。

训练 shuffle：

- 物化 train 文件按 user 排列。
- 不使用小 `shuffle_buffer_size` 作为主要混洗机制。
- 训练前生成 deterministic hash-bucket shuffled train CSV。

当前本地生成：

```text
outputs/preprocessed/ctr-454e7ccb12f7/materialized/train_shuffled_seed20260525_b16.csv
```

`metadata_path`：

- config 中可以写本地 smoke metadata。
- `scripts/train.py` 必须支持 `--metadata` 覆盖。
- 服务器 full preprocessing 会生成新 run_id，不能假设本地 `ctr-454e7ccb12f7` 存在。

`max_train_rows` / `max_valid_rows`：

- 这是 head 截断。
- 只允许用于 smoke。
- 任何带 `max_*_rows` 的 run 不允许作为正式指标报告。

### 10M preprocessing 内存验证

日期：2026-05-27

目的：服务器 full preprocessing 前，验证两遍流式预处理不会在 10M 级别样本上整文件 load 或按行数线性爆内存。

样本：

```text
data/samples/ctr_user_block_10m_seed20260525.csv
rows: 10,000,035
users: 82,761
file size bytes: 886,528,483
```

预处理：

```text
config: configs/ctr_user_block_10m.yaml
run_id: ctr-1961cdee479f
peak RSS: 136.68 MiB
monitor backend: psutil
Pass1 elapsed: 38.223s
Pass2 elapsed: 71.914s
```

split：

```text
train: 8,072,351
valid: 963,842
test: 963,842
```

vocab：

```text
user_id: 82,763
item_id: 766,087
video_category: 4
gender: 5
age: 10
```

OOV 不变量：

```text
valid/test user_id OOV: 0
valid item_id OOV rows: 46,239, rate 0.04797363053280517
test item_id OOV rows: 47,786, rate 0.04957866538291546
```

物化输出大小：

```text
train.csv: 167,999,362 bytes
valid.csv: 19,920,285 bytes
test.csv: 19,946,855 bytes
total: 207,866,502 bytes
```

1M 对照：

```text
run_id: ctr-454e7ccb12f7
peak RSS: 54.77 MiB
user_id vocab: 8,183
item_id vocab: 222,831
```

判断：

- 10M 行数约为 1M 的 10 倍，但 peak RSS 只从 54.77 MiB 增至 136.68 MiB。
- 内存增长主要来自 vocab 条目增加，不是保存全部行。
- 当前未发现两遍预处理存在 hidden full-file buffer。
- full 120M 仍需在服务器验证。

## Tenrec 小样本检查计划

1. 访问官方 dataset page；如需 license terms，手动确认。
2. 下载最小但适合 CTR/schema inspection 的官方子集；如果官方页面提供 `ctr_data_1M.csv`，优先考虑。
3. 原始数据放在 git 控制之外，或在 `.gitignore` 已覆盖后放入 `data/raw/`。
4. 检查文件名、大小、编码、header、行数、缺失率、label 分布、timestamp 范围、per-user/per-item 计数。
5. 只把轻量 schema summary 和命令输出写入 docs；不要提交原始数据。
