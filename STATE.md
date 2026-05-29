> STATE.md 只反映"现在"。完整历史在 docs/。此文件持续覆盖更新，不追加；更新规则见 AGENTS.md §4.5。

# 当前状态

## 1. 当前阶段

Phase C dual-protocol 对照已完成，待记录与提交。official-compatible full 3 模型 × 3 seeds 已跑完，并完成 Official->Strict cross-protocol PCOC 校准评估。

## 2. 最近完成

- 2026-05-28：完成 LR/MLP/DeepFM/DCN-v2 strict full 多 seed baseline；完整指标见 `docs/experiment_log.md`。
- 2026-05-28：完成 tensor loader 优化和等价性验证；决策与性能边界见 `docs/decision_log.md`、`docs/issue_log.md`。
- 2026-05-28：完成 `hist_1..hist_10` 泄漏闸门验证 PASS；方法和限制见 `docs/experiment_log.md`、`docs/data_notes.md`。
- 2026-05-28：确认 full `ctr_data_1M.csv` 中 `hist_*` 是 user 级静态快照；DIEN 已移出当前路线图，见 `docs/data_notes.md`、`docs/decision_log.md`。
- 2026-05-28：完成 full hist preprocessing，DIN 使用新 run `ctr-972e0dcb2b8d`；产物在 ignored `outputs/preprocessed/`。
- 2026-05-29：完成 DIN 本地实现、focused tests、overfit gate 和 1M hist CPU smoke；完整记录见 `docs/experiment_log.md`。
- 2026-05-29：完成 DIN strict FULL 3 seeds 服务器训练和 test 评估；完整指标见 `docs/experiment_log.md`。
- 2026-05-29：启动 Phase C，新增 PCOC 指标和 official-compatible preprocessing，并完成 official 1M smoke 与 LR overfit gate。
- 2026-05-29：完成 Phase C official-compatible FULL 3 模型 × 3 seeds 和 Official->Strict cross-protocol evaluation；完整指标见 `docs/experiment_log.md`。

## 3. 下一步

1. 提交 Phase C full 结果文档，保持 `project_summary.md` 不写具体指标数字。
2. 把 Phase C 结论整理进 `docs/paper_review.md`：official-compatible 提高 AUC，但需要负采样校准。
3. 设计同数据契约下的 hist ablation：no-hist / target-attention / shuffled-hist。
4. 规划 Phase D 低泄漏统计特征，优先补足“特征空间 > 模型复杂度”的解释链。
5. 如需 exact paper replication，另开独立协议，不与 strict mainline 混写。

## 4. 活跃约束

- `STATE.md` 不是事实源；事实仍以 `AGENTS.md`、`docs/data_notes.md`、`docs/decision_log.md`、`docs/experiment_log.md`、`docs/issue_log.md` 为准。
- 不提交 `data/`、`outputs/`、`.venv/`、checkpoints、logs、tokens、private keys。
- 不把 smoke、single seed 或未审结果写成正式结论；指标数字留在 `docs/experiment_log.md`。
- strict protocol 仍是主线：不负采样、user 内文件顺序 split、train-only vocab、OOV/missing 保留、AUC/GAUC/LogLoss。
- DIN 语义限定为 static hist snapshot + target-dependent attention；当前不做 DIEN。
- 代码/文档默认只在本地编辑；服务器只 `git pull` 和跑训练，server-only config 放在 repo 外，未 commit 改动不超过 24 小时；commit message 默认中文（type 保留英文 conventional 前缀）。
- 当前任务未获 Eddy 明确授权时，不 commit、不 push。
