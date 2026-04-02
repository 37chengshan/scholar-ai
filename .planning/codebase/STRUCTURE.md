# Codebase Structure

**Analysis Date:** 2026-04-02

## Directory Layout

```
scholar-ai/
├── .planning/                  # Planning and analysis documents
│   ├── codebase/               # Codebase mapping output
│   │   ├── ARCHITECTURE.md
│   │   └── STRUCTURE.md
│   └── debug/                  # Debug logs and phase reports
├── backend-node/               # Node.js API Gateway (Express + TypeScript)
│   ├── prisma/
│   │   ├── schema.prisma       # Database schema definition
│   │   ├── migrations/         # Database migrations
│   │   └── seed.ts             # Seed data script
│   ├── src/
│   │   ├── index.ts            # Application entry point
│   │   ├── config/             # Configuration modules
│   │   │   ├── auth.ts         # JWT/cookie settings
│   │   │   ├── database.ts     # Prisma client setup
│   │   │   └── redis.ts        # Redis connection
│   │   ├── middleware/         # Express middleware
│   │   │   ├── auth.ts         # JWT authentication
│   │   │   ├── errorHandler.ts # RFC 7807 error handling
│   │   │   └── rbac.ts         # Role-based access control
│   │   ├── routes/             # API route handlers
│   │   │   ├── auth.ts         # Authentication endpoints
│   │   │   ├── papers.ts       # Paper CRUD + upload
│   │   │   ├── queries.ts      # Query management
│   │   │   ├── users.ts        # User management
│   │   │   ├── search.ts       # Search endpoints
│   │   │   ├── graph.ts        # Graph API proxy
│   │   │   ├── entities.ts     # Entity extraction proxy
│   │   │   ├── compare.ts      # Paper comparison
│   │   │   └── health.ts       # Health checks
│   │   ├── services/           # Business logic services
│   │   │   ├── storage.ts      # S3/MinIO/local storage
│   │   │   └── tasks.ts        # Task status management
│   │   ├── types/              # TypeScript type definitions
│   │   │   └── auth.ts         # Auth types, ProblemDetail
│   │   └── utils/              # Utility functions
│   │       ├── crypto.ts       # Password hashing (Argon2)
│   │       ├── jwt.ts          # JWT signing/verification
│   │       ├── logger.ts       # Winston logger
│   │       └── cli.ts          # CLI utilities
│   ├── tests/
│   │   ├── e2e/                # End-to-end tests
│   │   │   ├── auth.e2e.test.ts
│   │   │   ├── papers.e2e.test.ts
│   │   │   ├── rbac.e2e.test.ts
│   │   │   └── ...
│   │   └── helpers/            # Test utilities
│   │       ├── server.ts
│   │       └── db.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── jest.config.js
├── backend-python/             # Python AI Service (FastAPI)
│   ├── app/
│   │   ├── main.py             # FastAPI application entry
│   │   ├── api/                # API route modules
│   │   │   ├── health.py
│   │   │   ├── papers.py
│   │   │   ├── parse.py        # PDF parsing endpoints
│   │   │   ├── rag.py          # RAG query endpoints
│   │   │   ├── entities.py     # Entity extraction
│   │   │   ├── graph.py        # Knowledge graph
│   │   │   ├── search.py       # External search
│   │   │   ├── compare.py      # Paper comparison
│   │   │   ├── notes.py        # Notes generation
│   │   │   └── internal.py     # Internal service endpoints
│   │   ├── core/               # Core business logic
│   │   │   ├── config.py       # Pydantic settings
│   │   │   ├── database.py     # Database connection
│   │   │   ├── docling_service.py  # PDF parsing (Docling)
│   │   │   ├── embedding_service.py # Vector embeddings
│   │   │   ├── rag_service.py  # RAG retrieval
│   │   │   ├── agentic_retrieval.py # Multi-round retrieval
│   │   │   ├── query_decomposer.py
│   │   │   ├── imrad_extractor.py
│   │   │   ├── neo4j_service.py
│   │   │   ├── pagerank_service.py
│   │   │   ├── notes_generator.py
│   │   │   └── storage.py      # Object storage client
│   │   ├── models/             # Pydantic models
│   │   │   └── rag.py
│   │   ├── utils/              # Utilities
│   │   │   ├── logger.py       # Structlog setup
│   │   │   ├── cache.py        # Redis cache helpers
│   │   │   └── retry.py        # Retry decorators
│   │   └── workers/            # Background workers
│   │       ├── pdf_worker.py   # PDF processing worker
│   │       ├── entity_worker.py
│   │       └── pdf_download_worker.py
│   ├── tests/                  # Test suite
│   │   ├── e2e/
│   │   ├── test_graph/
│   │   └── fixtures/
│   ├── migrations/             # Database migrations
│   └── scripts/                # Utility scripts
├── docker-compose.yml          # Local development stack
├── Makefile                    # Build automation
└── README.md                   # Project documentation
```

## Directory Purposes

**backend-node/src/routes/:**
- Purpose: Express route handlers, one file per domain
- Contains: Route definitions, request validation, response formatting
- Pattern: Each router handles CRUD for a single resource
- Key files: `papers.ts` (912 lines - largest), `auth.ts`, `graph.ts`

