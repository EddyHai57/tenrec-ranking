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

官方仓库列出的 raw scenario files：

- `QK-video.csv`
- `QB-video.csv`
- `QK-article.csv`
- `QB-artilce.csv`

注意：`QB-artilce.csv` 是官方 README 中的拼写。引用原始文件名时保留上游拼写。

## 本地验证状态

尚未下载或检查本地 Tenrec 数据。

本地 schema inspection 前仍未知：

- 精确字段名；
- click label 字段和值语义；
- true negative label 编码；
- timestamp 字段和粒度；
- scenario / domain 字段；
- user ID 和 item ID 字段；
- user / item 侧特征；
- multi-task labels；
- 是否能稳定构造用户历史序列；
- 官方预处理 CTR 文件是否保留时间顺序。

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

## Tenrec 小样本检查计划

1. 访问官方 dataset page；如需 license terms，手动确认。
2. 下载最小但适合 CTR/schema inspection 的官方子集；如果官方页面提供 `ctr_data_1M.csv`，优先考虑。
3. 原始数据放在 git 控制之外，或在 `.gitignore` 已覆盖后放入 `data/raw/`。
4. 检查文件名、大小、编码、header、行数、缺失率、label 分布、timestamp 范围、per-user/per-item 计数。
5. 只把轻量 schema summary 和命令输出写入 docs；不要提交原始数据。
