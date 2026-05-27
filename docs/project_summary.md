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
- `ctr_user_block_1m_seed20260525.csv` 已完成 split feasibility check：按 user 内文件顺序 80/10/10 切分后，train / valid / test 分别为 807,282 / 96,459 / 96,459 行。
- valid / test 的有效 GAUC row coverage rate 分别为 0.87316891 和 0.82024487，smoke 阶段可用于 GAUC implementation 验证。
- user-block smoke split 存在 unseen item：valid item 未出现在 train 的比例为 0.30998672，test item 未出现在 train 的比例为 0.30694255；后续 embedding / feature mapping 需要 OOV 处理。
- 第一版 MVP 数据契约已确认：click prediction，输入特征为 `user_id`、`item_id`、`video_category`、`gender`、`age`，暂不使用 `watching_times`、`hist_*`、`follow/like/share`。
- 已实现最小数据层：user 内顺序 split、train-only vocab、统一 `0=OOV / 1=missing / 2..=seen` 编码、两遍流式预处理和物化 split 输出。
- 已实现 AUC、LogLoss 和 impression-weighted GAUC；GAUC 输出包含有效 user 数和 row coverage。
- 已新增数据契约和指标单元测试，覆盖 split 整数公式、missing/OOV、train-only vocab、AUC/LogLoss known-answer、GAUC 单类用户跳过。
- `ctr_tiny_100k_head.csv` 已完成物化预处理，run_id 为 `ctr-78004c39c1dd`，split rows 为 80,672 / 9,664 / 9,664。
- `ctr_user_block_1m_seed20260525.csv` 已完成物化预处理，run_id 为 `ctr-454e7ccb12f7`，split rows 为 807,282 / 96,459 / 96,459。
- 使用重构后的共享 split 函数重新运行 1M split feasibility，复现 807,282 / 96,459 / 96,459。
- sklearn LR learnability smoke 已在物化编码数据上跑通：1M sample 的前 100,000 train rows 和前 50,000 valid rows 上，train AUC 为 0.8866438867118259，valid AUC 为 0.6283948058203263。该结果只证明 pipeline 可学习，不是正式模型指标。
- 本地已安装 `torch==2.12.0+cpu`，用于 CPU smoke；服务器 CUDA torch 版本尚未确认。
- 已实现 torch LR 和 MLP 最小训练入口；LR 是 scalar lookup sum，不使用 dense embedding。
- 已实现 deterministic hash-bucket shuffled train CSV，避免直接按 user 聚簇顺序训练。
- torch LR overfit gate 通过：loss 从 0.6931471824645996 降到 0.02680760808289051。
- torch MLP overfit gate 通过：loss 从 0.6972130537033081 降到 0.00024013200891204178。
- torch LR train smoke 跑通并落盘 checkpoint：valid LogLoss 0.5508678869033629，valid AUC 0.677162416436456，valid GAUC 0.599984004757329，GAUC coverage 0.89796。
- torch MLP train smoke 跑通并落盘 checkpoint：best valid LogLoss 0.5926276149280864；该结果只用于 smoke，MLP 尚未调参。
- G1 生成 10,000,035 行完整 user-block 样本，并完成两遍流式预处理：run_id `ctr-1961cdee479f`，peak RSS 136.68 MiB，Pass1 38.223s，Pass2 71.914s。
- G1 1M 对照 peak RSS 为 54.77 MiB；10M 行数约 10 倍但 RSS 未接近 10 倍增长，暂未发现整文件 load 或按行数线性爆内存问题。
- G2 复跑 MLP train smoke 并记录 train/valid AUC：epoch 5 train AUC 0.6758640335529477，valid AUC 0.5641194888327414；未发现 embedding / forward / backward 硬 bug，但 MLP smoke 仍不能作为正式模型结论。

## 尚未验证

- 尚未验证 `hist_1` 到 `hist_10` 是否严格只使用 target event 之前的历史。
- 尚未实现 DeepFM/DCN-v2 模型训练代码。
- 尚未在 full data 上验证最终 split 方案和正式指标。
- 尚未在服务器上验证 Python / CUDA / Torch 环境。
- 尚未在 full 120M 数据上验证预处理 RSS 和训练耗时。
