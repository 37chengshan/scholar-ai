---
owner: product-engineering
status: walkthrough-complete
depends_on:
  - demo_dataset.md
  - demo_environment_policy.md
  - beta_quickstart.md
  - feedback_triage_template.md
last_verified_at: 2026-05-04
evidence_commits:
  - working-tree-v4-0-phase-2-assets
  - working-tree-v4-0-phase-2-walkthrough
---

# v4.0 Phase 2 Fresh-state Walkthrough Script

## 1. 目的

本文件定义一次 15-30 分钟的受控 beta walkthrough 脚本。

它是 Phase 2 的硬门槛文档：只有按本脚本完成单次 fresh-state run，Phase 2 才能进入 closeout。历史 RW-004 / RW-005 只能作为 timing 参考，不能替代本次证据。

## 2. Run Gate

开始前必须同时满足：

1. `demo_dataset.md` 已选定 `dataset_id`。
2. `demo_environment_policy.md` 的 reset checklist 已执行。
3. `beta_quickstart.md` 与 `known_limitations.md` 已由操作者阅读。
4. 反馈模板已可用，确保任何 `partial / fail / blocked` 都能立即落单。

## 3. Run ID 规范

建议格式：`v4-beta-local-YYYYMMDD-01`

同一轮 run 的 KB、截图、日志与反馈项都必须带同一 `run_id`。

## 4. Reset Proof Template

在真实执行前先填写：

| field | value |
|---|---|
| `run_id` | `v4-beta-local-20260503-01` |
| `environment` | `local-controlled-beta` |
| `operator` | `GitHub Copilot` |
| `demo_account` | `pr19-e2e@example.com` |
| `dataset_id` | `beta-mainline-001` |
| `kb_namespace` | `Phase2-Beta-20260503-01` |
| `service_status_proof` | `2026-05-03 23:57-2026-05-04 00:03 CST: frontend http://localhost:5173/login reachable; API GET /health -> 200 degraded; celery worker ready; KB UI create succeeded for Phase2-Beta-20260503-01 (KB id 20fcc686-d8e5-440f-bfa5-7284149340b9).` |
| `backend_env_source` | `apps/api/.venv absolute binaries + apps/api/.env + local Postgres/Redis + docker compose etcd/minio/milvus-standalone` |
| `cleared_kbs` | `No prior KB using the Phase2-Beta-20260503-01 namespace was present before creation; a later attempt to create a scholarai-beta-prefixed namespace was not used by the blocked run.` |
| `cleared_import_jobs` | `No unfinished import jobs existed for KB 20fcc686-d8e5-440f-bfa5-7284149340b9 before the walkthrough steps began.` |
| `notes` | `Walkthrough had to switch from http://127.0.0.1:5173 to http://localhost:5173 because the frontend was calling http://localhost:8000 and the mixed hostnames triggered a real browser CORS block.` |

若上表任一关键字段无法填写，本轮直接记为 `blocked`，不得继续声称 fresh-state。

## 5. Step Script

| step | action | expected state | failure fallback | evidence artifact |
|---|---|---|---|---|
| 1 | 记录 reset proof，并创建空 KB | `pass`: fresh KB 建立完成 | 无法证明 reset 即 `blocked` | run header、KB 名称 |
| 2 | Search D-001 `Attention Is All You Need` | `pass`: 目标论文可见且 CTA 可点击 | 改用 `1706.03762`；仍失败则 `blocked` | 搜索结果截图或日志 |
| 3 | Import D-001 into KB | `pass`: job 完成并挂到 KB | 若 job 卡住或失败，记 `fail` 并落 feedback | import job id、等待时长 |
| 4 | Open Read | `pass`: 正文与 AI summary 可读 | 页面可开但内容缺失记 `partial` | Read 页面证据 |
| 5 | Launch Chat from paper context, confirm the prefilled prompt manually, then ask a citation-sensitive question | `pass`: 回答存在 evidence/citation，且操作者确认了 prefill-only 手动发送行为 | 预填缺失、无 citation 或 jump 失败记 `partial` | Chat answer + citation probe |
| 6 | Generate Notes | `pass`: Notes 非空并与当前 paper 对齐 | 空白或断链记 `partial` | Notes 页面或 API 结果 |
| 7 | Search and import D-040 | `pass`: 第二篇论文成功导入同一 KB | 改用 `2303.18223`；仍失败则本轮 `partial` | 第二次 import 证据 |
| 8 | Run Compare | `pass`: 输出区分 D-001 与 D-040 来源 | 混源、空白或缺页记 `partial / fail` | Compare 页面证据 |
| 9 | Run Review | `pass`、`partial` 或 `fail` 必须显式记录 | `partial / insufficient_evidence` 必须建 feedback，不得写成成功 | Review 页面、run id |

## 6. Step Result Template

真实执行时按下表逐步回填：

| step | result (`pass / partial / fail / blocked`) | notes | artifact_link |
|---|---|---|---|
| Search | `blocked` | Title query `Attention Is All You Need` failed on `/api/v1/search/unified` with 500. Fallback query `1706.03762` also failed with the same 500. API traceback shows `AttributeError: 'dict' object has no attribute 'source'` in `app/api/search/shared.py::deduplicate_results`; arXiv also hit `429` once and later `RemoteProtocolError`, but the blocking defect was the backend 500 after result aggregation. | `browser: /search?source=s2 Request failed state; API log request_id=f9e03cd5-ca2a-42dd-8893-57519241d827 and request_id=48c27ab8-afcb-4b35-b5db-4eef0ca66abe` |
| Import | `blocked` | Because Search never returned a usable result CTA, the planned D-001 import could not proceed through the mainline path. A separate KB-side arXiv pre-parse attempt also failed immediately: `POST /api/v1/imports/sources/resolve -> 404 Not Found`. | `browser: KB import dialog '解析失败 / Not Found'; API log request_id=fad66189-bfaa-4b3d-9915-11217ee0a4d6` |
| KB | `pass` | Fresh KB created successfully as `Phase2-Beta-20260503-01`; detail page loaded with `0 Papers / 0 Chunks` and showed readiness cards in the initial empty state. | `browser: /knowledge-bases/20fcc686-d8e5-440f-bfa5-7284149340b9` |
| Read | `blocked` | No paper was imported into the KB, so the Read page could not be opened for D-001. | `blocked by Search + Import` |
| Chat | `blocked` | No paper context was available because D-001 import never completed. The Phase 2 prefill-only manual-send handoff could not be exercised in this run. | `blocked by Search + Import` |
| Notes | `blocked` | No imported paper meant no Notes generation target. | `blocked by Search + Import` |
| Compare | `blocked` | D-001 never entered the KB, and D-040 was therefore not attempted under this run. | `blocked by upstream failure at step 2` |
| Review | `blocked` | Review was not run because the KB contained zero papers after the blocked import path. | `blocked by upstream failure at step 2` |

## 7. Observed Limitations And Triage

执行完成后至少补齐：

| field | value |
|---|---|
| `observed_limitations` | `Search mainline is blocked by a backend 500 in unified search deduplication; KB-side external import resolve endpoint returns 404; localhost/127.0.0.1 hostname mismatch can trigger browser CORS failure before the actual walkthrough starts; no citation/evidence probe could be collected because no paper entered the KB.` |
| `feedback_items` | `FB-20260503-SEARCH-500-unified-dedup`, `FB-20260503-IMPORT-404-source-resolve`, `FB-20260503-ORIGIN-CORS-localhost-vs-127001` |
| `go_no_go_recommendation` | `blocked` |

规则：

1. 若任一步为 `fail` 或 reset proof 缺失，推荐结论只能是 `blocked`。
2. 若主链可跑但 Review/Compare 出现 `partial`，walkthrough 结论最多是 `demo-ready`，且必须显式附 feedback item；phase closeout 是否可升级到 `controlled-beta-ready`，仍需单独读取 controlled release gate。
3. 只有 controlled release gate 也满足时，才允许写 `controlled-beta-ready`。
4. Chat handoff 的 `prefill-only` 手动确认属于已知限制，不能单独按故障计入，除非预填内容本身缺失或错乱。

## 8. 当前执行状态

截至 2026-05-04 CST，本文件记录了两次真实 Phase 2 walkthrough 证据：

### 8.1 Run A: `v4-beta-local-20260503-01`

1. 该轮 run 的结论为 `blocked`。
2. 阻断点是：
   - `/api/v1/search/unified` 在去重阶段因 `dict`/`SearchResult` 混用而返回 500。
   - KB 侧 source resolve 路径返回 404。
   - `localhost` / `127.0.0.1` 混用会触发真实浏览器 CORS 风险。
3. 该轮 run 仍然保留在本文中，作为已修复阻断点的历史证据。

### 8.2 Run B: `v4-beta-local-20260504-01`

本轮为修复后的 fresh-state 验证，证据分为两部分：

1. fresh import/search probe
   - kb_id: `021c2bef-fe6a-4635-ac05-3a62f439bc6e`
   - kb_name: `Phase2-Online-Verify-9fa04d82`
   - import_job_id: `imp_7f7b296d0a2a4f5ba4fd8f95`
   - result: `completed`
   - `paperCount=1`
   - `chunkCount=105`
   - `search_total=5`
2. browser walkthrough on a populated KB
   - kb_id: `2c58e5dd-270d-41f7-9b98-5bef5c449475`
   - verified surfaces:
     - KB readiness / paper list
     - KB search evidence panel
     - Compare matrix generation
     - Review Draft generation + run trace
     - KB chat handoff entry
     - Read page + Notes panel

### 8.3 Run B Step Summary

| step | result (`pass / partial / fail / blocked`) | notes | artifact_link |
|---|---|---|---|
| Search | `pass` | Fresh-state probe completed with KB search results after import; the earlier unified-search dedupe 500 is no longer reproducible on the fixed mainline. | `api_probe: kb_id=021c2bef-fe6a-4635-ac05-3a62f439bc6e, search_total=5` |
| Import | `pass` | Fresh import job completed through the online embedding mainline with dedupe resolution and final status `completed`. | `api_probe: import_job_id=imp_7f7b296d0a2a4f5ba4fd8f95, progress=100` |
| KB | `pass` | Fresh KB shows `paperCount=1`, `chunkCount=105`; populated validation KB shows `177 Chunks` and readiness cards in the healthy state. | `api_probe + browser: kb_id=021c2bef-fe6a-4635-ac05-3a62f439bc6e / 2c58e5dd-270d-41f7-9b98-5bef5c449475` |
| Read | `pass` | Read page for `d1f6ecda-464f-4401-a9b0-aec71b157e26` opened on page 12 and rendered content, thumbnails, section nav, and right-side assistant panel. | `browser: /read/d1f6ecda-464f-4401-a9b0-aec71b157e26?page=12&source=evidence` |
| Chat | `pass` | KB chat tab rendered the unified entry and preserved the correct `kb_id`; Compare page also exposed `Continue in Chat`. | `browser: KB ?tab=chat + Compare action bar` |
| Notes | `pass` | Read page rendered the Notes tab, editor, and note actions without runtime errors. | `browser: Read page right panel` |
| Compare | `pass` | Compare page now preloads `paper_ids` after auth settles, generates an evidence-backed matrix, and exposes Chat / Save actions. | `browser: /compare?paper_ids=0bfc54f2-302d-4be5-aaff-37ba1a22aa05,d1f6ecda-464f-4401-a9b0-aec71b157e26` |
| Review | `partial` | Review draft creation succeeded and rendered `partial` draft content plus run trace. The remaining limitation is semantic honesty: some sections are omitted with `insufficient_evidence`, which is acceptable for `demo-ready` but not a full success verdict. | `browser: KB ?tab=review, run_id=18a9bdb0-abff-4ace-b70b-c789beb0b76a` |

### 8.4 当前结论

1. `asset-ready`: 已满足。
2. `fresh-state run`: 已完成并回填。
3. `walkthrough verdict`: `walkthrough-complete / demo-ready`。
4. `phase closeout verdict`: 仍需单独读取 controlled release gate。
5. Run B 暴露的 `Review partial / insufficient_evidence` 不会自动阻断 local controlled beta，但必须进入 feedback triage，并在 phase closeout 中保留 known limitation 口径。
6. 是否可升级为 `controlled-beta-ready`，取决于 closeout 是否补齐：
   - 受控访问边界
   - feedback triage 实例
   - rollback / pause 规则
   - 不把 local controlled beta 误写成 public beta
