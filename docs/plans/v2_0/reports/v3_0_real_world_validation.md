# v3.0 Real-world Validation Report

- total_samples: 8
- total_runs: 5
- beta_readiness: not_ready
- rationale: blocking failures or honesty regressions remain

## 样本组成

- cross_discipline_kb: 1
- external_import: 1
- figure_heavy: 1
- formula_heavy: 1
- known_failure: 1
- long_survey: 1
- multilingual: 1
- scan_pdf: 1

## Workflow 覆盖

- full_chain_runs: 0
- chat: passed=3, consumed_by_next=3
- import: passed=3, consumed_by_next=3
- notes: passed=3, consumed_by_next=3
- read: passed=4, consumed_by_next=4
- review: passed=3, consumed_by_next=3
- search: passed=4, consumed_by_next=4

## 本次真实执行链路

- RW-001: sample_ids=D-001; success_state=blocked
  - steps: search=passed -> import=failed -> read=skipped -> chat=skipped -> notes=skipped -> compare=skipped -> review=skipped
  - search notes: Unified search eventually returned 20 results for D-001. | First pass took about 30.3s because arXiv timed out while Semantic Scholar succeeded.
  - import notes: Search import modal opened, but selecting the target KB was blocked by unstable/out-of-viewport modal option behavior under a larger KB list.
  - blocking_conditions:
    - Import-to-KB modal did not allow stable selection of the freshly created knowledge base once the KB list was long enough; the target option became unstable/outside viewport and import POST never fired.
  - degraded_conditions:
    - Unified search returned only after an arXiv read timeout stretched the request to roughly 30 seconds.
    - Search sidecar evidence request hit a backend exception in artifact_loader because artifact_root was treated as str instead of Path.
  - user_visible_confusions:
    - Search page stayed in a generic '搜索中...' state for roughly 30 seconds before any result panel appeared.
    - Import modal showed the target KB name but did not provide a stable, scroll-safe selection interaction once the KB list grew.
    - The evidence sidecar request failed in backend logs without a dedicated user-facing explanation.
- RW-002: sample_ids=D-001; success_state=partial
  - steps: search=passed -> import=passed -> read=passed -> chat=skipped -> notes=skipped -> compare=skipped -> review=skipped
  - search notes: Unified search returned the D-001 target card and the real import CTA was actionable.
  - import notes: Import job completed with real Semantic Scholar metadata resolution, arXiv PDF download, PDF parsing, chunking, embedding, and KB attach.
  - read notes: Redirect landed on the KB papers tab and the imported paper opened in read view.
  - chat notes: RW-002 scope stopped after read-page verification.
  - notes notes: RW-002 scope stopped after read-page verification.
  - compare notes: RW-002 scope stopped after read-page verification.
  - review notes: RW-002 scope stopped after read-page verification.
  - user_visible_confusions:
    - Real PDF processing still takes about 3 minutes before the KB papers tab is ready.
- RW-003: sample_ids=D-001; success_state=partial
  - steps: search=skipped -> import=skipped -> read=passed -> chat=passed -> notes=passed -> compare=skipped -> review=passed
  - search notes: RW-003 reused the previously imported D-001 paper from RW-002 and did not rerun search.
  - import notes: RW-003 reused the previously imported D-001 paper from RW-002 and did not rerun import.
  - read notes: The imported paper remained accessible from the KB papers tab and opened successfully in read view.
  - chat notes: Single-paper chat on /chat?paperId=... streamed a real answer and the composer re-enabled.
  - notes notes: The paper summary endpoint returned non-empty reading notes for the imported paper.
  - compare notes: Compare remained out of scope for the follow-up closeout run and was not rerun.
  - review notes: Review draft b6a0cc60-091b-47fd-b4e0-2e2737490178 reached partial and review run 81e92445-30ab-498c-bc1f-004cd82c5a2d reached completed. | The review UI loaded /knowledge-bases/89376111-88a1-4ae6-a4e9-703665f87e82?tab=review&runId=81e92445-30ab-498c-bc1f-004cd82c5a2d and rendered run_id plus draft_finalizer from GET /api/v1/runs/{run_id}.
  - degraded_conditions:
    - The follow-up review run completed, but the generated draft surfaced as partial with insufficient_evidence and omitted sections instead of a full synthesized draft.
  - user_visible_confusions:
    - The review result finished as partial and left sections empty with omitted_reason=insufficient_evidence, even though the run itself completed.
