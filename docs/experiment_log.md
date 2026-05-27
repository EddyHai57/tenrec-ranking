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

## 2026-05-28 — DeepFM / DCN-v2 local smoke

类型：`tiny subset training / smoke test`

目的：

- 补齐 strict protocol baseline 阶梯：`LR -> MLP -> DeepFM -> DCN-v2`。
- 验证 DeepFM / DCN-v2 能复用现有 metadata、物化数据读取、训练、评估、overfit、checkpoint 和 metrics 流程。
- 只做本地 CPU smoke，不作为正式模型结果。

共同限制：

- 输入为 `outputs/preprocessed/ctr-454e7ccb12f7/metadata.json`。
- 数据来自 `ctr_user_block_1m_seed20260525.csv` 的物化结果。
- 使用 `max_train_rows=100000` 和 `max_valid_rows=50000`，因此只允许作为 smoke。
- 不做 class reweighting，不做重采样。
- 使用 materialized hash-bucket shuffled train CSV。

### Run: `deepfm_overfit`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\deepfm_smoke.yaml --overfit --device cpu
```

Result：

```text
initial_loss: 0.6765590310096741
final_loss: 1.746938149693733e-09
target_loss: 0.05
passed: true
```

结论：DeepFM forward / loss / backward 可以在单 batch 上过拟合。

### Run: `dcnv2_overfit`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\dcnv2_smoke.yaml --overfit --device cpu
```

Result：

```text
initial_loss: 0.908693790435791
final_loss: 3.74729802388174e-06
target_loss: 0.05
passed: true
```

结论：DCN-v2 forward / loss / backward 可以在单 batch 上过拟合。

### Run: `20260528-010753-deepfm_smoke-deepfm`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\deepfm_smoke.yaml --device cpu
```

Output：

```text
outputs/runs/20260528-010753-deepfm_smoke-deepfm/
outputs/runs/20260528-010753-deepfm_smoke-deepfm/metrics.jsonl
outputs/runs/20260528-010753-deepfm_smoke-deepfm/summary.json
outputs/runs/20260528-010753-deepfm_smoke-deepfm/checkpoints/best.pt
```

Metrics：

| epoch | train loss | valid AUC | valid GAUC | GAUC coverage | valid LogLoss |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.5864733688545227 | 0.6609157271411433 | 0.5932246750132204 | 0.89796 | 0.5829442686843472 |
| 2 | 0.47309519799232486 | 0.6712964224072929 | 0.5984632023912543 | 0.89796 | 0.5821876039626651 |
| 3 | 0.3278996840763092 | 0.6548994740541586 | 0.5943389296777046 | 0.89796 | 0.691819411284184 |
| 4 | 0.2517506833028793 | 0.6496638645610264 | 0.591013837262858 | 0.89796 | 0.7623940945371613 |

Best checkpoint：

```text
epoch: 2
checkpoint metric: logloss
best metric: 0.5821876039626651
```

结论：DeepFM 已接入一条命令训练、valid 评估、metrics 和 checkpoint 流程。该 smoke 中 epoch 2 后 valid LogLoss 变差，说明 head-truncated 小样本下存在过拟合趋势，不能作为正式模型结论。

### Run: `20260528-010814-dcnv2_smoke-dcnv2`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\dcnv2_smoke.yaml --device cpu
```

Output：

```text
outputs/runs/20260528-010814-dcnv2_smoke-dcnv2/
outputs/runs/20260528-010814-dcnv2_smoke-dcnv2/metrics.jsonl
outputs/runs/20260528-010814-dcnv2_smoke-dcnv2/summary.json
outputs/runs/20260528-010814-dcnv2_smoke-dcnv2/checkpoints/best.pt
```

Metrics：

| epoch | train loss | valid AUC | valid GAUC | GAUC coverage | valid LogLoss |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.5673010801887512 | 0.5241001837053098 | 0.5076045845847659 | 0.89796 | 0.59944790928456 |
| 2 | 0.5467337486839294 | 0.5340191846947128 | 0.509562857013943 | 0.89796 | 0.5963719971695486 |
| 3 | 0.5409393929290771 | 0.5412185870660677 | 0.5123980166464907 | 0.89796 | 0.5967281034435536 |
| 4 | 0.5340481583976746 | 0.549233990622756 | 0.5147455230827509 | 0.89796 | 0.5983962953976021 |

Best checkpoint：

```text
epoch: 2
checkpoint metric: logloss
best metric: 0.5963719971695486
```

