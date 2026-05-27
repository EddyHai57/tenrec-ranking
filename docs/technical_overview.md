# Tenrec 推荐排序系统 — 技术文档

## 1. 项目目标

基于腾讯 Tenrec feed 数据，构建单场景 CTR 排序系统，覆盖从数据契约、特征工程、模型迭代到评估审计的完整链路。

## 2. 数据与契约

- 数据源：`ctr_data_1M.csv`，1.2 亿行真实曝光/点击。
- 样本粒度：一行 = 一次曝光（exposure-like），不去重。
- label：`click`（0/1）。
- 切分：user 内文件顺序 80/10/10（无 timestamp，顺序隐含时间）。
- OOV 率依赖训练覆盖度：1M sample 的 valid item OOV 约 30.1%，10M sample（run_id `ctr-1961cdee479f`）降至约 4.8%，全量 120M 下预计更低。
- 特征分级：
  - 一阶：`user_id, item_id, video_category, gender, age`
  - 序列：`hist_1..hist_10`（泄漏验证后启用）
  - 多任务标签：`follow, like, share`

## 3. 数据处理 Pipeline

两遍流式架构（支持全量，不依赖整文件内存）：

- Pass 1：扫描 → user-order split → 仅 train 行建 vocab。
- Pass 2：冻结 vocab 编码 → 物化 train/valid/test。
- 编码约定：`0=OOV / 1=missing / 2..=seen`，词表落盘 + run_id（内容 hash）可复现。
- OOV 策略：OOV 率是训练样本规模的函数，小样本下压力更高；统一保留槽 + 未来冷启动特征补充。

## 4. 模型迭代路线

| 阶段 | 模型 | 目的 |
| --- | --- | --- |
| Baseline | LR | 参考线 / 管道验证 |
| 浅层 | MLP | 非线性 |
| 特征交互 | DeepFM | 显式二阶 + 隐式高阶 |
| 进阶交互 | DCN-v2 | 显式高阶 cross |
| 序列建模 | DIN / BST | 用户兴趣建模（依赖 hist 泄漏验证） |
| 多任务 | MMOE / PLE | click/like/share/follow 联合建模 |

## 5. 评估

- 指标：AUC、impression-weighted GAUC、LogLoss。
- GAUC 口径：跳过单类用户，**强制并报 coverage**。
- 对比维度：模型间纵向对比 + 特征 ablation。
- 报告分级：smoke / tiny / large-subset / full，禁止 smoke 冒充正式结果。

## 6. 测试与质量

- 单元测试：split 整数公式、train-only vocab、missing 优先 OOV、AUC/LogLoss/GAUC known-answer、单类用户跳过。
- 回归：split 结果对拍 oracle（807282/96459/96459）。
- 不变量断言：valid/test user_id OOV = 0（切分正确性硬校验）。
- learnability gate：LR 跑通证明管道有信号后才进深度模型。

## 7. 工业化水平

- 本地/服务器同一 preprocessing path，代码跨平台（pathlib/utf-8）。
- 依赖锁版本，run_id + git commit + config 全程可追溯。
- 数据/产出/checkpoint 不进 git，文档为 canonical fact source。
- local 开发 smoke → push → server pull → server full train 工作流。
- 边界：离线实验级，**不含线上 serving / A/B / 实时特征**，不宣称生产可用。

## 8. 项目亮点（差异化优势）

- **真实工业级数据**：1.2 亿行腾讯 feed 真实曝光/点击，远超 Criteo/MovieLens 等公开 demo 数据集的真实度。
- **可审计性是核心壁垒**：train-only vocab 防泄漏、GAUC 强制报 coverage、指标 known-answer 测试、split 不变量硬断言（user_id OOV=0）——多数候选人项目只报 AUC，讲不清这些。
- **全量可扩展的两遍流式 pipeline**：不依赖整文件内存，本地 smoke 与服务器 full 走同一条代码路径。
- **主动的数据契约风险识别**：无 timestamp、hist 泄漏未排除、`(user,item)` click 冲突、小样本 item OOV 压力，全部显式记录并定边界，而非默认忽略。
- **完整工程化闭环**：run_id + git commit + config 全程可追溯，依赖锁版本，文档为 canonical fact source。

## 9. 拔高点（提升竞争力）

- **序列建模 DIN / BST**：利用 `hist_1..hist_10` 做用户兴趣建模；前置 hist 泄漏验证是关键卖点（体现对数据严谨性的把控）。
- **多任务 MMOE / PLE**：Tenrec 的 `click/like/share/follow` 多行为标签是天然多任务素材，从单任务 CTR 升级到联合建模。
- **冷启动 / OOV 处理**：OOV 处理机制保留；但严重程度随训练覆盖度下降，1M 子集约 30%、10M 降至约 5%，全量下 ID embedding 的 OOV 压力远小于小样本估计。
- **多场景能力**：Tenrec 四场景存在 user/item overlap，可扩展跨场景迁移或多域建模。

## 10. 最终交付

- 完整可复现的 CTR 排序实验框架。
- LR→DCN-v2（+序列/多任务）模型对比与 ablation。
- 全程可审计的数据契约、指标 provenance 与实验日志。
