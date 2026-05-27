# 服务器运行手册 DRAFT

本文件是服务器训练前的草案。当前尚未租用服务器，因此 CUDA、GPU 型号、Linux 发行版、磁盘路径和网络环境都没有验证。所有未知项保持 `TODO`，不能写成已完成事实。

## 目标

服务器用于：

- full / large subset preprocessing；
- torch LR / MLP / DeepFM / DCN-v2 训练；
- 后续获批的 DIN/BST 或 MMOE/PLE；
- 长时间实验和 checkpoint 生成。

本地 Windows 仍用于：

- 代码修改；
- small sample smoke；
- 文档和日志维护；
- commit / push。

## GitHub 方向

服务器启动时方向是：

```text
GitHub -> server
```

不要假设服务器有 Windows 本机 SSH key：

```text
C:\Users\Eddy\.ssh\github_key
```

服务器 GitHub access 待选：

- TODO：配置服务器自己的 SSH key，并添加到 GitHub。
- TODO：或使用 HTTPS clone / pull。

服务器上先验证：

```bash
ssh -T git@github.com
git remote -v
```

## 环境创建 DRAFT

服务器 Python 版本尚未确认。当前本地为：

```text
Python 3.12.7
```

服务器需确认：

```bash
python --version
nvidia-smi
nvcc --version
```

本地已验证的数据层依赖：

```text
numpy==2.2.6
PyYAML==6.0.2
scikit-learn==1.6.1
```

本地已验证 CPU torch smoke：

```text
torch==2.12.0+cpu
```

注意：

- `requirements-torch-cpu.txt` 只用于本地 CPU smoke。
- torch / CUDA wheel 版本暂不写死，等服务器镜像确认后再定。
- 服务器上先确认 `python --version` 和 `nvidia-smi`，再选择 CUDA wheel。

## 数据目录 DRAFT

原始数据不进入 git。服务器数据路径待定：

```text
TODO: /path/to/tenrec-ranking/data/Tenrec/ctr_data_1M.csv
```

期望文件：

```text
data/Tenrec/ctr_data_1M.csv
data/samples/ctr_tiny_100k_head.csv
data/samples/ctr_user_block_1m_seed20260525.csv
```

如果服务器只跑 full data，至少需要：

```text
data/Tenrec/ctr_data_1M.csv
```

数据获取方式待定：

- TODO：服务器重新下载 Tenrec。
- TODO：或从本地 / 网盘 / 对象存储传输。

## Smoke-first 顺序

服务器上不要直接启动长训练。先跑：

```bash
python -m py_compile src/tenrec/data.py src/tenrec/metrics.py scripts/preprocess_ctr_data.py scripts/run_sklearn_lr_smoke.py
python -m py_compile src/tenrec/torch_data.py src/tenrec/models.py src/tenrec/training.py scripts/train.py
python -m unittest tests.test_data_contract tests.test_metrics tests.test_torch_models
```

如果有 100k sample：

```bash
python scripts/preprocess_ctr_data.py --config configs/ctr_smoke.yaml
python scripts/smoke_materialized_dataloader.py --metadata outputs/preprocessed/<run_id>/metadata.json --batch-size 32
```

如果有 1M user-block sample：

```bash
python scripts/preprocess_ctr_data.py --config configs/ctr_user_block_1m.yaml
python scripts/run_sklearn_lr_smoke.py --metadata outputs/preprocessed/<run_id>/metadata.json --max-train-rows 100000 --max-valid-rows 50000 --output outputs/inspection/sklearn_lr_smoke_ctr_user_block_1m.json
python scripts/train.py --config configs/torch_lr_smoke.yaml --metadata outputs/preprocessed/<run_id>/metadata.json --device auto --overfit
python scripts/train.py --config configs/torch_mlp_smoke.yaml --metadata outputs/preprocessed/<run_id>/metadata.json --device auto --overfit
python scripts/train.py --config configs/torch_lr_smoke.yaml --metadata outputs/preprocessed/<run_id>/metadata.json --device auto
python scripts/train.py --config configs/torch_mlp_smoke.yaml --metadata outputs/preprocessed/<run_id>/metadata.json --device auto
```

`<run_id>` 由 metadata 输出确认，不能手猜。

`metadata_path` 必须通过 `--metadata` 或 config 指向服务器实际生成的文件。不要写死本地路径：

```text
outputs/preprocessed/ctr-454e7ccb12f7/metadata.json
```

原因：full preprocessing 会生成新的 deterministic run_id。

## Full preprocessing DRAFT

full data config 尚未创建。需要在服务器确认磁盘和时间成本后再添加，例如：

```text
configs/ctr_full.yaml
```

full preprocessing 预计仍使用两遍流式方案：

```bash
python scripts/preprocess_ctr_data.py --config configs/ctr_full.yaml
```

输出：

```text
outputs/preprocessed/{run_id}/metadata.json
outputs/preprocessed/{run_id}/vocabs/
outputs/preprocessed/{run_id}/materialized/
```

这些输出不进入 git。

## Full training DRAFT

full training config 尚未创建。服务器 full run 不能使用 smoke config 中的：

```text
max_train_rows
max_valid_rows
```

如果这些字段存在，则只能标记为 smoke-only。

训练前必须生成或复用 shuffled train file。当前实现使用 deterministic hash-bucket shuffle：

```text
outputs/preprocessed/{run_id}/materialized/train_shuffled_seed{seed}_b{bucket_count}.csv
```

该文件不进入 git。

训练命令占位：

```bash
python scripts/train.py --config configs/torch_lr_full.yaml --metadata outputs/preprocessed/<run_id>/metadata.json --device auto
python scripts/train.py --config configs/torch_mlp_full.yaml --metadata outputs/preprocessed/<run_id>/metadata.json --device auto
```

TODO：

- 确认服务器 GPU 显存和磁盘空间后再定 `batch_size`。
- 确认 CUDA torch wheel 后再写服务器 requirements。
- 确认 full valid 评估内存占用；当前评估会收集 valid labels / predictions / user groups 后计算 AUC 和 GAUC。

## 实验记录要求

服务器每个 run 必须记录到：

```text
docs/experiment_log.md
```

至少包含：

- 日期；
- run_id；
- git commit；
- command；
- config；
- data contract version；
- split rule；
- model；
- metrics；
- output path；
- 结论；
- 已知限制。

raw outputs、checkpoints、logs 不进 git。只把必要 summary 写回 docs。
