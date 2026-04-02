# External Integrations

**Analysis Date:** 2026-04-02

## APIs & External Services

**LLM Providers (via LiteLLM):**
- **OpenAI** - Primary LLM provider
  - Models: gpt-4o-mini (default), text-embedding-3-small
  - Config: `OPENAI_API_KEY` env var
  - Usage: Entity extraction, notes generation, comparison, query decomposition (`backend-python/app/core/`)

- **Anthropic** - Optional Claude models
  - Config: `ANTHROPIC_API_KEY` env var
  - Usage: Alternative LLM backend via LiteLLM

- **Aliyun DashScope** - Chinese cloud LLM provider
  - Model format: `openai/qwen-plus`, `openai/deepseek-v3`
  - Config: `LLM_API_BASE` env var (default: https://api.openai.com/v1)
  - Usage: Entity extraction and LLM operations in China region

**Academic Search APIs:**
- **arXiv API** - Academic paper search
  - Endpoint: `http://export.arxiv.org/api/query`
  - No API key required
  - Usage: Search papers by keyword, fetch metadata and PDF URLs (`backend-python/app/api/search.py`)

- **Semantic Scholar API** - Academic paper search with citations
  - Endpoint: `https://api.semanticscholar.org/graph/v1/paper/search`
  - No API key required (rate limited)
  - Usage: Enhanced paper search with citation counts

**Object Storage:**
- **AWS S3 SDK** - Used for MinIO/Aliyun OSS compatibility
  - Package: `@aws-sdk/client-s3` 3.1009+
  - Features: Presigned URLs for upload/download, streaming
  - Config: `OSS_ENDPOINT`, `OSS_REGION`, `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`, `OSS_BUCKET`
  - Local fallback: Filesystem storage when `OSS_ENDPOINT=local` or not set (`backend-node/src/services/storage.ts`)

## Data Storage

**Primary Database:**
- **PostgreSQL 15** with PGVector extension
  - Connection: `DATABASE_URL` env var
  - ORM: Prisma (Node.js), asyncpg (Python)
  - Extensions: PGVector for 1536/768-dimensional embeddings
  - Tables: users, papers, paper_chunks, queries, knowledge_maps, roles, permissions, etc.

**Vector Store:**
- **PGVector** - PostgreSQL vector extension
  - Dimension support: 768 (sentence-transformers), 1536 (OpenAI)
  - Operations: Cosine similarity search (`<=>` operator), L2 distance
  - Tables: `paper_chunks` with `embedding vector(dimension)` column

**Graph Database:**
- **Neo4j 5 Community**
  - Connection: `NEO4J_URI` (default: bolt://localhost:7687)
  - Auth: `NEO4J_AUTH` (username/password)
  - Plugins: APOC, GDS (Graph Data Science)
  - Usage: Knowledge graphs, entity relationships, PageRank analysis
  - Python driver: `neo4j` 5.14+ (`backend-python/app/core/neo4j_service.py`)
  - Node.js driver: `neo4j-driver` 5.18+ (not actively used in current code)

**Cache & Session Store:**
- **Redis 7**
  - Connection: `REDIS_URL` (default: redis://localhost:6379/0)
  - Usage:
    - JWT token blacklist (logout)
    - Refresh token storage
    - Search result caching (24-hour TTL)
    - Rate limiting (planned)
  - Libraries: `redis` (Python), `ioredis` (Node.js)

**File Storage:**
- **Local filesystem** - Development mode
  - Path: `./uploads` or `/app/papers`
  - Fallback when OSS not configured

- **MinIO/Aliyun OSS** - Production object storage
  - Presigned URL-based upload/download
  - Bucket: `scholarai-papers` (default)

## Authentication & Identity

**JWT-based Authentication:**
- **Node.js Gateway** - Issues RS256-signed JWTs for users
  - Access tokens (short-lived)
  - Refresh tokens (stored in Redis)
  - Library: `jsonwebtoken`

- **Python AI Service** - Validates tokens from Node.js
  - Algorithm: RS256 (asymmetric)
  - Public key verification via `JWT_INTERNAL_PUBLIC_KEY` or `JWT_INTERNAL_PUBLIC_KEY_FILE`
  - Library: `PyJWT` with `cryptography`

**Password Security:**
- **Argon2** - Password hashing (Node.js)
- Argon2id variant with memory-hard properties

**RBAC System:**
- Custom implementation with Prisma
- Tables: `roles`, `permissions`, `user_roles`
- Resources: papers, queries, admin
- Actions: create, read, update, delete

## Monitoring & Observability

**Logging:**
- **Winston** (Node.js) - Structured logging with JSON output (`backend-node/src/utils/logger.ts`)
- **structlog** (Python) - Structured logging with context (`backend-python/app/utils/logger.py`)
- Log levels: debug, info, warning, error
- Config: `LOG_LEVEL` env var (default: info)

**HTTP Logging:**
- **morgan** (Node.js) - Express request logging

**Error Tracking:**
- Custom error handling middleware
- UUID-based error correlation
- Not integrated with external error tracking service (Sentry, etc.)

## CI/CD & Deployment

**Container Orchestration:**
- **Docker Compose** - Local development
  - 6 services: postgres, redis, neo4j, ai-service, api, frontend
  - Health checks for database dependencies
  - Volume persistence for data

**Deployment Scripts:**
- `deploy-cloud.sh` - Cloud deployment (comprehensive)
- `deploy-cloud-minimal.sh` - Minimal deployment
- `deploy-cloud-fixed.sh` - Fixed deployment script
- `Makefile` - Development convenience commands

**No CI/CD Pipeline Detected:**
- No GitHub Actions, GitLab CI, or other CI configuration found
- Deployment appears to be manual or script-based

## Environment Configuration

**Required Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
NEO4J_AUTH=neo4j/password

# AI Services
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...  # Optional

# Authentication
JWT_SECRET=your-secret-key
JWT_INTERNAL_PUBLIC_KEY_FILE=/path/to/public.pem

# Object Storage (optional for local dev)
OSS_ENDPOINT=...  # Set to 'local' or omit for filesystem
OSS_ACCESS_KEY_ID=...
OSS_ACCESS_KEY_SECRET=...

# Service URLs
AI_SERVICE_URL=http://ai-service:8000
FRONTEND_URL=http://localhost:3000
```

**Secrets Location:**
- `.env` file (gitignored)
- `.env.example` provides template
- Docker Compose reads from environment or `.env` file
- JWT public key file path configured via env var

## Webhooks & Callbacks

**Incoming:**
- None detected - no webhook endpoints for external services

**Outgoing:**
- None detected - no outbound webhooks configured

## Service Communication

**Internal Service-to-Service:**
- **Node.js -> Python AI Service**
  - Protocol: HTTP/REST
  - Authentication: JWT with RS256 signature
  - Endpoint pattern: `AI_SERVICE_URL` + route
  - Used for: PDF processing triggers, RAG queries, entity extraction

**Cross-Service Data Flow:**
1. User uploads PDF to Node.js API
2. Node.js stores in object storage (MinIO/OSS)
3. Node.js sends internal request to Python service with JWT
4. Python service downloads PDF, processes with Docling
5. Python service stores embeddings in PostgreSQL, entities in Neo4j
6. Node.js polls or receives completion status

## External API Rate Limits

**arXiv:**
- No explicit rate limiting, but requests should be reasonable
- Results cached in Redis for 24 hours

**Semantic Scholar:**
- Rate limited (no API key)
- Results cached in Redis for 24 hours

**OpenAI/Anthropic:**
- Subject to provider rate limits
- Managed via LiteLLM abstraction

---

*Integration audit: 2026-04-02*
