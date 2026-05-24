# 环境说明

本文件记录本地环境决策和环境问题。

## 当前策略

- 初始阶段只做本地开发。
- 初始阶段不租服务器、不配置服务器训练环境。
- 数据 schema 和第一版 dataloader 范围确认前，不安装 PyTorch 或其他深度学习框架。
- 原始数据、虚拟环境、cache、checkpoint 不进入 git。

## 最小本地环境

建议第一步命令：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

依赖只在需要时添加。第一轮 schema inspection 可能需要：

- `pandas`
- `pyarrow`，如果需要 parquet 转换或更高效的表格检查
- `scikit-learn`，后续 baseline metrics 需要时再加

## 尚未完成

- Python 版本尚未 pin。
- 尚未创建 `requirements.txt`、`pyproject.toml` 或 lock file。
- 尚未安装深度学习框架。
