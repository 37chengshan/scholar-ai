# Technology Stack

**Analysis Date:** 2026-04-02

## Languages

**Primary:**
- **Python 3.11** - AI/ML services (`backend-python/`)
  - FastAPI for API endpoints
  - Async/await patterns throughout
  - Type hints with Pydantic models

- **TypeScript** - API Gateway and user-facing services (`backend-node/`)
  - Node.js 20+ runtime
  - Express.js framework
  - Strict mode enabled

**Secondary:**
- **SQL** - PostgreSQL with PGVector extension
- **Cypher** - Neo4j graph queries
- **Dockerfile** - Container definitions
- **Shell** - Deployment scripts

## Runtime

**Environment:**
- Docker & Docker Compose for local development
- Node.js 20 (Alpine-based containers)
- Python 3.11 (Slim-based containers)

**Package Managers:**
- **npm** (Node.js) - `backend-node/package.json`
- **pip** (Python) - `backend-python/requirements.txt`
- Lockfiles: `package-lock.json` present for Node.js

## Frameworks

**Core Backend (Node.js):**
- Express.js 4.18.3 - HTTP server and routing (`backend-node/src/index.ts`)
- Prisma 5.10 - ORM and database client (`backend-node/prisma/schema.prisma`)
- Zod 3.22.4 - Schema validation

**AI Service (Python):**
- FastAPI 0.100-0.110 - Async API framework (`backend-python/app/main.py`)
- Pydantic 2.0+ - Data validation and settings
- Uvicorn - ASGI server

**AI/ML Libraries:**
- **PaperQA2** 5.0+ - Academic paper QA system (`backend-python/requirements.txt`)
- **Docling** 2.0+ - PDF parsing and document understanding
- **LiteLLM** 1.0+ - Unified LLM API interface for multiple providers
- **Sentence Transformers** 2.0+ - Text embeddings (`backend-python/app/core/embedding_service.py`)

**Testing:**
- **Jest** 30.3.0 (Node.js) - Test runner with coverage (`backend-node/jest.config.js`)
- **pytest** 7.4+ (Python) - Async test support with pytest-asyncio

**Build/Dev:**
- **TypeScript** 5.4.2 - Type checking and compilation
- **tsx** 4.7.1 - TypeScript execution for development
- **ESLint** 8.57.0 - Linting with @typescript-eslint
- **Black** & **isort** - Python formatting

## Key Dependencies

**Critical Infrastructure:**
- **asyncpg** 0.29+ - Async PostgreSQL driver
- **pgvector** 0.2+ - PostgreSQL vector extension support
- **neo4j** 5.14+ (Python) / **neo4j-driver** 5.18+ (Node.js) - Graph database
- **redis** 5.0+ (Python) / **ioredis** 5.3+ (Node.js) - Caching and session storage

**Authentication & Security:**
- **jsonwebtoken** 9.0.2 - JWT token generation/validation
- **argon2** 0.44.0 - Password hashing
- **PyJWT** 2.8.0 + **cryptography** 42.0.5 - Python JWT with RS256
- **helmet** 7.1.0 - Express security headers
- **cors** 2.8.5 - Cross-origin resource sharing

**External APIs:**
- **@aws-sdk/client-s3** 3.1009+ - Object storage (MinIO/Aliyun OSS)
- **httpx** 0.25+ - Async HTTP client for external APIs

**Search & NLP:**
- **tantivy** 0.20+ - Full-text search engine
- **rapidfuzz** 3.0+ - Fast text similarity/deduplication
- **structlog** 23.0+ - Structured logging

**Utilities:**
- **multer** 1.4.5 - File upload handling
- **uuid** 9.0.1 - UUID generation
- **ms** 2.1.3 - Time duration parsing
- **python-dotenv** 1.0+ - Environment loading

## Configuration

**Environment Variables (`.env.example`):**
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `NEO4J_AUTH` - Neo4j credentials
- `OPENAI_API_KEY` - OpenAI API access
- `ANTHROPIC_API_KEY` - Anthropic API access (optional)
- `AI_SERVICE_URL` - Internal Python service URL
- `JWT_SECRET` - JWT signing key
- `OSS_ENDPOINT` / `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` - Object storage

**Build Configuration:**
- `tsconfig.json` - TypeScript compiler options (`backend-node/tsconfig.json`)
  - Target: ES2022
  - Module: NodeNext
  - Strict mode enabled
- `pytest.ini` - Python test configuration
- `jest.config.js` - Jest test configuration

**Docker Configuration:**
- `docker-compose.yml` - Multi-service orchestration
  - PostgreSQL 15 with PGVector
  - Redis 7 (Alpine)
  - Neo4j 5 Community with APOC and GDS plugins
  - Python AI service (port 8000)
  - Node.js API service (port 4000)
  - Frontend dev server (port 3000)

## Platform Requirements

**Development:**
- Docker Desktop or Docker Engine 20.10+
- Node.js 20+ (for local dev without Docker)
- Python 3.11+ (for local dev without Docker)
- Make (for convenience commands)

**Production:**
- Container orchestration (Docker Compose or Kubernetes)
- Minimum 4GB RAM for AI service (with 4G memory limit configured)
- PostgreSQL 15+ with PGVector extension
- Neo4j 5+ with APOC and GDS plugins
- Redis 7+

**External Service Dependencies:**
- OpenAI API or compatible LLM API (configurable via LiteLLM)
- Optional: Anthropic API
- Optional: Aliyun OSS or MinIO for object storage

## Architecture Notes

**Service Separation:**
- **Node.js Gateway** (`backend-node/`) - User-facing API, auth, file uploads, business logic
- **Python AI Service** (`backend-python/`) - PDF parsing, embeddings, RAG, entity extraction, LLM interactions
- **Internal Communication** - JWT-signed requests between services

**Database Strategy:**
- PostgreSQL + PGVector - Primary data with vector embeddings
- Neo4j - Knowledge graph and entity relationships
- Redis - Caching, rate limiting, session management

---

*Stack analysis: 2026-04-02*
