"""应用配置"""

from typing import List
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 基础配置
    APP_NAME: str = "ScholarAI AI Service"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"

    # PostgreSQL 数据库
    DATABASE_URL: str = "postgresql://scholarai:scholarai123@localhost:5432/scholarai"

    # Redis 缓存
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # Neo4j 图数据库
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "scholarai123"

    # API密钥
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]

    # 文件上传
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "/app/papers"

    # RAG配置
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 10

    # LLM配置
    DEFAULT_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # JWT内部服务通信 (RS256公钥用于验证Node.js Gateway发来的token)
    JWT_INTERNAL_PUBLIC_KEY: str = ""

    class Config:
        env_file = ".env.local"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
