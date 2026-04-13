"""Notes 异步生成 Worker。

Per Review Fix #9: 独立任务表 + FOR UPDATE SKIP LOCKED 抢占。
"""

import asyncio
import os
from datetime import datetime
from typing import Optional

import asyncpg

from app.core.notes_generator import NotesGenerator
from app.utils.logger import logger


class NotesWorker:
    """Notes 异步生成 Worker。

    Per Review Fix #9: 使用 FOR UPDATE SKIP LOCKED 抢占机制防止多 worker 重复处理。
    """

    WORKER_ID = "notes-worker-01"  # 可配置
    POLL_INTERVAL = 5
    MAX_ATTEMPTS = 3

    def __init__(self):
        self.db_pool: Optional[asyncpg.Pool] = None
        self.notes_generator = NotesGenerator()

    async def init_db(self) -> None:
        """初始化数据库连接。"""
        if not self.db_pool:
            db_url = os.getenv("DATABASE_URL")
            # Convert async URL to sync URL for asyncpg
            if db_url and db_url.startswith("postgresql+asyncpg://"):
                db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            self.db_pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)
            logger.info("Notes worker database pool initialized")

    async def claim_task(self) -> Optional[dict]:
        """抢占任务（FOR UPDATE SKIP LOCKED）。

        Per Review Fix #9: 防止多 worker 重复处理。

        Returns:
            Task dict if claimed, None if no pending tasks.
        """
        async with self.db_pool.acquire() as conn:
            task = await conn.fetchrow(
                """UPDATE notes_generation_tasks
                   SET status = 'claimed',
                       claimed_by = $1,
                       claimed_at = NOW()
                   WHERE id = (
                       SELECT id FROM notes_generation_tasks
                       WHERE status = 'pending'
                         AND attempts < $2
                       ORDER BY created_at ASC
                       FOR UPDATE SKIP LOCKED
                       LIMIT 1
                   )
                   RETURNING *""",
                self.WORKER_ID,
                self.MAX_ATTEMPTS,
            )
            return dict(task) if task else None

    async def generate_notes(self, paper_id: str) -> Optional[str]:
        """生成阅读笔记。

        Args:
            paper_id: Paper UUID

        Returns:
            Generated notes string, or None if paper not found.
        """
        async with self.db_pool.acquire() as conn:
            paper = await conn.fetchrow(
                """SELECT title, authors, year, venue, "imradJson"
                   FROM papers WHERE id = $1""",
                paper_id,
            )

        if not paper:
            logger.warning("Paper not found for notes generation", paper_id=paper_id)
            return None

        notes = await self.notes_generator.generate_notes(
            paper_metadata={
                "title": paper["title"],
                "authors": paper["authors"] or [],
                "year": paper["year"],
                "venue": paper["venue"],
            },
            imrad_structure=paper["imradJson"] or {},
        )

        return notes

    async def complete_task(self, task_id: str, paper_id: str, notes: str) -> None:
        """完成任务，更新 Paper 和 NotesTask。

        Args:
            task_id: NotesTask UUID
            paper_id: Paper UUID
            notes: Generated notes content
        """
        async with self.db_pool.acquire() as conn:
            # 更新 Paper
            await conn.execute(
                """UPDATE papers
                   SET reading_notes = $1,
                       "isNotesReady" = TRUE,
                       notes_version = notes_version + 1,
                       "updatedAt" = NOW()
                   WHERE id = $2""",
                notes,
                paper_id,
            )

            # 更新 NotesTask
            await conn.execute(
                """UPDATE notes_generation_tasks
                   SET status = 'completed',
                       completed_at = NOW()
                   WHERE id = $1""",
                task_id,
            )

        logger.info(
            "Notes task completed",
            task_id=task_id,
            paper_id=paper_id,
            notes_length=len(notes),
        )

    async def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败。

        Args:
            task_id: NotesTask UUID
            error: Error message
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE notes_generation_tasks
                   SET status = 'failed',
                       error_message = $1,
                       attempts = attempts + 1
                   WHERE id = $2""",
                error[:500],  # Truncate to 500 chars
                task_id,
            )

        logger.error("Notes task failed", task_id=task_id, error=error[:200])

    async def run_loop(self) -> None:
        """Worker 主循环。

        Continuously polls for pending tasks and processes them.
        """
        await self.init_db()
        logger.info("Notes worker started", worker_id=self.WORKER_ID)

        while True:
            try:
                task = await self.claim_task()

                if task:
                    logger.info("Claimed notes task", task_id=task["id"], paper_id=task["paper_id"])
                    try:
                        notes = await self.generate_notes(task["paper_id"])
                        if notes:
                            await self.complete_task(task["id"], task["paper_id"], notes)
                            logger.info("Notes generated successfully", task_id=task["id"])
                        else:
                            await self.fail_task(task["id"], "Paper not found")
                    except Exception as e:
                        await self.fail_task(task["id"], str(e))
                        logger.error(
                            "Notes generation failed",
                            task_id=task["id"],
                            error=str(e),
                        )
                else:
                    # No pending tasks, wait before polling again
                    await asyncio.sleep(self.POLL_INTERVAL)

            except Exception as e:
                logger.error("Notes worker loop error", error=str(e))
                await asyncio.sleep(self.POLL_INTERVAL)

    async def shutdown(self) -> None:
        """关闭数据库连接池。"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("Notes worker database pool closed")


async def main():
    """Worker entry point."""
    worker = NotesWorker()
    try:
        await worker.run_loop()
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())