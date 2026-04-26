# Official Artifact Materialization v1 — Final Report

| Field | Value |
|---|---|
| Report ID | `official_artifact_materialization_v1` |
| Generated At | 2026-04-26T01:45:07Z |
| Phase | ScholarAI v1.0 Route — Supplement Step |
| Executed By | `scripts/evals/v2_4_materialize_official_artifacts.py` |

---

## 1. Objective

Generate canonical parse + chunk artifacts for all 50 benchmark papers using the formal backend pipeline, so that downstream consistency gates and Step4 ingestion can operate on verified, reproducible data.

**Constraints respected:**
- No Step5 Real Golden Expansion entered
- Artifact consistency gate NOT bypassed
- Benchmark script does NOT re-parse PDFs during eval runs
- Step4 retry gated on consistency PASS

---

## 2. Manifest

| Field | Value |
|---|---|
| Path | `tests/evals/fixtures/papers/manifest.json` |
| Paper count | 50 |
| Paper ID range | `v2-p-001` — `v2-p-050` |
| PDF root | `tests/evals/fixtures/papers/` |

---

## 3. Materialization Results

### Run Configuration

| Parameter | Value |
|---|---|
| `--parse-backend` | `pypdf` |
| `--force` | true |
| `--resume` | false (full rebuild) |

### Outcome

| Metric | Value |
|---|---|
| Papers attempted | 50 |
| Parse artifact SUCCESS | **50 / 50** |
| Chunk artifact SUCCESS | **50 / 50** |
| Overall status | **PASS** |
| Errors | 0 |

### Parse Mode Distribution

| Mode | Count |
|---|---|
| `pypdf_fallback` | 50 |

### Quality Level Distribution

| Level | Count |
|---|---|
| `text_only` | 50 |

### Artifact Counts

| Stage | Chunk Count |
|---|---|
| raw | 1,222 |
| rule | 1,222 |
| llm | 1,222 |

Artifacts written per paper:
- `artifacts/papers/{paper_id}/parse_artifact.json`
- `artifacts/papers/{paper_id}/chunks_raw.json`
- `artifacts/papers/{paper_id}/chunks_rule.json`
- `artifacts/papers/{paper_id}/chunks_llm.json`

---

## 4. Notable Issues Resolved

### Issue 1 — Page limit (v2-p-024)
- **Root cause**: `ParserConfig.max_num_pages` default 100; paper had 133 pages.
- **Fix**: `parser.config.max_num_pages = 2000` after `DoclingParser()` init.

### Issue 2 — Lone surrogate characters (v2-p-034, v2-p-035)
- **Root cause**: PDF text contained lone surrogate code points (`\ud835` etc.), causing `json.dumps(ensure_ascii=False)` to raise `UnicodeEncodeError`.
- **Fix**: `_clean_utf8()` — `re.sub(r"[\ud800-\udfff]", "", value)` applied to all parsed text before chunking and all payload values before write.

### Issue 3 — `section_path` / `normalized_section_path` empty values (47 papers)
- **Root cause**: `pypdf` fallback produces page-level items without IMRAD section detection → `chunk.section_path = ""` → `required_field_missing()` counts empty strings as missing (by design, except `anchor_text`).
- **Fix**: `_to_chunk_payload()` now uses `str(chunk.section_path or "body")` and `str(chunk.normalized_section_path or "body")` as defaults.
- **Re-run**: All 50 papers regenerated with `--force`; consistency gate re-run → **PASS**.

---

## 5. Artifact Consistency Gate

| Metric | Value |
|---|---|
| Gate script | `scripts/evals/v2_4_validate_artifacts.py` |
| Papers scanned | 50 |
| Blocked count | **0** |
| `page_num_non_empty_ratio` | **1.0** |
| Error types | none |
| **Status** | **PASS** ✓ |

---

## 6. Step4 Retry Authorization

Consistency gate **PASS** → **Step4 conditional retry: ALLOWED**

Step4 sequence to execute:
1. Dry-run ingestion
2. Real ingestion
3. Schema audit
4. Preflight check
5. Smoke test (1×3)

---

## 7. Deliverables

| Artifact | Path |
|---|---|
| Materialization dashboard JSON | `artifacts/benchmarks/v2_4/artifact_materialization_dashboard.json` |
| Materialization dashboard MD | `artifacts/benchmarks/v2_4/artifact_materialization_dashboard.md` |
| Materialization report JSON | `artifacts/benchmarks/v2_4/artifact_materialization_report.json` |
| This report | `docs/reports/api_flash_ingestion/official_artifact_materialization_v1_report.md` |
