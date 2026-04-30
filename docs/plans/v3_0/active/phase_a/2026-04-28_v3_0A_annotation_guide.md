---
标题：ScholarAI v3.0-A Academic Benchmark 3.0 标注规范
日期：2026-04-28
状态：guide
---

# 1. 目的

统一 `Benchmark 3.0` 的 paper intake、query 编写、gold answer、gold evidence、claim 和 abstain 标注质量。

# 2. 角色

1. `annotator`
   - 负责初标
2. `reviewer`
   - 负责 evidence、claim、abstain 复核

# 3. 标注顺序

1. paper intake
2. 复杂度标签
3. query 编写
4. gold answer
5. gold evidence
6. 可选 claim 拆分
7. reviewer 复核

# 4. Paper Intake 规则

每篇 paper 至少完成：

1. `paper_id`
2. `title`
3. `discipline`
4. `subfield`
5. `year`
6. `language`
7. `scan_quality`
8. `layout_complexity`
9. `table_density`
10. `figure_density`
11. `formula_density`

# 5. Query 规则

每条 query 必须：

1. 问题边界明确
2. family 单一
3. 标注人能指出至少一个 gold evidence

不允许：

1. 过于开放的泛总结题
2. 依赖外部常识才能判断的题
3. 一个问题同时考多个主 family

# 6. Gold Answer 规则

`gold_short_answer`：

1. 短
2. 明确
3. 可唯一判定

`gold_long_answer`：

1. 忠于 evidence
2. 可被 faithful paraphrase
3. 不引入 evidence 中没有的推断

# 7. Gold Evidence 规则

gold evidence 采用最小支撑原则：

1. 优先标最小必要 span
2. 必要时补 secondary evidence
3. 不要把整页当作默认 gold

多 evidence 情况：

1. `primary`
2. `secondary`
3. `contrast`
4. `limitation`

# 8. Claim 规则

以下 family 建议强制拆 claim：

1. `compare`
2. `cross_paper_synthesis`
3. `numeric`
4. `conflict_verification`
5. `limitation`

每个 claim 必须：

1. 单一断言
2. 对应明确 `evidence_ids`
3. 标明 `supports / partially_supports / insufficient / refutes`

# 9. No-Answer 规则

只有以下情形才可标 `must_abstain=true`：

1. corpus 内无答案
2. 证据不足
3. 问题超出材料范围
4. 指代不清无法唯一判定

禁止：

1. 因为标注人没找到就标 no-answer
2. 因为题太难就标 no-answer

# 10. 高风险 Family 复核要求

必须重点复核：

1. `numeric`
2. `table`
3. `figure`
4. `formula`
5. `conflict_verification`
6. `no_answer`

# 11. Reviewer Checklist

1. family 是否正确
2. gold short answer 是否唯一明确
3. gold long answer 是否超出 evidence
4. evidence 是否是最小必要片段
5. claim 与 evidence_ids 是否一致
6. abstain 是否合理

# 12. 质量门槛

进入 benchmark 前，至少满足：

1. 100% 有 family
2. 100% 有 discipline
3. 100% 有 gold_short_answer
4. 100% 有 expected_evidence 或 `must_abstain=true`
5. 高风险 family 100% reviewer 复核

# 13. 结论

```txt
Benchmark 3.0 的核心不是题多，
而是每题都能明确回答：
答案是什么、证据在哪里、为什么能答、为什么不能乱答。
```
