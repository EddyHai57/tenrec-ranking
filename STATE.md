> STATE.md 只反映"现在"。完整历史在 docs/。此文件持续覆盖更新，不追加；更新规则见 AGENTS.md §4.5。

# 当前状态

## 1. 当前阶段

Phase D 严格 ablation 重训 + DCN-v2 HP sweep 完成。**准备换 GPU 服务器**：当前 autodl 实例 50G 数据盘容量不足（已满过一次导致 checkpoint 写失败），长任务有中断风险；数据将通过 autodl 网站直接迁移到新实例。

## 2. 最近完成

- 2026-05-30：严格 ablation 重训（LR/DCN-v2 × 3 seeds，同 base run `ctr-972e0dcb2b8d`）完成，修补原 Phase D baseline 使用不同 preprocessing run 的归因瑕疵。
- 2026-05-30：DCN-v2 HP sweep（7 组合 valid 选优）+ sweep-best test 复核完成。
- 2026-05-30：原 Phase D"DCN-v2 统计显著提升"经严格对照后**撤回**；统计特征与模型容量均只剩小幅增益，瓶颈在特征信息量。详见 experiment_log / project_summary。
- 新增 `configs/phase_d_lr_nostats_full.yaml`、`configs/phase_d_dcnv2_nostats_full.yaml`（commit 292dc44）。

## 3. 下一步

1. commit + push 本轮文档（experiment_log / project_summary / STATE）。
2. 换 GPU 服务器：autodl 网站迁移数据（`ctr-972e0dcb2b8d` + `ctr-5580cbc9aa26-stats`），新机配 SSH key + `git pull`，跑 smoke gate（unittest + overfit）。
3. 新机重跑清单：sweep-best 多 seed 确认 + PCOC OOF shift 诊断（需先改 `train.py` dump per-row 预测，要 push）。
4. 写简历 bullet（基于撤回后的修正结论，不夸大）。

## 4. 活跃约束

- `STATE.md` 不是事实源；事实仍以 `AGENTS.md`、`docs/data_notes.md`、`docs/decision_log.md`、`docs/experiment_log.md`、`docs/issue_log.md` 为准。
- 原 Phase D"DCN-v2 统计显著"已撤回；严格对照下统计特征/模型容量增益均 < 3σ。
- 当前服务器 checkpoints 已清理（可重训复现，指标级一致）；summary/metrics 指标证据保留。
- 换服务器期间数据以 autodl 网站迁移为准；新机训练前先验证数据完整性。
- ISSUE-20260530-001（PCOC OOF shift）Open，留新机诊断。
- 不提交 `data/`、`outputs/`、`.venv/`、checkpoints、logs、tokens、private keys。
- strict protocol 仍是主线；指标数字留在 `docs/experiment_log.md`。
- 代码/文档默认只在本地编辑；服务器只 `git pull` 和跑训练；commit message 默认中文。
- 当前任务未获 Eddy 明确授权时，不 commit、不 push。
