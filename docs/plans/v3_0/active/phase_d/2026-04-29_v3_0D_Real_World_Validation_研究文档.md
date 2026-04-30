---
标题：ScholarAI v3.0-D Real-world Validation 研究文档
日期：2026-04-29
状态：research
范围：真实论文集验证、真实工作流穿透、失败模式盘点、验收报告结构
前提：文档层假设 Phase A / Phase B / Phase C 的结构性产物已完成并可复用；不等同于仓库当前代码状态已全部完成
---

# 1. 研究目标

本文件定义 ScholarAI `v3.0-D: Real-world Validation` 的研究方案。

它回答的核心问题是：

```txt
怎样证明 ScholarAI 不只是 benchmark 上看起来更强，
而是在真实论文、真实导入、真实阅读、真实问答和真实失败模式下仍然成立。
```

本文件只定义验证目标、样本结构、工作流范围、失败模式、验收产物与边界；不展开到具体执行脚本、逐页面测试用例或最终报告正文。

# 2. 执行摘要

当前仓库已经具备三类与 `Phase D` 强相关的基础：

1. benchmark / gate 侧已有更正式的学术评测基础：
   - `docs/plans/v3_0/reports/validation/v3_0_academic_adoption_report.md`
2. 真实代码主链已具备 Search / Import / KB / Read / Chat / Review 的可复用入口：
   - `apps/web/src/features/search/components/SearchWorkspace.tsx`
   - `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
   - `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
   - `apps/web/src/features/kb/components/KnowledgeReviewPanel.tsx`
3. 仓库里已经有真实链路验证与大规模真实数据验证基线：
   - `docs/plans/v3_0/reports/validation/2026-04-22_retrieval_benchmark_large_real_report.md`
   - `docs/plans/v3_0/reports/release/v3_6_release_gate_report.md`

这说明 `Phase D` 的正确方向不是再做一轮抽象能力评估，而是：

```txt
把真实论文样本、真实外部导入、真实阅读问答综述流程和真实失败模式，
收口成一套正式的 v3.0 真实世界验证框架。
```

# 3. 前提假设

本文件写作时采用以下前提：

1. `Phase A` 已提供更严格的 benchmark / gold evidence / blind gate 基线。
2. `Phase B` 已让外部论文搜索与导入进入正式主链。
3. `Phase C` 已让 citation / claim verification 进入正式 evidence contract。
4. 这不表示当前仓库代码里 A/B/C 全部实现都已收尾，只表示 Phase D 文档默认可以消费它们定义好的结构边界与主链。

换句话说：

```txt
Phase D 文档把 A/B/C 当成“已定义可复用的上游产物”，
不是把当前实际代码状态误判成“所有前置任务都已经彻底完成”。
```

# 4. 当前基线盘点

## 4.1 已有真实验证信号

仓库里已经出现了真实验证而非纯 mock 的基础信号：

1. `v3_0_academic_adoption_report.md`
   - 已有 `200 papers / 688 queries`
2. `2026-04-22_retrieval_benchmark_large_real_report.md`
   - 已有大规模真实论文集三轮稳定性验证
3. `v3_6_release_gate_report.md`
   - 已有真实代码 + 真实 E2E + 真实 gate 的 release 证明

结论：

1. ScholarAI 并不是完全没有真实验证基础
2. 但这些验证仍然更偏局部能力或 release gate，不等于完整的真实研究工作流验证

## 4.2 已有工作流主链

当前真实代码里已经存在可串联的主链入口：

1. Search
2. KB Import
3. Knowledge Workspace
4. Read
5. Chat
6. Notes
7. Compare
8. Review Draft

这意味着：

1. `Phase D` 不需要新造“验证专用前端”
2. 正确做法是使用现有正式入口穿透真实工作流

## 4.3 当前仍缺什么

当前验证仍缺少四类正式收口：

1. 缺少一套专门面向真实论文类型差异的样本框架
2. 缺少 `external search -> import -> KB -> Read -> Chat -> Notes -> Compare -> Review` 的整链路验证定义
3. 缺少对扫描版 PDF、图表密集、公式密集、跨学科 KB 的系统性失败模式盘点
4. 缺少一份面向 v3.0 close-out 的正式真实世界验证报告模板

# 5. 为什么 Phase D 必须单独成立

## 5.1 benchmark 不是现实

