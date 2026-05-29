> STATE.md 只反映"现在"。完整历史在 docs/。此文件持续覆盖更新，不追加；更新规则见 AGENTS.md §4.5。

# 当前状态

## 1. 当前阶段

Phase D full 前本地工作已闭环：leakage-safe 统计特征已改成 streaming，并完成 streaming vs 内存原型 1M 等价性对拍（6 列 max abs diff ≤ 1e-7，纯浮点噪声）+ 全套 36 tests OK。下一步是 commit/push 后上服务器跑 full（留给新对话交接执行）。尚未跑 full、未上服务器、Phase D 代码尚未 commit。

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
- 2026-05-29：完成 Phase D leakage-safe stats features 本地设计、实现、泄漏闸门和 1M smoke；完整记录见 `docs/phase_d_design.md`、`docs/experiment_log.md`。
- 2026-05-29：`preprocess_ctr_stats.py` 已改 streaming（fold-out 累减法），并完成 streaming vs 内存原型 1M 等价性对拍 PASS + 全套 36 tests OK。

## 3. 下一步

1. commit/push Phase D 本地代码与文档（streaming 等价性已验证，可提交）。stage：src/tenrec/{models,torch_data,training}.py、tests/{test_phase_d_stats,test_torch_data,test_torch_models}.py、scripts/preprocess_ctr_stats.py、docs/phase_d_design.md、docs 日志、STATE.md。
2. 服务器 pull 后跑 Phase D full preprocessing（source = ctr-972e0dcb2b8d），生成 numeric_features full run；用 run_with_resource_monitor 实测 peak RSS。
3. 服务器跑 LR / DCN-v2（可含 DIN）+ Phase D 特征，multi-seed，做 feature ablation（有统计特征 vs 无）；对照表进 experiment_log。
4. Phase D 待 Eddy 拍板项：alpha=20（建议直接定）、标准化（不加分桶）、先只上高 ROI 特征集合。
5. 收口：Phase C 结论整理进 `docs/paper_review.md`，写简历 bullet。
6. 服务器只 pull 跑训练，不改源码；DeepFM/DIN 是否接 numeric_features 待定（当前仅 LR/MLP/DCN-v2 接入）。

## 4. 活跃约束

- `STATE.md` 不是事实源；事实仍以 `AGENTS.md`、`docs/data_notes.md`、`docs/decision_log.md`、`docs/experiment_log.md`、`docs/issue_log.md` 为准。
- 不提交 `data/`、`outputs/`、`.venv/`、checkpoints、logs、tokens、private keys。
- 不把 smoke、single seed 或未审结果写成正式结论；指标数字留在 `docs/experiment_log.md`。
- strict protocol 仍是主线：不负采样、user 内文件顺序 split、train-only vocab、OOV/missing 保留、AUC/GAUC/LogLoss。
- Phase D 统计特征必须 leakage-safe：train 用 k-fold OOF，valid/test 只查 train 全量统计；naive in-sample target encoding 仅作泄漏对照。
- DIN 语义限定为 static hist snapshot + target-dependent attention；当前不做 DIEN。
- 代码/文档默认只在本地编辑；服务器只 `git pull` 和跑训练，server-only config 放在 repo 外，未 commit 改动不超过 24 小时；commit message 默认中文（type 保留英文 conventional 前缀）。
- 当前任务未获 Eddy 明确授权时，不 commit、不 push。
