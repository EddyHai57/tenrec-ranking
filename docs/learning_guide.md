# Tenrec 推荐排序项目学习指南

本文是给 Eddy 自己学习、复盘、面试准备和后续写简历用的教学文档。它不追求像 README 那样短，而是尽量把“我们做了什么、为什么这么做、遇到什么问题、怎么解决、面试如何讲”讲清楚。

重要边界：

- 本文只写已经在本地验证过的事实。
- 本文会明确区分 `smoke`、`tiny`、`large-subset`、`full`。
- 目前所有模型指标都不是正式 full-data 结果，不能直接写成最终简历指标。
- 未来 DeepFM、DCN-v2、DIN/BST、MMOE/PLE 还没有完成，不能写成已完成成果。

## 1. 项目一句话介绍

这个项目叫：

```text
Tenrec 多行为推荐排序系统
```

一句话解释：

```text
基于腾讯 Tenrec feed 数据，构建一个可审计、可复现的推荐排序（Ranking）实验工程，从数据契约、特征编码、指标验证，到 LR/MLP/DeepFM/DCN-v2 等排序模型逐步推进。
```

这里的关键词是：

- 推荐排序（Ranking）
- CTR prediction
- 多行为数据
- 可审计实验工程
- 简历和面试可讲清楚

### 它和 Amazon Two-Tower 项目的区别

你之前的 Amazon Two-Tower 项目偏召回层（Retrieval）。

召回层的目标是：

```text
从海量 item 中快速找出一批候选 item。
```

典型方法包括：

- Two-Tower
- ItemCF
- 多路召回
- Faiss ANN

Tenrec 项目偏排序层（Ranking）。

排序层的目标是：

```text
对召回来的候选 item 做精排，预测用户点不点击、喜不喜欢、会不会分享或关注。
```

典型方法包括：

- LR
- MLP
- DeepFM
- DCN-v2
- DIN/BST
- MMOE/PLE

所以这两个项目是互补的：

| 项目 | 层级 | 核心问题 |
| --- | --- | --- |
| Amazon Two-Tower | Retrieval | 怎么快速找候选 item |
| Tenrec Ranking | Ranking | 怎么更准确地给候选 item 排序 |

面试时可以这样说：

```text
我做过召回和排序两个推荐系统项目。Amazon 项目重点是 Two-Tower 召回和 ANN 检索；Tenrec 项目重点是排序层的 CTR 预测、特征交互、多行为建模和实验审计。
```

## 2. 从 0 理解推荐排序

### 推荐系统为什么通常分两阶段

真实推荐系统面对的 item 数量非常大，可能是百万、千万甚至更多。如果每次用户打开 App，都对所有 item 跑一个复杂模型，会非常慢。

所以工业推荐通常拆成：

1. 召回（Retrieval）
2. 排序（Ranking）

召回阶段先粗略筛选：

```text
百万 item -> 几百或几千个候选 item
```

排序阶段再精细打分：

```text
几百个候选 item -> 按点击概率、转化概率、满意度等排序
```

本项目做的是排序层。

### CTR prediction 是什么

CTR 是 click-through rate，点击率。

CTR prediction 就是预测：

```text
用户 u 看到 item i 后，会不会点击？
```

在数据里通常表现为一个二分类任务：

```text
click = 1  表示点击
click = 0  表示曝光但未点击
```

模型输入是一组特征，例如：

- 用户 ID
- 物品 ID
- 视频类别
- 用户性别
- 用户年龄段

模型输出是一个概率：

```text
P(click = 1 | user, item, features)
```

比如：

```text
user_id = 100
item_id = 200
video_category = 1
gender = 1
age = 4
model output = 0.37
```

意思是模型认为这个用户点击这个 item 的概率约为 37%。

### 一行样本代表什么

在本项目中，一行样本定义为：

```text
一次 exposure-like row
```

也就是一次类似曝光的记录，而不是唯一的 `(user_id,item_id)`。

为什么要这样定义？

因为我们已经在 `ctr_data_1M.csv` 里验证到：

- 完全重复行：883,646 条
- 重复 `(user_id,item_id)`：1,810,484 条
- 重复 pair 中 click 冲突：560,994 条

这说明同一个用户和同一个 item 可能多次出现，而且 click 结果可能不同。

如果把 `(user_id,item_id)` 当成唯一键，会出问题：

```text
同一个 pair 有时 click=0，有时 click=1，无法简单合并成一条样本。
```

所以当前契约是：

```text
一行就是一条样本，不机械去重。
```

### 为什么真实负样本重要

很多推荐数据只有正反馈，例如：

```text
用户点击过 item A
用户买过 item B
用户收藏过 item C
```

这种数据很难知道用户“不喜欢什么”。没点过一个 item，可能是因为：

- 用户看到了但不喜欢
- 用户根本没看到
- 系统没推荐给他

Tenrec 的优势之一是包含真实负反馈（true negative feedback）。也就是：

```text
用户确实被曝光了，但没有点击。
```

这对排序任务很重要，因为 CTR 预测需要同时学习：

- 什么样的样本容易点击
- 什么样的样本曝光后不会点击

### 为什么不能只看 AUC

本项目 MVP 指标是：

- AUC
- GAUC
- LogLoss

它们关注的问题不一样。

#### AUC

AUC 衡量模型把正样本排在负样本前面的能力。

直觉例子：

```text
正样本分数普遍高于负样本 -> AUC 高
正负样本分数混在一起 -> AUC 接近 0.5
正样本分数反而低于负样本 -> AUC 低
```

AUC 适合看排序能力，但它没有直接告诉你概率准不准。

#### LogLoss

LogLoss 衡量概率预测是否校准。

如果真实 click=1，而模型只给 0.01，会被重罚。

如果真实 click=0，而模型给 0.99，也会被重罚。

CTR 项目很看重 LogLoss，因为线上系统经常需要用概率做：

- 排序分数
- 多目标融合
- 预估收益
- calibration

所以本项目明确规定：

```text
CTR baseline 不做 class reweighting，也不做正负样本重采样。
```

原因是 reweight 或 resampling 会改变概率含义，使 LogLoss 难以解释。

#### GAUC

GAUC 是 Group AUC，这里的 group 是 user。

