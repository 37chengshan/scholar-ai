# RAG Runtime Cleanup：api_flash_qwen_rerank_glm 单主链收口

## 目标

把 ScholarAI RAG 主链收口为唯一正式 runtime：

```text
PDF / ParseArtifact / ChunkArtifact
→ tongyi-embedding-vision-flash-2026-03-06
→ Milvus api_flash collection
→ qwen3-vl-rerank
→ glm-4.5-air answer / citation verification
```

本轮原则：删除默认 runtime 中的多模型串线风险，BGE / SPECTER2 / local qwen embedding 只允许作为 deprecated / experimental，不允许进入正式检索链路和 official benchmark gate。

## Active runtime

```text
RAG_RUNTIME_PROFILE=api_flash_qwen_rerank_glm
EMBEDDING_PROVIDER=tongyi
EMBEDDING_MODEL=tongyi-embedding-vision-flash-2026-03-06
RERANKER_PROVIDER=qwen_api
RERANKER_MODEL=qwen3-vl-rerank
LLM_PROVIDER=zhipu
LLM_MODEL=glm-4.5-air
```

## Active collections

```text
paper_contents_v2_api_tongyi_flash_raw_v2_3
paper_contents_v2_api_tongyi_flash_rule_v2_3
paper_contents_v2_api_tongyi_flash_llm_v2_3
```

## Deprecated runtime lines

以下线路不得被默认 runtime 启用：

```text
bge_m3
bge-reranker
specter2
qwen_dual
bge_dual
academic_hybrid
local_qwen_embedding
local_qwen_reranker
graph_branch
scientific_text_branch
```

旧 collection 暂不 drop，只从 runtime、registry 和 benchmark gate 中移除引用：

```text
paper_contents_v2_qwen_v2_*
paper_contents_v2_specter2_*
paper_contents_v2_bge_*
paper_contents
```

## 收口步骤

### Phase 1：配置收口

1. 新增唯一 runtime profile：`api_flash_qwen_rerank_glm`。
2. 默认 embedding provider 切到 Tongyi vision flash。
3. 默认 reranker 固定为 `qwen3-vl-rerank`。
4. 默认 LLM 固定为 `glm-4.5-air`。
5. `RETRIEVAL_MODEL_STACK`、`BGE_DUAL_*`、`QWEN_DUAL_*`、`SCIENTIFIC_TEXT_*`、`GRAPH_RETRIEVAL_ENABLED` 标记 deprecated。

### Phase 2：Model Gateway 收口

只保留主链 provider：

```text
TongyiVisionFlashEmbeddingProvider
Qwen3VLRerankProvider
GLM45AirProvider
```

其他 provider 移入 deprecated 或从 active registry 删除：

```text
BGE
SPECTER2
local qwen embedding
local qwen reranker
```

### Phase 3：Retrieval Branch Registry 收口

只允许 active branch：

```text
api_flash_dense
```

如果 runtime 启动时检测到 deprecated branch 启用，直接 fail，不允许 fallback。

### Phase 4：Benchmark 收口

official benchmark 只允许：

```text
api_flash_qwen_rerank_glm
```

synthetic golden 只允许 smoke，不允许 official gate。

### Phase 5：回归测试

必须覆盖：

```text
- active runtime profile
- deprecated provider/branch 不启用
- active collection registry only
- qwen3-vl-rerank provider contract
- official benchmark rejects synthetic golden
```

## Gate

收口成功的最低条件：

```text
provider_probe: PASS
schema_audit: PASS
preflight: PASS
deprecated_active_usage_count = 0
fallback_used = 0
dimension_mismatch = 0
synthetic_golden_in_official_gate = 0
```

质量门槛：

```text
citation_coverage >= 0.85
unsupported_claim_rate <= 0.10
answer_evidence_consistency >= 0.65
citation_jump_validity >= 0.90
```

## 非目标

本 PR 不 drop 旧 collection，不删除历史 benchmark artifact，不重跑 64×3，不扩 50 篇。先完成 runtime 合同和防串线 guard，再做物理删除。