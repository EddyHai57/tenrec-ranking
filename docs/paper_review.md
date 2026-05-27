# Tenrec 论文与官方 benchmark 审阅

日期：2026-05-27

审阅对象：

- Paper: `Tenrec: A Large-scale Multipurpose Benchmark Dataset for Recommender Systems`
- Paper URL: https://papers.nips.cc/paper_files/paper/2022/file/4ad4fc1528374422dd7a69dea9e72948-Paper-Datasets_and_Benchmarks.pdf
- Official GitHub: https://github.com/yuangh-x/2022-NIPS-Tenrec
- Official CTR code: https://github.com/yuangh-x/2022-NIPS-Tenrec/blob/master/utils.py

本文件记录论文和官方代码对本项目方向的影响。它不是实验日志，不记录本项目训练指标。

## 1. 论文确认的核心事实

Tenrec 是 Tencent 与 Westlake University 等机构发布的 NeurIPS 2022 Datasets and Benchmarks 数据集。论文定位是 large-scale multipurpose benchmark dataset for recommender systems。

论文确认的关键事实：

- Tenrec 来自两个 Tencent feed recommendation app。
- 数据覆盖四个场景：`QK-video`、`QK-article`、`QB-video`、`QB-article`。
- 总体约 5 million users 和 140 million interactions。
- 包含真实负反馈（true negative feedback），即曝光但没有用户行为。
- 包含多种正向反馈：click、like、share、follow、read、favorite 等。
- 包含 user / item ID 之外的特征，例如 gender、age、video category。
- timestamp 被移除，但论文说明 interaction behaviors 按时间顺序呈现。

对本项目的影响：

- 选择 Tenrec 作为排序（Ranking）主数据没有问题。
- QK-video 作为第一阶段 CTR / click prediction 主场景是合理的。
- 多行为、多场景和真实负样本仍然支持后续扩展到 DIN/DIEN、MMOE/PLE 或 cross-domain / transfer learning。
- 由于 timestamp 被移除，本项目不能伪造 timestamp-based split，只能基于文件顺序和 user block 做可审计的 order-based split。

## 2. 官方 CTR benchmark 协议

论文 3.1 CTR Prediction 中，官方 CTR 任务使用 `QK-video-1M`：

- 随机抽取 1 million users。
- 保留全部正反馈。
- 按 positive:negative = 1:2 抽取真实负样本。
- 得到约 86,642,580 interactions。
- 使用 8:1:1 train / validation / test split。
- 特征包括 `user_id`、`item_id`、`gender`、`age`、`video_category` 和 user past 10 clicked items。

官方 GitHub README 的 CTR command 覆盖：

- `AFM`
- `DeepFM`
- `xDeepFM`
- `NFM`
- `Wide & Deep`
- `DCN`
- `DCNv2`
- `DIN`
- `DIEN`

官方 `utils.py` 的 `ctrdataset()` 进一步显示了代码级口径：

- 读取字段包含 `user_id`、`item_id`、`click`、`video_category`、`gender`、`age`、`hist_1` 到 `hist_10`。
- 调用 `sample_data(df)` 进行负采样。
- 对 `click` 和所有 sparse features 使用 `LabelEncoder().fit_transform()`。
- 最后使用 `train_test_split(df, test_size=0.1)` 得到 train / test。

官方 `sample_data()` 代码显示：

- `click == 1` 的正样本全部保留。
- `click == 0` 的负样本采样数量为正样本数量的 2 倍。
- 采样后进行全局 shuffle。

## 3. 官方协议与本项目协议的差异

| 维度 | 官方 benchmark | 本项目 strict protocol |
| --- | --- | --- |
| 负样本 | 1:2 下采样 | 不采样，保留原始 click 分布 |
| split | 官方论文写 8:1:1；代码中 `ctrdataset()` 为随机 train/test split | user 内文件顺序 80/10/10 |
| vocab | 官方代码对全量 df 做 `LabelEncoder().fit_transform()` | train-only vocab，valid/test unseen 映射 OOV |
| history | 官方直接使用 `hist_1..hist_10` | MVP 暂不使用，待确认构造口径 |
| metric | 官方主要报告 AUC / LogLoss | AUC / GAUC / LogLoss，并报告 GAUC coverage |
| 目标 | benchmark 对比 | 可审计实验工程和面试可解释性 |

关键判断：

- 官方 benchmark 更适合复现论文结果和做模型动物园横向对比。
- 本项目 strict protocol 更适合证明数据处理、split、OOV 和 metric 没有明显泄漏。
- 不能把官方 AUC 直接拿来对比本项目 strict protocol 的 AUC，因为数据分布、采样、split 和 vocab 口径不同。

## 4. 对“数据是否有缺陷”的判断

当前判断：不需要大改方向。