即使 `Phase A` 做得很好，benchmark 仍然主要回答：

1. 在受控问题集上系统是否退化
2. 在固定 gold 约束下系统是否更强

但它不能充分回答：

1. 外部导入来的论文在真实 UI 中是否真能用
2. 扫描版或公式密集论文是否会击穿主链
3. 用户跨页面工作流是否连续

## 5.2 真实工作流的失败方式和 benchmark 不同

真实世界里的失败通常不只是“答错了”，而是：

1. import 成功但全文不可问答
2. citation 能跳页但找不到真正支撑 claim 的 span
3. Compare 有内容但证据太弱
4. Review Draft 能生成，但 unsupported claim 太多
5. 页面之间状态不同步，用户丢失上下文

## 5.3 这是 v3.0 是否能对外演示的前置条件

如果 Phase D 不成立，那么：

1. `Phase G Public Beta` 的 demo 只是理想样例
2. 对外展示无法说明系统是否能处理“脏真实世界”
3. release 结论会过于依赖 benchmark 和点状 E2E

# 6. Phase D 的正式目标

`Phase D` 需要同时满足以下六个目标：

1. `统一真实样本框架`
   - 建立真实论文验证集，而不是只靠 benchmark
2. `统一工作流验证`
   - 固定从 Search 到 Review 的正式验证主链
3. `统一失败模式`
   - 明确扫描版、图表、公式、跨学科等高风险场景
4. `统一结果记录`
   - 每条真实验证都能记录成功、失败、退化点与恢复情况
5. `统一 close-out 产物`
   - 形成正式报告，而不是零散 issue/截图
6. `统一 release 解释`
   - 让后续 Public Beta 能引用 Phase D 结果说明边界与可信度

# 7. 产品主链定义

建议将 `Phase D` 的验证主链固定为：

```txt
external search
-> import to KB
-> import status / dedupe / indexing
-> Read
-> Chat
-> Notes
-> Compare
-> Review Draft
-> quality / failure capture
```

关键点：

1. `Phase D` 不是只看某一个页面是否通过
2. 必须验证“上一环输出是否真能被下一环消费”

# 8. 推荐的样本结构

## 8.1 样本类型

建议真实验证集至少覆盖以下八类：

1. `外部导入论文`
   - 真实来自 `arXiv / Semantic Scholar`
2. `扫描版 PDF`
   - OCR 质量不稳定
3. `图表密集论文`
   - figure / table 是主证据
4. `公式密集论文`
   - 数学段落与符号解释占高比重
5. `长综述论文`
   - 跨章节综合与全文检索压力更高
6. `跨学科 KB`
   - 多篇论文来自不同领域
7. `中英文混合`
   - query / metadata / evidence 混合语言
8. `边界失败样本`
   - 已知可能失败、但对 v3.0 很重要的场景

## 8.2 样本规模建议

P0 不要求极大规模，但必须足够暴露真实问题。

建议目标：

1. `100-300` 篇真实论文
2. 覆盖至少 `20-40` 个完整工作流验证 run
3. 每类高风险样本都至少有可复现 case

## 8.3 样本记录原则

每条真实样本至少记录：

1. `sample_id`
2. `source_type`
3. `discipline`
4. `document_complexity`
5. `language_mix`
6. `workflow_path`
7. `expected_risk`
8. `observed_failures`

# 9. 为什么 Phase D 不能只验证 retrieval

真实使用里，retrieval 只是第一层。

`Phase D` 必须验证：

1. `import correctness`
2. `metadata-only / fulltext-ready` 区分是否真实
3. `reading jump` 是否落到合理位置
4. `chat evidence` 是否真可消费
5. `notes` 是否能沉淀 evidence
6. `compare` 是否有足够证据支撑
7. `review draft` 是否在真实文库上仍可控

否则会出现：

```txt
retrieval 看起来很好，
但真实用户依然无法完成研究任务。
```

# 10. 验证维度建议

## 10.1 流程完整性

验证重点：

1. 是否能从外部搜索顺利进入 KB
2. 导入状态是否真实
3. 已导入论文是否能进入 Read / Chat / Review

## 10.2 证据可信性

验证重点：

1. citation jump 是否能落到合理证据
2. unsupported claim 是否真实暴露
3. compare / review 是否过度生成

## 10.3 交互连续性

验证重点：

