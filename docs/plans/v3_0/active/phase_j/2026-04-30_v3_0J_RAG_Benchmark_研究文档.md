# v3.0J RAG Benchmark 与 Comparative Gate 研究文档

> 日期：2026-04-30  
> 状态：research-freeze  
> 用途：为 `Phase 3.0-J` 提供外部研究依据，冻结 ScholarAI 的 benchmark 边界、comparative gate 角色和首批采用策略。  

## 1. 研究目标

`Phase J` 不是再做一轮泛化的“RAG 评测综述”，而是要回答 ScholarAI 当前最实际的问题：

1. `Phase A` 已经在建设 academic benchmark 资产，但还没有形成统一 comparative gate。
2. `Phase D` 已经在推进真实 workflow，但 workflow 结果还没有进入统一对比口径。
3. `Phase H` 已经要求 runtime honesty 与 degrade visibility。
4. `Phase I` 已经把 `Truth + Route` 作为首批 academic kernel 落进主链，并输出了首批可消费 hook。

因此，`Phase J` 的研究目标是定义一个系统级 benchmark layer，使 ScholarAI 能稳定比较：

1. 当前线上基线
2. 候选 route / truth / retrieval 策略
3. 后续更强 academic kernel
4. release 前后的真实退化风险

## 2. 外部研究结论

本轮参考的外部材料主要来自近两年 RAG evaluation / benchmark / diagnostics 工作：

1. `RAGAs`：提出无需人工标注即可从 faithfulness、answer relevance、context precision、context recall 等维度自动评测 RAG，核心价值是把“回答质量”和“检索质量”拆开评，而不是只看最终答案得分。  
   链接：<https://arxiv.org/abs/2309.15217>
2. `ARES`：强调用合成数据与 judge 组合提升自动评测可扩展性，但本质仍是在回答相关性、faithfulness、context relevance 上建立结构化评测接口。  
   链接：<https://arxiv.org/abs/2311.09476>
3. `RAGChecker`：强调细粒度 diagnostics，不满足于“系统整体好不好”，而是要求把 claim、retrieval、citation、support failure 拆成可定位的问题桶。  
   链接：<https://arxiv.org/abs/2408.08067>
4. `CRUD-RAG`：指出复杂信息更新、冲突证据、长上下文、动态知识不是普通 factoid QA 能覆盖的，benchmark 必须引入更接近真实知识工作的 case 结构。  
   链接：<https://arxiv.org/abs/2401.17043>
5. `BRIGHT`：说明真实高难检索任务往往是 reasoning-intensive 的，简单 top-k 命中不能代表系统是否真能支撑复杂学术问答与 synthesis。  
   链接：<https://arxiv.org/abs/2407.12883>
6. `MT-RAG`：强调多轮、多阶段 retrieval 在真实交互里与单轮 QA 不同，benchmark 需要覆盖 multi-turn / iterative retrieval 行为。  
   链接：<https://research.ibm.com/publications/mt-rag-a-multi-turn-retrieval-augmented-generation-benchmark-for-evaluating-conversational-systems>

这些工作虽然实现路径不同，但结论高度一致：

1. 不能只用单一 answer score 评估 RAG。
2. 必须把 retrieval quality、faithfulness / support、citation quality、runtime trade-off 分开建模。
3. 复杂任务需要更高阶 case taxonomy，不能让 benchmark 只停留在简单 factoid QA。
4. 单纯自动分数不够，系统还需要 failure bucket 和可解释 diagnostics。
5. 多轮交互与真实工作流不能完全被离线 QA benchmark 替代。

## 3. 对 ScholarAI 的直接启发

ScholarAI 不是通用客服问答，而是学术工作流产品，因此比通用 RAG 更需要以下几类评测：

1. `claim support / citation fidelity`
   因为 Read、Compare、Review 的核心不是“像不像答案”，而是 claim 是否被证据支持、引用是否可追溯。