普通 AUC 是把所有用户的样本混在一起算。GAUC 是先按用户算 AUC，再按曝光数加权平均。

本项目使用 impression-weighted GAUC：

```text
GAUC = sum(user_auc * user_impressions) / sum(user_impressions)
```

为什么选曝光数加权，而不是每个用户等权？

因为当前任务是曝光级 CTR prediction。曝光多的用户贡献了更多训练和评估样本，如果完全用户等权，一个只有 2 条 valid 样本的用户会和一个有 200 条 valid 样本的用户权重相同，指标方差会更大。曝光加权的 GAUC 更接近“模型在所有有效曝光上的用户内排序能力”。代价是活跃用户影响更大，所以后续做诊断时仍然需要看用户活跃度分桶。

为什么要 GAUC？

因为推荐系统真正关心的是：

```text
对每个用户，模型能不能把他会点击的 item 排在不会点击的 item 前面？
```

但是 GAUC 有一个坑：

如果某个 user 在 valid split 里全是 click=0，或者全是 click=1，那么这个 user 的 AUC 没有定义。

所以本项目规定：

```text
GAUC 跳过 only-positive / only-negative user，并且必须同时报告 coverage。
```

如果只报 GAUC，不报 coverage，就可能误导。

例如 1M sample 的 split feasibility 中：

- valid GAUC row coverage：0.87316891
- test GAUC row coverage：0.82024487

这表示 GAUC 不是覆盖全部行的指标。

## 3. Tenrec 数据集介绍

### 数据来源

Tenrec 来自腾讯 feed recommendation 场景。官方材料描述它包含：

- 多场景
- 多行为反馈
- 真实负样本
- 用户和物品特征
- 匿名化处理

本项目确认过的官方来源包括：

- Tenrec official website
- Tenrec official GitHub repository
- Official dataset download page
- Tenrec paper

### 本地数据文件

本地数据解压在：

```text
D:\ANU\project\tenrec-ranking\data\Tenrec
```

`data/` 被 `.gitignore` 排除，不进入 git。

本项目第一阶段优先使用：

```text
data/Tenrec/ctr_data_1M.csv
```

注意，这个文件名有误导性。

我们全量流式 inspection 后发现：

```text
total rows = 120,342,306
```

也就是说它不是字面意义上的 1M 行，而是 1.2 亿行级别的 CTR 文件。

### `ctr_data_1M.csv` 的字段

表头是：

```text
user_id,item_id,click,follow,like,share,video_category,watching_times,gender,age,hist_1,hist_2,hist_3,hist_4,hist_5,hist_6,hist_7,hist_8,hist_9,hist_10
```

字段解释如下。

#### `user_id`

用户 ID，已经匿名化。

本项目发现：

```text
unique user_id = 999,447
```

文件中 `user_id` 是连续分块排列的，并且数值单调。

这件事很重要，因为它让我们可以做 user 内顺序 split。

#### `item_id`

物品 ID，在 QK-video 场景中可以理解为视频 ID。

本项目发现：

```text
unique item_id = 2,310,087
```

item 数量很大，所以 ID embedding 和 OOV 处理是必须考虑的。

#### `click`

点击标签。

分布：

```text
click=0: 91,461,446
click=1: 28,880,860
```

正样本率约 24%。

当前 MVP 的主任务就是预测 `click`。

#### `follow / like / share`

这些是多行为标签。

它们未来可以用于多任务学习（multi-task learning），例如 MMOE / PLE。

但在当前单任务 click prediction baseline 中，它们不能作为输入特征。

原因：

```text
follow / like / share 本身是用户反馈标签，把它们作为 click 输入容易造成 label leakage。
```

所以当前处理是：

```text
暂不使用 follow / like / share 作为输入。
```

#### `video_category`

视频类别。

全量统计：

```text
0: 64,475,979
1: 54,277,815
\N: 1,588,512
```

这里的 `\N` 是 missing，不是 OOV。

本项目统一编码：

```text
0 = OOV
1 = missing
2.. = train seen values
```

所以 `video_category=\N` 会被编码成 missing index 1。

#### `watching_times`

观看次数或观看相关行为。

它可能发生在曝光或点击之后，所以有 post-exposure / post-click leakage 风险。

当前 MVP 不使用它。

面试时可以说：

```text
我没有为了提升指标直接把 watching_times 放进特征，因为它可能是目标事件之后才产生的行为，会造成泄漏。
```

#### `gender / age`

用户侧特征。

全量 inspection 中没有发现 `\N` 缺失。

当前 MVP 把它们作为 categorical feature 编码。

#### `hist_1..hist_10`

历史行为序列字段。

它们很适合未来做 DIN / BST。

但当前不使用。

原因是：

- target item 没有出现在同一行 history 中，这是一个好信号。
- 但 sampled history items 没有出现在该文件此前同 user 行里。
- 这说明 `ctr_data_1M.csv` 可能是 task-specific 文件，不一定保留完整原始行为序列。
- 目前还不能证明 `hist_*` 严格只来自 target event 之前。

所以当前结论是：

```text
hist_* 暂不进入 MVP baseline，等泄漏验证后再考虑 DIN/BST。
```

## 4. 第一轮数据探查做了什么

### 全量流式 inspection

由于 `ctr_data_1M.csv` 约 9.94 GiB，不能简单用 pandas 一次性读入。

我们写了流式 inspection 脚本，用 Python 标准库 `csv` 一行一行扫描。

验证结果：

```text
size bytes: 10,670,097,636
size GiB: 9.9373
total rows: 120,342,306
bad width rows: 0
unique user_id: 999,447
unique item_id: 2,310,087
```

这一步解决了一个核心问题：

```text
文件名里的 1M 不能理解成 1M 行。
```

### user block 连续性检查

我们检查了 user 是否连续排列。

结果：

```text
user block count: 999,447
non-contiguous user count: 0
user_id monotonic violations: 0
```

这说明：

```text
同一个 user 的行在文件中是连续的。
```

这个事实支撑了后续 user 内顺序 split。

### 重复行、重复 pair 和 click 冲突

全量 probe 发现：

```text
完全重复行: 883,646
重复 (user_id,item_id): 1,810,484
重复 pair 中 click 冲突: 560,994
```

