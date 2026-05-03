# v4.0 决策复核清单

> 日期：2026-05-02  
> 状态：direction-confirmed-ac-priority  
> 用途：记录 v4.0 主线选择：A+C 优先，增加两个前端精细打磨 phase，B 保留为一个优化 phase 和一个测试评测 phase。

## 0. 已确认结论

用户已确认：

```txt
A + C 优先
再加两个 phase 来非常非常仔细地打磨前端
B 留一个 phase 优化
B 再留一个 phase 来测试
```

对应解释：

1. A：产品化研究工作流是 v4.0 第一主线。
2. C：Beta release、稳定性、演示资产是 v4.0 第二主线。
3. 前端精细打磨拆成两个 phase：视觉体验打磨和交互质量打磨。
4. B：学术 RAG 技术升级不作为开场主线，拆成 `Phase 4.0-6 Academic RAG Optimization`。
5. B 的效果验证单独拆成 `Phase 4.0-7 Testing and Evaluation Gate`。

## 1. 需要先确认的 7 个决策

| id | 决策点 | 当前草案默认 | 可选调整 |
|---|---|---|---|
| D1 | v4.0 的一句话目标 | Productized Research Workflow + Beta Release | 已确认 A+C 优先 |
| D2 | 是否先做 Phase 0 | 先收口 v3.0 残留 gate，再做新功能 | 仍需确认 Phase 0 是正式 phase 还是 kickoff gate |
| D3 | v4.0 第一批用户价值 | 连续研究工作流 + Beta 可演示性 | 已确认 A+C 优先 |
| D4 | Agentic 能力边界 | B 不开场，只进入优化 phase | 已确认 B 后置 |
| D5 | Graph / global synthesis 位置 | B 优化 phase 内评估，不替代主链 | 已确认 B 后置 |
| D6 | Benchmark / release gate 强度 | B 测试 phase 单独保留 | 已确认留一个测试 phase |
| D7 | Beta 资产是否作为 v4.0 前置 | C 主线内优先处理 | 已确认 C 优先 |
| D8 | 前端打磨强度 | 两个独立 phase，非常细致打磨 | 已确认新增两个前端 phase |

## 2. 三个可选主线版本

### Option A：产品化研究工作流优先（已选为主线）

一句话：

```txt
把 ScholarAI 做成一个连续研究工作台，而不是功能集合。
```

优先做：

1. Search -> Import -> KB -> Read -> Chat -> Review 的连续体验。
2. Dashboard 只展示阻塞和下一步。
3. Chat 预填 handoff、保留上下文、解释为什么建议下一步。
4. Review Draft 和 citation audit 产品化。

适合条件：

1. 当前目标是让真实用户更容易跑通完整研究流程。
2. v4.0 希望明显提升可演示性和可用性。
3. 不想在第一阶段引入过多新 RAG 技术风险。

### Option B：学术 RAG 技术升级优先（不作为开场主线）

一句话：

```txt
把 ScholarAI 做成更强的 academic RAG engine。
```

保留到优化 phase：

1. Agentic Evidence Loop / corrective retrieval。
2. Graph / global synthesis。
3. Claim verification 与 citation repair。
4. Evidence action contract 优化。

适合条件：

1. 当前目标是技术壁垒和评测领先。
2. 能接受产品体验继续有一定粗糙度。
3. v4.0 更像研发主线，不急于 Beta 演示。

### Option C：Beta release 和稳定性优先（已选为主线）

一句话：

```txt
先把已有 v3.0 能力包装成可以交付、可演示、可反馈的 Beta。
```

优先做：

1. Full-chain walkthrough。
2. Demo dataset / demo account / quickstart。
3. Known limitations 和 feedback 入口。
4. 测试、部署、监控、发布门禁。

适合条件：

1. 当前目标是尽快对外展示或小范围内测。
2. 不想再新增复杂核心能力。
3. v4.0 可以定义成 release hardening，而不是技术大扩展。

## 3. 我建议保留的内容

1. 不新增平行实现路径，继续把真实代码限制在 `apps/web` 和 `apps/api`。
2. Dashboard 只做指挥台，具体执行继续跳转到 Chat/Search/KB/Read/Review。
3. Chat 作为执行核心，跨页 handoff 预填待发送。
4. Claim / citation / evidence 作为 Chat、Compare、Review 的共同内核。
5. v3.0 未验证项不能被写成完成，只能关闭、带入或删除。
6. 前端打磨不重做信息架构，不新开平行页面，而是在现有主链上逐页抛光。

## 4. 仍需继续确认的内容

1. Phase 0 是否应该是正式第一阶段，还是只作为版本启动检查。
2. Productized Research Workflow 第一批先做 Search/Import/KB，还是先做 Chat handoff / Dashboard。
3. Beta release hardening 先做本地 demo 还是云端 demo。
4. Frontend Experience Craft 第一批先打磨 Dashboard/Search/KB，还是 Chat/Review。
5. Frontend Interaction Quality 是否要求浏览器 walkthrough 作为硬门禁。
6. Academic RAG Optimization 里优先做 corrective retrieval，还是 Graph/global synthesis。
7. Testing and Evaluation Gate 是否接入 CI，还是先保留手动 release gate。

## 5. 当前可删改路径

如果你不同意某个方向，可以直接删改这些文件：

1. `docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`
2. `docs/plans/v4_0/active/phase_0/19_v4_0_phase_0_execution_plan.md`
3. `docs/plans/v4_0/search/2026-05-02_v4_0_research_decision_note.md`
4. `docs/plans/PLAN_STATUS.md`
5. `docs/specs/governance/phase-delivery-ledger.md`
