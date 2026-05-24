# Tenrec 数据目录说明

本文件用于总览 `data/Tenrec/` 下载包中的文件、字段、官方用途和本项目用途。统计来源分三类：

- 官方 / 论文材料：来自 Tenrec official website、official GitHub、paper 或用户提供的官方材料截图。
- 本地文件头部检查：只读取本地 CSV header 和文件大小。
- 本地全量 inspection：仅目前已对 `ctr_data_1M.csv` 完成。

没有本地全量重算的统计，不写成本项目实验结果。

## 1. 数据包整体说明

- 数据来源：Tenrec，来自两个腾讯 feed recommendation app。
- 官方描述：覆盖四个场景，包含多行为反馈和真实负样本（true negative samples），数据已匿名化。
- 四个 raw scenario files：`QK-video.csv`、`QB-video.csv`、`QK-article.csv`、`QB-article.csv`。
- 本地路径：`D:\ANU\project\tenrec-ranking\data\Tenrec`
- 本地数据目录已被 `.gitignore` 忽略，不进入 git。
- 本地下载包文件总大小约 30.35 GB，不包含 `.DS_Store` 和 `Readme.txt`。

论文 / 官方材料中的规模统计用于背景说明，尚未由本地脚本全量重算。当前只有 `ctr_data_1M.csv` 已完成本地全量流式 inspection。

## 2. 文件总览表

| 文件 | 大小 | 数据类型 | 官方用途 | 是否用于本项目 MVP | 后续可能用途 |
| --- | ---: | --- | --- | --- | --- |
| `QK-video.csv` | 14.08 GiB | raw video scenario | raw dataset | 暂不直接用 | 严格 order-based split、history 构造溯源 |
| `QB-video.csv` | 73.87 MiB | raw video scenario / transfer target | Transfer Learning target、Model Inference Speedup | 暂不用于 MVP | 迁移学习或小场景验证 |
| `QK-article.csv` | 4.47 GiB | raw article scenario | raw dataset | 不作为 MVP 起点 | article 场景、多任务或跨域扩展 |
| `QB-article.csv` | 19.71 MiB | raw article scenario | raw dataset | 不作为 MVP 起点 | 小 article 场景检查 |
| `ctr_data_1M.csv` | 9.94 GiB | task-specific CTR / MTL | CTR task、Multi-Task Learning | 是，MVP 主候选 | LR / MLP / DeepFM / DCN-v2 排序 MVP |
| `sbr_data_1M.csv` | 1.04 GiB | task-specific sequence | Session-based Recommendation、Transfer Learning pre-training、User Profile Prediction、Model Compression / Training Speedup | 否 | DIN/BST 或 sequence 对照参考 |
| `cold_data.csv` | 31.48 MiB | task-specific cold-start | Cold-start | 否 | 冷启动扩展 |
| `cold_data_1.csv` | 18.95 MiB | task-specific cold-start | Cold-start | 否 | 冷启动扩展 |
| `cold_data_0.3.csv` | 247.51 MiB | task-specific cold-start | Cold-start | 否 | 冷启动扩展 |
| `cold_data_0.7.csv` | 115.60 MiB | task-specific cold-start | Cold-start | 否 | 冷启动扩展 |
| `task_0.csv` | 603.40 MiB | task-specific lifelong learning | Lifelong Learning | 否 | 持续学习扩展 |
| `task_1.csv` | 67.73 MiB | task-specific lifelong learning | Lifelong Learning | 否 | 持续学习扩展 |
| `task_2.csv` | 8.66 MiB | task-specific lifelong learning | Lifelong Learning | 否 | 持续学习扩展 |
| `task_3.csv` | 13.59 KiB | task-specific lifelong learning | Lifelong Learning | 否 | 持续学习扩展 |

## 3. Raw scenario files

### QK-video.csv

- 路径：`data/Tenrec/QK-video.csv`
- 大小：14.08 GiB
- 字段：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age
```

- 官方用途：raw video scenario。
- 本项目用途：暂不作为 MVP 起点；后续可用于验证 `ctr_data_1M.csv` 的 history / order 口径，或从 raw sequence 自建严格 order-based split。
- 风险 / 注意事项：文件大；没有预生成 `hist_1` 到 `hist_10`；需要额外构造 history。

### QB-video.csv

- 路径：`data/Tenrec/QB-video.csv`
- 大小：73.87 MiB
- 字段：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age
```

- 官方用途：Transfer Learning target dataset、Model Inference Speedup task。
- 本项目用途：暂不用于 MVP；后续适合做小场景迁移或快速验证。
- 风险 / 注意事项：场景规模较小，不代表 QK-video 主场景。

### QK-article.csv

- 路径：`data/Tenrec/QK-article.csv`
- 大小：4.47 GiB
- 字段：

```text
user_id,item_id,click,gender,age,exposure_count,click_count,like_count,comment_count,read_percentage,item_score1,item_score2,category_second,category_first,item_score3,read,read_time,share,like,follow,favorite
```

- 官方用途：raw article scenario。
- 本项目用途：不作为第一阶段 MVP 起点；后续可用于 article 排序或多行为任务。
- 风险 / 注意事项：字段与 video 场景不同；前 100,000 行抽样中 `click` 全为 `1.0`，不适合作为第一轮 CTR MVP 起点。

