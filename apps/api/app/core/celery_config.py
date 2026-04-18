"""Celery configuration for ScholarAI task queue.

Phase 11: Batch upload + concurrent processing infrastructure.

Per D-10: Use Redis as broker and backend.
- Broker: Redis DB 1 (task queue)
- Backend: Redis DB 2 (task results)

Per D-03: Dynamic concurrency scaling based on memory.
Per D-09: LLM API rate limit 120/min.
"""

import os

from celery import Celery


def _get_broker_url() -> str:
    """Resolve Celery broker URL from environment.

    Priority:
    1. CELERY_BROKER_URL (explicit)
    2. REDIS_URL with DB index replaced to /1
    3. Fallback to localhost (development only)
    """
    if os.environ.get("CELERY_BROKER_URL"):
        return os.environ["CELERY_BROKER_URL"]
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    # Replace the DB index at the end with /1
    parts = redis_url.rsplit("/", 1)
    return f"{parts[0]}/1"


def _get_backend_url() -> str:
    """Resolve Celery result backend URL from environment.

    Priority:
    1. CELERY_RESULT_BACKEND (explicit)
    2. REDIS_URL with DB index replaced to /2
    3. Fallback to localhost (development only)
    """
    if os.environ.get("CELERY_RESULT_BACKEND"):
        return os.environ["CELERY_RESULT_BACKEND"]
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    parts = redis_url.rsplit("/", 1)
    return f"{parts[0]}/2"


# Celery app configuration
celery_app = Celery(
    "scholar_ai",
    broker=_get_broker_url(),
    backend=_get_backend_url(),
    include=[
        "app.tasks.pdf_tasks",  # PDF processing tasks
        "app.workers.import_worker",  # ImportJob processing worker (Wave 5)
        "app.workers.finalize_import_job",  # Unified finalize worker
    ],
)

# Configuration per D-09 and D-10
celery_app.conf.update(
    # Execution limits (per D-03) - Reduced concurrency to prevent crashes
    worker_concurrency=1,  # Single worker to avoid memory issues
    worker_max_concurrency=1,  # Max 1 worker
    worker_min_concurrency=1,  # Min 1 worker
    task_soft_time_limit=600,  # 10 min soft limit
    task_time_limit=900,  # 15 min hard limit
    # Memory limits
    worker_max_memory_per_child=3072000,  # 3GB limit per worker (in KB)
    worker_prefetch_multiplier=1,  # Process one task at a time
    # Reliability settings
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,  # Reject if worker crashes
    broker_connection_retry_on_startup=True,
    # Rate limiting (per D-09)
    worker_disable_rate_limits=False,
    # Result backend
    result_expires=3600,  # 1 hour TTL for task results
    # Minimal queue boundaries for upload/import pipeline
    task_routes={
        "app.workers.import_worker.process_import_job": {"queue": "import.process"},
        "app.tasks.pdf_tasks.process_single_pdf_task": {"queue": "pdf.process"},
        "app.tasks.pdf_tasks.process_pdf_batch_task": {"queue": "pdf.process"},
        "app.workers.finalize_import_job.finalize_import_job_success_task": {
            "queue": "import.finalize"
        },
        "app.workers.finalize_import_job.finalize_import_job_failure_task": {
            "queue": "import.finalize"
        },
        "app.tasks.upload_maintenance_tasks.*": {"queue": "upload.maintenance"},
    },
)

# Export for use in tasks
__all__ = ["celery_app"]
