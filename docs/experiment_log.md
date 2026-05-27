# 实验日志

本文件只记录真实完成的训练和评估 run。

## 2026-05-25 — sklearn LR learnability smoke

类型：`tiny subset training / smoke test`

目的：

- 验证物化后的编码数据能够被简单线性模型学习。
- 检查 label、split、vocab/OOV/missing 编码和 metric 实现是否存在明显方向性错误。
- 不作为正式模型结果，不进入简历指标。

### Run: `sklearn_lr_smoke_ctr_tiny_100k`

- 日期：2026-05-25
- Run ID：`sklearn_lr_smoke_ctr_tiny_100k`
- 代码状态：working tree，未 commit
- Command：

```powershell
.\.venv\Scripts\python.exe scripts\run_sklearn_lr_smoke.py --metadata outputs\preprocessed\ctr-78004c39c1dd\metadata.json --max-train-rows 80000 --max-valid-rows 9664 --output outputs\inspection\sklearn_lr_smoke_ctr_tiny_100k.json
```

- Config：`configs/ctr_smoke.yaml`
- Dataset file：`data/samples/ctr_tiny_100k_head.csv`
- Preprocess run：`ctr-78004c39c1dd`
- Split rule：user 内文件顺序，`N<3 -> train only`，`N>=3 -> 80/10/10`，不 shuffle，不去重
- Model：`sklearn LogisticRegression`，one-hot categorical smoke
- Output path：`outputs/inspection/sklearn_lr_smoke_ctr_tiny_100k.json`

Metrics：

| split | rows | AUC | GAUC | GAUC coverage | LogLoss |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 80,000 | 0.8941783507999844 | 0.9200547791169456 | 0.9977 | 0.40980822366154607 |
| valid | 9,664 | 0.7141731574256482 | 0.5974393507668665 | 0.8908319536423841 | 0.5377791950409944 |

结论：

- 该 smoke 证明物化编码数据可以被简单 LR 学到信号。
- 该 sample 是 head sample，有顺序偏置，不能当正式指标。

已知限制：

- 不是正式 baseline。
- 未使用 full data。
- 未运行 torch 模型。

### Run: `sklearn_lr_smoke_ctr_user_block_1m`

- 日期：2026-05-25
- Run ID：`sklearn_lr_smoke_ctr_user_block_1m`
- 代码状态：working tree，未 commit
- Command：

```powershell
.\.venv\Scripts\python.exe scripts\run_sklearn_lr_smoke.py --metadata outputs\preprocessed\ctr-454e7ccb12f7\metadata.json --max-train-rows 100000 --max-valid-rows 50000 --output outputs\inspection\sklearn_lr_smoke_ctr_user_block_1m.json
```

- Config：`configs/ctr_user_block_1m.yaml`
- Dataset file：`data/samples/ctr_user_block_1m_seed20260525.csv`
- Preprocess run：`ctr-454e7ccb12f7`
- Split rule：user 内文件顺序，`N<3 -> train only`，`N>=3 -> 80/10/10`，不 shuffle，不去重
- Model：`sklearn LogisticRegression`，one-hot categorical smoke
- Output path：`outputs/inspection/sklearn_lr_smoke_ctr_user_block_1m.json`

Metrics：

| split | rows | AUC | GAUC | GAUC coverage | LogLoss |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 100,000 | 0.8866438867118259 | 0.9012071068750077 | 0.99388 | 0.4080319738212789 |
| valid | 50,000 | 0.6283948058203263 | 0.6032205118880077 | 0.89796 | 0.5718098163083559 |

结论：

- 该 smoke 证明 1M user-block sample 经过 train-only vocab 和 OOV/missing 编码后可以被 LR 学到信号。
- LR 直接消费 `outputs/preprocessed/` 下的物化编码数据，没有绕过 preprocessing pipeline。

已知限制：

- 不是正式 baseline。
- 只使用 1M user-block smoke sample 的部分 train/valid 行。
- valid AUC / GAUC 只用于 learnability gate，不用于简历或对外报告。

## 2026-05-27 — torch LR / MLP local smoke

类型：`tiny subset training / smoke test`

目的：

- 验证 torch LR / MLP 能消费物化编码数据。
- 验证 forward / loss / backward / checkpoint / metrics log。
- 验证 `train.py` 一条命令可以完成训练和 valid 评估。

共同限制：

- 输入为 `outputs/preprocessed/ctr-454e7ccb12f7/metadata.json`。
- 数据来自 `ctr_user_block_1m_seed20260525.csv` 的物化结果。
- 使用 `max_train_rows` / `max_valid_rows` head 截断，因此只允许作为 smoke。
- 不做 class reweighting，不做重采样。
- 使用 materialized hash-bucket shuffled train CSV。

