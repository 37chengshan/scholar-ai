# EP-2026-04-20 vNext+1 验证版执行计划（PR-A/PR-B/PR-C）

作者：glm5.1+37chengshan
日期：2026-04-20
分支：feat/vnext-plus1-validation-20260420
基线：origin/main@bef0b52

## 1. 目标与边界（严格按任务单）

本阶段唯一目标：把 vNext 冻结能力转为可验证、可回归、可发布。

只做 4 个工作包：
1. WP1 统一验证环境与发布闸门
2. WP2 真实链路验收矩阵
3. WP3 指标沉淀与验证结果输出
4. WP4 RAG 最小评测集（30+）

明确不做：
1. 知识图谱重构
2. 新外部 source 接入
3. 重度 Agentic RAG 扩展
4. Chat 页面大改版
5. 非验证导向的顺手优化

停止线：
1. 有统一 verify 入口
2. CI 必跑验证
3. 12+ 真实链路验收场景
4. 30+ RAG 评测样本
5. 结构化验证结果可导出
6. 验证版总结文档完成

## 2. 现状盘点与差距

已存在：
1. 多个 governance gates 与 CI（ci-lite.yml / contract-gate.yml）
2. 前端 type-check/test 命令（apps/web）
3. 后端 pytest 依赖已在 requirements.txt
4. 评估脚本基础（scripts/eval_retrieval.py、scripts/eval_answer.py）
5. eval fixtures 与 golden_queries 基础（tests/evals）

主要差距：
1. 缺少单一 verify 入口（本地/CI/Codex 一致）
2. CI 缺少统一“全链路验证闸门”工作流（web+api+packages+gates 一体）
3. 缺少 vNext+1 的 12 场景验收矩阵文档与结果样例
4. 缺少统一指标汇总脚本与结构化导出（import + rag）
5. 缺少独立 30+ 条 RAG 最小评测集与可执行 runner

## 3. 实施顺序（必须按顺序）

Step 1：WP1 验证环境与 CI
Step 2：WP2 验收矩阵
Step 3：WP3 指标与结果导出
Step 4：WP4 RAG 评测集

## 4. 工作包与落地文件

## WP1：统一验证环境与发布闸门

目标：单一入口、可复现、可定位失败阶段。

计划改动：
1. 新增 `scripts/verify/run-all.sh`
   - 串联：governance gates、web type-check、web tests、api pytest、packages/types build、packages/sdk build
   - 输出分阶段日志与失败阶段标识
2. 新增 `scripts/verify/bootstrap-api-env.sh`
   - 自动检测 `apps/api/.venv`
   - 缺失时执行：`python3 -m venv apps/api/.venv`
   - 激活后执行：`python -m pip install --upgrade pip && pip install -r requirements.txt`
   - 额外校验：`python -c "import pytest"`，失败即退出
   - 统一解决 pytest 缺失问题
3. 根 `Makefile` 新增 `verify` 目标（调用 run-all.sh）
4. 根 `package.json` 新增 `verify:all` 脚本（调用 run-all.sh）
5. 新增 `.github/workflows/verify.yml`
   - 触发：`pull_request`（base=main）+ `workflow_dispatch`
   - PR 到 main 强制运行统一验证
   - job 至少包含：governance、web、api、packages、verify-summary
   - verify-summary 依赖前置 job，并在失败时输出失败阶段汇总
6. 更新 `README.md`（新增本地验证章节）

验收标准：
1. `bash scripts/verify/run-all.sh` 在新环境可跑
2. `make verify` 与 `npm run verify:all` 可跑
3. CI 对 PR 自动触发并给出阶段化失败信息
4. 不再出现“pytest 缺失无法验证”作为交付状态

## WP2：真实链路验收矩阵

目标：导入到问答主链路固定化验收，不依赖个人记忆。

计划改动：
1. 新增 `docs/plans/archive/reports/qa/validation-matrix-vnext-plus1.md`
   - 至少 12 场景：
     - 导入：local 小文件、local 大文件、上传恢复、DOI、arXiv、pdf_url、无 PDF 接力、dedupe 决策
     - 问答：单文档、跨文档、citation、低置信提示
   - 字段：case_id/scenario/input_type/sample_input/expected_result/expected_status_path/expected_user_action/expected_query_ready/notes
2. 新增 `docs/plans/archive/reports/qa/validation-results/2026-04-vnext-plus1.md`
   - 结构化结果表（可人工/自动填充）
3. 新增 `artifacts/validation-results/2026-04-vnext-plus1.sample.json`
   - 字段：case_id/pass_fail/duration_ms/final_status/final_stage/fallback_depth/recoverable/paper_created/query_ready/citation_present/low_confidence_flag/failure_reason

验收标准：
1. 场景数 >= 12
2. 导入 8 + 问答 4 的结构完整
3. 失败/恢复类 >= 2（上传中断恢复、dedupe 命中决策）
4. 低置信类 >= 2（低置信提示、证据不足）
4. 结果文件可用于后续脚本统计

## WP3：指标沉淀与验证结果输出

目标：验证后自动产出可比较指标。

计划改动：
1. 新增 `scripts/verify/summarize_validation_results.py`
   - 输入：validation result JSON
   - 输出：metrics JSON + Markdown 汇总
