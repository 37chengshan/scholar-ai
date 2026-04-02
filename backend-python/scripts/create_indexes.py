"""Create vector and full-text indexes for paper_chunks table.

This script creates database indexes for efficient similarity search and
full-text search on the paper_chunks table.

When to run:
- Run AFTER data exists in paper_chunks table (not on empty tables)
- IVF_FLAT index needs data to train k-means clustering centroids
- For fresh databases, run after uploading first batch of papers

Index parameters:
- IVF_FLAT lists=100: Good for ~10k chunks
- Adjust lists = rows/1000 for larger datasets
- GIN index: Standard PostgreSQL full-text search

Usage:
    cd backend-python
    python scripts/create_indexes.py

Environment:
    DATABASE_URL must be set (defaults to localhost PostgreSQL)
"""

import asyncio
import asyncpg
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.utils.logger import logger


async def check_pgvector_extension(conn: asyncpg.Connection) -> bool:
    """Check if pgvector extension is installed."""
    try:
        result = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        return result
    except Exception as e:
        logger.error("Failed to check pgvector extension", error=str(e))
        return False


async def ensure_pgvector_extension(conn: asyncpg.Connection) -> bool:
    """Ensure pgvector extension is installed."""
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("pgvector extension ensured")
        return True
    except Exception as e:
        logger.error("Failed to create pgvector extension", error=str(e))
        return False


