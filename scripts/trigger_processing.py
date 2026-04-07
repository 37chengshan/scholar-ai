"""Trigger processing for existing pending papers.

This script creates processing_tasks for papers that have been uploaded
but not yet processed.
"""

import asyncio
import asyncpg
from uuid import uuid4
from datetime import datetime

DATABASE_URL = "postgresql://scholarai:scholarai123@localhost:5432/scholarai"


async def trigger_processing():
    """Create processing tasks for pending papers."""
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Find papers that are pending and have storage_key but no processing_task
        papers = await conn.fetch(
            """
            SELECT p.id, p."userId", p.storage_key, p.title
            FROM papers p
            LEFT JOIN processing_tasks pt ON p.id = pt.paper_id
            WHERE p.status = 'pending'
              AND p.storage_key IS NOT NULL
              AND pt.id IS NULL
            ORDER BY p."createdAt" ASC
            """
        )

        print(f"Found {len(papers)} papers to process")

        for paper in papers:
            paper_id = paper["id"]
            storage_key = paper["storage_key"]
            title = paper["title"]

            print(f"Creating processing task for: {title} ({paper_id})")

            # Create processing_task
            task_id = str(uuid4())
            await conn.execute(
                """
                INSERT INTO processing_tasks (id, paper_id, status, storage_key, updated_at)
                VALUES ($1, $2, 'pending', $3, $4)
                """,
                task_id,
                paper_id,
                storage_key,
                datetime.now(),
            )

            # Update paper status
            await conn.execute(
                """
                UPDATE papers
                SET status = 'processing',
                    "updatedAt" = $1
                WHERE id = $2
                """,
                datetime.now(),
                paper_id,
            )

            print(f"✓ Created task {task_id}")

        print(f"\n✓ Created {len(papers)} processing tasks")
        print("PDF Worker will now process these papers automatically")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(trigger_processing())