2. 新增 `docs/plans/archive/reports/qa/metrics-spec-vnext-plus1.md`
   - 口径冻结：
     - Import：import_success_rate/time_to_query_ready_ms/awaiting_user_action_rate/upload_resume_success_rate/source_failure_breakdown/fallback_depth
     - RAG：citation_coverage_rate/low_confidence_rate/answer_evidence_consistency_avg/no_valid_sources_rate
3. 新增 `artifacts/validation-results/README.md`
   - 结果文件命名、字段说明、回归比较方式
4. 新增 `scripts/verify/run-validation-matrix.sh`
   - 生成结果样板并调用 summarize 脚本

数据流（冻结）：
1. WP2 先生成/维护 `artifacts/validation-results/2026-04-vnext-plus1.sample.json`
2. `run-validation-matrix.sh` 读取该 JSON（或同 schema 的真实结果 JSON）
3. 调用 `summarize_validation_results.py` 产出：
   - `artifacts/validation-results/2026-04-vnext-plus1.summary.json`
   - `artifacts/validation-results/2026-04-vnext-plus1.summary.md`

验收标准：
1. 跑完后自动得到结构化 summary JSON
2. 同步生成 Markdown 概览
3. 指标命名统一，便于历史对比

## WP4：RAG 最小评测集

目标：建立 30+ 回归基线，支持后续策略变更比较。

计划改动：
1. 新增 `tests/evals/rag_eval_dataset.json`
   - >= 32 条，按任务单分布（冻结）：
     - A 单文档事实 8
     - B 单文档摘要 6
     - C 跨文档比较 6
     - D 冲突证据 4
     - E 无法回答/证据不足 4
     - F 低置信应触发 4
   - 字段：case_id/question/paper_ids/query_type/expected_behavior/must_have_citation/allow_low_confidence/expected_evidence_scope/notes
2. 新增 `docs/plans/archive/reports/qa/rag-eval-spec.md`
   - 定义样本字段、执行模式、判定规则
3. 新增 `scripts/evals/run_rag_eval.py`
   - 读取 dataset
   - mock/real 两种执行模式
   - 输出：total_cases/passed_cases/citation_present_rate/low_confidence_rate/average_consistency/failed_case_ids
4. 新增 `artifacts/validation-results/rag-eval-sample-summary.json`
   - 提供样例执行输出

验收标准：
1. 样本数 >= 30
2. 可重复执行
3. 输出结构化摘要字段齐全

## 5. PR 切分策略（按任务单）

PR-A（verify-env-and-ci）：
1. scripts/verify/run-all.sh
2. scripts/verify/bootstrap-api-env.sh
3. .github/workflows/verify.yml
4. Makefile/package.json/README 对应入口说明

依赖：
1. PR-A 必须先完成（PR-B/PR-C 依赖 verify 入口与 CI 闸门）

PR-B（validation-matrix-and-results）：
1. docs/plans/archive/reports/qa/validation-matrix-vnext-plus1.md
2. docs/plans/archive/reports/qa/validation-results/2026-04-vnext-plus1.md
3. scripts/verify/run-validation-matrix.sh
4. scripts/verify/summarize_validation_results.py
5. docs/plans/archive/reports/qa/metrics-spec-vnext-plus1.md

PR-C（rag-eval-baseline）：
1. tests/evals/rag_eval_dataset.json
2. scripts/evals/run_rag_eval.py
3. docs/plans/archive/reports/qa/rag-eval-spec.md
4. docs/plans/archive/reports/releases/vnext-plus1-validation-summary.md

说明：若用户要求单 PR 推进，则保留 3 个逻辑提交组并在同一 PR 中展示。

## 6. 快速审核清单（计划自检）

1. 是否完整覆盖 WP1-WP4：是
2. 是否包含 6 项硬完成条件：是
3. 是否有“禁止事项”控制：是
4. 是否可在现有仓库结构落地：是
5. 是否避免范围缩小：是（在任务单基础上增加了指标规格、结果产物说明、执行脚本）

## 7. 交付清单（文件级）

1. `.github/workflows/verify.yml`
2. `scripts/verify/run-all.sh`
3. `scripts/verify/bootstrap-api-env.sh`
4. `scripts/verify/run-validation-matrix.sh`
5. `scripts/verify/summarize_validation_results.py`
6. `docs/plans/archive/reports/qa/validation-matrix-vnext-plus1.md`
7. `docs/plans/archive/reports/qa/validation-results/2026-04-vnext-plus1.md`
8. `docs/plans/archive/reports/qa/metrics-spec-vnext-plus1.md`
9. `docs/plans/archive/reports/qa/rag-eval-spec.md`
10. `tests/evals/rag_eval_dataset.json`
11. `scripts/evals/run_rag_eval.py`
12. `docs/plans/archive/reports/releases/vnext-plus1-validation-summary.md`
13. `artifacts/validation-results/2026-04-vnext-plus1.sample.json`
14. `artifacts/validation-results/rag-eval-sample-summary.json`

总结文档最低结构（冻结）：
1. 背景与范围（只含 WP1-WP4）
2. 执行命令与环境
3. 验收矩阵结果摘要（通过/失败分布）
4. 指标摘要（Import + RAG）
5. 评测集运行结果（总量/通过率/失败 case）
6. 风险与后续建议（不扩功能）