这说明：

```text
(user_id,item_id) 不能作为唯一样本键。
```

如果机械去重，可能会错误删除真实曝光，也可能把 click=0 和 click=1 的冲突样本强行合并。

所以当前数据契约明确：

```text
不去重。
一行样本 = 一次 exposure-like row。
```

### 无 timestamp 的影响

`ctr_data_1M.csv` 没有显式 timestamp 字段。

这意味着我们不能做严格的 timestamp-based split。

如果硬说做了时间切分，是不诚实的。

当前采用的是：

```text
user 内文件顺序 split
```

理由：

- Readme 说明 item 在 user level 按 click time 排序。
- 文件中 user block 连续。
- 但没有显式 timestamp，所以必须把它叫 order-based split，而不是严格 timestamp split。

### `hist_*` 泄漏风险

我们检查过 target item 是否出现在同一行 history：

```text
target item in history count: 0
```

这是正向信号。

但不能证明没有未来信息泄漏。

因为 sampled history items 没有出现在该文件此前同 user 行里。这说明 `ctr_data_1M.csv` 可能不是完整原始序列，而是官方预处理后的任务文件。

所以当前不把 `hist_*` 用进 baseline。

这是一个很重要的面试点：

```text
我没有看到 hist 字段就直接上 DIN/BST，而是先检查它是否可能引入未来信息。
```

### `video_category=\N` missing 处理

`video_category` 存在 `\N`：

```text
\N: 1,588,512
```

我们没有把它和 OOV 混在一起。

原因：

- missing 是原始数据中明确存在的缺失状态。
- OOV 是 valid/test 或未来数据中 train 没见过的新值。

所以统一编码：

```text
0 = OOV
1 = missing
2.. = seen
```

## 5. 数据契约是什么，为什么重要

数据契约就是：

```text
在写模型前，把样本、label、split、feature、OOV、missing、metric 的口径全部固定下来。
```

它的价值是防止后续出现：

- 本地和服务器口径不一致
- valid/test 泄漏进 train
- smoke 指标被误当正式指标
- 模型训练结果无法复现
- 面试时解释不清楚

### 当前 MVP 数据契约

任务：

```text
click prediction
```

label：

```text
click
```

输入特征：

```text
user_id
item_id
video_category
gender
age
```

暂不使用：

```text
watching_times
hist_1..hist_10
follow
like
share
```

### split 公式

每个 user block 内保持原始文件顺序。

如果某个 user 有 N 行：

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

例如：

| N | train | valid | test |
| ---: | ---: | ---: | ---: |
| 1 | 1 | 0 | 0 |
| 2 | 2 | 0 | 0 |
| 3 | 1 | 1 | 1 |
| 7 | 5 | 1 | 1 |
| 10 | 8 | 1 | 1 |
| 100 | 80 | 10 | 10 |

1M user-block sample 上复现 oracle：

```text
train: 807,282
valid: 96,459
test: 96,459
```

这个 oracle 后来用共享 split 函数重新跑过，确认没有因为重构产生口径漂移。

### train-only vocab

词表只能用 train split 构建。

不能用全文件建 vocab。

原因：

如果用全文件建 vocab，valid/test 中出现过的 item 会提前进入词表。

这属于信息泄漏。

正确流程是：

```text
train 行出现过 -> seen index
train 行没出现过 -> valid/test 编码成 OOV
```

### OOV 和 missing 编码

统一约定：

```text
0 = OOV
1 = missing
2.. = seen values
```

这个约定适用于：

- `user_id`
- `item_id`
- `video_category`
- `gender`
- `age`

为什么所有字段都保留 missing 槽？

因为统一规则比逐字段特殊处理更不容易写错。

哪怕 `gender` 和 `age` 当前没有 missing，也保留 index 1。

### OOV 率不是固定数据属性

早期 1M sample 中：

```text
valid item OOV rate: 0.30998672
test item OOV rate: 0.30694255
```

这看起来像 30% item OOV。

但后来 10M sample 验证：

```text
valid item_id OOV rate: 0.04797363053280517
test item_id OOV rate: 0.04957866538291546
```

这说明：

```text
OOV 率依赖训练覆盖度。
```

小样本 train 覆盖 item 少，所以 OOV 高。

样本变大后 train 见过的 item 增多，所以 OOV 下降。

全量 120M 下，ID embedding 的 OOV 压力预计会比小样本低很多。

但是 OOV 机制仍然必须保留，因为线上或未来数据永远可能出现 train 未见 item。

### 冷启动和 OOV 后续怎么处理

当前 MVP 的 OOV 处理是：

```text
train 未见值 -> OOV index 0
```

这能保证 valid/test 不泄漏，但它不是冷启动问题的完整解法。真实系统里，新 item、新 user 和长尾 item 会持续出现，后续可以考虑：

- hashing trick：把未登录词表的大量 ID hash 到固定数量的 bucket，降低纯 OOV 槽的信息损失。
- 内容或属性 fallback：item ID 未见时，依赖 `video_category`、文本、图像、作者、发布时间等属性特征。
- 用户画像 fallback：user ID 未见时，依赖 `gender`、`age`、设备、地域、近期行为等非 ID 特征。
- ID2vec / item embedding warm start：用召回侧共现、序列、内容或图结构预训练 item 表征，再给排序模型初始化。

面试时不要把当前 OOV 槽说成“解决了冷启动”。准确说法是：

```text
当前实现了防泄漏的 OOV 机制；冷启动需要进一步引入属性、内容或预训练表征。
```

### 特征工程：现在少，不代表最终只做这些

当前 MVP 只使用：

```text
user_id
item_id
video_category
gender
age
```

这是有意收窄范围。第一阶段重点是把数据契约、split、vocab、metrics 和训练入口打通，而不是一开始堆很多高风险特征。

CTR 面试里常见的特征工程方向包括：

- 统计 / 计数特征：例如 user 历史曝光数、user 历史点击数、item 历史曝光数、item 历史点击数。
- 历史 CTR 特征：例如 `item_click_count / item_exposure_count`、`user_click_count / user_exposure_count`。
- 分桶特征：例如 item 热度分桶、user 活跃度分桶、年龄段和类别组合分桶。
- 特征交叉：例如 `gender x video_category`、`age x video_category`、`user_activity_bucket x item_popularity_bucket`。
- target encoding：用历史 label 统计给类别值编码，例如某个 category 的历史点击率。