2. `task-family aware evaluation`
   `fact`、`method`、`compare`、`survey`、`related_work`、`conflicting_evidence`、`hard` 的成功条件本来就不同，不能强行用一套总体分数覆盖。
3. `route honesty and degrade visibility`
   ScholarAI 现在已经有 `Phase H` 和 `Phase I` 的 route / truth hook，如果 benchmark 不消费这些 hook，就无法判断候选是否只是“看起来更强”，实际却靠 silent fallback 混过去。
4. `workflow-level success`
   用户实际不是只做单轮 QA，而是要完成 `Search -> Import -> KB -> Read -> Chat`、`KB -> Review`、`Compare` 等完整链路。
5. `cost / latency / degraded rate`
   学术场景的高质量回答通常更昂贵，benchmark 必须同时判断“是否更真”和“是否 still practical”。

## 4. ScholarAI 不采用什么

结合外部研究与当前仓库状态，`Phase J` 明确不采用以下路线作为首批默认主线：

1. 不把单一 LLM judge overall score 当作真源。
   原因：这会掩盖 retrieval、citation、claim support、fallback honesty 等关键结构。
2. 不把 benchmark 做成纯 academic offline leaderboard。
   原因：ScholarAI 的真实价值在 workflow 成功率，离线 QA 只能覆盖其中一部分。
3. 不把 `GraphRAG / STORM / 强 verifier` 的实现与 benchmark gate 绑死。
   原因：`Phase J` 的职责是比较候选，不是预设某个候选一定正确。
4. 不允许 candidate 缺少 required hook 仍进入正式 comparative verdict。
   原因：缺 hook 的结果无法证明 route honesty 和 truthfulness contract。
5. 不把“answer 看起来更强”视作 release pass。
   原因：如果 unsupported claim rate、citation coverage、degraded rate 变差，ScholarAI 不能接受这种收益。

## 5. Phase J 在整体路线中的准确位置

`Phase J` 应被定义为 comparative benchmark + gate layer，而不是另一个独立产品 phase。

职责边界如下：

1. `Phase A`
   提供 academic benchmark asset、case taxonomy、blind set、dataset slicing。
2. `Phase D`
   提供真实 workflow run、failure bucket、端到端成功率。
3. `Phase H`
   提供 runtime parity、degrade honesty、fallback visibility。
4. `Phase I`
   提供首批 academic kernel hook，包括 `task_family`、`execution_mode`、`truthfulness_report_summary`、`retrieval_plane_policy`、`degraded_conditions`。
5. `Phase J`
   消费 A / D / H / I 的产物，把 baseline / candidate / diff 组织成正式 comparative verdict。

换句话说：

```txt
Phase A = benchmark asset source
Phase D = workflow validation source
Phase H = runtime honesty source
Phase I = candidate framework hook source
Phase J = comparative gate and release-consume layer
```

## 6. ScholarAI 应采用的 Benchmark Taxonomy

结合文献与现状，`Phase J` 首批 benchmark taxonomy 应冻结为五个维度，而不是继续泛化成“大而全总表”。

### 6.1 Retrieval Plane

用于判断候选是否真的改进了证据获取，而不是只靠回答模型补偿。

首批字段：

1. `task_family`
2. `execution_mode`
3. `retrieval_plane_policy`
4. retrieval completeness / failure bucket

### 6.2 Truthfulness Plane

用于判断 claim 与证据之间是否仍然成立。

首批字段：

1. `truthfulness_report_summary`
2. `unsupported_claim_rate`
3. `citation_coverage`
4. claim support bucket

### 6.3 Runtime Plane

用于判断候选是否 practical。

首批字段：

1. `total_latency_ms`
2. `cost_estimate`
3. `degraded_conditions`
4. degraded rate

### 6.4 Workflow Plane

用于判断真实使用路径是否成功。

首批 suite：

1. `Search -> Import -> KB -> Read -> Chat`
2. `KB -> Review`
3. `Compare`

