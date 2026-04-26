# Step6.1 Retrieval Recall Debug Report

## Step6 Regression 原始结果

- total: 48
- recall_at_10: 0.0
- citation_coverage: 0.743
- unsupported_claim_rate: 0.451
- answer_evidence_consistency: 0.319
- final_gate: BLOCKED

## Step6.1 诊断摘要

- expected source id existence: PASS
- artifact vs collection alignment: PASS
- oracle recall: PASS
- query embedding consistency: PASS
- filter expr diagnostic: PASS
- neighbor overlap exact_chunk_hit_rate: 0.0

## Final Diagnosis

- Step6.1 diagnosis: PASS
- Blocked category: QUALITY_ERROR
- Step6 rerun allowed: ALLOWED

## Recommended Fix
- 进入 retrieval quality tuning：query rewrite、hybrid sparse、增大 rerank 前候选。
- 在质量优化前保持现有 runtime 合约不变。
