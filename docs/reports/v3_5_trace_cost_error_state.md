# v3.5 Trace / Cost / Error State Report

## Scope

- 后端 answer contract 增强：trace、cost_estimate、error_state。
- 前端可见性：EvidencePanel 展示 fallback / error state / trace id。
- 测试：新增后端契约测试与前端 warning 测试。

## Implemented Changes

- `build_answer_contract_payload` 输出：
  - `trace`（runtime_profile、spans、fallback、cost_estimate）
  - `cost_estimate`
  - `error_state`（`fallback_used|partial_answer|abstain`）
  - `retrieval_trace_id`
- 前端 SSE `done` 扩展字段落盘并可视化展示。
- 新增前端测试：`EvidencePanel.test.tsx`，覆盖 fallback warning + error state + trace 文案。

## Verification

- `cd apps/api && uv run --with-requirements requirements.txt --with pytest pytest -q tests/unit/test_rag_trace_contract.py tests/unit/test_rag_error_state_contract.py --maxfail=1`：3 passed
- `cd apps/web && npm run test:run -- src/features/chat/components/evidence/EvidencePanel.test.tsx`：passed（已并入 v3.4 验证批次）

## Contract Sync

- 已更新 `docs/architecture/api-contract.md`：
  - `chat/stream done` 扩展字段
  - `POST /api/v1/search/evidence`
  - `GET /api/v1/evidence/source/{source_chunk_id}`
  - `POST /api/v1/notes/evidence`
- 已更新 `docs/domain/resources.md`：`EvidenceSourceView`、`EvidenceNote` 资源约束。