这些特征的最大风险是泄漏。

错误做法：

```text
用全量数据统计 item CTR，再把这个 CTR 喂给 train/valid/test。
```

这样 valid/test 的 label 已经参与了特征构造，指标会虚高。

正确做法必须遵守时间或顺序边界：

```text
每一行样本的统计特征，只能使用这行之前已经发生的数据。
```

在本项目里，因为没有显式 timestamp，后续如果做统计特征，至少要按 user block / 文件顺序或更保守的 split 规则构造：

- train 特征只能由 train 内前序样本累积。
- valid 特征只能使用 train 和 valid 内当前行之前的样本。
- test 特征只能使用 train、valid 和 test 内当前行之前的样本。

更严格的方案是等拿到可靠时间字段或能重建全局事件顺序后，再做全局历史统计特征。

面试时可以这样回答“你的特征工程就这些吗？”：

```text
当前 MVP 先用 ID/profile 特征验证防泄漏数据链路。统计 CTR、热度、活跃度和交叉特征是后续方向，但这类特征必须按 target event 之前的数据构造，不能用全量 label 做 target encoding，否则会泄漏。
```

## 6. 两遍流式预处理 Pipeline

### 为什么不能 pandas 全量 load

`ctr_data_1M.csv` 有：

```text
120,342,306 行
约 9.94 GiB
```

如果用 pandas 一次性读入：

- 原始 CSV 会膨胀成内存对象
- 字符串列会占大量内存
- 本地容易爆内存
- 服务器 full preprocessing 也不稳

所以本项目采用流式读取。

### 为什么不能边扫边编码

一开始可能会想：

```text
读一行 -> split -> 建 vocab -> 编码 -> 写出
```

但这是错的。

原因：

```text
valid/test 的 OOV 判定必须基于完整 train vocab。
```

如果边扫边编码，早期 user 的 valid 行可能遇到一个 item，此时这个 item 还没在后续 user 的 train 行中出现。

你会把它错误编码成 OOV。

但完整 train 扫完后，它其实可能是 seen item。

所以必须两遍：

```text
Pass 1: 扫描全文件，只从 train 行建 vocab
Pass 2: 冻结 vocab，再编码 train/valid/test
```

### Pass 1 做什么

Pass 1：

```text
读取原始 CSV
按 user block 切分 train/valid/test
只看 train 行
把 train 行中的 user_id/item_id/video_category/gender/age 加入 vocab
```

Pass 1 不写训练数据。

它只负责确定：

```text
哪些值是 train seen values
```

### Pass 2 做什么

Pass 2：

```text
再次读取原始 CSV
使用同一个 split 函数
用冻结 vocab 编码
写出 train.csv / valid.csv / test.csv
```

物化输出在：

```text
outputs/preprocessed/{run_id}/materialized/
```

### 输出文件的作用

一次 preprocessing 产生：

```text
metadata.json
vocabs/
materialized/train.csv
materialized/valid.csv
materialized/test.csv
```

#### `metadata.json`

记录：

- run_id
- input_path
- input_size_bytes
- config
- split rule
- reserved indices
- vocab sizes
- OOV counts
- missing counts
- git commit

训练脚本不应该猜测 vocab size，而应该从 metadata 读。

#### `vocabs/`

保存每个字段的词表。

例如：

```text
user_id.json
item_id.json
video_category.json
gender.json
age.json
```

这保证本地和服务器可以复现同样的编码。

#### `materialized/*.csv`

模型训练直接读这些编码后的文件，而不是重新读 raw CSV。

这样可以保证：

```text
所有模型消费同一套 split、vocab、OOV/missing 口径。
```

### G1 10M 内存验证

为了验证两遍流式预处理不会在大样本上爆内存，我们做了 G1。

生成 10M user-block sample：

```text
data/samples/ctr_user_block_10m_seed20260525.csv
rows: 10,000,035
users: 82,761
file size bytes: 886,528,483
```

预处理结果：

```text
run_id: ctr-1961cdee479f
peak RSS: 136.68 MiB
Pass1 elapsed: 38.223s
Pass2 elapsed: 71.914s
```

1M 对照：

```text
peak RSS: 54.77 MiB
```

结论：

```text
10M 行数约为 1M 的 10 倍，但 peak RSS 没有接近 10 倍增长。
```

内存增长主要来自 vocab 条目增加，而不是保存全部行。

这说明当前没有发现 hidden full-file buffer。

但 full 120M 仍需在服务器上验证。

## 7. 指标体系

### AUC

AUC 衡量排序能力。

如果模型给点击样本更高分、未点击样本更低分，AUC 就高。

本项目写了 `binary_auc`，并用 known-answer 测试：

- 完美预测 -> AUC = 1.0
- 反向预测 -> AUC = 0.0
- 常数预测 -> AUC = 0.5

为什么要 known-answer？

因为指标函数如果写错，模型结果就没有意义。

### LogLoss

LogLoss 衡量概率校准。

CTR 排序不只是要排对，还要概率尽量准。

所以本项目：

- 不做 class reweighting
- 不做正负样本重采样
- 用普通 BCE / BCEWithLogitsLoss

这样 LogLoss 更容易解释。

### PCOC / COPC

工业 CTR 里还常看校准比值，例如 PCOC 或 COPC。不同团队命名会不同，核心都是比较：

```text
预测 CTR 总和 / 真实 CTR 总和
```

一种常见写法是：

```text
PCOC = sum(predicted_ctr) / sum(label)
```

如果 PCOC 接近 1，说明整体预估点击数和真实点击数接近。

如果 PCOC 明显大于 1，说明模型整体高估 CTR。

如果 PCOC 明显小于 1，说明模型整体低估 CTR。

本项目当前 MVP 指标先固定为 AUC / GAUC / LogLoss，PCOC 还没有实现。它是后续校准诊断的自然补充，尤其适合在服务器 large/full run 后和 LogLoss 一起看。

### GAUC

GAUC 按 user 分组。

它比普通 AUC 更贴近推荐场景。

