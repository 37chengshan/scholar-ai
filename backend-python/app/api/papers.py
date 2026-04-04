"""论文数据 API

展示如何使用数据库连接:
- PostgreSQL: 论文元数据存储
- Neo4j: 论文引用关系图谱
- Redis: 热门论文缓存
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.core.database import postgres_db, neo4j_db, redis_db
from app.utils.logger import logger
from app.utils.problem_detail import Errors

router = APIRouter()


# =============================================================================
# 数据模型
# =============================================================================

class PaperCreate(BaseModel):
    """创建论文请求"""
    id: str
    title: str
    authors: List[str]
    year: Optional[int] = None
    doi: Optional[str] = None


class PaperResponse(BaseModel):
    """论文响应"""
    id: str
    title: str
    authors: List[str]
    year: Optional[int]
    doi: Optional[str]
    citations: Optional[List[dict]] = None


class CitationCreate(BaseModel):
    """创建引用关系"""
    from_paper: str
    to_paper: str


# =============================================================================
# API 路由
# =============================================================================

@router.post("/", response_model=PaperResponse)
async def create_paper(paper: PaperCreate):
    """
    创建论文 (写入 PostgreSQL + Neo4j)

    示例:
        POST /papers/
        {
            "id": "paper_001",
            "title": "Attention Is All You Need",
            "authors": ["Vaswani et al."],
            "year": 2017,
            "doi": "10.5555/3295222.3295349"
        }
    """
    try:
        # 1. 写入 PostgreSQL (元数据)
        await postgres_db.execute(
            """
            INSERT INTO papers (id, title, authors, year, doi, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                authors = EXCLUDED.authors,
                year = EXCLUDED.year,
                doi = EXCLUDED.doi
            """,
            paper.id,
            paper.title,
            paper.authors,
            paper.year,
            paper.doi
        )

        # 2. 写入 Neo4j (图节点)
        await neo4j_db.create_paper_node(
            paper_id=paper.id,
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            doi=paper.doi
        )

        # 3. 写入作者节点
        for author in paper.authors:
            await neo4j_db.create_author_node(author)

        logger.info(f"✅ 论文创建成功: {paper.id}")

        return PaperResponse(**paper.model_dump())

    except Exception as e:
        logger.error(f"❌ 创建论文失败: {e}")
        raise HTTPException(status_code=500, detail=Errors.internal(str(e)))


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: str):
    """
    获取论文详情 (PostgreSQL + Neo4j 引用数据)

    示例:
        GET /papers/paper_001
    """
    try:
        # 1. 从 PostgreSQL 获取元数据
        row = await postgres_db.fetchrow(
            "SELECT * FROM papers WHERE id = $1",
            paper_id
        )

        if not row:
            raise HTTPException(status_code=404, detail=Errors.not_found("论文不存在"))

        # 2. 从 Neo4j 获取引用关系
        citations = await neo4j_db.get_paper_citations(paper_id)

        return PaperResponse(
            id=row['id'],
            title=row['title'],
            authors=row['authors'],
            year=row['year'],
            doi=row['doi'],
            citations=citations
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取论文失败: {e}")
        raise HTTPException(status_code=500, detail=Errors.internal(str(e)))


@router.get("/hot", response_model=List[PaperResponse])
async def get_hot_papers():
    """
    获取热门论文 (Redis 缓存 + PostgreSQL)

    示例:
        GET /papers/hot
    """
    try:
        # 1. 检查 Redis 缓存
        cached = await redis_db.get("papers:hot")
        if cached:
            logger.info("📦 从缓存获取热门论文")
            # 这里简化处理，实际应该反序列化
            return []

        # 2. 从 PostgreSQL 查询 (按引用数排序)
        rows = await postgres_db.fetch(
            """
            SELECT p.*, COUNT(c.id) as citation_count
            FROM papers p
            LEFT JOIN citations c ON p.id = c.to_paper
            GROUP BY p.id
            ORDER BY citation_count DESC
            LIMIT 10
            """
        )

        papers = [PaperResponse(
            id=row['id'],
            title=row['title'],
            authors=row['authors'],
            year=row['year'],
            doi=row['doi']
        ) for row in rows]

        # 3. 写入 Redis 缓存 (10分钟)
        # await redis_db.set("papers:hot", serialize(papers), expire=600)

        return papers

    except Exception as e:
        logger.error(f"❌ 获取热门论文失败: {e}")
        raise HTTPException(status_code=500, detail=Errors.internal(str(e)))


@router.post("/citations")
async def create_citation(citation: CitationCreate):
    """
    创建论文引用关系 (Neo4j 关系 + PostgreSQL 记录)

    示例:
        POST /papers/citations
        {
            "from_paper": "paper_001",
            "to_paper": "paper_002"
        }
    """
    try:
        # 1. 写入 PostgreSQL (引用记录)
        await postgres_db.execute(
            """
            INSERT INTO citations (from_paper, to_paper, created_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (from_paper, to_paper) DO NOTHING
            """,
            citation.from_paper,
            citation.to_paper
        )

        # 2. 写入 Neo4j (图关系)
        await neo4j_db.create_citation_relation(
            from_paper=citation.from_paper,
            to_paper=citation.to_paper
        )

        # 3. 清除热门论文缓存 (数据已变更)
        await redis_db.delete("papers:hot")

        logger.info(f"✅ 引用关系创建成功: {citation.from_paper} -> {citation.to_paper}")

        return {"message": "引用关系创建成功"}

    except Exception as e:
        logger.error(f"❌ 创建引用关系失败: {e}")
        raise HTTPException(status_code=500, detail=Errors.internal(str(e)))


@router.get("/{paper_id}/related")
async def get_related_papers(paper_id: str):
    """
    获取相关论文 (Neo4j 图遍历)

    基于引用关系推荐相关论文:
    - 引用的论文
    - 被引用的论文
    - 共同引用的论文

    示例:
        GET /papers/paper_001/related
    """
    try:
        # Cypher 查询: 查找引用关系网络
        query = """
        MATCH (p:Paper {id: $paper_id})
        OPTIONAL MATCH (p)-[:CITES]->(cited:Paper)
        OPTIONAL MATCH (citing:Paper)-[:CITES]->(p)
        OPTIONAL MATCH (p)-[:CITES]->(:Paper)<-[:CITES]-(related:Paper)
        WHERE related.id <> p.id
        RETURN DISTINCT related.id as id, related.title as title,
               count(*) as common_citations
        ORDER BY common_citations DESC
        LIMIT 10
        """

        result = await neo4j_db.run(query, {"paper_id": paper_id})

        return {
            "paper_id": paper_id,
            "related_papers": [
                {
                    "id": r['id'],
                    "title": r['title'],
                    "common_citations": r['common_citations']
                }
                for r in result if r.get('id')
            ]
        }

    except Exception as e:
        logger.error(f"❌ 获取相关论文失败: {e}")
        raise HTTPException(status_code=500, detail=Errors.internal(str(e)))
