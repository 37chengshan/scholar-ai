"""数据库连接模块

提供 Neo4j 和 Redis 的数据库连接管理。
PostgreSQL 已迁移到 app/database.py (SQLAlchemy ORM)。

Per Task 2: NEO4J_DISABLED 显式禁用逻辑
- NEO4J_DISABLED=true: 主动跳过连接，打印 info 日志
- NEO4J_DISABLED=false: 尝试连接，失败时 warn 不阻塞
- Redis 连接失败必须 raise（必需服务）
"""

import os
from neo4j import AsyncGraphDatabase
import redis.asyncio as redis
from typing import Optional

from app.config import settings
from app.utils.logger import logger


def _is_neo4j_disabled() -> bool:
    """Check if Neo4j is explicitly disabled via environment variable.

    Returns:
        True if NEO4J_DISABLED=true, False otherwise.
    """
    return os.getenv("NEO4J_DISABLED", "false").lower() == "true"


# =============================================================================
# Neo4j 驱动
# =============================================================================

class Neo4jDB:
    """Neo4j 图数据库连接管理"""

    def __init__(self):
        self.driver = None

    async def connect(self):
        """初始化驱动"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            await self.driver.verify_connectivity()
            logger.info("✅ Neo4j 连接成功")
        except Exception as e:
            logger.error(f"❌ Neo4j 连接失败: {e}")
            raise

    async def disconnect(self):
        """关闭驱动"""
        if self.driver:
            await self.driver.close()
            logger.info("🔌 Neo4j 连接已关闭")

    async def run(self, query: str, parameters: dict = None):
        """执行 Cypher 查询"""
        if not self.driver:
            raise RuntimeError("Neo4j 未连接")
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            return await result.data()

    async def create_paper_node(self, paper_id: str, title: str, authors: list,
                                year: int = None, doi: str = None):
        """创建论文节点"""
        query = """
        MERGE (p:Paper {id: $paper_id})
        SET p.title = $title,
            p.authors = $authors,
            p.year = $year,
            p.doi = $doi,
            p.created_at = datetime()
        RETURN p
        """
        return await self.run(query, {
            "paper_id": paper_id,
            "title": title,
            "authors": authors,
            "year": year,
            "doi": doi
        })

    async def create_author_node(self, author_name: str):
        """创建作者节点"""
        query = """
        MERGE (a:Author {name: $name})
        RETURN a
        """
        return await self.run(query, {"name": author_name})

    async def create_citation_relation(self, from_paper: str, to_paper: str):
        """创建引用关系"""
        query = """
        MATCH (from:Paper {id: $from_paper})
        MATCH (to:Paper {id: $to_paper})
        MERGE (from)-[:CITES]->(to)
        """
        return await self.run(query, {
            "from_paper": from_paper,
            "to_paper": to_paper
        })

    async def get_paper_citations(self, paper_id: str):
        """获取论文的引用关系"""
        query = """
        MATCH (p:Paper {id: $paper_id})-[:CITES]->(cited:Paper)
        RETURN cited.id as cited_paper_id, cited.title as title
        """
        return await self.run(query, {"paper_id": paper_id})


# 全局 Neo4j 实例
neo4j_db = Neo4jDB()


# =============================================================================
# Redis 客户端
# =============================================================================

class RedisDB:
    """Redis 缓存连接管理"""

    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """连接 Redis"""
        try:
            if settings.REDIS_PASSWORD:
                self.client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True
                )
            else:
                self.client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
            await self.client.ping()
            logger.info("✅ Redis 连接成功")
        except Exception as e:
            logger.error(f"❌ Redis 连接失败: {e}")
            raise

    async def disconnect(self):
        """关闭连接"""
        if self.client:
            await self.client.close()
            logger.info("🔌 Redis 连接已关闭")

    async def get(self, key: str):
        """获取缓存值"""
        if not self.client:
            return None
        return await self.client.get(key)

    async def set(self, key: str, value: str, expire: int = 3600):
        """设置缓存值"""
        if not self.client:
            return None
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str):
        """删除缓存"""
        if not self.client:
            return None
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.client:
            return False
        return await self.client.exists(key) > 0


# 全局 Redis 实例
redis_db = RedisDB()


# =============================================================================
# 依赖注入函数 (FastAPI 依赖)
# =============================================================================

async def get_neo4j() -> Neo4jDB:
    """获取 Neo4j 实例"""
    return neo4j_db


async def get_redis() -> RedisDB:
    """获取 Redis 实例"""
    return redis_db


# =============================================================================
# 生命周期管理
# =============================================================================

async def init_databases():
    """初始化 Neo4j 和 Redis 连接。

    PostgreSQL 已迁移到 app/database.py (SQLAlchemy)。

    Per Task 2: NEO4J_DISABLED 显式禁用逻辑
    - NEO4J_DISABLED=true: 主动跳过 Neo4j，打印 info 日志
    - NEO4J_DISABLED=false: 尝试连接 Neo4j，失败时 warn 不阻塞
    - Redis 连接失败必须 raise（必需服务）
    """
    logger.info("正在初始化 Neo4j 和 Redis 连接...")

    # Neo4j - 显式禁用检查
    if _is_neo4j_disabled():
        logger.info("NEO4J_DISABLED=true, 主动跳过 Neo4j 连接")
    else:
        # NEO4J_DISABLED=false 或未设置，尝试连接
        try:
            await neo4j_db.connect()
        except Exception as e:
            # 连接失败：warn 不阻塞（允许应用启动）
            logger.warning(f"Neo4j 连接失败 (NEO4J_DISABLED=false): {e}")

    # Redis - 必需服务，失败必须 raise
    await redis_db.connect()

    logger.info("Neo4j 和 Redis 连接初始化完成")


async def close_databases():
    """关闭 Neo4j 和 Redis 连接。

    Per Task 2: NEO4J_DISABLED 显式禁用逻辑
    - NEO4J_DISABLED=true: 跳过 Neo4j disconnect
    - NEO4J_DISABLED=false: 尝试 disconnect
    """
    logger.info("正在关闭 Neo4j 和 Redis 连接...")

    # Neo4j - 仅在未禁用时关闭
    if not _is_neo4j_disabled():
        await neo4j_db.disconnect()

    # Redis - 始终关闭
    await redis_db.disconnect()

    logger.info("Neo4j 和 Redis 连接已关闭")


