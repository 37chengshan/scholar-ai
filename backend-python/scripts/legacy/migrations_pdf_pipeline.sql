-- PDF 解析流程工程化迭代迁移脚本
-- 执行顺序: 001 → 002 → 003 → 004
-- 生成时间: 2026-04-13

-- ============================================================================
-- Migration 001: Knowledge Bases (已存在，跳过)
-- ============================================================================

-- ============================================================================
-- Migration 002: ProcessingTask checkpoint and trace fields
-- Per Review Fix #3: checkpoint只存路径引用，不存大JSON
-- Per Review Fix #4: Boolean使用PostgreSQL原生Boolean
-- Per Review Fix #8: trace_id贯穿日志
-- ============================================================================

-- Checkpoint路径引用
ALTER TABLE processing_tasks
ADD COLUMN IF NOT EXISTS checkpoint_stage VARCHAR(50),
ADD COLUMN IF NOT EXISTS checkpoint_storage_key VARCHAR(255),
ADD COLUMN IF NOT EXISTS checkpoint_version INTEGER DEFAULT 0;

-- 阶段耗时（JSON）
ALTER TABLE processing_tasks
ADD COLUMN IF NOT EXISTS stage_timings JSONB;

-- 失败分类（统一 vocabulary: download/parse/extract/store）
ALTER TABLE processing_tasks
ADD COLUMN IF NOT EXISTS failure_stage VARCHAR(20),
ADD COLUMN IF NOT EXISTS failure_code VARCHAR(100),
ADD COLUMN IF NOT EXISTS failure_message TEXT;

-- 重试标记（PostgreSQL Boolean）
ALTER TABLE processing_tasks
ADD COLUMN IF NOT EXISTS is_retryable BOOLEAN DEFAULT TRUE;

-- trace_id
ALTER TABLE processing_tasks
ADD COLUMN IF NOT EXISTS trace_id VARCHAR(36);

-- 索引
CREATE INDEX IF NOT EXISTS idx_processing_tasks_trace_id ON processing_tasks(trace_id);

-- ============================================================================
-- Migration 003: Paper substatus fields
-- Per Section 2: 子状态语义
-- Per Review Fix #4: Boolean使用PostgreSQL原生Boolean
-- ============================================================================

-- 子状态（PostgreSQL Boolean）
-- isSearchReady: PostgreSQL + Milvus text chunks 成功
-- isMultimodalReady: Milvus images/tables 成功
-- isNotesReady: reading_notes 字段有内容
ALTER TABLE papers
ADD COLUMN IF NOT EXISTS "isSearchReady" BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS "isMultimodalReady" BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS "isNotesReady" BOOLEAN DEFAULT FALSE;

-- 失败标记
ALTER TABLE papers
ADD COLUMN IF NOT EXISTS "notesFailed" BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS "multimodalFailed" BOOLEAN DEFAULT FALSE;

-- trace_id（继承自 task）
ALTER TABLE papers
ADD COLUMN IF NOT EXISTS "traceId" VARCHAR(36);

-- 索引
CREATE INDEX IF NOT EXISTS idx_papers_trace_id ON papers("traceId");
CREATE INDEX IF NOT EXISTS idx_papers_search_ready ON papers("isSearchReady");
CREATE INDEX IF NOT EXISTS idx_papers_notes_ready ON papers("isNotesReady");

-- ============================================================================
-- Migration 004: Notes generation tasks table
-- Per Review Fix #9: Notes异步化 + 抢占锁
-- ============================================================================

CREATE TABLE IF NOT EXISTS notes_generation_tasks (
    id VARCHAR(36) PRIMARY KEY,
    paper_id VARCHAR(36) NOT NULL UNIQUE REFERENCES papers(id),
    status VARCHAR(20) DEFAULT 'pending',
    claimed_by VARCHAR(50),
    claimed_at TIMESTAMP WITH TIME ZONE,
    error_message VARCHAR(500),
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_notes_tasks_status ON notes_generation_tasks(status);
CREATE INDEX IF NOT EXISTS idx_notes_tasks_paper_id ON notes_generation_tasks(paper_id);

-- ============================================================================
-- 验证迁移完成
-- ============================================================================

-- 检查 processing_tasks 新字段
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'processing_tasks'
AND column_name IN ('checkpoint_stage', 'checkpoint_storage_key', 'trace_id', 'is_retryable', 'stage_timings');

-- 检查 papers 新字段
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'papers'
AND column_name IN ('isSearchReady', 'isNotesReady', 'traceId', 'notesFailed');

-- 检查 notes_generation_tasks 表
SELECT table_name FROM information_schema.tables WHERE table_name = 'notes_generation_tasks';