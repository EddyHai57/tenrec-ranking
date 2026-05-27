# 环境说明

本文件记录本地环境决策和环境问题。

## 当前策略

- 初始阶段只做本地开发。
- 初始阶段不租服务器、不配置服务器训练环境。
- 数据 schema 和第一版 dataloader 范围确认前，不安装 PyTorch 或其他深度学习框架。
- 原始数据、虚拟环境、cache、checkpoint 不进入 git。

## 本地环境状态

- 已创建 `.venv`。
- Python 版本：`3.12.7`。
- `.venv` 内 `pip` 已升级到 `26.1.1`。
- 已安装数据层和 sklearn LR smoke 的最小依赖：
  - `numpy==2.2.6`
  - `psutil==7.2.2`
  - `PyYAML==6.0.2`
  - `scikit-learn==1.6.1`
  - `scipy==1.17.1`
  - `joblib==1.5.3`
  - `threadpoolctl==3.6.0`
- 已安装本地 CPU torch smoke 依赖：
  - `torch==2.12.0+cpu`
  - `filelock==3.29.0`
  - `fsspec==2026.4.0`
  - `Jinja2==3.1.6`
  - `MarkupSafe==3.0.3`
  - `mpmath==1.3.0`
  - `networkx==3.6.1`
  - `setuptools==70.2.0`
  - `sympy==1.14.0`
  - `typing-extensions==4.15.0`
- 尚未安装 pandas、pyarrow 或服务器 CUDA torch 依赖。

验证命令：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe -m pip list
```

验证输出：

```text
Python 3.12.7
pip 26.1.1 from D:\ANU\project\tenrec-ranking\.venv\Lib\site-packages\pip (python 3.12)
```

## 最小本地环境命令

已执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-torch-cpu.txt
```

依赖只在需要时添加。当前没有引入 pandas / pyarrow，因为两遍预处理使用 Python 标准库 `csv` 流式读取。

## 尚未完成

- Python 版本尚未通过 `.python-version` 或 toolchain 文件 pin。
- 服务器 Python / CUDA / Torch wheel 版本尚未确认。
- `requirements-torch-cpu.txt` 只用于本地 CPU smoke；服务器不要直接复用该文件作为 CUDA 训练环境。