- RW-004: sample_ids=D-001; success_state=partial
  - steps: search=passed -> import=passed -> read=passed -> chat=passed -> notes=passed -> compare=skipped -> review=passed
  - search notes: A fresh account search returned the D-001 target card and the real import CTA was actionable.
  - import notes: Import job imp_379a6b862f0542878575eae2 completed with real Semantic Scholar metadata resolution, arXiv PDF download, PDF parsing, chunking, embedding, primary Milvus insert, and KB attach. | This closeout used real Milvus on localhost:19530 with embedded fallback disabled; Milvus Lite was not used.
  - read notes: The imported paper opened from the fresh KB in read view and the AI summary panel loaded without Request failed.
  - chat notes: Single-paper chat on /chat?paperId=... streamed a real answer and the composer re-enabled.
  - notes notes: The paper summary endpoint returned non-empty reading notes for the fresh imported paper.
  - compare notes: Compare remained out of scope for this closeout and was not rerun.
  - review notes: Review draft 3ef02085-6188-49c6-bcb2-877b06feb40e reached partial and review run 01ed7d27-779d-43e2-bad3-099babd74413 reached completed. | The review UI loaded /knowledge-bases/2ba613f8-24f5-4b9a-bae3-370243bf4cbd?tab=review&runId=01ed7d27-779d-43e2-bad3-099babd74413 and rendered run_id plus draft_finalizer from GET /api/v1/runs/{run_id}.
  - degraded_conditions:
    - The fresh-account review run completed, but the generated draft surfaced as partial with insufficient_evidence and omitted sections instead of a full synthesized draft.
    - During import finalization, summary-index storage hit a Milvus VARCHAR max-length boundary (8016 > 8000), but the primary Milvus vector insert and the user-visible import flow still completed successfully.
  - user_visible_confusions:
    - Real import plus processing still takes roughly 3 to 4 minutes before downstream read, chat, and review surfaces become usable.
    - The review result finished as partial and left sections empty with omitted_reason=insufficient_evidence, even though the run itself completed.
- RW-005: sample_ids=D-001; success_state=partial
  - steps: search=passed -> import=passed -> read=passed -> chat=passed -> notes=passed -> compare=skipped -> review=passed
  - search notes: A fresh-account closeout rerun returned the D-001 target card and the import CTA stayed actionable.
  - import notes: Import job imp_05017fc617304b44a112ec99 was created in about 1.3 seconds after the confirm-import modal contract was exercised correctly. | Processing task 529cd2b1-92e9-4895-9d6f-bf8248abe134 completed on real Milvus with embedded fallback disabled, and the full import job reached completed in about 4.1 minutes. | Worker prewarm loaded the shared Qwen embedding service and connected Milvus before the first import task; Milvus Lite was not used.
  - read notes: The imported paper opened from KB 6391447a-5471-4ef7-8e63-83f270a56f5b in read view and the AI summary panel loaded without Request failed.
  - chat notes: Single-paper chat on /chat?paperId=75ead5f7-e487-4bc4-b142-9ccb5d84123d streamed a real answer and the composer re-enabled.
  - notes notes: The paper summary endpoint returned non-empty reading notes for the fresh imported paper.
  - compare notes: Compare remained out of scope for the closeout rerun and was not rerun.
  - review notes: Review draft e29bc9f2-7bc5-410e-82a1-b2b0891c94f3 reached partial and review run ca11c91d-a331-41fc-91cc-0eac8fca2c9a reached completed. | The review UI loaded /knowledge-bases/6391447a-5471-4ef7-8e63-83f270a56f5b?tab=review&runId=ca11c91d-a331-41fc-91cc-0eac8fca2c9a and rendered run_id plus draft_finalizer from GET /api/v1/runs/{run_id}.
  - degraded_conditions:
    - The closeout fresh-account review run completed, but the generated draft still surfaced as partial with insufficient_evidence and omitted sections instead of a full synthesized draft.
    - Even after worker prewarm, the first-run real import chain still took about 4.1 minutes end-to-end, with the text embedding batch remaining the dominant latency hotspot.
  - user_visible_confusions:
    - The first real import still keeps the user waiting for about 4 minutes before downstream read, chat, and review surfaces become usable.
    - The review result still finishes as partial with omitted_reason=insufficient_evidence, even though the run itself completed.

## 失败分桶

- total_failures: 8
- blocking: 1
- degrading: 7

## Evidence 质量

- total_reviews: 0
- unsupported_claim_count: 0
- weakly_supported_claim_count: 0
- citation_jump_pass_rate: 0.0

## Honesty 检查

- total_failed_checks: 1
- citation_jump_honest: 1
- fulltext_ready_honest: 0
- metadata_only_honest: 0
- unsupported_claim_visible: 0

## Release 建议

- beta_readiness: not_ready
- rationale: blocking failures or honesty regressions remain
- next_steps:
  - fix blocking runs before beta
  - clear honesty check failures for metadata/fulltext and citation jumps