async def get_existing_indexes(conn: asyncpg.Connection, table_name: str) -> set:
    """Get set of existing index names for a table."""
    try:
        rows = await conn.fetch(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename = $1
            """,
            table_name
        )
        return {r['indexname'] for r in rows}
    except Exception as e:
        logger.error("Failed to get existing indexes", error=str(e))
        return set()


async def create_ivfflat_index(conn: asyncpg.Connection) -> bool:
    """Create IVF_FLAT index for vector similarity search.
    
    Returns:
        True if created or already exists, False on error
    """
    index_name = "idx_paper_chunks_embedding_cosine"
    
    try:
        existing = await get_existing_indexes(conn, "paper_chunks")
        
        if index_name in existing:
            logger.info("IVF_FLAT index already exists", index=index_name)
            return True
        
        logger.info("Creating IVF_FLAT index for vector similarity search...")
        
        # Check if table has data (IVF_FLAT needs data for k-means training)
        count = await conn.fetchval("SELECT COUNT(*) FROM paper_chunks")
        
        if count == 0:
            logger.warning(
                "paper_chunks table is empty - IVF_FLAT index needs data for training",
                recommendation="Run this script after adding paper chunks"
            )
            return False
        
        # Calculate optimal lists parameter (rows/1000, capped at reasonable range)
        lists = max(10, min(1000, count // 1000))
        logger.info(f"Using lists={lists} for {count} rows")
        
        # Create index CONCURRENTLY to avoid blocking
        await conn.execute(
            f"""
            CREATE INDEX CONCURRENTLY {index_name}
            ON paper_chunks
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = {lists})
            """
        )
        
        logger.info("IVF_FLAT index created successfully", index=index_name, lists=lists)
        return True
        
    except Exception as e:
        logger.error("Failed to create IVF_FLAT index", error=str(e))
        return False


async def create_gin_index(conn: asyncpg.Connection) -> bool:
    """Create GIN index for full-text search.
    
    Returns:
        True if created or already exists, False on error
    """
    index_name = "idx_paper_chunks_content_fts"
    
    try:
        existing = await get_existing_indexes(conn, "paper_chunks")
        
        if index_name in existing:
            logger.info("GIN full-text index already exists", index=index_name)
            return True
        
        logger.info("Creating GIN index for full-text search...")
        
        # Create index CONCURRENTLY to avoid blocking
        await conn.execute(
            f"""
            CREATE INDEX CONCURRENTLY {index_name}
            ON paper_chunks
            USING gin(to_tsvector('english', content))
            """
        )
        
        logger.info("GIN full-text index created successfully", index=index_name)
        return True
        
    except Exception as e:
        logger.error("Failed to create GIN index", error=str(e))
        return False


async def analyze_table(conn: asyncpg.Connection) -> bool:
    """Run ANALYZE to update query planner statistics."""
    try:
        logger.info("Running ANALYZE on paper_chunks table...")
        await conn.execute("ANALYZE paper_chunks")
        logger.info("Table statistics updated")
        return True
    except Exception as e:
        logger.error("Failed to analyze table", error=str(e))
        return False


async def create_indexes():
    """Create vector and full-text indexes for paper_chunks table.
    
    This is the main entry point for index creation.
    """
    logger.info("Starting index creation process...")
    
    # Connect to database
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        logger.info("Connected to PostgreSQL database")
    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        return False
    
    try:
        # Ensure pgvector extension
        if not await check_pgvector_extension(conn):
            logger.info("pgvector extension not found, attempting to install...")
            if not await ensure_pgvector_extension(conn):
                logger.error("pgvector extension required but not available")
                return False
        
        # Create indexes
        ivfflat_success = await create_ivfflat_index(conn)
        gin_success = await create_gin_index(conn)
        
        # Analyze table
        analyze_success = await analyze_table(conn)
        
        # Summary
        if ivfflat_success and gin_success and analyze_success:
            logger.info("✅ All indexes created successfully")
            return True
        else:
            logger.warning(
                "⚠️ Index creation completed with some failures",
                ivfflat=ivfflat_success,
                gin=gin_success,
                analyze=analyze_success
            )
            return False
            
    finally:
        await conn.close()
        logger.info("Database connection closed")


async def show_index_info():
    """Display information about existing indexes."""
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        # Get indexes
        indexes = await conn.fetch(
            """
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'paper_chunks'
            ORDER BY indexname
            """
        )
        
        print("\n=== Existing indexes on paper_chunks ===")
        for idx in indexes:
            print(f"\nIndex: {idx['indexname']}")
            print(f"Definition: {idx['indexdef']}")
            
            # Get size
            size = await conn.fetchval(
                f"SELECT pg_size_pretty(pg_relation_size('{idx['indexname']}'))"
            )
            print(f"Size: {size}")
        
        # Get row count
        count = await conn.fetchval("SELECT COUNT(*) FROM paper_chunks")
        print(f"\nTotal rows: {count}")
        
        await conn.close()
        
    except Exception as e:
        logger.error("Failed to show index info", error=str(e))


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create database indexes")
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show existing index information without creating new indexes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check what indexes exist without creating new ones"
    )
    
    args = parser.parse_args()
    
    if args.info:
        asyncio.run(show_index_info())
    elif args.dry_run:
        asyncio.run(check_indexes())
    else:
        success = asyncio.run(create_indexes())
        sys.exit(0 if success else 1)


async def check_indexes():
    """Check existing indexes without creating new ones."""
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        existing = await get_existing_indexes(conn, "paper_chunks")
        
        print("\n=== Index check ===")
        
        ivfflat_name = "idx_paper_chunks_embedding_cosine"
        gin_name = "idx_paper_chunks_content_fts"
        
        if ivfflat_name in existing:
            print(f"✅ IVF_FLAT index exists: {ivfflat_name}")
        else:
            print(f"❌ IVF_FLAT index missing: {ivfflat_name}")
        
        if gin_name in existing:
            print(f"✅ GIN index exists: {gin_name}")
        else:
            print(f"❌ GIN index missing: {gin_name}")
        
        count = await conn.fetchval("SELECT COUNT(*) FROM paper_chunks")
        print(f"\nRows in paper_chunks: {count}")
        
        await conn.close()
        
    except Exception as e:
        logger.error("Failed to check indexes", error=str(e))


if __name__ == "__main__":
    main()