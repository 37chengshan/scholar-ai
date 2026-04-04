-- Add Semantic Scholar integration columns to papers table
-- Per D-07, D-08, D-09: Metadata enrichment integration

-- Add s2_paper_id column (unique for deduplication)
ALTER TABLE papers ADD COLUMN IF NOT EXISTS s2_paper_id VARCHAR(255) UNIQUE;

-- Add citation_count for impact analysis
ALTER TABLE papers ADD COLUMN IF NOT EXISTS citation_count INTEGER DEFAULT 0;

-- Add venue for publication source tracking
ALTER TABLE papers ADD COLUMN IF NOT EXISTS venue VARCHAR(255);

-- Create index for fast S2 paper lookups
CREATE INDEX IF NOT EXISTS idx_papers_s2_paper_id ON papers(s2_paper_id);

-- Create index for citation-based sorting
CREATE INDEX IF NOT EXISTS idx_papers_citation_count ON papers(citation_count DESC);

-- Comment on columns
COMMENT ON COLUMN papers.s2_paper_id IS 'Semantic Scholar paper ID for metadata enrichment';
COMMENT ON COLUMN papers.citation_count IS 'Number of citations from Semantic Scholar';
COMMENT ON COLUMN papers.venue IS 'Publication venue (journal/conference name)';