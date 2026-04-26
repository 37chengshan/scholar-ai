# Runtime Integration Cleanup v1 Report

Date: 2026-04-26
Scope: ScholarAI v1.0 Step 2 (RAG Runtime Integration Cleanup)

## 1. Active Runtime Profile

- runtime_profile: api_flash_qwen_rerank_glm
- embedding_provider: tongyi
- embedding_model: tongyi-embedding-vision-flash-2026-03-06
- reranker_provider: qwen_api
- reranker_model: qwen3-vl-rerank
- llm_provider: zhipu
- llm_model: glm-4.5-air

## 2. Active Collections

- raw: paper_contents_v2_api_tongyi_flash_raw_v2_3
- rule: paper_contents_v2_api_tongyi_flash_rule_v2_3
- llm: paper_contents_v2_api_tongyi_flash_llm_v2_3

## 3. Disabled Retrieval Branches

- qwen_dense
- bge_dense
- specter2_scientific
- academic_hybrid
- graph_branch
- sparse_branch

Behavior now:
- Active runtime only accepts branch: api_flash_dense
- Deprecated branch request raises RuntimeError/PreflightError with message:
  Deprecated retrieval branch is not allowed in api_flash_qwen_rerank_glm runtime.

## 4. Config / Guard Integration

Implemented:
- Added runtime contract module: app/core/rag_runtime_profile.py
- Added runtime guard adapter: app/core/rag_runtime_guard.py
- Added config validator: validate_rag_runtime_settings()
- main.py startup integrates runtime guard and prints active runtime block
- If PREFLIGHT_ON_STARTUP=true, guard runs in strict mode before service starts

Startup runtime logs now include:
- RAG runtime profile: api_flash_qwen_rerank_glm
- Embedding: tongyi-embedding-vision-flash-2026-03-06
- Reranker: qwen3-vl-rerank
- LLM: glm-4.5-air
- Deprecated branches active: 0

## 5. Retrieval Registry Closure

Updated files:
- app/core/retrieval_branch_registry.py
- app/core/milvus_service.py
- app/core/multimodal_search_service.py

Result:
- Registry only resolves api_flash_dense (+ bm25 lexical path)
- qwen/specter2/academic_hybrid/graph/sparse deprecated branches are blocked in active runtime
- No fallback to old collection is allowed

## 6. Model Gateway Active Registry

Updated files:
- app/core/model_gateway/active_providers.py
- app/core/model_gateway/registry.py
- app/core/model_gateway/__init__.py
- app/core/embedding/tongyi_flash_embedding.py
- app/core/reranker/qwen_api_reranker.py
- app/core/embedding/factory.py
- app/core/reranker/factory.py

Active registry returns only:
- TongyiVisionFlashEmbeddingProvider
- Qwen3VLRerankProvider
- GLM45AirProvider

Deprecated provider active import status:
- local_qwen / bge / specter2 code still exists (deprecated, retained)
- Not part of active provider registry
- Active runtime factory now blocks deprecated model selection

## 7. Benchmark Guard Closure

Updated file:
- scripts/evals/v2_3_benchmark.py

Implemented:
- official benchmark runtime profile must be api_flash_qwen_rerank_glm
- synthetic golden is rejected for official gate (SMOKE_ONLY)
- non-corpus paper_id in golden is EVAL_BLOCKED
- benchmark output now includes runtime metadata:
  - runtime_profile
  - embedding_model
  - reranker_model
  - llm_model
  - deprecated_branch_used
  - synthetic_golden_used_for_official_gate

## 8. Official Benchmark Profiles

Official mode allowed:
- api_flash_qwen_rerank_glm only

Official mode disabled:
- bge_dual
- qwen_dual
- academic_hybrid
- specter2_line
- fusion

## 9. Tests Run Result

Command:
- cd apps/api && python -m pytest tests/test_rag_runtime_config.py tests/test_rag_runtime_guard.py tests/test_retrieval_branch_registry_runtime.py tests/test_model_gateway_active_registry.py tests/test_benchmark_runtime_profile_guard.py tests/unit/test_runtime_profile.py -q

Result:
- 20 passed
- 0 failed

New/updated tests:
- apps/api/tests/test_rag_runtime_config.py
- apps/api/tests/test_rag_runtime_guard.py
- apps/api/tests/test_retrieval_branch_registry_runtime.py
- apps/api/tests/test_model_gateway_active_registry.py
- apps/api/tests/test_benchmark_runtime_profile_guard.py

## 10. Remaining Legacy Code List

Kept (deprecated, not active):
- config deprecated fields: RETRIEVAL_MODEL_STACK, BGE_DUAL_*, QWEN_DUAL_*, SCIENTIFIC_TEXT_*, GRAPH_RETRIEVAL_ENABLED, QWEN3VL_*_MODEL_PATH
- legacy embedding/reranker implementations:
  - app/core/embedding/bge_embedding.py
  - app/core/embedding/qwen3vl_embedding.py
  - app/core/reranker/bge_reranker.py
  - app/core/reranker/qwen3vl_reranker.py
- specter2-related modules retained for migration safety and historical experiments

## 11. Step-3 Readiness

Can proceed to Step 3 (ParseArtifact / ChunkArtifact standardization): YES

Reason:
- Runtime config guard: PASS
- Startup guard: PASS
- Retrieval registry closure: PASS
- Model gateway active registry: PASS
- Benchmark guard: PASS
- Deprecated branch active usage: 0

## 12. Final Verdict

- Runtime config: PASS
- Startup guard: PASS
- Retrieval registry: PASS
- Model gateway registry: PASS
- Benchmark guard: PASS
- Deprecated branch active usage: 0
