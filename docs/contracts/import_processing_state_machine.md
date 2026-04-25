# Import / Processing State Machine

> Version: v1.0 · Backend Pipeline Cleanup Phase

## 1. Overview

Every file import flows through two coupled state machines:

```
ImportJob  (orchestration layer)
  └── ProcessingTask  (execution layer)
        └── PDFCoordinator  (stage source of truth)
```

`ImportJob` stage is **always derived** from `ProcessingTask` real stages; it
must never advance ahead of the underlying task.

## 2. ImportJob States

| Status | Stage | Description |
|--------|-------|-------------|
| `created` | `uploaded` | ImportJob exists, file not yet attached |
| `queued` | `queued` | File attached; Celery task enqueued |
| `running` | `resolving_source` | Worker started, resolving source |
| `running` | `validating_pdf` | PDF magic bytes check |
| `running` | `hashing_file` | SHA-256 computed |
| `running` | `dedupe_check` | Deduplication check against existing papers |
| `running` | `materializing_paper` | Paper row being created |
| `running` | `attaching_to_kb` | Paper attached to KnowledgeBase |
| `running` | `triggering_processing` | ProcessingTask created + Celery queued |
| `running` | `parsing` | PDFCoordinator: download + parse |
| `running` | `chunking` | PDFCoordinator: extraction |
| `running` | `embedding` | PDFCoordinator: storage phase |
| `running` | `indexing` | PDFCoordinator: finalizing |
| `running` | `finalizing` | Post-processing sync |
| `completed` | `completed` | Only after ProcessingTask.status == 'completed' |
| `failed` | `failed` | Terminal failure; retry available via next_action |

## 3. ProcessingTask States

| Status | Source | Notes |
|--------|--------|-------|
| `pending` | import_worker | Created before coordinator starts |
| `processing` | pdf_tasks | Coordinator running; no fake stages |
| `downloading` | PDFCoordinator callback | Stage 1: downloading PDF |
| `parsing` | PDFCoordinator callback | Stage 2: Docling OCR |
| `extracting` | PDFCoordinator callback | Stage 3: parallel extraction |
| `storing` | PDFCoordinator callback | Stage 4: PostgreSQL + Milvus + Neo4j |
| `completed` | PDFCoordinator / pdf_tasks | Terminal success |
| `failed` | PDFCoordinator / pdf_tasks | Terminal failure |

Stage values come **exclusively** from `PDFCoordinator.process()` via the
`on_stage_change` callback.  The fake stage loop
(`processing_ocr / extracting_imrad / generating_notes / storing_vectors /
indexing_multimodal`) has been removed in Pipeline Cleanup v1.

## 4. Stage Flow Diagram

```
[Upload endpoint]
      │  create ImportJob (status=created, stage=uploaded)
      │  save file → set_file_info → process_import_job.delay()
      ▼
[process_import_job Celery task]
  created → queued → running/resolving_source
      │  resolve / download (for URL/arXiv)
      │  validate PDF
      │  compute sha256
      │  dedupe check
      │  materialize Paper
      │  create ProcessingTask (pending)
      │  process_single_pdf_task.delay(paper_id, task_id)
      ▼
[process_single_pdf_task Celery task]
  ProcessingTask: pending → processing
      │
      ▼  PDFCoordinator.process(task_id, on_stage_change=...)
         on_stage_change("downloading", 15)   → ImportJob stage=parsing,   progress=20
         on_stage_change("parsing",    30)   → ImportJob stage=parsing,   progress=50
         on_stage_change("extracting", 55)   → ImportJob stage=chunking,  progress=70
         on_stage_change("storing",    80)   → ImportJob stage=indexing,  progress=85
         on_stage_change("completed",  100)  → ImportJob stage=completed  ← ONLY here
         on_stage_change("failed",     0)    → ImportJob stage=failed     ← or here
      ▼
  ProcessingTask: completed / failed
  ImportJob:      completed / failed
  UploadHistory:  COMPLETED / FAILED
  Paper.status:   completed / failed
```

## 5. Invariants

1. `ImportJob.status == 'completed'` ⟹ `ProcessingTask.status == 'completed'`
2. `ImportJob.completed_at IS NOT NULL` ⟹ `ProcessingTask.completed_at IS NOT NULL`
3. `ImportJob.status == 'failed'` ⟹ `ImportJob.error_code IS NOT NULL`
4. A single `paper_id` has at most **one** non-failed `ProcessingTask` at any
   time (enforced by the unique index on `processing_tasks.paper_id`).
5. Retrying a failed job does **not** create a new ProcessingTask if one already
   exists in `failed` state; it resets the existing task to `pending`.
6. `UploadHistory.status` mirrors the terminal ImportJob status on completion.

## 6. Retry Protocol

| Scenario | Behaviour |
|----------|-----------|
| `ImportJob.status == 'failed'` | `next_action = {"type": "retry"}` set |
| Re-triggering `process_import_job` | Idempotent: reuses existing ProcessingTask |
| ProcessingTask in `failed` state | Reset to `pending` before re-running |
| ProcessingTask in `completed` state | ImportJob marked completed; no re-run |
| ProcessingTask in `processing` state | No duplicate task created; return current state |

## 7. Canonical Celery Entry Points

| Task | Purpose |
|------|---------|
| `process_import_job(job_id)` | ImportJob orchestration; single entry point per import |
| `process_single_pdf_task(paper_id, task_id)` | PDF processing via PDFCoordinator |
| `on_processing_task_complete(task_id, paper_id)` | Post-completion callback (idempotent) |

`process_pdf_batch_task` remains for legacy batch flows but is **not** the
official entry point for new imports.