### Run: `torch_lr_overfit`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\torch_lr_smoke.yaml --overfit --device cpu
```

Result：

```text
initial_loss: 0.6931471824645996
final_loss: 0.02680760808289051
target_loss: 0.05
passed: true
```

结论：LR forward / loss / backward 可以在单 batch 上过拟合。

### Run: `torch_mlp_overfit`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\torch_mlp_smoke.yaml --overfit --device cpu
```

Result：

```text
initial_loss: 0.6972130537033081
final_loss: 0.00024013200891204178
target_loss: 0.05
passed: true
```

结论：MLP forward / loss / backward 可以在单 batch 上过拟合。

### Run: `20260527-164500-torch_lr_smoke-lr`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\torch_lr_smoke.yaml --device cpu
```

Output：

```text
outputs/runs/20260527-164500-torch_lr_smoke-lr/
outputs/runs/20260527-164500-torch_lr_smoke-lr/metrics.jsonl
outputs/runs/20260527-164500-torch_lr_smoke-lr/summary.json
outputs/runs/20260527-164500-torch_lr_smoke-lr/checkpoints/best.pt
```

Metrics：

| epoch | train loss | valid AUC | valid GAUC | GAUC coverage | valid LogLoss |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.5558694330215455 | 0.6713101559280241 | 0.5961861985023545 | 0.89796 | 0.5746971582179735 |
| 2 | 0.49556085777282716 | 0.6769976360975771 | 0.5993388882172885 | 0.89796 | 0.5616649100162441 |
| 3 | 0.4589645572185516 | 0.677851746558059 | 0.5998304001871494 | 0.89796 | 0.5545902430237066 |
| 4 | 0.4295658135700226 | 0.6776799759666773 | 0.6000102219050139 | 0.89796 | 0.5514814610423758 |
| 5 | 0.40544721200942996 | 0.677162416436456 | 0.599984004757329 | 0.89796 | 0.5508678869033629 |

Best checkpoint：

```text
epoch: 5
checkpoint metric: logloss
best metric: 0.5508678869033629
```

结论：torch LR 一条命令训练、valid 评估、metrics 和 checkpoint 落盘均跑通。

### Run: `20260527-164529-torch_mlp_smoke-mlp`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\torch_mlp_smoke.yaml --device cpu
```

Output：

```text
outputs/runs/20260527-164529-torch_mlp_smoke-mlp/
outputs/runs/20260527-164529-torch_mlp_smoke-mlp/metrics.jsonl
outputs/runs/20260527-164529-torch_mlp_smoke-mlp/summary.json
outputs/runs/20260527-164529-torch_mlp_smoke-mlp/checkpoints/best.pt
```

Metrics：

| epoch | train loss | valid AUC | valid GAUC | GAUC coverage | valid LogLoss |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.5630411438941956 | 0.5197096996237808 | 0.49627787940952867 | 0.89796 | 0.5973948575354018 |
| 2 | 0.5484503300666809 | 0.534898682748413 | 0.5066246379823998 | 0.89796 | 0.5944793008281283 |
| 3 | 0.5430316017532348 | 0.543106674284724 | 0.5111475306008336 | 0.89796 | 0.5926276149280864 |
| 4 | 0.5358314865684509 | 0.5535725552237716 | 0.5138535816607508 | 0.89796 | 0.5934145911107419 |
| 5 | 0.5258482336425782 | 0.5641194888327414 | 0.5185113647677471 | 0.89796 | 0.5961076589424403 |

Best checkpoint：

```text
epoch: 3
checkpoint metric: logloss
best metric: 0.5926276149280864
```

结论：torch MLP 一条命令训练、valid 评估、metrics 和 checkpoint 落盘均跑通。当前 MLP 未调参，结果只用于 smoke。

## 2026-05-27 — G1 10M preprocessing memory check

类型：`schema inspection / preprocessing smoke`

目的：

- 在服务器训练前验证两遍流式预处理在更大样本上内存有界。
- 不跑 full 120M，先用约 10M 行完整 user-block sample 验证。

### 10M sample generation

Command：

```powershell
.\.venv\Scripts\python.exe scripts\make_ctr_smoke_samples.py --input data\Tenrec\ctr_data_1M.csv --sample-dir data\samples --output-dir outputs\inspection --tiny-rows 0 --target-rows 10000000 --seed 20260525 --tiny-sample-name ctr_tiny_0_for_10m_generation.csv --user-block-sample-name ctr_user_block_10m_seed20260525.csv
```

Result：

```text
file: data\samples\ctr_user_block_10m_seed20260525.csv
actual rows: 10,000,035
users: 82,761
file size bytes: 886,528,483
click=0: 7,608,029
click=1: 2,392,006
first pass elapsed: 157.466s
second pass elapsed: 145.859s
```

### 10M preprocessing with RSS monitor

Command：

