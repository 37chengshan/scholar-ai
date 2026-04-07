"""Celery configuration for ScholarAI task queue.

Phase 11: Batch upload + concurrent processing infrastructure.

Per D-10: Use Redis as broker and backend.
- Broker: Redis DB 1 (task queue)
- Backend: Redis DB 2 (task results)

Per D-03: Dynamic concurrency scaling based on memory.
Per D-09: LLM API rate limit 120/min.
"""

from celery import Celery

# Celery app configuration
celery_app = Celery(
    'scholar_ai',
    broker='redis://localhost:6379/1',      # Broker: Redis DB 1
    backend='redis://localhost:6379/2',     # Backend: Redis DB 2
    include=[
        'app.tasks.pdf_tasks',  # Will be created in Plan 02
    ]
)

# Configuration per D-09 and D-10
celery_app.conf.update(
    # Execution limits (per D-03) - Reduced concurrency to prevent crashes
    worker_concurrency=1,              # Single worker to avoid memory issues
    worker_max_concurrency=1,          # Max 1 worker
    worker_min_concurrency=1,          # Min 1 worker
    task_soft_time_limit=600,          # 10 min soft limit
    task_time_limit=900,               # 15 min hard limit

    # Memory limits
    worker_max_memory_per_child=3072000,  # 3GB limit per worker (in KB)
    worker_prefetch_multiplier=1,         # Process one task at a time

    # Reliability settings
    task_acks_late=True,               # Acknowledge after completion
    task_reject_on_worker_lost=True,   # Reject if worker crashes
    broker_connection_retry_on_startup=True,

    # Rate limiting (per D-09)
    worker_disable_rate_limits=False,

    # Result backend
    result_expires=3600,  # 1 hour TTL for task results
)

# Export for use in tasks
__all__ = ['celery_app']