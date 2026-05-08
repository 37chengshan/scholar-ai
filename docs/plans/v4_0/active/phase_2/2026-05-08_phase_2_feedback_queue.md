---
owner: product-engineering
status: controlled-beta-ready
depends_on:
  - feedback_triage_template.md
  - fresh_state_walkthrough_script.md
last_verified_at: 2026-05-08
evidence_commits:
  - PR70
  - PR71
---

# v4.0 Phase 2 Feedback Queue

## 1. Purpose

本文件把 Phase 2 walkthrough 中真实出现过的 `blocked / partial / degraded` 项落成 repo 内 feedback queue。

它不是新的 issue tracker，而是 controlled beta gate 的最小证据：证明本轮 local controlled beta 不只是“能演示”，还已经有明确的 triage 入口、owner 和决策。

## 2. Active Items

### Phase 2 Feedback Item

- feedback_id: `FB-20260503-SEARCH-500-unified-dedup`
- reported_at: `2026-05-03`
- reporter: `GitHub Copilot`
- reporter_role: `primary operator`
- run_id: `v4-beta-local-20260503-01`
- dataset_id: `beta-mainline-001`
- environment: `local-controlled-beta`
- workflow_step: `Search`
- expected_behavior: `Search "Attention Is All You Need" should return a usable import CTA.`
- actual_behavior: `Unified search failed with backend 500 because deduplication mixed dict and SearchResult payloads.`
- evidence_issue: `No usable paper result reached the UI, so the workflow was blocked before any evidence probe could run.`
- artifact_link: `docs/plans/v4_0/active/phase_2/fresh_state_walkthrough_script.md`
- severity: `P0`
- owner: `product-engineering`
- decision: `fix-now`
- downstream_phase: `-`
- notes: `Resolved in the Phase 2 online mainline closeout carried by PR70.`

### Phase 2 Feedback Item

- feedback_id: `FB-20260503-IMPORT-404-source-resolve`
- reported_at: `2026-05-03`
- reporter: `GitHub Copilot`
- reporter_role: `primary operator`
- run_id: `v4-beta-local-20260503-01`
- dataset_id: `beta-mainline-001`
- environment: `local-controlled-beta`
- workflow_step: `Import`
- expected_behavior: `The KB-side import resolve path should accept the selected paper and continue into ImportJob creation.`
- actual_behavior: `The source resolve request returned 404, blocking the import path for the fresh-state run.`
- evidence_issue: `No imported paper entered the KB, so downstream Read / Chat / Notes / Compare / Review could not be exercised.`
- artifact_link: `docs/plans/v4_0/active/phase_2/fresh_state_walkthrough_script.md`
- severity: `P0`
- owner: `product-engineering`
- decision: `fix-now`
- downstream_phase: `-`
- notes: `Resolved before Run B and covered by the PR70 closeout evidence.`

### Phase 2 Feedback Item

- feedback_id: `FB-20260503-ORIGIN-CORS-localhost-vs-127001`
- reported_at: `2026-05-03`
- reporter: `GitHub Copilot`
- reporter_role: `primary operator`
- run_id: `v4-beta-local-20260503-01`
- dataset_id: `beta-mainline-001`
- environment: `local-controlled-beta`
- workflow_step: `Environment bootstrap`
- expected_behavior: `Frontend and backend should use a consistent origin so the walkthrough can start from a real browser session.`
- actual_behavior: `Mixing http://127.0.0.1:5173 with backend calls to http://localhost:8000 triggered a browser CORS failure before the walkthrough could proceed.`
- evidence_issue: `The browser session was invalid until the operator switched to a consistent localhost origin.`
- artifact_link: `docs/plans/v4_0/active/phase_2/fresh_state_walkthrough_script.md`
- severity: `P1`
- owner: `product-engineering`
- decision: `accepted-limitation`
- downstream_phase: `-`
- notes: `Current local quickstart now explicitly records the hostname rule; if it regresses again, the beta gate must pause.`

### Phase 2 Feedback Item

- feedback_id: `FB-20260504-REVIEW-PARTIAL-HONESTY`
- reported_at: `2026-05-04`
- reporter: `GitHub Copilot`
- reporter_role: `primary operator`
- run_id: `v4-beta-local-20260504-01`
- dataset_id: `beta-mainline-001`
- environment: `local-controlled-beta`
- workflow_step: `Review`
- expected_behavior: `Review should produce a structured artifact and honestly surface unsupported or insufficiently evidenced sections.`
- actual_behavior: `Review draft generation succeeded, but some sections were omitted with insufficient evidence and the draft status remained partial.`
- evidence_issue: `The artifact is usable, but citation support is incomplete and cannot be represented as a full-success review.`
- artifact_link: `docs/plans/v4_0/active/phase_2/fresh_state_walkthrough_script.md`
- severity: `P1`
- owner: `product-engineering`
- decision: `carry-forward`
- downstream_phase: `4.0-3 / 4.0-7`
- notes: `Accepted as a truthful Phase 2 known limitation; it must stay visible in Phase 3 artifact work and later evaluation gating.`

## 3. Controlled Beta Readiness Signal

本队列当前已经满足 controlled release gate 的最小要求：

1. 至少一个真实 `blocked` run 已留下 `P0` 反馈，并记录为 `fix-now`。
2. 至少一个真实 `partial` run 已留下 `P1` 反馈，并明确 `carry-forward` 到后续 phase。
3. 每条记录都具备 reporter、run_id、workflow_step、artifact_link、owner 和 decision。
4. 当前 local controlled beta 不依赖口头说明来解释 limitation。
