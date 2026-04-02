-- Migration: Fix vector dimension and create indexes
-- Date: 2026-04-02
-- Purpose: Correct vector dimension from 1536 to 768 and create
--          IVF_FLAT index for vector similarity search and
--          GIN index for full-text search.

-- =============================================================================
-- Vector Dimension Fix
-- =============================================================================
-- Note: This migration handles the vector dimension mismatch.
-- The Prisma schema has been updated to vector(768).
-- For existing data, embeddings need to be re-generated with the correct model.
-- For fresh databases, the schema change handles this automatically.

-- =============================================================================
-- IVF_FLAT Index for Vector Similarity Search
-- =============================================================================
-- IVF_FLAT (Inverted File Flat) index for approximate nearest neighbor search.
-- This is optimized for cosine similarity search on vector embeddings.
-- Parameters:
--   - lists = 100: Number of clusters for k-means partitioning
--   - Good for ~10k chunks; adjust based on data size (rows/1000)
-- Requires: pgvector extension must be installed

-- Create index CONCURRENTLY to avoid blocking writes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_paper_chunks_embedding_cosine
ON paper_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- =============================================================================
-- GIN Index for Full-Text Search
-- =============================================================================
-- GIN (Generalized Inverted Index) for full-text search on English content.
-- Uses PostgreSQL's built-in text search functionality (tsvector).
-- Optimized for searching text content in chunks.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_paper_chunks_content_fts
ON paper_chunks
USING gin(to_tsvector('english', content));

-- =============================================================================
-- Query Optimization Settings
-- =============================================================================
-- For better recall with IVF_FLAT, increase probes setting at session level.
-- Default is 1 probe, which may miss relevant results.
-- Recommended: SET ivfflat.probes = 10; (execute before queries)

-- Example query with optimized probes:
-- SET ivfflat.probes = 10;
-- SELECT * FROM paper_chunks
-- ORDER BY embedding <=> '[...]'::vector
-- LIMIT 10;

-- =============================================================================
-- Table Analysis
-- =============================================================================
-- Update statistics for query planner optimization

ANALYZE paper_chunks;

-- =============================================================================
-- Verification Queries
-- =============================================================================
-- Check indexes were created successfully:
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'paper_chunks';

-- Check index sizes:
-- SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size
-- FROM pg_indexes WHERE tablename = 'paper_chunks';