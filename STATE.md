> STATE.md 只反映"现在"。完整历史在 docs/。此文件持续覆盖更新，不追加；更新规则见 AGENTS.md §4.5。

# 当前状态

## 1. 当前阶段

Phase B 本地 DIN 审核阶段：strict Phase A baseline 已完成，`hist_1..hist_10` 已接入 DIN 本地模型与 CPU smoke，等待 Eddy review 后再 commit / push / 上服务器。

## 2. 最近完成

- 2026-05-28：完成 LR/MLP/DeepFM/DCN-v2 strict full 多 seed baseline；完整指标见 `docs/experiment_log.md`。
- 2026-05-28：完成 tensor loader 优化和等价性验证；决策与性能边界见 `docs/decision_log.md`、`docs/issue_log.md`。
- 2026-05-28：完成 `hist_1..hist_10` 泄漏闸门验证 PASS；方法和限制见 `docs/experiment_log.md`、`docs/data_notes.md`。
- 2026-05-28：确认 full `ctr_data_1M.csv` 中 `hist_*` 是 user 级静态快照；DIEN 已移出当前路线图，见 `docs/data_notes.md`、`docs/decision_log.md`。
- 2026-05-28：完成 full hist preprocessing，DIN 使用新 run `ctr-972e0dcb2b8d`；产物在 ignored `outputs/preprocessed/`。
- 2026-05-29：完成 DIN 本地实现、focused tests、overfit gate 和 1M hist CPU smoke；完整记录见 `docs/experiment_log.md`。

## 3. 下一步

1. Eddy review DIN 实现、focused tests、overfit gate 和 1M CPU smoke 结果。
2. Eddy 批准后，按本地流程 stage / commit / push；commit message 默认中文，type 保留英文 conventional 前缀。
3. 服务器 read-only pull 最新代码，不从服务器 push。
4. 确认 `ctr-972e0dcb2b8d` 已在服务器可用并生成 Linux 路径版 `metadata_server.json`。
5. 服务器只跑 DIN GPU sanity 和单 seed full，不直接 multi-seed。

## 4. 活跃约束

- `STATE.md` 不是事实源；事实仍以 `AGENTS.md`、`docs/data_notes.md`、`docs/decision_log.md`、`docs/experiment_log.md`、`docs/issue_log.md` 为准。
- 不提交 `data/`、`outputs/`、`.venv/`、checkpoints、logs、tokens、private keys。
- 不把 smoke、single seed 或未审结果写成正式结论；指标数字留在 `docs/experiment_log.md`。
- strict protocol 仍是主线：不负采样、user 内文件顺序 split、train-only vocab、OOV/missing 保留、AUC/GAUC/LogLoss。
- DIN 语义限定为 static hist snapshot + target-dependent attention；当前不做 DIEN。
- 代码/文档默认只在本地编辑；服务器只 `git pull` 和跑训练，server-only config 放在 repo 外，未 commit 改动不超过 24 小时；commit message 默认中文（type 保留英文 conventional 前缀）。
- 当前任务未获 Eddy 明确授权时，不 commit、不 push。