**backend-node/src/middleware/:**
- Purpose: Cross-cutting Express middleware
- Contains: Authentication, error handling, RBAC
- Pattern: Composable middleware chain
- Key files: `auth.ts`, `errorHandler.ts`, `rbac.ts`

**backend-node/src/services/:**
- Purpose: Business logic isolated from HTTP layer
- Contains: Storage abstraction, task management
- Pattern: Service modules export functions, not classes
- Key files: `storage.ts`, `tasks.ts`

**backend-node/src/config/:**
- Purpose: Configuration and connection setup
- Contains: Database clients, auth settings
- Pattern: Singleton instances exported
- Key files: `database.ts`, `redis.ts`, `auth.ts`

**backend-python/app/core/:**
- Purpose: AI/ML business logic
- Contains: PDF processing, embeddings, RAG, graph operations
- Pattern: Class-based services with async methods
- Key files: `docling_service.py`, `rag_service.py`, `agentic_retrieval.py`

**backend-python/app/api/:**
- Purpose: FastAPI route handlers
- Contains: Endpoint definitions, request/response models
- Pattern: Module per feature, router included in main.py
- Key files: `rag.py`, `parse.py`, `graph.py`

**backend-python/app/workers/:**
- Purpose: Background task processing
- Contains: Async worker loops for PDF processing
- Pattern: Standalone scripts with polling loops
- Key files: `pdf_worker.py`

## Key File Locations

**Entry Points:**
- `backend-node/src/index.ts`: Node.js API Gateway
- `backend-python/app/main.py`: Python AI Service
- `backend-python/app/workers/pdf_worker.py`: PDF processing worker

**Configuration:**
- `backend-node/prisma/schema.prisma`: Database schema (Prisma)
- `backend-python/app/core/config.py`: Python service settings (Pydantic)
- `.env.example`: Environment variable template

**Core Logic:**
- `backend-node/src/services/storage.ts`: Object storage abstraction
- `backend-node/src/middleware/auth.ts`: JWT authentication
- `backend-python/app/core/rag_service.py`: RAG implementation
- `backend-python/app/core/docling_service.py`: PDF parsing

**Testing:**
- `backend-node/tests/e2e/`: E2E tests (Jest + Supertest)
- `backend-node/jest.config.js`: Test configuration

## Naming Conventions

**Files:**
- TypeScript: `camelCase.ts` (e.g., `errorHandler.ts`, `auth.ts`)
- Python: `snake_case.py` (e.g., `rag_service.py`, `pdf_worker.py`)
- Test files: `*.e2e.test.ts` or `*.test.ts`
- Config files: `*.config.js`, `tsconfig.json`

**Directories:**
- Lowercase with hyphens: `backend-node/`, `backend-python/`
- Singular nouns: `routes/`, `services/`, `utils/`

**Classes (Python):**
- PascalCase: `DoclingParser`, `RAGService`, `AgenticRetrievalOrchestrator`

**Functions:**
- TypeScript: `camelCase`: `generateAccessToken`, `verifyPassword`
- Python: `snake_case`: `rag_query`, `extract_imrad_structure`

## Where to Add New Code

**New API Endpoint (Node.js):**
- Route handler: `backend-node/src/routes/[feature].ts`
- Types: `backend-node/src/types/[feature].ts` (if needed)
- Service logic: `backend-node/src/services/[feature].ts` (if complex)
- Registration: Add import and `app.use()` in `backend-node/src/index.ts`
- Tests: `backend-node/tests/e2e/[feature].e2e.test.ts`

**New AI Feature (Python):**
- Core logic: `backend-python/app/core/[feature].py`
- API routes: `backend-python/app/api/[feature].py`
- Models: `backend-python/app/models/[feature].py` (if needed)
- Registration: Include router in `backend-python/app/main.py`

**New Database Model:**
- Schema: Add to `backend-node/prisma/schema.prisma`
- Migration: Run `npm run db:migrate` in backend-node
- Generate: Run `npm run db:generate` for Prisma client update

**New Worker:**
- Implementation: `backend-python/app/workers/[name]_worker.py`
- Pattern: Copy structure from `pdf_worker.py`
- Execution: Add to docker-compose or run standalone

**Utilities:**
- Node.js: `backend-node/src/utils/[name].ts`
- Python: `backend-python/app/utils/[name].py`

## Special Directories

**.planning/:**
- Purpose: Development planning documents
- Generated: Yes (by GSD commands)
- Committed: Yes (project documentation)

**prisma/migrations/:**
- Purpose: Database schema migrations
- Generated: Yes (via Prisma CLI)
- Committed: Yes

**uploads/ (local development):**
- Purpose: Local file storage when S3 not configured
- Generated: Yes (at runtime)
- Committed: No (in .gitignore)

**tests/:**
- Purpose: Test suites
- Structure: Mirrors source with `*.test.ts` or `*.test.py` suffix
- Pattern: Co-located in `tests/` directories

---

*Structure analysis: 2026-04-02*