```powershell
.\.venv\Scripts\python.exe scripts\run_with_resource_monitor.py --output outputs\inspection\preprocess_10m_resource_monitor_psutil.json --interval 0.5 -- .\.venv\Scripts\python.exe scripts\preprocess_ctr_data.py --config configs\ctr_user_block_10m.yaml
```

Output：

```text
outputs/preprocessed/ctr-1961cdee479f/
outputs/inspection/preprocess_10m_resource_monitor_psutil.json
```

Metrics：

| item | value |
| --- | ---: |
| run_id | `ctr-1961cdee479f` |
| train rows | 8,072,351 |
| valid rows | 963,842 |
| test rows | 963,842 |
| peak RSS | 136.68 MiB |
| monitor backend | psutil |
| Pass1 elapsed | 38.223s |
| Pass2 elapsed | 71.914s |
| user_id vocab size | 82,763 |
| item_id vocab size | 766,087 |
| video_category vocab size | 4 |
| valid item_id OOV rows | 46,239 |
| valid item_id OOV rate | 0.04797363053280517 |
| test item_id OOV rows | 47,786 |
| test item_id OOV rate | 0.04957866538291546 |
| valid/test user_id OOV | 0 |
| materialized output bytes | 207,866,502 |

Materialized files：

| file | bytes |
| --- | ---: |
| `train.csv` | 167,999,362 |
| `valid.csv` | 19,920,285 |
| `test.csv` | 19,946,855 |

### 1M memory baseline

Command：

```powershell
.\.venv\Scripts\python.exe scripts\run_with_resource_monitor.py --output outputs\inspection\preprocess_1m_resource_monitor_psutil.json --interval 0.5 -- .\.venv\Scripts\python.exe scripts\preprocess_ctr_data.py --config configs\ctr_user_block_1m.yaml
```

Result：

| item | value |
| --- | ---: |
| run_id | `ctr-454e7ccb12f7` |
| peak RSS | 54.77 MiB |
| Pass1 elapsed | 3.844s |
| Pass2 elapsed | 8.455s |
| user_id vocab size | 8,183 |
| item_id vocab size | 222,831 |

结论：

- 10M 相比 1M 行数约 10 倍，但 peak RSS 从 54.77 MiB 增至 136.68 MiB，没有接近 10 倍线性增长。
- 内存增长主要与 vocab 条目增加有关，尤其 `item_id` vocab 从 222,831 增至 766,087。
- 暂未发现隐藏整文件 load 或按行数线性爆内存的问题。
- full 120M 仍需在服务器验证，但 G1 不阻塞上服务器。

## 2026-05-27 — G2 MLP train-vs-valid AUC check

类型：`tiny subset training / diagnostic`

目的：

- 解释 MLP valid GAUC 接近随机的问题。
- 判断是实现 bug，还是 smoke 配置下未充分学习 / 泛化弱。

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\torch_mlp_smoke.yaml --device cpu
```

Run：

```text
20260527-174430-torch_mlp_smoke-mlp
```

Metrics：

| epoch | train AUC | valid AUC | train GAUC | valid GAUC | train LogLoss | valid LogLoss |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.5435437311355459 | 0.5197096996237808 | 0.5340193502875008 | 0.49627787940952867 | 0.5500743907350816 | 0.5973948575354018 |
| 2 | 0.5760376017930043 | 0.534898682748413 | 0.5593793396022603 | 0.5066246379823998 | 0.544906177360974 | 0.5944793008281283 |
| 3 | 0.6065873845344981 | 0.543106674284724 | 0.5813285668683251 | 0.5111475306008336 | 0.5379654485932528 | 0.5926276149280864 |
| 4 | 0.6404150352231401 | 0.5535725552237716 | 0.606194072676756 | 0.5138535816607508 | 0.5287619970457057 | 0.5934145911107419 |
| 5 | 0.6758640335529477 | 0.5641194888327414 | 0.6337983297548897 | 0.5185113647677471 | 0.5163137918912449 | 0.5961076589424403 |

判别：

- train AUC 从 0.5435 持续升到 0.6759，valid AUC 从 0.5197 升到 0.5641。
- train AUC 明显高于 valid AUC，但没有达到 `>0.75` 的强过拟合判据。
- train AUC 也不是 `~0.55` 持平；结合单 batch overfit 已通过，未发现 embedding / forward / backward 硬 bug。

结论：

- G2 没有发现必须本地修复的 MLP 实现 bug。
- 当前更像 head-truncated smoke 配置下未充分学习 + 泛化弱。
- 该结果不阻塞上服务器，但 MLP 指标不能写成正式结论，服务器上必须继续观察 large/full subset 学习曲线。

未来每次 run 必须记录：

- 日期
- Run ID
- 命令
- Config 或 arguments
- Dataset file 和 split version
- Model
- Metrics：AUC、GAUC、LogLoss
- Output path
- 结论
- 已知限制
