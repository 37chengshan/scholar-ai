-- Remove embedding columns from papers and paper_chunks tables
-- Per D-31-D-33: Milvus becomes sole vector storage

-- Drop embedding column from papers table (nullable vector)
ALTER TABLE "papers" DROP COLUMN IF EXISTS "embedding";

-- Drop embedding column from paper_chunks table (required vector)
ALTER TABLE "paper_chunks" DROP COLUMN IF EXISTS "embedding";