但 GAUC 有一个常见坑：

```text
只有正样本或只有负样本的 user，AUC 没有定义。
```

所以本项目跳过这些 user，并报告：

- valid GAUC user count
- total user count
- valid GAUC row count
- total row count
- row coverage rate

面试时可以这样说：

```text
我没有只报 GAUC 数字，因为 GAUC 会跳过单类用户。如果不报 coverage，就不知道这个 GAUC 覆盖了多少样本。
```

## 8. 模型与训练目前做到哪一步

### sklearn LR learnability gate

在 torch 模型之前，我们先用 sklearn LR 做 learnability smoke。

目的不是拿正式指标，而是验证：

- label 没反
- split 可用
- feature encoding 可用
- metric 可用
- pipeline 有可学习信号

1M user-block sample 上，使用物化编码数据：

```text
train rows: 100,000
valid rows: 50,000
train AUC: 0.8866438867118259
valid AUC: 0.6283948058203263
valid GAUC: 0.6032205118880077
valid GAUC coverage: 0.89796
```

注意：

```text
这不是正式模型结果，只是 learnability gate。
```

### torch LR

torch LR 是真正的线性模型。

实现是：

```text
logit = bias + sum(field_scalar_lookup[field_value])
```

每个 categorical field 是：

```text
[vocab_size, 1]
```

也就是每个取值对应一个标量权重。

为什么不能用 `embedding_dim=16`？

因为 LR 是线性模型。如果给 LR 用 16 维 embedding，再接其他层，它就不是严格的 LR 了。

面试时可以说：

```text
我把 LR 写成每个离散特征取值对应一个 scalar weight，然后求和加 bias。这样它才是 ID 特征上的线性 baseline。
```

LR overfit gate：

```text
initial_loss: 0.6931471824645996
final_loss: 0.02680760808289051
target_loss: 0.05
passed: true
```

LR train smoke：

```text
valid LogLoss: 0.5508678869033629
valid AUC: 0.677162416436456
valid GAUC: 0.599984004757329
GAUC coverage: 0.89796
```

这些仍是 smoke，不是正式 full-data 指标。

### torch MLP

torch MLP 使用：

```text
embedding + MLP
```

也就是每个 categorical feature 先查 embedding，再拼接后送入多层感知机。

MLP overfit gate：

```text
initial_loss: 0.6972130537033081
final_loss: 0.00024013200891204178
target_loss: 0.05
passed: true
```

这说明：

```text
forward / loss / backward 基本没有硬 bug。
```

但 MLP valid GAUC 较低。

G2 复跑后记录 train/valid AUC：

| epoch | train AUC | valid AUC |
| ---: | ---: | ---: |
| 1 | 0.5435437311355459 | 0.5197096996237808 |
| 2 | 0.5760376017930043 | 0.534898682748413 |
| 3 | 0.6065873845344981 | 0.543106674284724 |
| 4 | 0.6404150352231401 | 0.5535725552237716 |
| 5 | 0.6758640335529477 | 0.5641194888327414 |

判别：

- train AUC 持续上升
- valid AUC 也上升但更低
- train AUC 没达到强过拟合判据 `>0.75`
- 但也不是完全学不动

结论：

```text
当前更像 head-truncated smoke 配置下未充分学习 + 泛化弱，而不是 embedding/forward/backward 硬 bug。
```

所以 MLP smoke 不阻塞上服务器，但不能写成正式模型结论。

### `train.py` 一条命令流程

当前训练入口是：

```text
scripts/train.py
```

它的流程：

1. 读取 config
2. 读取 `metadata.json`
3. 从 metadata 获取 feature list 和 vocab size
4. 读取物化后的 `train.csv` / `valid.csv`
5. 训练模型
6. 计算 valid AUC / GAUC / LogLoss
7. 写 `metrics.jsonl`
8. 保存 `checkpoints/best.pt`
9. 写 `summary.json`

