> STATE.md 只反映"现在"。完整历史在 docs/。此文件持续覆盖更新，不追加；更新规则见 AGENTS.md §4.5。

# 当前状态

## 1. 当前阶段

Phase D ablation 完成（9 runs，3 模型 × 3 seeds）。闸门 1 PASS，闸门 2 FAIL-new-issue（ISSUE-20260530-001 已立，不阻塞 commit）。当前进入**收口阶段**：写 experiment_log、issue_log、daily log、STATE.md、project_summary，commit 后写简历 bullet 和 paper_review。

## 2. 最近完成

- 2026-05-28：完成 LR/MLP/DeepFM/DCN-v2 strict full 多 seed baseline；完整指标见 `docs/experiment_log.md`。
- 2026-05-29：完成 DIN strict FULL 3 seeds；完成 Phase C official-compatible dual-protocol 对照；完成 Phase D 本地实现与 streaming 改造。
- 2026-05-30：完成 Phase D full preprocessing（ctr-5580cbc9aa26-stats，peak RSS 6056 MiB，97 min）。
- 2026-05-30：完成 DIN numeric_features 接入（models.py / training.py / tests），37 tests OK，已 commit ca84c9f。
- 2026-05-30：完成 Phase D ablation 9 runs（LR/DCN-v2/DIN × 3 seeds），全部 DONE，0 跳过。
- 2026-05-30：闸门验证 PASS（数字一手抽验）；ISSUE-20260530-001 立项（PCOC OOF shift）。

## 3. 下一步

1. commit docs（experiment_log Phase D 章节 + issue_log + daily log + STATE.md + project_summary）。
2. 写简历 bullet（Phase D ablation 结论，有证据后才写入 docs/project_summary.md 正式条目）。
3. 整理 Phase C / Phase D 结论进 `docs/paper_review.md`。
4. 如需继续 stats 特征方向：先处理 ISSUE-20260530-001（PCOC OOF shift）。

## 4. 活跃约束

- `STATE.md` 不是事实源；事实仍以 `AGENTS.md`、`docs/data_notes.md`、`docs/decision_log.md`、`docs/experiment_log.md`、`docs/issue_log.md` 为准。
- 不提交 `data/`、`outputs/`、`.venv/`、checkpoints、logs、tokens、private keys。
- strict protocol 仍是主线；指标数字留在 `docs/experiment_log.md`。
- DIN 语义限定为 static hist snapshot + target-dependent attention；当前不做 DIEN。
- ISSUE-20260530-001（PCOC OOF shift）Open，Phase D 收口不阻塞，未来继续 stats 特征前必须先处理。
- 代码/文档默认只在本地编辑；服务器只 `git pull` 和跑训练；commit message 默认中文。
- 当前任务未获 Eddy 明确授权时，不 commit、不 push。
