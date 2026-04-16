"""Memory monitoring service for dynamic concurrency scaling.

Phase 11: Batch upload + concurrent processing infrastructure.

Per D-03: Dynamic concurrency based on memory thresholds
Per D-04: Poll every 10 seconds
"""

import asyncio
import psutil

from app.utils.logger import logger


# Memory thresholds (in GB) per D-03
MEMORY_THRESHOLD_HIGH = 3.5   # Reduce to 2 workers
MEMORY_THRESHOLD_MEDIUM = 3.0 # Reduce to 3 workers
MEMORY_THRESHOLD_LOW = 2.5    # Can increase to 5 workers

# Concurrency limits per D-03
CONCURRENCY_MIN = 2
CONCURRENCY_MAX = 8
CONCURRENCY_DEFAULT = 8


class MemoryMonitor:
    """
    Memory monitor that adjusts Celery worker concurrency.

    Per D-03: Dynamic concurrency strategy
    Per D-04: Poll every 10 seconds
    """

    def __init__(self):
        self.running = False
        self.current_concurrency = CONCURRENCY_DEFAULT

    def get_memory_usage_gb(self) -> float:
        """Get current memory usage in GB."""
        mem = psutil.virtual_memory()
        return mem.used / (1024**3)

    def calculate_target_concurrency(self, memory_gb: float) -> int:
        """
        Calculate target concurrency based on memory usage.

        Per D-03:
        - >3.5GB → 2 workers
        - >3.0GB → 3 workers
        - <2.5GB → 5 workers (max 8)
        """
        if memory_gb > MEMORY_THRESHOLD_HIGH:
            return CONCURRENCY_MIN  # 2 workers
        elif memory_gb > MEMORY_THRESHOLD_MEDIUM:
            return 3
        elif memory_gb < MEMORY_THRESHOLD_LOW:
            return min(5, CONCURRENCY_MAX)  # 5 workers, max 8
        else:
            # Default range
            return self.current_concurrency

    async def monitor_loop(self):
        """
        Main monitoring loop.

        Per D-04: Check every 10 seconds
        """
        logger.info("Memory monitor started")

        while self.running:
            try:
                # Get memory usage
                memory_gb = self.get_memory_usage_gb()

                # Calculate target concurrency
                target_concurrency = self.calculate_target_concurrency(memory_gb)

                # Update if changed
                if target_concurrency != self.current_concurrency:
                    logger.info(
                        f"Memory {memory_gb:.2f}GB, "
                        f"adjusting concurrency from {self.current_concurrency} to {target_concurrency}"
                    )
                    self.current_concurrency = target_concurrency

                    # Update global concurrency for PDF tasks
                    from app.tasks.pdf_tasks import set_current_concurrency
                    set_current_concurrency(target_concurrency)

            except Exception as e:
                logger.error(f"Memory monitor error: {e}")

            # Sleep for 10 seconds (D-04)
            await asyncio.sleep(10)

    def start(self):
        """Start monitoring in background thread."""
        if not self.running:
            self.running = True
            # Create task in event loop
            asyncio.create_task(self.monitor_loop())
            logger.info("Memory monitor task created")

    def stop(self):
        """Stop monitoring."""
        self.running = False
        logger.info("Memory monitor stopped")


# Global monitor instance
_monitor_instance: MemoryMonitor = None


def get_memory_monitor() -> MemoryMonitor:
    """Get global memory monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = MemoryMonitor()
    return _monitor_instance


async def monitor_memory_and_scale():
    """
    Background task for memory monitoring.

    Call this from Celery worker startup or FastAPI lifespan.
    """
    monitor = get_memory_monitor()
    monitor.start()

    # Keep running until cancelled
    try:
        while monitor.running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        monitor.stop()
        raise