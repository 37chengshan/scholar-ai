-- Add indexes for common query patterns (per D-10)
-- Using CONCURRENTLY to avoid table locks

CREATE INDEX CONCURRENTLY IF NOT EXISTS papers_status_idx
ON papers(status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS papers_user_status_idx
ON papers("user_id", status);

-- Note: Run this migration during low-traffic period to minimize impact
-- CONCURRENTLY allows reads/writes to continue during index creation
-- Expected duration: ~1-2 minutes for 1000 papers, scales linearly