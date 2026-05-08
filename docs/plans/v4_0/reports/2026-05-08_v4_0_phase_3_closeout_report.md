# v4.0 Phase 3 Closeout Report

> 日期：2026-05-08  
> phase: `4.0-3`  
> status: `closeout-complete`  
> verdict: `artifact-ready`

## 1. 结论

Phase 4.0-3 已完成本轮 closeout，结论是 `artifact-ready`。

本阶段不重做 Review/Notes/Compare IA，而是把既有结构化产物收束成 citation-backed artifact bundle。当前 bundle 已补齐：

1. `review_draft`
2. `citation_audit`
3. `evidence_note`
4. `compare_matrix`
5. `known_limitations`
6. `run_trace`

## 2. 本轮关闭内容

### 2.1 Review artifact bundle hardening

后端 review run 现在会输出统一 artifact contract，并补齐回跳语义：

1. `evidence_note` 通过 note 路径回跳证据
2. `compare_matrix` 通过 `/compare?paper_ids=...` 回跳对比页
3. `known_limitations` 保持为一等 artifact
4. `run_trace` 保持为执行轨迹真源

### 2.2 Frontend artifact consumption

KB Review 面板现在可以：

1. 显示 artifact bundle
2. 对带 `url` 的 artifact 提供 `打开` 回跳入口
3. 保留 `known limitations` 的可见展示

## 3. Remaining Limitations

当前仍保留到后续 gate 的事项：

1. Phase 3 只到 `artifact-ready`，不是 beta-ready
2. review 仍可能出现 `partial / insufficient_evidence`
3. 仍不应把该阶段写成 release-pass
4. 后续前端精修与更大范围评测仍需另一个阶段承接

## 4. Verification

后端：

- `cd apps/api && PYTHONPATH=$PWD /Users/cc/.virtualenvs/scholar-ai-api/bin/python -m pytest -q tests/unit/test_review_draft_service.py --maxfail=1`

前端：

- `cd apps/web && npm run type-check`
- `cd apps/web && npm run test:run -- src/features/kb/components/KnowledgeReviewPanel.test.tsx`

## 5. Handoff

Phase 4/5 可以直接消费这套 artifact bundle 与回跳契约，继续做前端体验与交互精修。
