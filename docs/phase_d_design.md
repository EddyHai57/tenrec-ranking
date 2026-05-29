# Phase D 统计特征设计草案

本阶段目标是探索 leakage-safe statistical features 是否能补足当前 5 个 ID/profile 特征空间。所有结果先停留在 1M smoke，不进入 full preprocessing，不作为正式结论。

## 1. 特征清单

高 ROI：

- `item_hist_ctr`：item 历史点击率，来自过去点击数 / 过去曝光数。
- `user_hist_ctr`：user 历史点击率。
- `user_log_impressions`：user 累计曝光数的 `log1p` 变换。
- `item_log_impressions`：item 累计曝光数的 `log1p` 变换。

中 ROI：

- `category_hist_ctr`：`video_category` 历史点击率。
- `user_category_hist_ctr`：`user_id × video_category` 历史点击率。

原料只使用当前 strict materialized 数据中的 `click`、`user_id_idx`、`item_id_idx`、`video_category_idx`。不使用 valid/test label 反推统计，不使用任何 future row 信息。

## 2. Leakage-Safe 构造

Valid/test：

- 只使用 train split 全体 rows 计算聚合统计。
- valid/test 每行仅按 key 查 train 统计表。
- 未见 key 回退到 train 全局先验。

Train：

- 使用 5-fold out-of-fold target encoding。
- 对每个 train row，只使用其余 4 folds 的统计，禁止使用同一 row 的 label。
- fold assignment 使用固定 seed 的稳定 hash，不依赖 label。

平滑：

```text
ctr = (clicks + alpha * global_ctr) / (impressions + alpha)
```

- `global_ctr` 只来自 train split。
- 初始 alpha 取 20，后续可在 10 / 20 / 50 做小范围 sensitivity check。
- OOV / missing key 使用 `clicks=0, impressions=0` 的平滑结果，即 `global_ctr`。

数值处理：

- CTR 类特征先按平滑公式得到 `[0,1]` 浮点值，再用 train OOF 均值/std 做标准化。
- count 类特征先做 `log1p(impressions)`，再用 train OOF 均值/std 标准化。
- 暂不分桶。理由：LR / DCN-v2 可以直接消费标准化 numeric inputs；分桶会引入额外 vocab 和边界选择，先作为后续 ablation。

## 3. 架构

Metadata 新增独立命名空间：

```json
"numeric_features": {
  "columns": ["item_hist_ctr", "..."],
  "stats": {
    "item_hist_ctr": {"mean": 0.0, "std": 1.0, "missing_rate": 0.0}
  },
  "construction": {
    "train": "5-fold out-of-fold target encoding",
    "valid_test": "train-only lookup",
    "alpha": 20
  }
}
```

旧 baseline metadata 不含 `numeric_features`，旧模型默认不消费 numeric inputs。统计特征预处理生成新的 `ctr-*-stats` run_id，不覆盖 `ctr-3999a64f6fad`、`ctr-972e0dcb2b8d` 或 DIN 结果。

训练侧只在 metadata 存在 `numeric_features.columns` 时把 numeric tensor 放入 batch。LR 和 DCN-v2 先支持 numeric inputs；DeepFM / DIN 不在本阶段扩展。

## 4. 被否决方案

User 内 causal expanding：

- 理论上最接近时间安全。
- 当前 `ctr_data_1M.csv` 没有显式 timestamp，user 内文件顺序只能作为弱顺序假设。
- 很多 user 行数较少，expanding stats 方差高，且与 current strict split 的 train-only 统计目标不一致。
- 本阶段暂不采用。

Naive in-sample target encoding：

- 对 train row 使用包含自身 label 的统计。
- 会让高稀疏 key 直接记住 label，尤其是 singleton item / user。
- 必须作为 D3 leakage demonstration 的反例，而不是正式特征。

## 5. D3 验证闸门

- 对比 OOF vs naive：同一统计特征集合分别生成安全版和 naive 版，跑 LR smoke。若 naive train AUC 明显更高而 valid AUC 不同步提升，视为泄漏证据。
- 检查 train/valid/test numeric feature 均值、std、missing/OOV rate 和极值。
- 代码层 assert：valid/test lookup 只读取 train stats；不读 valid/test label 聚合。
- 单元测试覆盖 OOF、不见 key 回退、平滑公式。

## 6. D4 Smoke 边界

- 只在本地 1M run 上跑 LR / DCN-v2 smoke。
- 对比对象是同一 1M 数据、无统计特征的 smoke baseline。
- smoke 指标只用于判断是否值得进入 full，不写成正式模型结论。

## 7. 当前实现边界

- `scripts/preprocess_ctr_stats.py` 当前是本地 1M 原型，会把 train/valid/test rows 读入内存。
- full preprocessing 前必须改成 streaming / chunked 实现，或至少在服务器上先做内存预算验证。
- 当前 `numeric_features` 只接入 LR / MLP / DCN-v2；DeepFM / DIN 暂不消费。
