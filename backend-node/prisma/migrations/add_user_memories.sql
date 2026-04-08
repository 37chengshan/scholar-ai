-- Migration: Add user_memories table for long-term memory storage
-- Per D-12: Long-term memory stores user preferences, patterns, and feedback
-- Note: Embeddings stored in Milvus (not PostgreSQL) per Phase 13 migration

CREATE TABLE IF NOT EXISTS user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    memory_type VARCHAR(50) NOT NULL,  -- 'preference', 'pattern', 'feedback'
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for fast user lookup
CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories(user_id);

-- Create index for memory type filtering
CREATE INDEX IF NOT EXISTS idx_user_memories_type ON user_memories(memory_type);

-- Create index for created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_user_memories_created_at ON user_memories(created_at DESC);