训练命令示例：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\torch_lr_smoke.yaml --device cpu
```

服务器上可通过 `--metadata` 覆盖 metadata 路径：

```bash
python scripts/train.py --config configs/torch_lr_smoke.yaml --metadata outputs/preprocessed/<run_id>/metadata.json --device auto
```

这是为了避免写死本地 run_id。

### deterministic hash-bucket shuffle

物化 `train.csv` 是按 user 排列的。

如果直接训练，同一个 user 的样本会连续进入 batch。

这会导致 batch 梯度相关性高，影响 SGD。

我们没有使用小 `shuffle_buffer_size`，因为小 buffer 只打散局部窗口。

当前做法是生成 deterministic hash-bucket shuffled train file。

本地生成过：

```text
outputs/preprocessed/ctr-454e7ccb12f7/materialized/train_shuffled_seed20260525_b16.csv
```

这里的 `b16` 表示：

```text
bucket_count = 16
```

实现思路是：

1. 流式读取 `train.csv`，不把全量 train 读进内存。
2. 对每一行计算稳定 hash，hash 输入包括 `seed`、行号和该行字段值。
3. 用 `hash % bucket_count` 决定这行写入哪个临时 bucket 文件。
4. 用固定 `seed` 打乱 bucket 的读取顺序。
5. 对每个 bucket 内的行再用固定 `seed + bucket_id` 打乱。
6. 拼接所有 bucket，得到一个确定性的 shuffled train file。

这个方法的目标是：

```text
用磁盘临时文件换取近似全局打散，同时避免全量 load 到内存。
```

它不是完美随机洗牌。bucket 内仍然要读入内存，所以 full run 时 `bucket_count` 要按服务器内存调整。如果 bucket 太少，单个 bucket 可能太大；如果 bucket 太多，临时文件数量和 I/O 开销会上升。

这个文件不进 git。

## 9. 后续模型原理：DeepFM 和 DCN-v2 先理解什么

DeepFM 和 DCN-v2 目前还没有实现。本节是学习和面试准备，不是已完成成果。

### 为什么 LR 和 MLP 不够

LR 能学到每个单独特征值的权重，例如：

```text
item_id=123 -> +0.8
video_category=1 -> +0.2
```

但 LR 不直接建模特征之间的组合关系，例如：

```text
age=4 且 video_category=1
user_id=100 且 item_id=200
```

MLP 可以隐式学习非线性组合，但它不显式告诉模型哪些二阶交叉很重要，而且在稀疏 ID 特征上可能需要更多数据和调参。

所以工业 CTR 模型常会强调：

```text
显式特征交叉 + 深层非线性表示
```

### FM：二阶交叉的基本思想

FM 是 Factorization Machine。

对两个离散特征 `i` 和 `j`，普通线性模型只学：

```text
w_i + w_j
```

FM 额外学习二阶交叉：

```text
<v_i, v_j>
```

这里 `v_i` 和 `v_j` 是两个特征值的 embedding，`< , >` 是内积。

直觉是：

```text
如果某个 user 特征和某个 item 特征经常一起导致点击，它们的 embedding 内积会变大。
```

FM 的好处是参数共享。它不需要给每一个 pair 单独学一个参数，而是让不同 pair 共享 embedding。

### DeepFM 是什么

DeepFM 可以理解为：

```text
FM part + deep part
```

FM part 负责显式二阶交叉：

```text
哪些 feature pair 有强交互？
```

deep part 负责高阶非线性表达：

```text
多个 feature 组合起来有什么复杂模式？
```

两部分通常共享同一套 feature embedding，最后把 FM logit 和 deep logit 加起来。

面试时可以这样讲：

```text
DeepFM 的价值在于同时保留 FM 的显式二阶交叉和 DNN 的高阶非线性表达，并且共享 embedding，适合稀疏 categorical feature 的 CTR 排序。
```

### DCN-v2 是什么

DCN 是 Deep & Cross Network。

它的 cross network 显式构造高阶特征交叉。简化理解：

```text
x_{l+1} = x_0 * f(x_l) + x_l
```

其中 `x_0` 是原始输入，`x_l` 是第 l 层 cross 表示。每一层都会把原始输入和当前表示再交叉一次。

DCN-v2 相比早期 DCN，通常使用更灵活的矩阵参数化和 mixture / low-rank 变体，表达能力更强。

和 DeepFM 的区别可以这样理解：

| 模型 | 重点 |
| --- | --- |
| DeepFM | FM 显式二阶交叉 + DNN 隐式高阶组合 |
| DCN-v2 | Cross Network 显式构造多阶交叉 + Deep Network |

面试时不要只说“我用了 DCN-v2”。更好的说法是：

```text
我希望用 DCN-v2 检验显式高阶 cross feature interaction 是否能在 Tenrec CTR 上超过 LR/MLP/DeepFM，尤其是在 ID、category、profile 等稀疏特征组合上。
```

## 10. 遇到的问题和解决方案

### 问题 1：`ctr_data_1M.csv` 名字误导

现象：

```text
文件名像 1M 行，实际有 120,342,306 行。
```

风险：

- 如果按 1M 行估计，会低估内存和时间成本。
- 可能错误使用 pandas 全量 load。

解决：

- 全量流式 inspection。
- 本地生成 100k / 1M / 10M sample 做开发验证。
- full run 放到服务器。

面试怎么讲：

```text
我没有直接相信文件名，而是先做了全量流式统计，确认这个 CTR 文件实际是 1.2 亿行级别。
```

### 问题 2：无 timestamp

现象：

```text
没有显式 timestamp 字段。
```

风险：

- 不能声称做了严格 timestamp-based split。
- 如果随机切分，可能出现同一 user 的未来行为泄漏到训练。

解决：

- 利用 user block 连续排列。
- 使用 user 内文件顺序 split。
- 文档中明确叫 order-based split，不伪装成 timestamp split。

### 问题 3：重复和 click 冲突

现象：

```text
重复 (user_id,item_id) 多，且存在 click 冲突。
```

风险：

- 机械去重会破坏样本语义。
- 把 `(user_id,item_id)` 当唯一键会错。

解决：

```text
不去重。一行样本定义为一次 exposure-like row。
```

### 问题 4：OOV 泄漏风险

现象：

valid/test 中有 train 未见 item。

风险：

如果全文件建 vocab，valid/test 的信息会泄漏到训练特征空间。

解决：

```text
train-only vocab
valid/test unseen -> OOV
```

并加不变量：

```text
valid/test user_id OOV 必须为 0
```

因为 user 内 split 下，valid/test 的 user 必然在 train 中出现。

### 问题 5：GAUC 单类用户

现象：

很多 user 在 valid/test 中只有正样本或只有负样本。

风险：

直接算 AUC 会报错，或者跳过后不报 coverage 会误导。

解决：

- 跳过单类 user
- 报 GAUC coverage
- 加 known-answer 单元测试

### 问题 6：Windows RSS 监控不可信

现象：

第一次用 Windows ctypes 监控 10M preprocessing，peak RSS 只有 4.574 MiB。

这个数明显不合理。

解决：

- 安装 `psutil==7.2.2`
- 用 psutil 统计主进程和子进程 RSS
- 重跑得到可信结果：136.68 MiB

### 问题 7：MLP valid GAUC 低

现象：

MLP smoke 的 valid GAUC 接近随机。

风险：

可能是：

- embedding / forward / backward 有 bug
- 或只是 head-truncated smoke 下学习不足

解决：

- 单 batch overfit gate：通过
- 复跑 G2，记录 train AUC 和 valid AUC

G2 结论：

```text
没有发现硬 bug，但 MLP 仍不能作为正式模型结论。
```

## 11. 当前成果与不能夸大的边界

### 已经完成

已经完成：

- repo 和文档骨架
- Tenrec 官方来源识别
- 本地 Python 环境
- 全量 schema inspection
- 数据契约 probe
- 100k / 1M / 10M sample
- user 内顺序 split
- train-only vocab
- OOV/missing 统一编码
- 两遍流式预处理
- AUC / LogLoss / GAUC
- metric known-answer tests
- sklearn LR learnability gate
- torch LR / MLP overfit
- torch LR / MLP train smoke
- G1 10M preprocessing memory check
- G2 MLP train-vs-valid AUC diagnostic
- server runbook DRAFT

### 尚未完成

尚未完成：

- full 120M preprocessing
- 服务器 Python / CUDA / Torch 环境验证
- full training
- large-subset 正式模型对比
- DeepFM
- DCN-v2
- DIN / BST
- MMOE / PLE
- `hist_*` 泄漏验证

### 哪些指标不能写成正式结果

不能把以下结果写成正式模型指标：

- sklearn LR smoke AUC
- torch LR smoke AUC / GAUC / LogLoss
- torch MLP smoke AUC / GAUC / LogLoss
- 100k / 1M / 10M sample 上的任何模型指标

它们可以写成：

```text
本地 smoke / learnability gate / pipeline validation
```

但不能写成：

```text
模型最终效果
正式 baseline
full-data result
线上效果
显著提升
```

## 12. 面试讲述模板

### 30 秒版本

```text
我在做一个基于 Tenrec 的推荐排序项目，目标是补齐召回项目之外的排序层能力。当前完成了 1.2 亿行 CTR 数据的流式探查，发现并处理了无 timestamp、重复曝光、click 冲突、OOV 和 GAUC 单类用户等数据契约问题；实现了 train-only vocab、OOV/missing 编码、user-order split、两遍流式预处理和 AUC/GAUC/LogLoss 指标，并用 sklearn LR 和 torch LR/MLP 在本地 smoke 中验证了 pipeline 可学习。后续会在服务器上做 full preprocessing 和 LR/MLP/DeepFM/DCN-v2 正式对比。
```

### 2 分钟版本

```text
这个项目定位是推荐系统排序层，和我之前的 Amazon Two-Tower 召回项目互补。Tenrec 数据来自腾讯 feed 推荐场景，有真实负样本和多行为标签，比较适合做 CTR、多任务和后续用户兴趣建模。

