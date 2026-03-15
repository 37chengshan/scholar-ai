"""
ScholarAI Python AI Service

基于FastAPI的AI服务，提供：
- PDF解析 (Docling)
- RAG问答 (PaperQA2)
- 实体抽取
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, parse, rag, entities, papers, internal
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_databases, close_databases
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    setup_logging()
    logger.info("🤖 ScholarAI AI Service starting...")
    logger.info(f"📚 Log level: {settings.LOG_LEVEL}")
    logger.info(f"🔗 Database: {settings.DATABASE_URL}")
    logger.info(f"🕸️  Neo4j: {settings.NEO4J_URI}")
    logger.info(f"⚡ Redis: {settings.REDIS_URL}")

    # 初始化数据库连接
    await init_databases()

    yield

    # 关闭
    logger.info("🛑 ScholarAI AI Service shutting down...")
    await close_databases()


app = FastAPI(
    title="ScholarAI AI Service",
    description="AI services for ScholarAI - PDF parsing, RAG Q&A, Entity extraction",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(papers.router, prefix="/papers", tags=["Papers"])
app.include_router(parse.router, prefix="/parse", tags=["PDF Parsing"])
app.include_router(rag.router, prefix="/rag", tags=["RAG Q&A"])
app.include_router(entities.router, prefix="/entities", tags=["Entity Extraction"])
app.include_router(internal.router, prefix="/internal", tags=["Internal API"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "ScholarAI AI Service",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }
