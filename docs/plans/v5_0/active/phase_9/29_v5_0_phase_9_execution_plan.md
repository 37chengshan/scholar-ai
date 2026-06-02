---
owner: product-engineering
status: active
created_at: 2026-05-31
last_verified_at: 2026-05-31
depends_on:
  - scripts/evals/run_v5_release_gate.py
  - docs/plans/v5_0/active/phase_0/v5_0_gate_input_matrix.md
  - docs/plans/PLAN_STATUS.md
consumed_by:
  - scripts/evals/run_v5_release_gate.py
---

# Phase 5.0-9 Execution Plan: Release Gate

> consolidated gate runner 最终执行：7 E2E journeys、walkthrough summary、
> Lighthouse collection、multidimensional audit、release verdict。

---

## 1. Objective

完成 v5.0 consolidated release gate 的全部 5 个输入面（audit / benchmark /
walkthrough / governance / perf），使 `run_v5_release_gate.py` 能产出
`release-pass` 或 `experiment-only` verdict。

**核心交付物：**

1. 7 个 E2E journey spec（J1-J7）覆盖产品主链
2. walkthrough summary generator（Python）产出 `latest_summary.json`
3. Lighthouse collection 脚本产出 4 路由 JSON
4. multidimensional audit 报告模板
5. gate runner 修复（path traversal、version label）
6. 干跑验证 + 最终 release verdict

---

## 2. Pre-Conditions & Mandatory Fixes

### 2.1 Path Traversal Fix (CRITICAL)

`--output-json` 和 `--output-md` CLI 参数绕过 `_safe_path()` 验证，允许
写入项目树外任意文件。必须在 Wave 0 修复。

**文件**: `scripts/evals/run_v5_release_gate.py` L471, L475

**修复**:

```python
# L471: wrap with _safe_path
jp = _safe_path(Path(args.output_json)) if args.output_json else ROOT / "artifacts" / ...
# L475: wrap with _safe_path
mp = _safe_path(Path(args.output_md)) if args.output_md else ROOT / "docs" / ...
```

### 2.2 Version Label Fix

`_GATE_VERSION = "5.0-0"` 应为 `"5.0-9"`。当前值在 gate report 中产生
误导性标签。

### 2.3 Chat-Notes Bridge Pre-Verification

Phase 5.0-6 closeout 明确标注 "Out of scope: Chat-to-Notes bridge (5.0-6b)"。
J6（Notes -> @chat session）和 J7（Chat -> Push to notes）依赖该桥接。
必须在写 J6/J7 spec 前验证桥接 API 端点是否可用。

---

## 3. Tasks

### Wave 0: Foundation & Fixes

#### T0.1 -- Gate Runner Fixes + Artifact Scaffolding

**name**: gate-runner-fixes-and-scaffolding
**files**:
- `scripts/evals/run_v5_release_gate.py` (fix path traversal + version)
- `scripts/evals/test_run_v5_release_gate.py` (add tests for fixes)
- `artifacts/walkthrough/v5_0/` (mkdir -p)
- `artifacts/perf/v5_0/` (mkdir -p)
- `docs/plans/v5_0/reports/` (audit template)

**action**:
1. Fix `_safe_path()` on `--output-json` (L471) and `--output-md` (L475)
2. Fix `_GATE_VERSION` from `"5.0-0"` to `"5.0-9"`
3. Add test: `--output-json` with path outside ROOT raises SystemExit(2)
4. Add test: `--output-md` with path outside ROOT raises SystemExit(2)
5. Add test: `_GATE_VERSION == "5.0-9"`
6. `mkdir -p artifacts/walkthrough/v5_0 artifacts/perf/v5_0`
7. Create skeleton `artifacts/walkthrough/v5_0/latest_summary.json` with
   correct schema (all 7 journeys skipped) for gate runner dry-run

**verify**:
```bash
cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai
python -m pytest scripts/evals/test_run_v5_release_gate.py -q
ls artifacts/walkthrough/v5_0/latest_summary.json
ls artifacts/perf/v5_0/
```

**done**: gate runner tests pass including new path/version tests; artifact
directories exist; skeleton summary has correct schema

**type**: fix + infra

---

#### T0.2 -- Multidimensional Audit Report Template

**name**: multidimensional-audit-template
**files**:
- `docs/plans/v5_0/reports/2026-05-31_v5_0_multidimensional_audit.md`

**action**:
1. Create audit report with all 5 required dimensions:
   `[frontend, backend, rag, governance, perf]`
2. For each dimension, enumerate known issues from phases 0-8 closeout
3. Classify issues as P1/P2/P3
4. Set `p1_count_open: 0` if no P1 issues remain (or list them)
5. Include required fields: `p1_count_open`, `p2_count_open`,
   `last_audit_date`, `audit_dimensions_covered`

**verify**:
```bash
python -c "
import re
text = open('docs/plans/v5_0/reports/2026-05-31_v5_0_multidimensional_audit.md').read()
m1 = re.search(r'p1_count_open[:\s]+\`?(\d+)\`?', text)
mx = re.search(r'audit_dimensions_covered[:\s]+\`?\[([^\]]*)\]\`?', text)
assert m1, 'p1_count_open not found'
dims = [d.strip().strip('\"\'') for d in mx.group(1).split(',') if d.strip()]
assert set(dims) == {'frontend','backend','rag','governance','perf'}, f'dims={dims}'
print(f'p1={m1.group(1)}, dims={dims}')
"
```

**done**: audit report exists, has p1_count_open=0 (or lists blockers),
covers all 5 dimensions, gate runner Face A parses it

**type**: docs

---

#### T0.3 -- Walkthrough Summary Generator

**name**: walkthrough-summary-generator
**files**:
- `scripts/evals/generate_walkthrough_summary.py`
- `scripts/evals/test_generate_walkthrough_summary.py`

**action**:
1. Create Python script at `scripts/evals/generate_walkthrough_summary.py`
2. Accept `--playwright-json` (Playwright JSON reporter output path)
   and `--output` (default: `artifacts/walkthrough/v5_0/latest_summary.json`)
3. Parse Playwright JSON results, match test titles to journey IDs (J1-J7)
   via regex on spec filename (`journey-j{N}-*.spec.ts`)
4. Output JSON schema matching gate runner Face C expectations:
   ```json
   {
     "journey_passed_count": 0,
     "journey_failed_count": 0,
     "journey_skipped_count": 7,
     "journey_details": [
       {"journey_id": "J1", "status": "skipped", "error_summary": null}
     ],
     "last_run_at": "2026-05-31T00:00:00Z",
     "playwright_report_path": "apps/web/playwright-report"
   }
   ```
5. Create test file with 4 test cases: all pass, partial fail, all skip,
   missing input file

**verify**:
```bash
python -m pytest scripts/evals/test_generate_walkthrough_summary.py -q
python scripts/evals/generate_walkthrough_summary.py --help
```

**done**: generator script exists, tests pass, output schema matches gate
runner Face C parser (L226-239 of run_v5_release_gate.py)

**type**: infra

---

### Wave 1: E2E Journey Specs (J1-J4)

> J1-J4 依赖单模块功能，不跨 Chat-Notes 边界。可并行编写。

#### T1.1 -- J1: Landing -> Login -> Dashboard

**name**: journey-j1-landing-login-dashboard
**files**:
- `apps/web/e2e/journey-j1-landing-login-dashboard.spec.ts`

**action**:
1. Create spec following `chat-critical.spec.ts` pattern:
   - `test.describe.configure({ mode: 'serial' })`
   - Use `registerAndLogin()` from `helpers/auth.ts`
2. Journey steps:
   - Navigate to `/` (landing page)
   - Assert landing page renders (heading or CTA visible)
   - Navigate to `/login`
   - Login with `registerAndLogin()`
   - Assert redirect to `/dashboard`
   - Assert dashboard renders (heading, cards, or nav visible)
3. Tag test title with `J1` for summary generator matching

**verify**:
```bash
cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai/apps/web
npx playwright test journey-j1-landing-login-dashboard --reporter=json 2>&1 | head -20
```

**done**: spec file exists, test passes against running dev server,
test title contains "J1"

**type**: e2e

---

#### T1.2 -- J2: Upload -> Parse -> Index -> Ready

**name**: journey-j2-upload-pipeline
**files**:
- `apps/web/e2e/journey-j2-upload-pipeline.spec.ts`

**action**:
1. Create spec following `pr19-min-flow.spec.ts` pattern with SSE mocking
2. Journey steps:
   - Login via `registerAndLogin()`
   - Navigate to `/kb` (knowledge base)
   - Trigger upload action (click upload button or drag-drop)
   - Mock SSE events for 7-stage pipeline progress using `page.route()`
   - Assert PipelineProgressCard stepper renders each stage
   - Assert final "Ready" status
3. Use route mocking (`page.route('**/api/v1/imports/events*')`) to
   simulate SSE pipeline without requiring running backend
4. Tag test title with `J2`

**verify**: spec file exists, test passes, title contains "J2"

**type**: e2e

---

#### T1.3 -- J3: Search -> Import to KB

**name**: journey-j3-search-import-kb
**files**:
- `apps/web/e2e/journey-j3-search-import-kb.spec.ts`

**action**:
1. Create spec combining search and KB flows
2. Journey steps:
   - Login via `registerAndLogin()`
   - Navigate to search page (e.g., `/search` or search bar in sidebar)
   - Enter search query, assert results appear
   - Select a result, click "Import to KB" action
   - Assert KB creation/import confirmation
   - Navigate to `/kb`, assert paper appears in KB list
3. Mock search API response if backend unavailable
4. Tag test title with `J3`

**verify**: spec file exists, test passes, title contains "J3"

**type**: e2e

---

### Wave 2: E2E Journey Specs (J4-J5) + Chat-Notes Bridge Verify

#### T2.1 -- J4: KB -> Read Paper

**name**: journey-j4-kb-read-paper
**files**:
- `apps/web/e2e/journey-j4-kb-read-paper.spec.ts`

**action**:
1. Create spec following `kb-critical.spec.ts` + `read-workspace.spec.ts` pattern
2. Journey steps:
   - Login via `registerAndLogin()`
   - Navigate to `/kb`
   - Select a paper from KB (or mock KB list response)
   - Click paper to open Read workspace
   - Assert `/read/:paperId` URL loads
   - Assert Read workspace renders (PDF viewer, toolbar, or loading state)
3. Tag test title with `J4`

**verify**: spec file exists, test passes, title contains "J4"

**type**: e2e

---

#### T2.2 -- J5: Read -> Highlight -> Linked Note

**name**: journey-j5-read-highlight-note
**files**:
- `apps/web/e2e/journey-j5-read-highlight-note.spec.ts`

**action**:
1. Create spec based on `read-workspace.spec.ts` pattern
2. Journey steps:
   - Login via `registerAndLogin()`
   - Navigate to `/read/:paperId`
   - Wait for PDF content to render
   - Select text in PDF (dispatch `mouseup` event on content area)
   - Assert floating annotation toolbar appears (`[data-testid="floating-annotation-toolbar"]`)
   - Click "Create Note" or "Highlight" action on toolbar
   - Assert linked note is created (note panel shows new entry)
3. If highlight creation requires backend, mock the annotation API
4. Tag test title with `J5`

**verify**: spec file exists, test passes, title contains "J5"

**type**: e2e

---

#### T2.3 -- Chat-Notes Bridge API Pre-Verification

**name**: chat-notes-bridge-verify
**files**:
- `scripts/evals/verify_chat_notes_bridge.py` (temporary verification script)

**action**:
1. Check if `apps/api` has endpoints for:
   - `POST /api/v1/sessions/:id/notes` (push chat to notes)
   - `GET /api/v1/notes/:id/chat-sessions` (notes @mention chat)
2. If endpoints exist: test with curl/httpx, record response
3. If endpoints do not exist:
   - Document the gap
   - Determine if J6/J7 should be marked `skipped` or if a minimal
     bridge can be implemented in-line
4. Output: `artifacts/walkthrough/v5_0/bridge_verification.json` with
   `{j6_bridge_available: bool, j7_bridge_available: bool, details: {...}}`

**verify**:
```bash
python scripts/evals/verify_chat_notes_bridge.py
cat artifacts/walkthrough/v5_0/bridge_verification.json
```

**done**: bridge verification result is known; J6/J7 spec scope is
adjusted based on findings

**type**: verification

---

### Wave 3: E2E Journey Specs (J6-J7) + Lighthouse

> J6/J7 scope depends on T2.3 bridge verification outcome.

#### T3.1 -- J6: Notes -> @ Chat Session

**name**: journey-j6-notes-mention-chat
**files**:
- `apps/web/e2e/journey-j6-notes-mention-chat.spec.ts`

**action**:
1. If bridge available:
   - Login, navigate to notes page
   - Open a note, type `@` to trigger mention suggestion
   - Select a chat session from suggestion list
   - Assert mention pill renders
   - Click mention pill, assert navigation to chat session
2. If bridge unavailable:
   - Write spec with `test.skip()` and `error_summary` explaining gap
   - Tag as `J6` so summary generator counts as skipped
3. Tag test title with `J6`

**verify**: spec file exists, passes or skips with documented reason,
title contains "J6"

**type**: e2e

---

#### T3.2 -- J7: Chat -> Push to Notes

**name**: journey-j7-chat-push-notes
**files**:
- `apps/web/e2e/journey-j7-chat-push-notes.spec.ts`

**action**:
1. If bridge available:
   - Login, navigate to `/chat`
   - Send a message, wait for response
   - Find "Push to Notes" or "Save to Notes" action on message
   - Click action, assert note creation confirmation
   - Navigate to notes page, assert new note exists
2. If bridge unavailable:
   - Write spec with `test.skip()` and `error_summary` explaining gap
   - Tag as `J7` so summary generator counts as skipped
3. Tag test title with `J7`

**verify**: spec file exists, passes or skips with documented reason,
title contains "J7"

**type**: e2e

---

#### T3.3 -- Lighthouse Collection Script

**name**: lighthouse-collection-script
**files**:
- `scripts/evals/collect_lighthouse.sh`

**action**:
1. Create bash script that:
   - Starts dev server if not running (or assumes `PLAYWRIGHT_BASE_URL`)
   - Runs `npx lighthouse` for each of 4 routes: `/`, `/kb`, `/read`, `/chat`
   - Saves JSON to `artifacts/perf/v5_0/lighthouse-{route_id}.json`
   - Route IDs must match gate runner `_ROUTES` dict exactly:
     `route_landing`, `route_kb`, `route_read`, `route_chat`
2. Accept `--base-url` flag (default: `http://localhost:5173`)
3. Accept `--output-dir` flag (default: `artifacts/perf/v5_0`)
4. Exit non-zero if any Lighthouse run fails

**verify**:
```bash
bash scripts/evals/collect_lighthouse.sh --help
# dry-run: check filename convention matches gate runner
ls artifacts/perf/v5_0/lighthouse-route_*.json 2>/dev/null || echo "No artifacts yet (expected)"
```

**done**: script exists, filenames match gate runner glob pattern
`lighthouse-{rid}*.json` (line 310 of gate runner)

**type**: infra

---

### Wave 4: Integration & Gate Execution

#### T4.1 -- Wire Summary Generator to Playwright + Gate Runner

**name**: wire-walkthrough-to-gate
**files**:
- `scripts/evals/generate_walkthrough_summary.py` (update)
- `package.json` (add e2e:journeys script)

**action**:
1. Add npm script in `apps/web/package.json`:
   ```json
   "e2e:journeys": "npx playwright test journey-j --reporter=json > /tmp/pw-results.json"
   ```
2. Update summary generator to also accept stdin or default path
3. End-to-end test:
   - Run `npm run e2e:journeys` (may fail if no backend -- that's OK)
   - Run `python scripts/evals/generate_walkthrough_summary.py`
   - Verify `artifacts/walkthrough/v5_0/latest_summary.json` has
     correct schema
4. Run gate runner dry-run:
   ```bash
   python scripts/evals/run_v5_release_gate.py \
     --output-json /tmp/gate-dry-run.json \
     --output-md /tmp/gate-dry-run.md
   ```
   Expected: `blocked` (missing benchmark artifacts, possibly missing
   Lighthouse). Verify Face C reads summary correctly.

**verify**:
```bash
python scripts/evals/run_v5_release_gate.py 2>&1 | grep "verdict="
cat artifacts/validation-results/v5_0/phase0_gate_results.json | python -m json.tool | head -30
```

**done**: gate runner dry-run completes, Face C shows journey counts
from summary generator, other faces show expected block reasons

**type**: integration

---

#### T4.2 -- Governance Face D Circular Dependency Resolution

**name**: face-d-circular-dependency-fix
**files**:
- `scripts/evals/run_v5_release_gate.py` (optional --skip-phase-closeout flag)
- `docs/plans/PLAN_STATUS.md` (update Phase 9 status after gate passes)

**action**:
1. The circular dependency: Face D checks `all_phases_closeout` which
   requires Phase 9 to be `done`, but Phase 9 IS the gate runner.
2. Strategy: Add `--skip-phase-closeout` CLI flag to gate runner that
   sets `all_phases_closeout = True` for dry-run purposes.
3. After all other faces pass, update PLAN_STATUS.md Phase 9 to
   `closeout-complete` and re-run gate without the skip flag.
4. Add test for the new flag.

**verify**:
```bash
python scripts/evals/run_v5_release_gate.py --skip-phase-closeout 2>&1 | grep "verdict="
python -m pytest scripts/evals/test_run_v5_release_gate.py -q -k "skip_phase"
```

**done**: gate runner supports `--skip-phase-closeout`, test passes,
PLAN_STATUS Phase 9 updated after final run

**type**: fix

---

#### T4.3 -- Final Gate Execution + Closeout

**name**: final-gate-execution
**files**:
- `docs/plans/PLAN_STATUS.md` (Phase 9 status)
- `docs/plans/v5_0/reports/` (gate report)
- `artifacts/validation-results/v5_0/` (gate JSON)

**action**:
1. Ensure all 5 faces have valid input artifacts:
   - Face A: audit report exists with p1_count_open=0
   - Face B: benchmark artifacts exist (or document as blocked)
   - Face C: walkthrough summary shows 7 journeys (pass or skip)
   - Face D: all governance scripts pass + phases closed
   - Face E: Lighthouse JSONs exist (or document as blocked)
2. Run gate runner without skip flag:
   ```bash
   python scripts/evals/run_v5_release_gate.py
   ```
3. Record verdict. If `blocked`, document block reasons. If
   `experiment-only`, document downgrades. If `release-pass`, celebrate.
4. Update PLAN_STATUS.md Phase 9 to `closeout-complete`
5. Create closeout report at
   `docs/plans/v5_0/reports/2026-05-31_v5_0_phase_9_release_gate_closeout.md`

**verify**:
```bash
python scripts/evals/run_v5_release_gate.py
grep "closeout-complete" docs/plans/PLAN_STATUS.md | grep "9"
ls docs/plans/v5_0/reports/*phase_9*closeout*.md
```

**done**: gate runner produces verdict, PLAN_STATUS updated, closeout
report exists

**type**: closeout

---

## 4. Wave Dependency Map

```
Wave 0 (Foundation)
  T0.1 gate-runner-fixes ──────┐
  T0.2 audit-template ─────────┤
  T0.3 summary-generator ──────┤
                               ├─> Wave 1 (J1-J4)
                               │     T1.1 J1 ─────────┐
                               │     T1.2 J2 ─────────┤
                               │     T1.3 J3 ─────────┤
                               │                       ├─> Wave 2 (J5 + Bridge)
                               │                       │     T2.1 J4 (from Wave 1)
                               │                       │     T2.2 J5
                               │                       │     T2.3 bridge-verify
                               │                       │
                               │                       ├─> Wave 3 (J6-J7 + Lighthouse)
                               │                       │     T3.1 J6 (needs T2.3)
                               │                       │     T3.2 J7 (needs T2.3)
                               │                       │     T3.3 lighthouse
                               │                       │
                               │                       └─> Wave 4 (Integration)
                               │                             T4.1 wire + dry-run
                               │                             T4.2 circular-dep fix
                               │                             T4.3 final gate + closeout
```

---

## 5. Success Criteria

| Criterion | Measurable Check |
|-----------|-----------------|
| Gate runner path traversal fixed | `--output-json /etc/x` raises error |
| Gate runner version is 5.0-9 | `_GATE_VERSION == "5.0-9"` |
| 7 E2E journey specs exist | `ls apps/web/e2e/journey-j*.spec.ts \| wc -l` == 7 |
| Walkthrough summary generator works | `pytest scripts/evals/test_generate_walkthrough_summary.py` passes |
| Gate runner Face C reads summary | dry-run shows `journey_passed_count` or `journey_skipped_count` in Face C |
| Audit report covers 5 dimensions | regex parse confirms `["frontend","backend","rag","governance","perf"]` |
| Lighthouse filenames match gate runner | `lighthouse-route_landing.json` matches glob `lighthouse-{rid}*.json` |
| Gate runner dry-run completes | `python scripts/evals/run_v5_release_gate.py` exits with verdict |
| PLAN_STATUS Phase 9 is closeout-complete | grep confirms |
| Closeout report exists | file at `docs/plans/v5_0/reports/*phase_9*closeout*` |

---

## 6. Risk Inventory

| Risk | Impact | Mitigation |
|------|--------|------------|
| J6/J7 Chat-Notes bridge not implemented | 2 journeys skip -> experiment-only | T2.3 pre-verification; skip with documented reason is acceptable |
| Backend not running during E2E | J2/J3 may need more mocking | Use `page.route()` for API mocking |
| Lighthouse requires running dev server | Face E blocks if no perf artifacts | T3.3 script handles server startup |
| Face D circular dependency | Gate always blocks on phase closeout | T4.2 adds `--skip-phase-closeout` flag |
| Existing 17 E2E specs may regress | False failures in journey runs | Run existing specs first as baseline |

---

## 7. Effort Estimate

| Wave | Tasks | Estimated Effort |
|------|-------|-----------------|
| Wave 0 | 3 | 1.5 days |
| Wave 1 | 3 | 2 days |
| Wave 2 | 3 | 2 days |
| Wave 3 | 3 | 2 days |
| Wave 4 | 3 | 1.5 days |
| **Total** | **15** | **~9 days** |

---

## 8. Gate Runner Face C JSON Schema Contract

Gate runner `_evaluate_face_c()` (L224-246) reads `latest_summary.json` with
this exact schema. The walkthrough summary generator MUST produce this shape:

```json
{
  "journey_passed_count": 7,
  "journey_failed_count": 0,
  "journey_skipped_count": 0,
  "journey_details": [
    {
      "journey_id": "J1",
      "status": "passed",
      "error_summary": null
    }
  ],
  "last_run_at": "2026-05-31T10:00:00Z",
  "playwright_report_path": "apps/web/playwright-report"
}
```

Field types:
- `journey_passed_count`: integer (0-7)
- `journey_failed_count`: integer (0-7)
- `journey_skipped_count`: integer (0-7)
- `journey_details`: array of `{journey_id: string, status: "passed"|"failed"|"skipped", error_summary: string|null}`
- `last_run_at`: ISO 8601 datetime string
- `playwright_report_path`: string (relative to ROOT)

---

## 9. Lighthouse Filename Convention

Gate runner `_evaluate_face_e()` (L310) globs for:
```
artifacts/perf/v5_0/lighthouse-{route_id}*.json
```

Where `route_id` is one of: `route_landing`, `route_kb`, `route_read`, `route_chat`.

Collection script MUST produce files named:
```
artifacts/perf/v5_0/lighthouse-route_landing.json
artifacts/perf/v5_0/lighthouse-route_kb.json
artifacts/perf/v5_0/lighthouse-route_read.json
artifacts/perf/v5_0/lighthouse-route_chat.json
```