结论：DCN-v2 已接入一条命令训练、valid 评估、metrics 和 checkpoint 流程。该 smoke 中 valid AUC / GAUC 较弱，只能说明本地 smoke 配置下尚未形成强泛化结论，不阻塞后续 large/full subset 验证。

## 2026-05-28 — DCN-v2 initialization diagnosis and rerun

类型：`tiny subset training / diagnostic`

目的：

- 诊断 DCN-v2 valid AUC 接近随机的问题。
- 检查未训练初始化的预测概率、LogLoss 和 logit 分布。
- 只修初始化尺度，不做超参搜索。

### 修复前复跑：`20260528-012130-dcnv2_smoke-dcnv2`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\dcnv2_smoke.yaml --device cpu
```

Metrics：

| epoch | train AUC | valid AUC | train GAUC | valid GAUC | valid LogLoss |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.5596665820712516 | 0.5241001837053098 | 0.5395428199899386 | 0.5076045845847659 | 0.59944790928456 |
| 2 | 0.5909355377465221 | 0.5340191846947128 | 0.5663241825971963 | 0.509562857013943 | 0.5963719971695486 |
| 3 | 0.6185828145981577 | 0.5412185870660677 | 0.5887942039563439 | 0.5123980166464907 | 0.5967281034435536 |
| 4 | 0.6502114529137548 | 0.549233990622756 | 0.6152072043892258 | 0.5147455230827509 | 0.5983962953976021 |

判断：

- train AUC 有学习趋势，但 valid AUC 仍偏弱。
- 问题不是完全学不动，更像初始化和 tiny smoke 泛化共同影响。

### 未训练初始化诊断

在 50k train rows 上，修复前：

```text
batch base rate: 0.266400009393692
constant batch base LogLoss: 0.5796452164649963
init LogLoss: 0.7147810888671875
mean predicted probability: 0.40860605239868164
logit std: 1.0905441045761108
embedding std mean: 0.9925519704818726
cross weight std: ~0.111
output bias: 0.05396714061498642
```

修复后：

```text
metadata train base logit: -1.1410586334170694
init LogLoss: 0.5812454168701172
mean predicted probability: 0.24155035614967346
logit std: 0.008613877929747105
embedding std mean: 0.009735829196870327
cross weight std: ~0.010
output bias: -1.1410586833953857
```

解释：

- 之前 `nn.Embedding` 默认接近 `N(0,1)`，直接进入 DCN-v2 cross network，导致初始 logit 过宽。
- output bias 未对齐 train base rate，使平均预测概率明显高于 base rate。
- 修复后 init LogLoss 接近 constant-base LogLoss，初始化不再把模型推到错误概率区间。

### 修复后 overfit：`dcnv2_overfit`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\dcnv2_smoke.yaml --overfit --device cpu
```

Result：

```text
initial_loss: 0.40232211351394653
final_loss: 5.579277009237912e-20
target_loss: 0.05
passed: true
```

注意：`run_overfit` 当前记录的 `initial_loss` 是第 1 个 overfit epoch 后的 loss，不是严格未训练 loss；未训练 loss 以上面的初始化诊断为准。

### 修复后 train smoke：`20260528-012603-dcnv2_smoke-dcnv2`

Command：

```powershell
.\.venv\Scripts\python.exe scripts\train.py --config configs\dcnv2_smoke.yaml --device cpu
```

Output：

```text
outputs/runs/20260528-012603-dcnv2_smoke-dcnv2/
outputs/runs/20260528-012603-dcnv2_smoke-dcnv2/metrics.jsonl
outputs/runs/20260528-012603-dcnv2_smoke-dcnv2/summary.json
outputs/runs/20260528-012603-dcnv2_smoke-dcnv2/checkpoints/best.pt
```

Metrics：

| epoch | train AUC | valid AUC | train GAUC | valid GAUC | GAUC coverage | valid LogLoss |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.8646336669951349 | 0.6689654983604069 | 0.8661423294790751 | 0.5930922436479876 | 0.89796 | 0.5616743797625655 |
| 2 | 0.9507707756335112 | 0.6515789328198313 | 0.9283259730720234 | 0.5903481854927853 | 0.89796 | 0.6405017679536366 |
| 3 | 0.9670724073822755 | 0.6475846881987664 | 0.9424242555560012 | 0.5875580599389937 | 0.89796 | 0.7040453644895988 |

Best checkpoint：