1. 页面切换是否丢状态
2. import 完成后的跳转是否正确
3. 从 Chat/Notes/Compare 回到 Read/KB 的路径是否顺滑

## 10.4 失败恢复能力

验证重点：

1. 下载失败能否重试
2. metadata-only 是否被诚实标记
3. 局部失败是否污染整个 KB

## 10.5 语言与文档复杂度鲁棒性

验证重点：

1. 中英文 query 是否稳定
2. 扫描版 / 图表 / 公式论文是否击穿主链
3. 多学科 KB 是否导致 evidence 混乱

# 11. 典型失败模式清单

`Phase D` 至少要主动寻找以下失败：

1. `导入成功假象`
   - 任务 completed，但论文仍不可 Read / Chat
2. `metadata/fulltext 语义错乱`
   - metadata-only 被误标成可全文消费
3. `citation jump 伪可用`
   - 能跳页，但找不到真正支撑 claim 的证据
4. `compare 证据不足`
   - 生成了比较表，但证据实际很弱
5. `review 过度生成`
   - unsupported claim 太多，仍被写成正式段落
6. `跨页面状态断裂`
   - import / reading / chat / review 的上下文无法连续传递
7. `复杂论文退化`
   - 扫描版、图表、公式论文明显比普通 PDF 退化

# 12. 推荐的结果记录方式

建议每条真实验证 run 至少输出：

1. `run_id`
2. `sample_set`
3. `workflow_steps[]`
4. `success_state`
5. `failure_points[]`
6. `recovery_actions[]`
7. `evidence_quality_notes`
8. `user_visible_confusions`

建议把失败分成三类：

1. `blocking`
   - 主链无法继续
2. `degrading`
   - 可继续，但质量明显下滑
3. `paper_cut`
   - 不阻断，但会削弱对外演示与真实采用

# 13. 正式报告产物建议

`Phase D` 的正式输出应固定为：

1. `docs/plans/v3_0/reports/validation/v3_0_real_world_validation.md`

建议报告包含：

1. 样本组成
2. 工作流覆盖
3. 成功率
4. 失败分桶
5. 高风险样本复盘
6. 是否允许进入下一阶段 release / beta

## 13.1 为什么要单独成报告

因为 Phase D 的价值不是再给内部工程师看一堆 raw logs，而是：

1. 给产品、工程、演示和 release 一个统一真源
2. 让后续 `Phase G` 能明确引用“系统在哪些真实场景可用，哪些仍是已知限制”

# 14. 与 Phase A / B / C / E / G 的关系

## 14.1 与 Phase A

Phase A 提供：

1. benchmark/gate 的受控基线

Phase D 负责补上：

1. benchmark 无法覆盖的真实工作流验证

## 14.2 与 Phase B

Phase B 提供：

1. 外部发现与导入能力

Phase D 负责验证：

1. 外部论文导入后是否真能进入主链

## 14.3 与 Phase C

Phase C 提供：

1. claim / citation / verification 正式语义

Phase D 负责验证：

1. 这些语义在真实论文和真实 review 流程里是否仍然成立

## 14.4 与 Phase E

Phase D 会暴露：

1. latency
2. cache 缺口
3. retry / recovery 缺口
4. cost / speed / reliability 瓶颈

这些问题会成为 `Phase E` 的真实输入，而不是拍脑袋的优化清单。

## 14.5 与 Phase G

Phase G 是否能做 public beta，取决于：

1. Phase D 是否证明主链可用
2. 是否已经知道边界在哪里

# 15. 正式建议

基于现有代码与 v3.0 主线，`Phase D` 的正式建议是：

1. 用真实论文和真实工作流补齐 v3.0 的现实证明，而不是再做一轮抽象能力评测。
2. 把 `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review` 固定为正式验证主链。
3. 样本必须覆盖外部导入、扫描版、图表、公式、长综述、跨学科、中英文混合等高风险场景。
4. 报告必须记录失败点与恢复能力，而不是只给一个“通过/失败”结论。
5. Phase D 的目标不是证明“系统完美”，而是证明“系统在真实世界里哪里可靠、哪里还不可靠”。

# 16. 结论

一句话总结：

```txt
Phase D 的本质，不是“再做一次 QA”，
而是把 ScholarAI 从 benchmark 和 feature pass，
推进到真实研究工作流可验证、可解释、可 close-out 的阶段。
```