### 6.5 Verdict Plane

用于区分 experiment signal 与 release signal。

首批 verdict：

1. `pass`
2. `warn`
3. `fail`
4. `experiment-only`

其中 `experiment-only` 专门用于 mode parity 不一致或 hook 不全但仍想保留研究记录的场景。

## 7. 当前仓库已经具备的基础

当前仓库不是从零开始。`Phase I` 已经产出 `Phase J` 可直接消费的首批字段：

1. `task_family`
2. `execution_mode`
3. `truthfulness_report_summary`
4. `retrieval_plane_policy`
5. `degraded_conditions`
6. `citation_coverage`
7. `unsupported_claim_rate`
8. `total_latency_ms`
9. `cost_estimate`

并且仓库已存在正式脚本：

1. `scripts/evals/run_phase_j_comparative_gate.py`

当前脚本已经冻结了非常关键的第一层 gate 逻辑：

1. required hook 缺失则失败
2. baseline / candidate case set 不一致则失败
3. `unsupported_claim_rate` 显著回退则失败
4. `citation_coverage` 回退则失败
5. `latency / cost / degraded_rate` 超预算回退则失败

这与外部研究结论是对齐的：先保证结构化可比，再讨论性能提升。

## 8. 研究结论：Phase J 首批应该做什么

综合文献和当前工程状态，`Phase J` 的首批正确落点不是“再发明一个新 benchmark 框架”，而是完成以下冻结：

1. 冻结 ScholarAI 自己的 comparative taxonomy。
2. 把 `Phase I` hook 正式升级成 `Phase J` required consume contract。
3. 把 `Phase A` academic benchmark 与 `Phase D` workflow suite 接到同一个 comparative verdict。
4. 把 current script 从“基础 gate”升级为“可被 phase / release 消费的正式 runbook 与 verdict artifact”。
5. 为后续 `STORM-lite`、更强 verifier、Graph-enhanced retrieval 保留公平接入的比较口径。

## 9. 对执行计划的直接约束

研究结论对后续执行计划提出以下硬约束：

1. 先做 taxonomy freeze，再做 suite 扩容。
2. 先做 contract freeze，再做 candidate onboarding。
3. workflow suite 必须进入 comparative gate，不能只保留 academic offline case。
4. gate verdict 必须区分 `experiment-only` 和 `release-pass`。
5. 首批 threshold 允许保守，但必须写成正式规则，不能继续口头协商。
6. 首批不要求一次性引入人工标注大规模 judge，但需要保留后续 calibration hook。

## 10. ScholarAI 版 Adopt / Defer 冻结

### Adopt Now

1. `RAGAs` 风格的多维拆解思想，但不照搬其全部指标实现。
2. `ARES` / `RAGChecker` 的 structured evaluation contract 思想。
3. `CRUD-RAG` / `BRIGHT` 对复杂任务与高难检索的 case taxonomy 启发。
4. `MT-RAG` 对 multi-turn / iterative workflow 的 benchmark 启发。

### Defer

1. 强依赖 LLM judge 的统一总分系统
2. 大规模新 benchmark 数据集建设
3. 新框架默认接主链
4. 大量人工标注评审作为首批 gate 前置条件

## 11. 最终结论

`Phase J` 的正确定位已经足够明确：

1. 它不是 `Phase A` 的替代物。
2. 它不是 `Phase D` 的替代物。
3. 它也不是 `Phase I` 候选框架本身。
4. 它是 ScholarAI 把 academic asset、workflow reality、runtime honesty、truthfulness hook 收成统一 comparative verdict 的那一层。

所以 `Phase J` 首批工作的成功标准不是“评测做得多花”，而是：

1. 任意 baseline / candidate 都能按同一 contract 运行。
2. 真正的 regression 会被 gate 明确抓出来。
3. workflow 结果不再游离在 benchmark 外。
4. 后续 Phase 和 release 都能消费同一 verdict，而不是各自发明口径。
