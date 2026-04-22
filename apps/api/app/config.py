"""Unified Pydantic Settings configuration for ScholarAI.

Merges environment variables from both Node.js and Python backends.
Per D-07: Type-safe configuration with automatic env loading.

Usage:
    from app.config import settings, get_settings

    # Access settings
    db_url = settings.DATABASE_URL
    async_url = settings.async_database_url
"""

import os
from typing import Dict, Literal
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


API_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Unified configuration merging Node.js + Python settings.

    Application:
        APP_NAME, DEBUG, LOG_LEVEL, PORT

    Database:
        DATABASE_URL (postgresql://user:pass@host/db)

    Redis:
        REDIS_URL

    Neo4j:
        NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

    JWT/Auth:
        JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

    CORS:
        ALLOWED_HOSTS

    File Upload:
        MAX_FILE_SIZE, UPLOAD_DIR

    S3 Storage:
        S3_ENDPOINT, S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, USE_LOCAL_STORAGE

    AI Service:
        ZHIPU_API_KEY, EMBEDDING_MODEL
    """

    model_config = SettingsConfigDict(
        # Use absolute env file path so runtime cwd does not affect config loading.
        env_file=(str(API_ROOT / ".env"), ".env"),
        case_sensitive=True,
        extra="ignore",
    )

    # =========================================================================
    # Application Configuration
    # =========================================================================
    APP_NAME: str = "ScholarAI API"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    PORT: int = 8000
    ENVIRONMENT: str = "development"  # development | staging | production
    RUNTIME_PROFILE: Optional[str] = None  # dev-lite | dev-full | prod
    AI_STARTUP_MODE: Optional[str] = None  # eager | lazy | off
    PREFLIGHT_ON_STARTUP: bool = False
    REQUIRED_PYTHON_MAJOR: int = 3
    REQUIRED_PYTHON_MINOR: int = 11

    def validate_production_settings(self) -> None:
        """Validate settings for non-development environments.

        Raises ValueError if dangerous defaults are used outside development.
        """
        if self.ENVIRONMENT not in {"development", "test"}:
            errors = []

            if self.JWT_SECRET == "test-secret-key-for-development-only":
                errors.append(
                    "JWT_SECRET must not use development default in production"
                )

            if "*" in self.ALLOWED_HOSTS:
                errors.append("ALLOWED_HOSTS must not be '*' in production")

            if "scholarai123" in self.DATABASE_URL:
                errors.append(
                    "DATABASE_URL contains default password - use secure credentials"
                )

            if self.NEO4J_PASSWORD == "scholarai123":
                errors.append(
                    "NEO4J_PASSWORD uses default value - use secure credentials"
                )

            if errors:
                raise ValueError(
                    "Environment security validation failed:\n"
                    + "\n".join(f"  - {e}" for e in errors)
                )

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_HOUR: int = 200

    # =========================================================================
    # Database Configuration
    # =========================================================================
    DATABASE_URL: str = "postgresql://scholarai:scholarai123@localhost:5432/scholarai"

    @property
    def async_database_url(self) -> str:
        """Convert DATABASE_URL to asyncpg URL format.

        Replaces postgresql:// with postgresql+asyncpg:// for SQLAlchemy async engine.
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql+asyncpg://"):
            return url
        return url

    @property
    def DB_HOST(self) -> str:
        """Extract host from DATABASE_URL for safe logging."""
        url = self.DATABASE_URL
        if "@" in url:
            return url.split("@")[-1].split(":")[0].split("/")[0]
        return "localhost"

    @property
    def NEO4J_HOST(self) -> str:
        """Extract host from NEO4J_URI for safe logging."""
        uri = self.NEO4J_URI
        if "://" in uri:
            return uri.split("://")[-1].split(":")[0]
        return "localhost"

    # =========================================================================
    # Redis Configuration
    # =========================================================================
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # =========================================================================
    # Neo4j Graph Database Configuration
    # =========================================================================
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "scholarai123"

    # =========================================================================
    # Milvus Vector Database Configuration
    # =========================================================================
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_IMAGES: str = "paper_images"
    MILVUS_COLLECTION_TABLES: str = "paper_tables"
    MILVUS_COLLECTION_CONTENTS: str = "paper_contents"
    MILVUS_COLLECTION_CONTENTS_V2: str = "paper_contents_v2"
    MILVUS_POOL_SIZE: int = 10
    MILVUS_TIMEOUT: int = 10
    MILVUS_INDEX_TYPE: str = "IVF_FLAT"
    MILVUS_METRIC_TYPE: str = "COSINE"
    MILVUS_NLIST: int = 1024
    MILVUS_NPROBE: int = 32
    MILVUS_BATCH_SIZE: int = 50
    MILVUS_SEARCH_PROFILE: str = "default"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_CONTENTS_V2: str = "paper_contents_v2"
    EMBEDDING_PROVIDER: str = "qwen3vl"
    EMBEDDING_VARIANT: str = "2b"
    RERANKER_PROVIDER: str = "qwen3vl"
    RERANKER_VARIANT: str = "2b"
    VECTOR_STORE_BACKEND: Literal["milvus", "qdrant"] = "milvus"
    RETRIEVAL_BENCH_PROFILE: str = "dev"
    RETRIEVAL_TRACE_ENABLED: bool = False
    RETRIEVAL_TRACE_INCLUDE_RESULTS: bool = False
    RETRIEVAL_VECTOR_WEIGHT: float = 0.75
    RETRIEVAL_SPARSE_WEIGHT: float = 0.25
    GRAPH_RETRIEVAL_ENABLED: bool = True
    GRAPH_RETRIEVAL_TOP_K: int = 8
    GRAPH_EXTRACTION_ON_INGEST: bool = False

    # =========================================================================
    # JWT Authentication Configuration
    # =========================================================================
    JWT_SECRET: str = "test-secret-key-for-development-only"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Internal service JWT (RS256)
    JWT_INTERNAL_PUBLIC_KEY: str = ""
    JWT_INTERNAL_PUBLIC_KEY_FILE: str = ""

    # =========================================================================
    # CORS Configuration
    # =========================================================================
    ALLOWED_HOSTS: List[str] = ["*"]

    # =========================================================================
    # File Upload Configuration
    # =========================================================================
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "/app/uploads"

    # =========================================================================
    # S3 / Object Storage Configuration
    # =========================================================================
    S3_ENDPOINT: Optional[str] = None
    S3_BUCKET: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    USE_LOCAL_STORAGE: bool = True

    # Legacy OSS configuration (for backward compatibility)
    OSS_ENDPOINT: str = "local"
    LOCAL_STORAGE_PATH: str = "/app/uploads"

    # =========================================================================
    # AI Service Configuration
    # =========================================================================
    # Zhipu AI API (for LLM and Vision)
    ZHIPU_API_KEY: str = ""
    ZHIPU_MODEL_VISION: str = "glm-4v"
    ZHIPU_MODEL_TEXT: str = "glm-4-flash"
    ZHIPU_MAX_TOKENS: int = 150
    ZHIPU_TEMPERATURE: float = 0.3

    # LLM Configuration
    LLM_MODEL: str = "glm-4.5-air"
    LLM_API_BASE: str = "https://open.bigmodel.cn/api/paas/v4"
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_RETRIES: int = 5
    DEFAULT_MODEL: str = "gpt-4o-mini"

    # Embedding Model Configuration
    EMBEDDING_MODEL: str = "qwen3-vl-2b"
    EMBEDDING_QUANTIZATION: str = "int4"
    EMBEDDING_DIMENSION: int = 2048
    EMBEDDING_DEVICE: str = "auto"  # auto | cpu | cuda | mps

    # Reranker Configuration
    RERANKER_MODEL: str = "bge-reranker"
    RERANKER_QUANTIZATION: str = "fp16"

    # Local Model Paths
    QWEN3VL_EMBEDDING_MODEL_PATH: str = "./Qwen/Qwen3-VL-Embedding-2B"
    QWEN3VL_RERANKER_MODEL_PATH: str = "./Qwen/Qwen3-VL-Reranker-2B"

    # =========================================================================
    # PDF Parser Configuration (Docling)
    # =========================================================================
    # Per Sprint 4 Task 1: Configurable OCR and multimodal extraction
    # Per PR7 Phase 7A: OCR should NOT be enabled by default
    # - born-digital PDFs use native parser (fast, accurate text order)
    # - scanned/image-heavy PDFs auto-fallback to OCR when text density < 80 chars/page
    # - This avoids speed degradation and parsing noise on well-formed PDFs
    PARSER_DO_OCR: bool = False  # OCR disabled by default (smart fallback enabled)
    PARSER_GENERATE_PICTURE_IMAGES: bool = True  # Extract images
    PARSER_GENERATE_TABLE_IMAGES: bool = True  # Extract tables
    PARSER_OCR_LANGUAGE: str = "en,zh"  # English + Chinese
    PARSER_OCR_RETRY_MIN_CHARS_PER_PAGE: int = 80  # Native parse fallback threshold
    PARSER_MAX_PAGES: int = 100  # Maximum pages to parse
    PARSER_MAX_FILE_SIZE_MB: int = 50  # Maximum file size (MB)
    PARSER_TIMEOUT_SECONDS: int = 300  # Parsing timeout (seconds)
    PARSER_CPU_THREADS: int = 4  # CPU thread limit

    # =========================================================================
    # RAG Configuration
    # =========================================================================
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    CHUNK_MIN_SIZE: int = 100
    CHUNK_MAX_SIZE: int = 600
    CHUNK_ADAPTIVE_ENABLED: bool = True
    CHUNK_QUALITY_THRESHOLD: float = 0.7
    TOP_K_RETRIEVAL: int = 10

    # =========================================================================
    # External API Configuration
    # =========================================================================
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    SEMANTIC_SCHOLAR_API_KEY: str = ""
    S2_API_KEY: str = ""

    # Semantic Scholar Cache TTLs
    S2_CACHE_TTL: int = 86400  # 24 hours
    S2_PAPER_TTL: int = 604800  # 7 days
    S2_CITATION_TTL: int = 2592000  # 30 days

    # HuggingFace Offline Mode
    HF_HUB_OFFLINE: str = "1"
    TRANSFORMERS_OFFLINE: str = "1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        runtime_profile = self.RUNTIME_PROFILE or self._default_runtime_profile()
        ai_startup_mode = self.AI_STARTUP_MODE or self._default_ai_startup_mode(runtime_profile)
        object.__setattr__(self, "RUNTIME_PROFILE", runtime_profile)
        object.__setattr__(self, "AI_STARTUP_MODE", ai_startup_mode)

        # Load JWT public key from file if configured
        if self.JWT_INTERNAL_PUBLIC_KEY_FILE and os.path.exists(
            self.JWT_INTERNAL_PUBLIC_KEY_FILE
        ):
            with open(self.JWT_INTERNAL_PUBLIC_KEY_FILE, "r") as f:
                # Need to set on the instance, not class
                object.__setattr__(self, "JWT_INTERNAL_PUBLIC_KEY", f.read())

    def _default_runtime_profile(self) -> str:
        env_to_profile: Dict[str, str] = {
            "development": "dev-lite",
            "staging": "dev-full",
            "production": "prod",
            "test": "dev-lite",
        }
        return env_to_profile.get(self.ENVIRONMENT, "dev-lite")

    @staticmethod
    def _default_ai_startup_mode(runtime_profile: str) -> str:
        profile_to_mode: Dict[str, str] = {
            "dev-lite": "lazy",
            "dev-full": "lazy",
            "prod": "eager",
        }
        return profile_to_mode.get(runtime_profile, "lazy")


@lru_cache()
def get_settings() -> Settings:
    """Get cached Settings instance.

    Uses lru_cache to ensure only one Settings instance is created.
    """
    return Settings()


# Global settings instance
settings = get_settings()
