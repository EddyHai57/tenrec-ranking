> STATE.md 只反映"现在"。完整历史在 docs/。此文件持续覆盖更新，不追加；更新规则见 AGENTS.md §4.5。

# 当前状态

## 1. 当前阶段

Phase B 准备阶段：strict Phase A baseline 已完成，当前正在把 `hist_1..hist_10` 接入 DIN 前的数据与模型链路。

## 2. 最近完成

- 2026-05-28：完成 LR/MLP/DeepFM/DCN-v2 strict full 多 seed baseline；完整指标见 `docs/experiment_log.md`。
- 2026-05-28：完成 tensor loader 优化和等价性验证；决策与性能边界见 `docs/decision_log.md`、`docs/issue_log.md`。
- 2026-05-28：完成 `hist_1..hist_10` 泄漏闸门验证 PASS；方法和限制见 `docs/experiment_log.md`、`docs/data_notes.md`。
- 2026-05-28：确认 full `ctr_data_1M.csv` 中 `hist_*` 是 user 级静态快照；DIEN 已移出当前路线图，见 `docs/data_notes.md`、`docs/decision_log.md`。
- 2026-05-28：完成 full hist preprocessing，DIN 使用新 run `ctr-972e0dcb2b8d`；产物在 ignored `outputs/preprocessed/`。

## 3. 下一步

1. 确认 `ctr-972e0dcb2b8d` 已通过 Hugging Face private repo 传到服务器，并生成 Linux 路径版 `metadata_server.json`。
2. 实现 DIN 本地 CPU smoke：共享 item/hist embedding、target-dependent attention、padding mask、无 softmax。
3. 补 DIN focused tests：共享参数、padding-only mask、OOV 不 mask、target-dependent attention、forward shape。
4. 本地跑 DIN overfit gate 和 1M smoke，通过后再请求 Eddy 审。
5. Eddy 批准后，服务器只跑 DIN GPU sanity 和单 seed full，不直接 multi-seed。

## 4. 活跃约束

- `STATE.md` 不是事实源；事实仍以 `AGENTS.md`、`docs/data_notes.md`、`docs/decision_log.md`、`docs/experiment_log.md`、`docs/issue_log.md` 为准。
- 不提交 `data/`、`outputs/`、`.venv/`、checkpoints、logs、tokens、private keys。
- 不把 smoke、single seed 或未审结果写成正式结论；指标数字留在 `docs/experiment_log.md`。
- strict protocol 仍是主线：不负采样、user 内文件顺序 split、train-only vocab、OOV/missing 保留、AUC/GAUC/LogLoss。
- DIN 语义限定为 static hist snapshot + target-dependent attention；当前不做 DIEN。
- 当前任务未获 Eddy 明确授权时，不 commit、不 push。
