# v3.0D First Batch Run Templates

日期：2026-04-29
状态：active-template
范围：Phase D 首批真实 run 执行模板
约束：
- 本文档用于执行计划，不写入正式 `artifacts/validation-results/phase_d/real_world_validation.json`
- 只有真实执行完成后的结果，才能落入正式 payload 的 `runs[]`

## 1. 使用原则

1. 执行入口必须走正式主链：`Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review`
2. 每个模板执行后，都要把真实结果回填到正式 payload，而不是保留模板状态。
3. 每个 run 至少补齐：
   - `workflow_steps[]`
   - `success_state`
   - `failure_points[]`
   - `recovery_actions[]`
   - `evidence_reviews[]`
   - `honesty_checks{}`
   - `user_visible_confusions[]`

## 2. 首批模板

### RWT-001 Full Main Chain Baseline

- target_samples: `D-001`
- objective: 验证标准外部论文从 Search 到 Review 的完整主链是否贯通
- operator_path: `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review`
- primary_checks:
  - Search 命中论文并能发起正式导入
  - Import 后 KB 状态、去重、indexing 状态可见
  - Read 页面可打开并跳转到有效正文位置
  - Chat 引用证据后能被 Notes 消费
  - Compare 与 Review 能消费前序上下文而不丢失 run 关联
- evidence_probe:
  - 至少抽查 2 个 claim
  - 至少验证 1 次 citation jump
  - 记录 unsupported claim 是否可见
- honesty_probe:
  - `metadata-only` 与 `fulltext-ready` 是否真实区分
  - 失败时是否暴露明确恢复路径

### RWT-002 Figure And Long Context Chain

- target_samples: `D-020`, `D-040`
- objective: 验证 figure-heavy 与 long-survey 样本在阅读、问答、比较、审查环节的证据消费是否稳定
- operator_path: `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review`
- primary_checks:
  - 图表相关 claim 的 citation jump 是否落到合理区域
  - 长综述跨章节提问时，检索与 compare 是否返回同一篇内的稳定证据
  - Review 是否显式暴露 unsupported / weakly supported claims
- expected_risks:
  - caption grounding 失败
  - chunk 边界切断跨章节证据
  - compare 汇总过度抽象

### RWT-003 Cross-Discipline KB Compare Run

- target_samples: `D-050`
- objective: 验证跨学科 KB 中 Compare / Review 是否能维持来源边界，不把异领域证据错误混合
- operator_path: `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review`
- primary_checks:
  - KB 内多篇文献导入后状态一致
  - Chat 回答能区分不同论文来源
  - Compare 输出不会把 protein folding、climate forecasting、RAG 方法混为单一结论
  - Review Draft 的 claims 具备可回跳来源
- honesty_probe:
  - 证据不足时是否明确说“不足以支持”
  - citation jump 失败时是否暴露弱点而不是静默成功

### RWT-004 OCR And Failure Boundary Run

- target_samples: `D-010`, `D-070`
- objective: 主动寻找 OCR、版面解析、证据跳转类阻断或退化失败
- operator_path: `Import -> KB -> Read -> Chat -> Notes -> Review`
- primary_checks:
  - 扫描件导入后的状态表达是否诚实
  - OCR 差时，Chat / Review 是否退化为 metadata-only 但仍清楚可解释
  - layout-heavy 页面上的 citation jump 是否明显漂移
- default_failure_buckets:
  - `blocking`: 无法导入、无法打开、全文不可消费
  - `degrading`: 证据可见但跳转不稳、claim 支撑不足
  - `paper_cut`: 说明文案、状态文案、局部交互混淆

## 3. 回填顺序

1. 执行一个模板
2. 立即把真实结果写入 `real_world_validation.json` 的 `runs[]`
3. 执行 `python3 scripts/evals/v3_0_real_world_validation_report.py`
4. 检查 `docs/plans/v3_0/reports/validation/v3_0_real_world_validation.md` 与 summary JSON 是否同步刷新