### QB-article.csv

- 路径：`data/Tenrec/QB-article.csv`
- 大小：19.71 MiB
- 字段：

```text
user_id,item_id,click,gender,age,exposure_count,click_count,like_count,comment_count,read_percentage,item_score1,item_score2,category_second,category_first,item_score3
```

- 官方用途：raw article scenario。
- 本项目用途：不作为 MVP 起点；后续可作为小 article 场景检查。
- 风险 / 注意事项：字段少于 `QK-article.csv`；前 100,000 行抽样中 `click` 全为 `1.0`。

## 4. Task-specific files

### ctr_data_1M.csv

- 路径：`data/Tenrec/ctr_data_1M.csv`
- 大小：9.94 GiB
- 字段：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age,hist_1,hist_2,hist_3,hist_4,hist_5,hist_6,hist_7,hist_8,hist_9,hist_10
```

- 官方用途：CTR task / Multi-Task Learning。
- 本项目用途：MVP 主候选。
- 本地全量 inspection：
  - total rows：120,342,306
  - unique `user_id`：999,447
  - unique `item_id`：2,310,087
  - `click=0`：91,461,446
  - `click=1`：28,880,860
  - bad width rows：0
  - 无显式 timestamp
  - target `item_id` 出现在同一行 `hist_1` 到 `hist_10` 的次数：0
- 本地 contract probe：
  - user block count：999,447
  - user 连续排列：是
  - user_id 单调：是
  - 完全重复行：883,646
  - 重复 `(user_id,item_id)`：1,810,484
  - 重复 pair 中 click 冲突：560,994
- 风险：
  - 文件名中的 `1M` 不是行数。
  - 没有 timestamp，不能做 timestamp-based split。
  - `hist_1` 到 `hist_10` 是否只来自 target event 之前仍需谨慎验证。
  - 存在重复和 click 冲突，不能在未定义口径前直接去重。
  - `video_category` 有 `\N`，后续 dataloader 需要明确 missing category 编码。

### sbr_data_1M.csv

- 路径：`data/Tenrec/sbr_data_1M.csv`
- 大小：1.04 GiB
- 字段：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age
```

- 官方用途：Session-based Recommendation、Transfer Learning pre-training、User Profile Prediction、Model Compression、Model Training Speedup。
- 本项目用途：后续 DIN/BST 或 sequence 对照可能参考。
- 为什么不是 MVP 起点：前 100,000 行抽样中 `click` 全为 `1`，更像序列正反馈任务，不适合作为第一阶段 click prediction 起点。

### cold_data*.csv

- 文件：
  - `cold_data.csv`
  - `cold_data_1.csv`
  - `cold_data_0.3.csv`
  - `cold_data_0.7.csv`
- 字段：

```text
user_id,item_id,click,gender,age,click_count,like_count,comment_count,read_percentage,item_score1,item_score2,category_second,category_first,item_score3,read,read_time,share,like,follow,favorite
```

- 官方用途：Cold-start task。
- 本项目用途：后续可选，不进 MVP。
- 注意事项：字段偏 article / cold-start 任务，和第一阶段 video CTR MVP 不同。

### task_0.csv ~ task_3.csv

- 官方用途：Lifelong Learning。
- 本项目用途：后续可选，不进 MVP。
- 字段：
  - `task_0.csv`：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age
```

  - `task_1.csv`：

```text
user_id,item_id,click,gender,age,read,share,like,follow,favorite
```

  - `task_2.csv`：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age
```

  - `task_3.csv`：

```text
user_id,item_id,click,gender,age
```

## 5. MVP 数据选择建议

第一阶段选择 `ctr_data_1M.csv`。

原因：

- 官方 CTR benchmark 使用该文件。
- 本地全量 inspection 已确认它包含 `click` 0/1、用户 / 物品 ID、多行为标签和 `hist_1` 到 `hist_10`。
- 它能支持第一阶段 LR、MLP、DeepFM、DCN-v2 的排序（Ranking）MVP。
- user block 连续排列，为后续 order-based / user-level split 探查提供基础。

不选择其他文件作为 MVP 起点的原因：

- raw video 文件需要先自行构造 history，初始成本更高。
- article 文件前 100,000 行抽样中 `click` 全为正，不适合作为第一轮 CTR 起点。
- `sbr_data_1M.csv` 更偏 session / sequence 任务，不是基础 CTR MVP。
- cold-start 和 lifelong learning 文件属于后续扩展任务。

## 6. 尚未解决的问题

- split 口径：没有 timestamp，当前不应写 timestamp-based split。
- history 构造：`hist_1` 到 `hist_10` 是否严格来自 target event 之前仍未证明。
- 去重 / 多次曝光：存在完全重复行、重复 `(user_id,item_id)` 和 click 冲突，暂不清洗，只记录。
- full data 与 smoke sample：下一步应生成 `ctr_tiny_100k_head.csv` 和保留 user block 的 `ctr_user_block_1m_seed20260525.csv`，但这些 sample 不能当正式实验结果。
