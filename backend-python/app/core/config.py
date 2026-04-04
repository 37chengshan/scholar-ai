"""应用配置"""

import os
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

    # Milvus 向量数据库
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_IMAGES: str = "paper_images"
    MILVUS_COLLECTION_TABLES: str = "paper_tables"
    MILVUS_COLLECTION_CONTENTS: str = "paper_contents"  # Unified 1024-dim BGE-M3 collection
    MILVUS_COLLECTION_CONTENTS_V2: str = "paper_contents_v2"  # Unified 2048-dim Qwen3-VL collection
    MILVUS_POOL_SIZE: int = 10
    MILVUS_TIMEOUT: int = 10

    # Zhipu AI API密钥
    ZHIPU_API_KEY: str = ""  # For all ZhipuAI models (GLM-4.5-Air, glm-4v, glm-4-flash)
    ZHIPU_MODEL_VISION: str = "glm-4v"  # For image caption generation
    ZHIPU_MODEL_TEXT: str = "glm-4-flash"  # For table description generation
    ZHIPU_MAX_TOKENS: int = 150
    ZHIPU_TEMPERATURE: float = 0.3

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
    
    # Embedding Model Configuration (Qwen3-VL)
    EMBEDDING_MODEL: str = "qwen3-vl-2b"  # Model identifier
    EMBEDDING_QUANTIZATION: str = "int4"  # Quantization type: "int4" or "fp16"
    EMBEDDING_DIMENSION: int = 2048  # Qwen3-VL output dimension
    
    # Legacy embedding config (to be removed after migration)
    # EMBEDDING_MODEL: str = "text-embedding-3-small"  # Old OpenAI embedding
    
    # GLM-4.5-Air Configuration (for Agent Runner)
    LLM_MODEL: str = "glm-4.5-air"  # ZhipuAI model name (no prefix)
    LLM_API_BASE: str = "https://open.bigmodel.cn/api/paas/v4"  # Zhipu AI API base
    LLM_MAX_TOKENS: int = 2048  # Maximum output tokens
    LLM_TEMPERATURE: float = 0.7  # Sampling temperature
    LLM_MAX_RETRIES: int = 5  # Max retries for rate limits

    # JWT内部服务通信 (RS256公钥用于验证Node.js Gateway发来的token)
    JWT_INTERNAL_PUBLIC_KEY: str = ""
    JWT_INTERNAL_PUBLIC_KEY_FILE: str = ""
    
    # JWT Authentication (HS256 for direct API access)
    JWT_SECRET: str = "test-secret-key-for-development-only"  # Should be overridden in .env
    JWT_ALGORITHM: str = "HS256"

    # Semantic Scholar API
    S2_API_KEY: str = ""  # Optional API key for higher rate limits
    S2_CACHE_TTL: int = 86400  # 24 hours for search
    S2_PAPER_TTL: int = 604800  # 7 days for paper details
    S2_CITATION_TTL: int = 2592000  # 30 days for citations

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 如果配置了公钥文件路径，从文件读取
        if self.JWT_INTERNAL_PUBLIC_KEY_FILE and os.path.exists(self.JWT_INTERNAL_PUBLIC_KEY_FILE):
            with open(self.JWT_INTERNAL_PUBLIC_KEY_FILE, 'r') as f:
                self.JWT_INTERNAL_PUBLIC_KEY = f.read()

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 忽略未定义的环境变量


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
