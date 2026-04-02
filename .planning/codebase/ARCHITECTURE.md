# Architecture

**Analysis Date:** 2026-04-02

## Pattern Overview

**Overall:** Microservices with API Gateway Pattern

**Key Characteristics:**
- Dual-backend architecture: Node.js API Gateway + Python AI Service
- Service-oriented decomposition by capability
- Asynchronous task processing with worker queues
- Multi-database strategy (PostgreSQL + PGVector + Neo4j + Redis)
- JWT-based service-to-service authentication

## Layers

**Presentation Layer (Frontend):**
- Purpose: React-based SPA (landing/marketing site exists, full app in development)
- Location: Root `src/` (not fully implemented in current codebase)
- Contains: React components, Tailwind styles, Vite config
- Depends on: Node.js API Gateway
- Used by: End users

**API Gateway Layer (Node.js):**
- Purpose: Request routing, authentication, authorization, orchestration
- Location: `backend-node/src/`
- Contains: Express routes, middleware, Prisma client
- Depends on: PostgreSQL, Redis, Python AI Service
- Used by: Frontend, Mobile clients

**AI Service Layer (Python):**
- Purpose: PDF processing, RAG queries, entity extraction, graph operations
- Location: `backend-python/app/`
- Contains: FastAPI endpoints, core AI logic, workers
- Depends on: PostgreSQL + PGVector, Neo4j, Redis, Object Storage
- Used by: Node.js API Gateway (internal)

**Data Layer:**
- Purpose: Persistent storage and caching
- Components:
  - PostgreSQL + PGVector: Primary data, vector embeddings
  - Neo4j: Knowledge graph, citation networks
  - Redis: Sessions, caching, task queues
  - Object Storage (S3/MinIO): PDF files

## Data Flow

**PDF Upload and Processing Flow:**

1. Client requests upload URL from `POST /api/papers` (Node.js)
2. Node.js generates presigned URL (S3 or local storage)
3. Client uploads PDF directly to storage
4. Client calls `POST /api/papers/webhook` to confirm upload
5. Node.js creates `ProcessingTask` record in PostgreSQL
6. Python worker polls for pending tasks (`pdf_worker.py`)
7. Worker downloads PDF from object storage
8. Worker processes through pipeline:
   - OCR + Parsing (Docling)
   - IMRaD structure extraction
   - Reading notes generation
   - Chunking + embedding generation
   - Vector storage (PGVector)
   - Graph storage (Neo4j)
9. Worker updates task status to `completed`
10. Client polls `GET /api/papers/:id/status` for progress

**RAG Query Flow:**

1. Client sends query to `POST /api/queries` or `/rag/query` (Node.js proxies to Python)
2. Python service receives query via FastAPI
3. Query is embedded using embedding service
4. PGVector similarity search retrieves relevant chunks
5. Optional: Agentic retrieval decomposes complex queries
6. Results synthesized (LLM integration placeholder)
7. Response returned with citations and confidence scores

**Authentication Flow:**

1. User registers/logs in via `POST /api/auth/register` or `/login`
2. Node.js validates credentials against PostgreSQL
3. Access token (JWT) and refresh token generated
4. Tokens stored in httpOnly cookies
5. Redis stores refresh token mapping for revocation
6. Subsequent requests include cookies
7. `authenticate` middleware validates JWT and checks Redis blacklist
8. RBAC middleware checks permissions via `requirePermission()`

## Key Abstractions

**ProcessingTask (6-State Pipeline):**
- Purpose: Track PDF processing state machine
- States: `pending` → `processing_ocr` → `parsing` → `extracting_imrad` → `generating_notes` → `completed`/`failed`
- Location: `backend-node/prisma/schema.prisma` (model ProcessingTask)
- Pattern: State machine with progress tracking (0%, 10%, 30%, 50%, 80%, 100%)

**AuthRequest (Authenticated Request Context):**
- Purpose: Extend Express Request with authenticated user
- Location: `backend-node/src/types/auth.ts`
- Contains: `user.sub` (UUID), `user.email`, `user.roles`, `user.jti`
- Pattern: Middleware-augmented request types

**PGVectorStore (Vector Storage Abstraction):**
- Purpose: Unified interface for vector similarity search
- Location: `backend-python/app/core/rag_service.py`
- Methods: `search()`, `add_chunks()`, `delete_by_paper()`
- Pattern: Repository pattern over PGVector extension

**AgenticRetrievalOrchestrator:**
- Purpose: Handle complex multi-paper queries via decomposition
- Location: `backend-python/app/core/agentic_retrieval.py`
- Features: Query decomposition, parallel execution, convergence detection
- Pattern: Strategy pattern with round-based execution

**RFC 7807 Problem Details:**
- Purpose: Standardized error response format
- Location: `backend-node/src/types/auth.ts` (ProblemDetail interface)
- Used in: `backend-node/src/middleware/errorHandler.ts`
- Pattern: Standardized error envelope with type, title, status, detail

## Entry Points

**Node.js API Gateway:**
- Location: `backend-node/src/index.ts`
- Port: 4000 (default)
- Routes mounted at `/api/*`
- Health check: `GET /api/health`

**Python AI Service:**
- Location: `backend-python/app/main.py`
- Port: 8000 (default)
- Routes mounted at root with prefixes (e.g., `/rag`, `/parse`)
- Auto-generated docs: `/docs` (Swagger UI)

**PDF Processing Worker:**
- Location: `backend-python/app/workers/pdf_worker.py`
- Execution: Standalone async process
- Trigger: Polls database for `pending` tasks

## Error Handling

**Strategy:** Centralized error handling with RFC 7807 Problem Details

**Patterns:**
- Node.js: `errorHandler` middleware catches all errors
- Custom `ApiError` type with `statusCode` and `code` fields
- `Errors` factory for common error types (unauthorized, notFound, etc.)
- Async errors caught and passed to `next(error)`
- Request ID generated per request for log correlation

## Cross-Cutting Concerns

**Logging:**
- Node.js: Winston logger with structured JSON output (`backend-node/src/utils/logger.ts`)
- Python: Structlog with context binding (`backend-python/app/utils/logger.py`)

**Validation:**
- Node.js: Zod schemas (e.g., `registerSchema`, `loginSchema` in auth routes)
- Python: Pydantic models in FastAPI endpoints

**Authentication:**
- JWT access tokens (short-lived, in cookies)
- Refresh tokens (longer-lived, stored in Redis + PostgreSQL)
- Redis blacklist for token revocation
- RS256 for internal service tokens

**Rate Limiting:**
- Not explicitly implemented (placeholder for future)

---

*Architecture analysis: 2026-04-02*