我没有一开始直接搭模型，而是先做数据契约。因为排序项目很容易在 split、label、OOV 和 metric 上埋雷。我对 ctr_data_1M.csv 做了全量流式 inspection，发现它实际有 1.2 亿行，不是 1M 行；没有显式 timestamp；user 是连续分块排列；同时存在重复行、重复 user-item pair 和 click 冲突。所以我把一行定义成一次 exposure-like row，不机械去重，并采用 user 内文件顺序 split。

在特征处理上，我实现了两遍流式预处理。第一遍只用 train 行建 vocab，第二遍冻结 vocab 后编码 train/valid/test，这样避免 valid/test 泄漏进词表。编码上统一 0=OOV、1=missing、2..=seen，并对 video_category 的 \N 单独作为 missing。指标上实现了 AUC、LogLoss 和 impression-weighted GAUC，GAUC 会跳过单类用户并强制报告 coverage。

模型层目前完成了 sklearn LR learnability gate 和 torch LR/MLP smoke。LR 是真正的 scalar lookup sum，不是 dense embedding；MLP 做了 overfit gate。为了确认预处理能扩展，我还做了 10M user-block 样本的内存验证，peak RSS 约 136.68 MiB，没有发现按行数线性爆内存。当前结果都是 smoke，不作为正式指标；下一步是在服务器上跑 full preprocessing 和正式 baseline 对比。
```

### 面试官追问 1：为什么不随机切分？

回答：

```text
因为推荐排序数据里同一个 user 会有多条行为。如果随机切分，同一个 user 的未来行为或相近曝光可能进入 train，导致 valid/test 泄漏。这个文件没有显式 timestamp，但 user block 连续且 Readme 说明 item 在 user level 按 click time 排序，所以我采用 user 内文件顺序 split，而不是随机切分。
```

### 面试官追问 2：为什么 train-only vocab？

回答：

```text
如果用全文件建 vocab，valid/test 中出现过的 item 会提前进入训练特征空间，这属于信息泄漏。正确做法是只用 train 行建 vocab，valid/test 没见过的值编码成 OOV。这个项目里 1M sample 的 valid item OOV 约 30%，10M 降到约 4.8%，说明 OOV 压力是训练覆盖度的函数，但机制必须保留。
```

### 面试官追问 3：为什么不去重？

回答：

```text
我检查到完全重复行有 883,646 条，重复 user-item pair 有 1,810,484 条，其中 click 冲突有 560,994 条。这说明 user-item pair 不是唯一样本键，可能代表多次曝光或预处理后的曝光记录。如果机械去重，会改变样本语义。所以当前契约是一行代表一次 exposure-like row，不去重，但在文档里记录重复可能带来的记忆风险。
```

### 面试官追问 4：为什么 GAUC 要 coverage？

回答：

```text
GAUC 是按 user 分组算 AUC。但有些 user 在 valid/test 里只有正样本或只有负样本，这类 user 的 AUC 没有定义，只能跳过。如果只报 GAUC，不报跳过了多少行，就会误导。所以我同时报告 valid user count、valid row count 和 row coverage。
```

### 面试官追问 5：为什么 LR 不能用 `embedding_dim=16`？

回答：

```text
LR 是线性模型。对离散 ID 特征来说，正确形式是每个 feature value 对应一个 scalar weight，然后所有 field 的权重求和加 bias。如果用 16 维 embedding 再接网络层，就不是严格的 LR baseline 了，模型对比也不清楚。所以我把 torch LR 实现成 [vocab_size,1] 的 scalar lookup sum。
```

### 面试官追问 6：为什么 MLP 目前不算正式结果？

回答：

```text
目前 MLP 只在 head-truncated smoke 上跑过。它的 overfit gate 通过，说明 forward/loss/backward 没有硬 bug；G2 中 train AUC 从 0.54 升到 0.68，valid AUC 到 0.56，说明能学习但泛化弱。这只能说明本地 pipeline 可运行，不能代表 full-data MLP 效果。正式结论要等服务器 large/full subset 训练。
```

### 面试官追问 7：你的特征工程就这些吗？

回答：

```text
当前 MVP 只用 user_id、item_id、video_category、gender、age，是为了先把防泄漏 split、train-only vocab、OOV/missing 和 metric 链路打通。后续会加 item/user 历史统计、热度、活跃度、CTR target encoding 和特征交叉。但这类统计特征必须只用 target event 之前的数据构造，不能用全量 label，否则 valid/test 会泄漏。
```

### 面试官追问 8：DeepFM 和 DCN-v2 分别解决什么？

回答：

```text
DeepFM 同时使用 FM part 和 deep part。FM part 用 embedding 内积显式建模二阶特征交叉，deep part 学高阶非线性组合。DCN-v2 的 cross network 则显式构造多阶 feature crossing，适合检验高阶交叉对 CTR 排序的贡献。它们都还不是当前已完成结果，而是 LR/MLP 后的正式 baseline 方向。
```

### 面试官追问 9：不全量 load，怎么 shuffle？

回答：

```text
我用 deterministic hash-bucket shuffle。流式读 train.csv，把每一行按 seed、行号和字段值 hash 到多个 bucket 临时文件；然后固定 seed 打乱 bucket 顺序，并在每个 bucket 内打乱后拼接。这样避免全量 train 进内存，同时缓解按 user 聚簇导致的 batch 相关性。
```

### 面试官追问 10：校准除了 LogLoss 还能看什么？

回答：

```text
可以看 PCOC，也就是预测 CTR 总和和真实点击总和的比值。PCOC 接近 1 说明整体预估点击量接近真实点击量，大于 1 是高估，小于 1 是低估。本项目当前先实现 AUC、GAUC、LogLoss，PCOC 是 full run 后要补的校准诊断。
```

## 13. 简历可写草稿

### 当前阶段保守版 bullet

可以写：

```text
基于 Tenrec 构建推荐排序实验工程，完成 1.2 亿行 CTR 数据的流式 schema inspection，识别无 timestamp、重复曝光、click 冲突、history 泄漏风险和 OOV 等数据契约问题；设计并实现 train-only vocab、OOV/missing 编码、user-order split、impression-weighted GAUC 与两遍流式预处理 pipeline，并通过 100k/1M/10M 本地 smoke 验证数据链路、指标和 torch LR/MLP 训练入口。
```

更偏工程版：

```text
实现可审计 CTR 排序数据层：基于 Tenrec 1.2 亿行曝光点击数据，构建两遍流式预处理、train-only vocab、防泄漏 split、OOV/missing 统一编码和 GAUC coverage 评估，并通过 10M user-block 样本验证预处理 peak RSS 约 136.68 MiB，未发现整文件 load。
```

更偏面试叙事版：

```text
从数据契约入手构建 Tenrec 排序系统，系统处理无 timestamp、重复 user-item、click 冲突、OOV 和 GAUC 单类用户等真实推荐数据问题；在本地完成 sklearn LR learnability gate 和 torch LR/MLP smoke，为服务器 full-data baseline 训练做准备。
```

### 服务器训练完成后的升级版占位

等服务器完成 large/full baseline 后，可以升级为：

```text
在 Tenrec 1.2 亿行 CTR 数据上完成 LR/MLP/DeepFM/DCN-v2 排序模型对比，使用 user-order split、train-only vocab、AUC/GAUC/LogLoss 和分桶诊断构建可复现实验流程。
```

注意：这句话现在还不能写，因为 DeepFM/DCN-v2 和 full training 尚未完成。

### 当前不能写的表述

不能写：

- “完成 DeepFM/DCN-v2”
- “完成 DIN/BST”
- “完成 MMOE/PLE”
- “线上 A/B 提升”
- “生产可用”
- “在 full 120M 上取得正式 AUC”
- “MLP/DeepFM 显著优于 LR”

这些都还没有验证。

## 14. 下一步学习路线

### 第一步：服务器前复盘

你应该先能讲清楚：

- 为什么做排序而不是召回
- 为什么选 Tenrec
- 为什么先做 click prediction
- 为什么不随机切分
- 为什么 train-only vocab
- 为什么不使用 `hist_*`
- 为什么 smoke 指标不能写成正式结果

### 第二步：full preprocessing

上服务器后先做：

```text
GitHub -> server
创建环境
确认 Python / CUDA / Torch
准备数据
跑 unit tests
跑 preprocessing smoke
跑 full preprocessing
```

不要一上来直接训练大模型。

### 第三步：torch LR / MLP large subset

先用 large subset 跑：

- LR
- MLP

目标不是追 SOTA，而是确认：

- full pipeline 能跑
- metrics 正常
- checkpoint 正常
- training curve 正常

### 第四步：DeepFM

DeepFM 用于特征交互。

它适合回答：

```text
只用 ID 和简单用户特征时，显式/隐式二阶交互是否能提升排序效果？
```

### 第五步：DCN-v2

DCN-v2 用于更强的 cross feature interaction。

它是 MVP 中比较有面试价值的模型，因为能体现：

- 特征交互意识
- 工业 CTR 模型理解
- 和 LR/MLP/DeepFM 的对比关系

### 第六步：DIN/BST

只有在 `hist_*` 泄漏验证通过，或者从 raw sequence 重新构造历史后，才进入 DIN/BST。

不要为了模型名字直接上序列模型。

### 第七步：MMOE/PLE

Tenrec 有 `click/like/share/follow` 多行为标签，所以未来适合做多任务学习。

但多任务不是 MVP 阻塞项。

应该在单任务 click baseline 稳定后再做。

## 15. 你现在应该掌握的核心句子

如果只能记住几句话，记这些：

```text
1. 这个项目不是刷榜，而是可审计的推荐排序实验工程。
2. ctr_data_1M.csv 实际有 1.2 亿行，所以必须流式处理。
3. 没有 timestamp，所以不能声称 timestamp split；当前是 user 内文件顺序 split。
4. 重复 user-item 和 click 冲突说明不能机械去重，一行定义为 exposure-like row。
5. vocab 只能用 train 建，否则 valid/test 信息会泄漏。
6. GAUC 必须报告 coverage，因为单类用户会被跳过。
7. OOV 率不是固定属性，1M 约 30%，10M 降到约 5%，全量预计更低。
8. LR 必须是 scalar lookup sum，不能用 dense embedding 冒充 LR。
9. 当前所有模型结果都是 smoke，不是正式 full-data 指标。
10. 下一步是服务器 full preprocessing 和正式 baseline 对比。
11. 统计 CTR、热度、活跃度和 target encoding 都必须按 target 之前的数据构造，否则会泄漏。
12. DeepFM 重点是 FM 二阶交叉 + DNN，高阶交叉会继续用 DCN-v2 验证。
13. 冷启动不能只靠 OOV 槽，后续需要属性、内容、hashing 或预训练表征。
```
