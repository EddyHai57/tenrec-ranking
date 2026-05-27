# Tenrec Ranking

Tenrec 多行为推荐排序项目。

本仓库目标是搭建一个可审计、可复现、可用于面试讲述的推荐排序（Ranking）实验工程，而不是刷榜项目。第一阶段聚焦 Tenrec 上的小规模、可复现点击率预测（CTR / click prediction）MVP。

## 当前范围

- 主数据集：Tenrec。
- 第一任务：单场景 click prediction。
- MVP 模型：LR、MLP、DeepFM、DCN-v2。
- MVP 指标：AUC、GAUC、LogLoss。
- 当前切分：`ctr_data_1M.csv` 无显式 timestamp，第一版使用 user 内文件顺序 split，不使用随机切分。
- 数据原则：建模前先基于真实 schema 验证 label 和真实负样本（true negative samples）口径。

当前不做：

- 大规模 full training。
- DIN/BST、MMOE/PLE 或多场景建模。
- 服务器训练环境配置。
- 未经验证的 `hist_*` 序列建模。

## 项目结构

```text
docs/
  LOGGING_GUIDE.md
  decision_log.md
  data_notes.md
  dataset_catalog.md
  environment.md
  experiment_log.md
  issue_log.md
  progress_report_2026-05-25.md
  project_summary.md
  server_runbook.md
  daily_logs/
    YYYY-MM-DD.md
configs/
  ctr_smoke.yaml
  ctr_user_block_1m.yaml
src/
  tenrec/
    data.py
    metrics.py
scripts/
  preprocess_ctr_data.py
  smoke_materialized_dataloader.py
  run_sklearn_lr_smoke.py
tests/
  test_data_contract.py
  test_metrics.py
  test_torch_models.py
```

## 最小环境

先本地开发。当前不安装 PyTorch；训练服务器环境后续单独确认。

初始本地工具：

- Python 3.12.7
- `venv`
- `pip`

安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

当前依赖只覆盖数据层和 sklearn LR smoke。

本地 CPU torch smoke 额外安装：

```powershell
python -m pip install -r requirements-torch-cpu.txt
```

服务器 CUDA torch 版本等待真实服务器环境确认。

## 第一工程检查点

已完成：

1. `ctr_data_1M.csv` 全量流式 inspection。
2. 100k / 1M smoke sample 生成。
3. MVP 数据契约 v0.1。
4. 两遍流式预处理、train-only vocab、OOV/missing 编码。
5. AUC / LogLoss / impression-weighted GAUC。
6. sklearn LR learnability smoke。
7. torch LR / MLP overfit 和 train smoke。

当前最重要的事实源：

- `docs/data_notes.md`
- `docs/project_summary.md`
- `docs/progress_report_2026-05-25.md`
