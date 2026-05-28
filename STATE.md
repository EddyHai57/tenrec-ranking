> STATE.md 只反映"现在"。完整历史在 docs/。此文件持续覆盖更新，不追加；更新规则见 AGENTS.md §4.5。

# 当前状态

## 1. 当前阶段

Phase C dual-protocol 对照实现中。DIN strict full 已完成；official-compatible preprocessing 和 PCOC 已完成本地 smoke，等待 commit / push 后进入服务器 full 3 模型 × 3 seeds。

## 2. 最近完成

- 2026-05-28：完成 LR/MLP/DeepFM/DCN-v2 strict full 多 seed baseline；完整指标见 `docs/experiment_log.md`。
- 2026-05-28：完成 tensor loader 优化和等价性验证；决策与性能边界见 `docs/decision_log.md`、`docs/issue_log.md`。
- 2026-05-28：完成 `hist_1..hist_10` 泄漏闸门验证 PASS；方法和限制见 `docs/experiment_log.md`、`docs/data_notes.md`。
- 2026-05-28：确认 full `ctr_data_1M.csv` 中 `hist_*` 是 user 级静态快照；DIEN 已移出当前路线图，见 `docs/data_notes.md`、`docs/decision_log.md`。
- 2026-05-28：完成 full hist preprocessing，DIN 使用新 run `ctr-972e0dcb2b8d`；产物在 ignored `outputs/preprocessed/`。
- 2026-05-29：完成 DIN 本地实现、focused tests、overfit gate 和 1M hist CPU smoke；完整记录见 `docs/experiment_log.md`。
- 2026-05-29：完成 DIN strict FULL 3 seeds 服务器训练和 test 评估；完整指标见 `docs/experiment_log.md`。
- 2026-05-29：启动 Phase C，新增 PCOC 指标和 official-compatible preprocessing，并完成 official 1M smoke 与 LR overfit gate。

## 3. 下一步

1. 跑完整本地回归测试，确认 PCOC / official preprocessing / torch training 未破坏旧链路。
2. Eddy 确认后 commit / push Phase C 本地实现。
3. 服务器 read-only pull 后跑 full official preprocessing 和 LR / DeepFM / DCN-v2 3 seeds。
4. 生成 `dual_protocol_summary.md`，严格区分 official-compatible reproduction 与 exact paper replication。
5. 如需讨论原始 CTR 校准失真，新增 original-distribution calibration 指标，不能直接用当前 PCOC 下结论。

## 4. 活跃约束

- `STATE.md` 不是事实源；事实仍以 `AGENTS.md`、`docs/data_notes.md`、`docs/decision_log.md`、`docs/experiment_log.md`、`docs/issue_log.md` 为准。
- 不提交 `data/`、`outputs/`、`.venv/`、checkpoints、logs、tokens、private keys。
- 不把 smoke、single seed 或未审结果写成正式结论；指标数字留在 `docs/experiment_log.md`。
- strict protocol 仍是主线：不负采样、user 内文件顺序 split、train-only vocab、OOV/missing 保留、AUC/GAUC/LogLoss。
- DIN 语义限定为 static hist snapshot + target-dependent attention；当前不做 DIEN。
- 代码/文档默认只在本地编辑；服务器只 `git pull` 和跑训练，server-only config 放在 repo 外，未 commit 改动不超过 24 小时；commit message 默认中文（type 保留英文 conventional 前缀）。
- 当前任务未获 Eddy 明确授权时，不 commit、不 push。
