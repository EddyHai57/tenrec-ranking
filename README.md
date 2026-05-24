# Tenrec Ranking

Tenrec 多行为推荐排序项目。

本仓库目标是搭建一个可审计、可复现、可用于面试讲述的推荐排序（Ranking）实验工程，而不是刷榜项目。第一阶段聚焦 Tenrec 上的小规模、可复现点击率预测（CTR / click prediction）MVP。

## 当前范围

- 主数据集：Tenrec。
- 第一任务：单场景 click prediction。
- MVP 模型：LR、MLP、DeepFM、DCN-v2。
- MVP 指标：AUC、GAUC、LogLoss。
- 切分原则：使用时间切分（time-based split），不使用随机切分。
- 数据原则：建模前先基于真实 schema 验证 label 和真实负样本（true negative samples）口径。

当前不做：

- 大规模 full training。
- DIN/BST、MMOE/PLE 或多场景建模。
- 服务器训练环境配置。
- 在数据 schema 检查前搭完整 `src/` 和 `configs/`。

## 项目结构

```text
docs/
  LOGGING_GUIDE.md
  decision_log.md
  data_notes.md
  environment.md
  experiment_log.md
  issue_log.md
  project_summary.md
  daily_logs/
    YYYY-MM-DD.md
```

## 最小环境

先本地开发。Tenrec 子集和 schema inspection 路径确认前，不安装深度学习框架。

初始本地工具：

- Python 3.10+ 或 3.11
- `venv`
- `pip`
- `pandas`
- `pyarrow` 或其他 CSV/parquet 检查依赖，等数据格式确认后再装

建议第一步：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

依赖文件会在第一轮 schema inspection 计划确定后再添加。

## 第一工程检查点

添加训练代码前先完成：

1. 从官方来源下载或取得一个 Tenrec 小子集。
2. 检查真实字段、label 定义、timestamp、scenario 和 behavior 字段。
3. 在 `docs/data_notes.md` 写出数据契约草案。
4. 基于真实 schema 再决定 `src/` 和 `configs/` 边界。
