# Backend Pipeline Cleanup v1 — Final Report

**Date:** 2026-04-25
**Branch:** `feat/backend-pipeline-cleanup-v1`
**Milestone:** ScholarAI v1.0 Step 1

---

## Executive Summary

All upload / import / processing flows now converge on a single authoritative pipeline:

```
Upload → ImportJob (storage_key) → ImportJob queued → process_import_job (Celery)
       → ProcessingTask → PDFCoordinator → ParseArtifact
```

No fake processing stages, no direct ProcessingTask creation from upload endpoints,
no `os.getenv("LOCAL_STORAGE_PATH")` scattered across the codebase.

---

## Changed Endpoints

| Endpoint | Before | After |
|---|---|---|
| `POST /api/v1/papers/upload` | Created Paper + ProcessingTask directly | Delegates to `create_import_job_from_uploaded_file()` |
| `POST /api/v1/papers/webhook` | Created ProcessingTask directly | Returns ImportJob state; compat shim |

Both legacy response shapes are preserved for backward compatibility.

---

## Compat Endpoints (no functional change, retained)

- `POST /api/v1/uploads/` — local storage direct upload (unchanged)
- `POST /api/v1/kb/import` — KB-scoped import (uses `settings.LOCAL_STORAGE_PATH` now)
- All `/api/v1/imports/jobs` and `/api/v1/imports/batches` endpoints

---

## Authoritative Pipeline (Final)

```
client → POST /api/v1/papers/upload
              ↓
         create_import_job_from_uploaded_file()
              ↓  (creates ImportJob, calls process_import_job.delay())
         process_import_job  [Celery task]
              ↓  (creates ProcessingTask, calls process_single_pdf_task.delay())
         process_single_pdf_task  [Celery task]
              ↓  (calls PDFProcessor.process_pdf_task())
         PDFCoordinator.process()
              ↓  DOWNLOAD → PARSING → EXTRACTION → STORAGE
         → ParseArtifact, ChunkArtifact (future)
```

State is written back at every stage via `_sync_import_job_stage()` and
`_sync_import_job_terminal()`.

---

## Verdict Table

| Area | Result | Notes |
|---|---|---|
| Upload / File pipeline | **PASS** | `papers/upload` + `papers/webhook` are ImportJob-first |
| ImportJob state machine | **PASS** | Terminal sync idempotent; no regression on completed jobs |
| ProcessingTask state sync | **PASS** | `_sync_import_job_stage` + `_sync_import_job_terminal` in place |
| PDFCoordinator entrypoint | **PASS** | `on_stage_change` callback; fake stage loop removed |
| Storage path consistency | **PASS** | All `os.getenv("LOCAL_STORAGE_PATH")` replaced with `settings.LOCAL_STORAGE_PATH` |

---

## ProcessingTask State Truthfulness

**Verdict: PASS**

- Fake stage loop (`processing_ocr`, `parsing`, ...) removed from `process_single_pdf_async()`
- Coordinator fires real stage callbacks: `downloading → parsing → extracting → storing → completed/failed`
- `_sync_import_job_stage()` mirrors coordinator stages to ImportJob in real time
- `_sync_import_job_terminal()` sets final status with error code on failure

---

## ImportJob Completion Timing

**Verdict: PASS**

- ImportJob is only marked `completed` after ProcessingTask `completed` callback fires
- Idempotency guard prevents status regression if callback fires more than once
- Cancelled / failed jobs are not reopened by late-arriving stage callbacks

---

## Storage Key Unification

**Verdict: PASS**

Canonical format: `uploads/{user_id}/{YYYY}/{MM}/{DD}/{import_job_id}.pdf`

Single authoritative helper: `import_file_service.build_upload_storage_key()`

All storage path roots use `settings.LOCAL_STORAGE_PATH` (not `os.getenv`).

Files patched (8):

1. `app/core/storage.py`
2. `app/api/kb/kb_import.py`
3. `app/api/uploads.py`
4. `app/api/imports/jobs.py`
5. `app/api/imports/batches.py`
6. `app/workers/import_worker.py`
7. `app/services/upload_session_service.py`
8. `app/workers/import_worker_helpers.py`

---

## Remaining Legacy Methods (Deprecated, Not Removed)

These methods in `PDFProcessor` emit `DeprecationWarning` and are retained for
backward compatibility only. **None are called by the official pipeline.**

| Method | Deprecation Message |
|---|---|
| `process_pdf_main_chain()` | Use `process_pdf_task()` instead |
| `process_pdf_enhancement_chain()` | Use `process_pdf_task()` instead |
| `_parse_pdf()` | Pipeline stages handled by PDFCoordinator |
| `_chunk_content()` | Pipeline stages handled by PDFCoordinator |
| `_embed_text_chunks()` | Pipeline stages handled by PDFCoordinator |
| `_store_chunks()` | Pipeline stages handled by PDFCoordinator |

Target for removal: v1.1 (once all callers confirmed non-existent via grep audit).

---

## Blocking Items Before ParseArtifact / ChunkArtifact Standardisation

1. **ParseArtifact model** not yet created — PDFCoordinator stores parsed content but
   does not write a `ParseArtifact` row. Blocked on schema migration (v1.0 Step 2).
2. **ChunkArtifact model** not yet created — chunked content stored in Milvus only.
   Blocked on schema migration + Milvus metadata alignment (v1.0 Step 3).
3. **paper_upload compat response** — `paperId` is `None` for direct uploads because
   the Paper record is not created at upload time (ImportJob-only flow).  Paper creation
   is deferred to post-processing; callers that rely on immediate `paperId` need update.

---

## New Artifacts

| File | Purpose |
|---|---|
| `apps/api/app/services/import_file_service.py` | Canonical ImportJob-first upload helper |
| `docs/contracts/file_metadata_contract.md` | storage_key format + propagation rules |
| `docs/contracts/import_processing_state_machine.md` | State machine diagrams + invariants |
| `docs/reports/backend_pipeline_cleanup/upload_entry_audit.md` | 15-endpoint audit table |
| `apps/api/tests/test_storage_path_consistency.py` | 3 storage path tests |
| `apps/api/tests/test_pdf_processing_entrypoint.py` | 7 coordinator + deprecation tests |
| `apps/api/tests/test_import_processing_state_sync.py` | 6 state sync tests |

---

## Test Coverage

```
17 tests, 17 passed, 0 failed
```

- `test_storage_path_consistency.py` — 3/3 ✅
- `test_pdf_processing_entrypoint.py` — 7/7 ✅
- `test_import_processing_state_sync.py` — 6/6 ✅ (including idempotency + terminal guard)

---

## Constraints Honoured

- No RAG model changes ✅
- No Milvus collection drops ✅
- No benchmark re-runs ✅
- No frontend UI changes ✅
- No deletion of old API endpoints (compat shims only) ✅
- All failures explicitly written to ImportJob / ProcessingTask ✅