```text
epoch: 1
checkpoint metric: logloss
best metric: 0.5616743797625655
```

结论：

- DCN-v2 valid AUC 接近随机的主要原因是初始化尺度和 output bias 问题。
- 修复后模型不再近随机，但 train AUC 很快明显高于 valid AUC，head-truncated smoke 存在过拟合趋势。
- 该结果仍是 smoke，不是正式模型指标。

## 2026-05-28 — Full 120M strict preprocessing

类型：`preprocessing / full data`

目的：

- 在本地 CPU 上对完整 `data/Tenrec/ctr_data_1M.csv` 运行 strict protocol 两遍流式预处理。
- 补全 G1 内存有界证据：从 1M、10M 扩展到 full 120M。
- 生成后续 GPU 训练使用的 full materialized splits 和 hash-bucket shuffled train CSV。

前置磁盘检查：

```text
D: free bytes: 236,546,326,528
```

Command：

```powershell
.\.venv\Scripts\python.exe scripts\run_with_resource_monitor.py --output outputs\inspection\preprocess_full_resource_monitor_psutil.json --interval 1.0 -- .\.venv\Scripts\python.exe scripts\preprocess_ctr_data.py --config configs\ctr_full.yaml
```

Output：

```text
outputs/preprocessed/ctr-3999a64f6fad/
outputs/preprocessed/ctr-3999a64f6fad/metadata.json
outputs/preprocessed/ctr-3999a64f6fad/materialized/train.csv
outputs/preprocessed/ctr-3999a64f6fad/materialized/valid.csv
outputs/preprocessed/ctr-3999a64f6fad/materialized/test.csv
outputs/inspection/preprocess_full_resource_monitor_psutil.json
```

Preprocessing result：

| item | value |
| --- | ---: |
| run_id | `ctr-3999a64f6fad` |
| train rows | 97,146,674 |
| valid rows | 11,597,816 |
| test rows | 11,597,816 |
| peak RSS | 453.531 MiB |
| monitor backend | psutil |
| Pass1 elapsed | 448.759s |
| Pass2 elapsed | 889.919s |
| total monitor elapsed | 1341.987s |
| user_id vocab size | 999,449 |
| item_id vocab size | 2,125,651 |
| video_category vocab size | 4 |
| gender vocab size | 5 |
| age vocab size | 10 |

OOV 不变量：

| split | user_id OOV rows | item_id OOV rows | item_id OOV rate |
| --- | ---: | ---: | ---: |
| valid | 0 | 100,564 | 0.008670942874072152 |
| test | 0 | 103,567 | 0.008929870934320738 |

Label counts：

| split | click=0 | click=1 |
| --- | ---: | ---: |
| train | 73,764,358 | 23,382,316 |
| valid | 8,556,785 | 3,041,031 |
| test | 9,140,303 | 2,457,513 |

Materialized file sizes：

| file | bytes |
| --- | ---: |
| `train.csv` | 2,128,091,876 |
| `valid.csv` | 254,545,792 |
| `test.csv` | 254,929,019 |

### Full hash-bucket shuffled train

Command：

```powershell
.\.venv\Scripts\python.exe - <ensure_shuffled_train metadata=outputs/preprocessed/ctr-3999a64f6fad/metadata.json seed=20260525 bucket_count=64>
```

Output：

```text
outputs/preprocessed/ctr-3999a64f6fad/materialized/train_shuffled_seed20260525_b64.csv
size bytes: 2,128,091,876
```

G1 memory comparison：

| run | rows | peak RSS | note |
| --- | ---: | ---: | --- |
| 1M | 1,000,200 | 54.77 MiB | `ctr-454e7ccb12f7` |
| 10M | 10,000,035 | 136.68 MiB | `ctr-1961cdee479f` |
| full | 120,342,306 | 453.531 MiB | `ctr-3999a64f6fad` |

判断：

- full 行数约为 10M 的 12 倍，但 peak RSS 从 136.68 MiB 增至 453.531 MiB，没有接近按行数线性增长。
- 内存增长主要来自 full train vocab，尤其 `item_id` vocab 从 766,087 增至 2,125,651。
- valid/test `user_id` OOV 均为 0，符合 user 内顺序 split 不变量。
- full valid/test `item_id` OOV 率约 0.87% / 0.89%，低于 10M 的约 4.8% / 5.0%，符合训练覆盖度增加后 OOV 压力下降的预期。
- 本 run 只是 full preprocessing 产物，不包含模型训练指标。
