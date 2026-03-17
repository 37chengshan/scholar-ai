-- Migration: Add tsvector search column to paper_chunks table
-- For hybrid search combining dense (PGVector) + sparse (tsvector) + RRF fusion
--
-- Date: 2026-03-16
-- Phase: 03-03 Hybrid Search
-- Requirements: SEARCH-01, SEARCH-04

-- =============================================================================
-- Step 1: Add search_vector column for tsvector
-- =============================================================================

ALTER TABLE paper_chunks
ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- =============================================================================
-- Step 2: Create GIN index for fast full-text search
-- =============================================================================

-- Drop existing index if recreating
DROP INDEX IF EXISTS idx_paper_chunks_search_vector;

-- Create GIN index for tsvector (optimized for search)
CREATE INDEX idx_paper_chunks_search_vector
ON paper_chunks
USING GIN (search_vector);

-- =============================================================================
-- Step 3: Create function to automatically update search_vector
-- =============================================================================

-- Drop existing function if recreating
DROP FUNCTION IF EXISTS update_paper_chunks_search_vector();

-- Create trigger function for automatic tsvector updates
CREATE OR REPLACE FUNCTION update_paper_chunks_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    -- Generate tsvector from content using english configuration
    -- Can be changed to 'simple' or 'chinese' if needed
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Step 4: Create trigger to auto-update on insert/update
-- =============================================================================

-- Drop existing trigger if recreating
DROP TRIGGER IF EXISTS trigger_update_paper_chunks_search_vector ON paper_chunks;

-- Create trigger for automatic updates
CREATE TRIGGER trigger_update_paper_chunks_search_vector
    BEFORE INSERT OR UPDATE OF content ON paper_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_paper_chunks_search_vector();

-- =============================================================================
-- Step 5: Backfill existing rows
-- =============================================================================

-- Update existing rows with search_vector
UPDATE paper_chunks
SET search_vector = to_tsvector('english', COALESCE(content, ''))
WHERE search_vector IS NULL OR search_vector = ''::tsvector;

-- =============================================================================
-- Step 6: Create index on paper_id for filtering (if not exists)
-- =============================================================================

-- This index already exists per Prisma schema but ensure it's there
CREATE INDEX IF NOT EXISTS idx_paper_chunks_paper_id
ON paper_chunks (paper_id);

-- =============================================================================
-- Verification Queries
-- =============================================================================

-- Check if column was added
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name = 'paper_chunks' AND column_name = 'search_vector';

-- Check if index was created
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'paper_chunks' AND indexname = 'idx_paper_chunks_search_vector';

-- Test tsvector search
-- SELECT id, content, ts_rank_cd(search_vector, query) as rank
-- FROM paper_chunks, to_tsquery('english', 'neural & network') query
-- WHERE search_vector @@ query
-- ORDER BY rank DESC
-- LIMIT 5;

-- =============================================================================
-- Rollback Instructions (if needed)
-- =============================================================================

-- To rollback this migration:
--
-- DROP TRIGGER IF EXISTS trigger_update_paper_chunks_search_vector ON paper_chunks;
-- DROP FUNCTION IF EXISTS update_paper_chunks_search_vector();
-- DROP INDEX IF EXISTS idx_paper_chunks_search_vector;
-- ALTER TABLE paper_chunks DROP COLUMN IF EXISTS search_vector;