更准确的说法是：

- Tenrec 数据本身仍然适合本项目。
- 官方 CTR benchmark 协议为了模型比较和计算成本做了简化。
- 这些简化包括负采样、随机切分、全量编码和直接使用 history 字段。
- 这些做法对论文 benchmark 不一定是错误，但不适合直接作为本项目“可审计排序工程”的唯一协议。

本项目更有价值的叙事不是“复刻官方最高指标”，而是：

> 在 Tenrec 官方 benchmark 基础上，审计并重构 CTR 排序实验协议：使用 train-only vocab、user-order split、真实负样本分布和 GAUC coverage，区分可复现 benchmark 分数与更接近工业评估纪律的 strict protocol。

## 5. 对模型路线的影响

MVP 路线不变：

```text
LR -> MLP -> DeepFM -> DCN-v2
```

需要补充的低成本方向：

- `Wide & Deep`：官方 CTR baseline 之一，工程成本低，适合作为 DeepFM 前的对照。
- `NFM` / `AFM` / `xDeepFM`：可以作为 MVP+ 特征交互扩展，但不应阻塞 DeepFM / DCN-v2。

需要重新评估但不立即纳入 MVP 的方向：

- `DIN` / `DIEN`：官方直接使用 `hist_1..hist_10`，说明该字段至少是官方 CTR 任务的一部分。我们可以把 DIN/DIEN 作为强 MVP+，但在使用前仍需确认 history 构造是否符合本项目 strict protocol。
- `MMOE` / `PLE`：论文多任务部分使用 click / like 等多目标，支持我们后续做 multi-task learning 的方向。但多任务不是当前服务器前阻塞项。
- `SASRec` / `BERT4Rec` / `GRU4Rec` / `NextItNet`：更适合 `sbr_data_1M.csv` 或 raw sequence 任务，不应混入第一阶段 CTR MVP。

## 6. 推荐后的项目双协议

后续建议保留两套协议，而不是二选一：

### A. Strict Auditable Protocol

这是本项目主协议。

- 不做负采样。
- 使用 user 内文件顺序 split。
- vocab 只用 train 构建。
- valid/test unseen 映射 OOV。
- 使用 AUC、GAUC、LogLoss。
- GAUC 必须报告 coverage。
- `hist_*` 在验证前不进入 MVP baseline。

用途：

- 项目主线。
- 简历和面试叙事。
- 证明本项目不是只复刻 benchmark，而是理解评估泄漏和数据契约。

### B. Official-Compatible Reproduction Protocol

这是对照协议，不替代主协议。

- 按官方 1:2 negative sampling。
- 复现官方随机切分和全量编码口径。
- 先在 sample 上复现流程，再考虑服务器上跑更大规模。
- 结果必须标注为 official-compatible，不与 strict protocol 直接比较。

用途：

- 对齐论文 table 和官方模型动物园。
- 解释为什么官方指标和本项目指标不同。
- 形成一个很强的 ablation：同一数据，不同评估纪律，结果和解释完全不同。

## 7. 当前需要保持的边界

- 不因为官方代码使用随机 split，就改掉本项目主协议。
- 不因为官方代码全量 `LabelEncoder`，就放弃 train-only vocab。
- 不因为官方代码使用 `hist_*`，就立即把 history 加进 MVP baseline。
- 不把官方 benchmark AUC 写成本项目已达到的结果。
- 不把 strict protocol 的低指标解释成模型失败，必须先确认协议差异。

## 8. 下一步建议

已完成：

- `decision_log.md` 已固化“双协议”方向：strict protocol 为主，official-compatible reproduction 为对照。
- `data_notes.md` 已增加官方 CTR benchmark 协议说明，避免后续误用官方指标。

建议和 Opus 讨论后再决定是否开工以下任务：

1. 设计 `official_ctr_smoke.yaml`，但先不跑 full，只在小样本验证采样 / split / full-encoder reproduction。
2. 等 strict LR / MLP / DeepFM / DCN-v2 跑通后，再决定是否实现 official-compatible DeepFM/DCNv2 对照。
3. 在使用 `hist_1..hist_10` 前，单独做 history audit，并把结论写进 `data_notes.md`。

## 9. 面试叙事价值

这次论文审阅带来的面试价值很高：

- 能说明为什么选择 Tenrec，而不是 Criteo 或纯 implicit feedback 数据集。
- 能指出官方 benchmark 协议和更严格工程评估协议之间的差异。
- 能解释负采样为什么会改变 base rate 和 LogLoss calibration。
- 能解释 train-only vocab 为什么能避免 valid/test 信息泄漏。
- 能解释随机切分和 user-order split 的指标不可直接比较。
- 能把模型路线从“堆模型”讲成“先验证数据契约，再做特征交互，再做用户兴趣和多任务”。
