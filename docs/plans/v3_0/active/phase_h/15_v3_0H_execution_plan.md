# 15 v3.0-H 执行计划：RAG 全面转向线上

> 日期：2026-04-30  
> 状态：execution-plan  
> 上游研究：`docs/plans/v3_0/active/phase_h/2026-04-30_v3_0H_RAG_Online_Transition_研究文档.md`  
> 文档前提：按当前仓库真实代码状态组织执行，明确承认主链仍有本地默认依赖、兼容 shim 与 lite fallback

## 1. 目标

`Phase H` 的执行目标是把 `RAG Online-first Transition` 从研究结论推进成可实施的运行时收口计划，形成：

```txt
provider inventory
-> default-path freeze
-> business entry unification
-> fallback honesty
-> runtime validation
-> benchmark / release consumption
```

## 2. 执行前先读什么

执行者开始前，按以下顺序读取：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/v3_0/active/phase_h/2026-04-30_v3_0H_RAG_Online_Transition_研究文档.md`
3. `apps/api/app/config.py`
4. `apps/api/app/core/qwen3vl_service.py`
5. `apps/api/app/core/embedding/factory.py`
6. `apps/api/app/core/reranker/factory.py`
7. `apps/api/app/core/model_gateway.py`
8. `apps/api/app/workers/storage_manager.py`
9. `apps/api/app/services/review_draft_service.py`
10. `apps/api/app/rag_v3/main_path_service.py`
11. `apps/api/app/services/compare_service.py`
12. `apps/api/app/core/milvus_service.py`

执行规则：

1. 先定义默认生产路径，再改代码入口。
2. 先让 runtime truth 可观测，再谈 benchmark 和 release 结论。
3. 不允许只替换配置项，却保留业务层对本地 singleton 的隐式依赖。
4. 不允许把 shim / lite / local fallback 统计进“正式线上成功”。
5. 默认按当前产品约束冻结双平面模型栈：
   - retrieval plane: `Qwen flash/pro + Qwen rerank + Milvus`
   - generation plane: `glm-4.5-air`

## 3. 范围

### 包含

```txt
1. generation / embedding / reranker provider identity freeze
2. 主索引、主检索、review、compare 等关键业务入口收口
3. online/local/shim/lite runtime mode 定义
4. fallback honesty 和 trace 字段补齐
5. Phase D / Phase J / release gate 消费口径接入
6. retrieval plane 与 generation plane 的配置和 trace 分离
```

### 不包含

```txt
1. 新向量库主线切换
2. Phase I 的前沿框架创新设计
3. 全量供应商横评与最终战略选择
4. 完整 benchmark 阈值设计
```

## 4. Work Packages

## WP0：Default Runtime Freeze

目标：

1. 冻结“什么叫线上默认主链”
2. 冻结 runtime mode taxonomy

输出：

1. online-first runtime definition
2. `online / local / shim / lite` 模式定义
3. retrieval plane / generation plane split definition

验收：

1. 所有后续验证 run 都能明确说明自己属于哪种 mode。

执行方式：

1. 以研究文档为准，先定义默认路径与 fallback 语义。
2. 不允许在代码修改前各模块自行发明 mode 字段。
3. 若某路径无法归类，先视为未收口风险，而不是默认归到 online。

## WP1：Provider Inventory and Contract Freeze

目标：

1. 盘点当前 generation / embedding / reranker / retrieval wiring 的真实 provider 来源
2. 冻结统一 provider contract

输出：

1. provider inventory
2. provider contract freeze
3. model / dimension / backend mapping
4. retrieval plane / generation plane explicit mapping

验收：

1. 能回答每条主链到底由谁提供 embedding、reranker、generation。

执行方式：

1. 盘点 `config.py`、`embedding.factory.py`、`reranker.factory.py`、`model_gateway.py`。
2. 显式标出真实远程 provider、本地 provider、shim provider。
3. collection dimension 与 provider model 必须同步记录，不能后补。
4. 按当前已知产品假设，将 `Qwen flash/pro`、`Qwen rerank`、`glm-4.5-air` 分别冻结到对应 plane，不允许再写成模糊“online model”。

## WP2：Business Entry Unification

目标：

1. 清理业务层对 `get_qwen3vl_service()` 的主链默认依赖
2. 把关键入口统一接到 provider contract

重点路径：

1. `workers/storage_manager.py`
2. `services/review_draft_service.py`
3. `workers/pdf_coordinator.py`
4. `workers/extraction_pipeline.py`
5. `services/compare_service.py`
6. `rag_v3/main_path_service.py`

验收：

1. 主索引、主检索、review、compare 不再各自拥有隐式本地默认真源。

执行方式：

1. 先改高价值主链：storage / review / retrieval。
2. 再改周边路径：pdf worker、image/table extractor、semantic cache。
3. 旧入口若暂时保留，必须显式标注为 legacy / fallback-only。

## WP3：Fallback Register and Runtime Honesty

目标：

1. 让 fallback 不再隐式发生
2. 让验证报告能诚实声明 degraded 条件

输出：

1. runtime trace 字段扩展
2. fallback register 扩展
3. report mode 字段
4. per-plane model identity fields

验收：

1. 任一 run 均可识别是否发生 local fallback、shim fallback、Milvus Lite fallback。

执行方式：

1. 把 `Milvus Lite` 从“透明兜底”改为“显式降级事件”。
2. 把 `model_gateway` shim 明确标成 shim mode。
3. Phase D / release 报告必须显示 degraded condition，不能只写 pass/fail。

## WP4：Online Runtime Validation

目标：

1. 在真实环境里验证 online-first 主链贯通
2. 验证线上化后主链行为没有静默退化

重点验证链：

1. `Search -> Import -> KB -> Read -> Chat`
2. `KB -> Review`
3. `Compare`
4. 同时记录上述链路的 retrieval plane 与 generation plane 实际模型身份

验收：

1. 关键链路在 online mode 下可运行。
2. 退化条件被显式记录，而不是被隐藏为普通成功。

执行方式：

1. 先跑 focused backend/runtime probes。
2. 再跑 real-world follow-up。
3. 若失败，先定位 provider truth，再判断是否为业务 bug。

## WP5：Benchmark and Release Consumption

目标：

1. 让 `Phase J` 和 release gate 能消费 Phase H 的 mode truth
2. 让线上基线与候选结果可比较

输出：

1. online baseline definition
2. candidate-vs-baseline runtime parity rule
3. release gate runtime truth rule

验收：

1. benchmark 不再混合本地/线上结果而不给说明。
2. release 结论不会把 fallback run 误判为正式线上成功。

执行方式：

1. 先冻结 baseline runtime mode。
2. candidate run 必须声明 mode parity 是否一致。
3. 若 mode 不一致，只能作为实验结果，不能直接替代 release baseline。

## 5. 实际执行顺序

执行者按以下顺序推进：

1. `WP0 Default Runtime Freeze`
2. `WP1 Provider Inventory and Contract Freeze`
3. `WP2 Business Entry Unification`
4. `WP3 Fallback Register and Runtime Honesty`
5. `WP4 Online Runtime Validation`
6. `WP5 Benchmark and Release Consumption`

原因：

1. 默认路径不冻，后续所有代码修改都会口径漂移。
2. provider inventory 不清，业务入口统一会变成盲改。
3. fallback 不诚实，任何验证结果都不可信。
4. runtime truth 不先收口，benchmark 和 release 都无法正确消费。

## 6. 下层文档

当前 Phase H 已有：

1. `docs/plans/v3_0/active/phase_h/2026-04-30_v3_0H_RAG_Online_Transition_研究文档.md`

后续建议补齐：

1. `v3_0H_provider_inventory.md`
2. `v3_0H_contract_freeze.md`
3. `v3_0H_runtime_validation_matrix.md`
4. `v3_0H_execution_plan_review.md`

## 7. 验收标准

Phase H P0 可视为完成，当且仅当：

1. 默认生产 RAG 主链的 runtime mode 已冻结为 online-first。
2. 主索引、主检索、review、compare 的关键入口不再默认直连本地 Qwen singleton。
3. `online / local / shim / lite` 模式在 trace / report / gate 中可识别。
4. Milvus Lite 与其他 fallback 被显式标记为 degraded condition。
5. 至少一条完整真实链路可在 online mode 下完成验证。
6. benchmark 与 release 结论能正确说明 runtime mode，而不是混口径。

## 8. 风险

1. 若只替换 config，而不改业务入口，线上化会停留在表面。
2. 若不记录 runtime mode，后续 benchmark 会继续混合本地与线上结果。
3. 若 collection dimension 与 provider model 不同步，Milvus 索引会出现隐性不兼容。
4. 若 fallback 仍透明发生，真实验证和 release 结论都会失真。
