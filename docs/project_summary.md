# 项目总结

本文件只写已验证的项目成果。

## 当前已验证

- 仓库目录存在：`D:\ANU\project\tenrec-ranking`。
- 初始文档骨架已于 2026-05-24 创建。
- Tenrec 官方来源已识别。
- 项目级 `AGENTS.md` 和 `docs/LOGGING_GUIDE.md` 已创建，用于定义工作规则和日志模板。
- 本地 git 仓库已初始化，SSH remote 为 `git@github.com:EddyHai57/tenrec-ranking.git`。
- 项目 Markdown 默认语言已规范为简体中文，专有名词、命令、路径、模型名和指标缩写除外。
- 本地 `.venv` 已创建，Python 为 `3.12.7`，pip 为 `26.1.1`。
- 官方材料确认存在 1M 级别 Tenrec 子集口径，CTR 任务使用路径为 `data/ctr_data_1M.csv`。
- Tenrec 数据已解压到本地 `data/Tenrec/`，其中 `ctr_data_1M.csv` 存在，大小约 9.94 GB。
- `ctr_data_1M.csv` 表头已确认包含 `click`、多行为标签和 `hist_1` 到 `hist_10`。
- `ctr_data_1M.csv` 已完成全量流式 inspection：120,342,306 行，bad width rows 为 0，unique `user_id` 为 999,447，unique `item_id` 为 2,310,087。
- `ctr_data_1M.csv` 全量 `click` 分布已确认：`0`: 91,461,446；`1`: 28,880,860。
- `ctr_data_1M.csv` 没有显式 timestamp 字段，不能直接做 timestamp-based split。
- Tenrec 下载包数据总览已写入 `docs/dataset_catalog.md`。
- `ctr_data_1M.csv` 已完成数据契约 probe：user block count 为 999,447，user 连续排列，user_id 单调，无 non-contiguous user。
- `ctr_data_1M.csv` 中发现完全重复行 883,646 条、重复 `(user_id,item_id)` 1,810,484 条，其中 click 冲突 560,994 条；因此 `(user_id,item_id)` 不能作为唯一样本键。
- 已生成 `ctr_tiny_100k_head.csv`：100,000 行，773 个 user，`click=0`: 71,756，`click=1`: 28,244。
- 已生成 `ctr_user_block_1m_seed20260525.csv`：1,000,200 行，8,181 个完整 user blocks，`click=0`: 758,425，`click=1`: 241,775。

## 尚未验证

- 尚未验证 `hist_1` 到 `hist_10` 是否严格只使用 target event 之前的历史。
- 尚未确定最终 split 方案、去重策略、dataloader、模型或指标结果。
