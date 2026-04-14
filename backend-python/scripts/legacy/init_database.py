"""
数据库初始化脚本

创建 PostgreSQL 和 Neo4j 的必要表结构

使用方法:
    cd backend-python
    python -m scripts.init_database
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import postgres_db, neo4j_db
from app.utils.logger import logger


# PostgreSQL 初始化 SQL
POSTGRES_SCHEMA = """
-- 论文表
CREATE TABLE IF NOT EXISTS papers (
    id VARCHAR(100) PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT[] NOT NULL DEFAULT '{}',
    abstract TEXT,
    year INTEGER,
    doi VARCHAR(255),
    pdf_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 引用关系表
CREATE TABLE IF NOT EXISTS citations (
    id SERIAL PRIMARY KEY,
    from_paper VARCHAR(100) NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    to_paper VARCHAR(100) NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_paper, to_paper)
);

-- 论文元数据表 (PaperQA2 解析结果)
CREATE TABLE IF NOT EXISTS paper_metadata (
    id SERIAL PRIMARY KEY,
    paper_id VARCHAR(100) NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunks JSONB,  -- 文本块
    entities JSONB,  -- 提取的实体
    summary TEXT,  -- 摘要
    key_findings TEXT[],  -- 关键发现
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(paper_id)
);

-- 向量索引表 (用于 pgvector)
CREATE TABLE IF NOT EXISTS paper_embeddings (
    id SERIAL PRIMARY KEY,
    paper_id VARCHAR(100) NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-small 维度
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(paper_id, chunk_index)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
CREATE INDEX IF NOT EXISTS idx_papers_authors ON papers USING GIN(authors);
CREATE INDEX IF NOT EXISTS idx_citations_from ON citations(from_paper);
CREATE INDEX IF NOT EXISTS idx_citations_to ON citations(to_paper);
CREATE INDEX IF NOT EXISTS idx_embeddings_paper ON paper_embeddings(paper_id);

-- 创建向量索引 (用于相似度搜索)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON paper_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- 更新触发器 (自动更新 updated_at)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_papers_updated_at ON papers;
CREATE TRIGGER update_papers_updated_at
    BEFORE UPDATE ON papers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""


# Neo4j 初始化 Cypher
NEO4J_SCHEMA = """
// 创建约束和索引
CREATE CONSTRAINT paper_id IF NOT EXISTS
FOR (p:Paper) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT author_name IF NOT EXISTS
FOR (a:Author) REQUIRE a.name IS UNIQUE;

CREATE INDEX paper_year IF NOT EXISTS
FOR (p:Paper) ON (p.year);

CREATE INDEX paper_doi IF NOT EXISTS
FOR (p:Paper) ON (p.doi);
"""


async def init_postgres():
    """初始化 PostgreSQL"""
    print("\n🐘 初始化 PostgreSQL...")

    try:
        await postgres_db.connect()

        # 启用 pgvector 扩展
        await postgres_db.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("   ✅ pgvector 扩展已启用")

        # 执行建表 SQL
        await postgres_db.execute(POSTGRES_SCHEMA)
        print("   ✅ 表结构创建成功")

        # 验证表创建
        tables = await postgres_db.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        table_names = [t['tablename'] for t in tables]
        print(f"   📊 现有表: {', '.join(table_names)}")

        return True

    except Exception as e:
        print(f"   ❌ PostgreSQL 初始化失败: {e}")
        return False


async def init_neo4j():
    """初始化 Neo4j"""
    print("\n🕸️  初始化 Neo4j...")

    try:
        await neo4j_db.connect()

        # 执行初始化 Cypher
        for statement in NEO4J_SCHEMA.strip().split(';'):
            stmt = statement.strip()
            if stmt:
                await neo4j_db.run(stmt)

        print("   ✅ 约束和索引创建成功")

        # 验证
        result = await neo4j_db.run(
            "SHOW CONSTRAINTS YIELD name, type RETURN count(*) as count"
        )
        constraint_count = result[0]['count'] if result else 0
        print(f"   📊 约束数量: {constraint_count}")

        return True

    except Exception as e:
        print(f"   ❌ Neo4j 初始化失败: {e}")
        return False


async def main():
    """主函数"""
    print("=" * 60)
    print("🗄️  ScholarAI 数据库初始化")
    print("=" * 60)

    results = {}

    try:
        # 初始化 PostgreSQL
        results['postgresql'] = await init_postgres()

        # 初始化 Neo4j
        results['neo4j'] = await init_neo4j()

    finally:
        # 关闭连接
        print("\n🔌 关闭连接...")
        await postgres_db.disconnect()
        await neo4j_db.disconnect()

    # 打印结果
    print("\n" + "=" * 60)
    print("📊 初始化结果")
    print("=" * 60)

    for service, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"   {service.upper():12} {status}")

    if all(results.values()):
        print("\n🎉 数据库初始化完成!")
        print("\n💡 现在你可以:")
        print("   1. 测试连接: python -m scripts.test_db_connection")
        print("   2. 启动服务: uvicorn app.main:app --reload --port 8000")
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
