# ScholarAI Unified FastAPI Backend

Complete API backend for ScholarAI - a multimodal academic paper reading system.

## Overview

This is the unified FastAPI backend that replaces the previous Node.js + Python split architecture. It provides all API services in a single Python application:

- OAuth 2.0 + Cookie-based Authentication
- User Management
- Paper CRUD Operations
- PDF Upload and Processing
- Task Management
- Notes, Projects, Annotations
- Reading Progress Tracking
- Dashboard Statistics
- External Search Integration
- Semantic Scholar Integration
- Session Management
- Chat with SSE Streaming
- Entity Extraction
- Knowledge Graph
- Paper Comparison
- RAG Q&A

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Neo4j 5+
- Milvus 2.3+

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/scholar-ai.git
cd scholar-ai/backend-python

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
# Edit .env with your actual configuration

# Run database migrations (if using Alembic)
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Docker Setup

For local development with all infrastructure services:

```bash
# From project root
docker-compose up -d postgres redis neo4j milvus etcd minio

# Wait for services to be ready (30-60 seconds)
# Then start the FastAPI backend
uvicorn app.main:app --reload --port 8000
```

## Project Structure

```
backend-python/
├── app/
│   ├── api/              # API routes (20+ routers)
│   │   ├── auth.py       # OAuth 2.0 authentication
│   │   ├── users.py      # User management
│   │   ├── papers.py     # Paper CRUD
│   │   ├── uploads.py    # File uploads
│   │   ├── tasks.py      # Background tasks
│   │   ├── notes.py      # Note management
│   │   ├── projects.py   # Project organization
│   │   ├── annotations.py # Paper annotations
│   │   ├── reading_progress.py # Reading tracking
│   │   ├── dashboard.py  # Statistics
│   │   ├── search.py     # External search
│   │   ├── semantic_scholar.py # S2 integration
│   │   ├── session.py    # Session management
│   │   ├── chat.py       # SSE streaming chat
│   │   ├── entities.py   # Entity extraction
│   │   ├── graph.py      # Knowledge graph
│   │   ├── compare.py    # Paper comparison
│   │   ├── system.py     # System diagnostics
│   │   ├── health.py     # Health checks
│   │   ├── parse.py      # PDF parsing (Python-specific)
│   │   ├── rag.py        # RAG Q&A (Python-specific)
│   │   └── internal.py   # Worker callbacks
│   ├── models/           # SQLAlchemy models
│   ├── services/         # Business logic layer
│   │   ├── auth_service.py
│   │   ├── paper_service.py
│   │   ├── storage_service.py
│   │   └── task_service.py
│   ├── middleware/       # Request middleware
│   │   ├── auth.py       # JWT authentication
│   │   ├── cors.py       # CORS configuration
│   │   ├── logging.py    # Request logging
│   │   ├── error_handler.py # RFC 7807 errors
│   │   └── file_validation.py # PDF validation
│   ├── core/             # AI services (unchanged)
│   │   ├── milvus_service.py
│   │   ├── reranker/
│   │   └── embedding/
│   ├── workers/          # Background tasks (unchanged)
│   ├── config.py         # Pydantic Settings
│   ├── database.py       # SQLAlchemy async
│   └── deps.py           # Dependency injection
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
└── README.md             # This file
```

## API Documentation

Access interactive API documentation after starting the server:

- **OpenAPI/Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/auth/login` | OAuth 2.0 login with cookie tokens |
| `/api/v1/auth/register` | Create new user account |
| `/api/v1/users/me` | Get current user profile |
| `/api/v1/papers` | List/upload papers |
| `/api/v1/papers/{id}` | Get/update/delete paper |
| `/api/v1/chat` | SSE streaming chat |
| `/api/v1/queries` | RAG Q&A endpoint |
| `/api/v1/graph` | Knowledge graph queries |
| `/api/v1/search` | External paper search |
| `/health` | Service health check |

## Testing

### Run Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requires services running)
pytest tests/integration -v

# All tests with coverage
pytest --cov=app --cov-report=html

# Coverage threshold: 80%
```

### Test Structure

- Unit tests mock external dependencies
- Integration tests require real services (PostgreSQL, Redis, etc.)
- Coverage reports in `htmlcov/` directory

## Deployment

### Docker Container

```bash
# Build image
docker build -t scholarai-backend .

# Run container
docker run -d \
  --name scholarai-api \
  -p 8000:8000 \
  --env-file .env \
  scholarai-backend
```

### Environment Variables

See `.env.example` for complete configuration. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection URL |
| `JWT_SECRET` | Yes | Secret key for JWT (min 32 chars) |
| `REDIS_URL` | Yes | Redis connection URL |
| `NEO4J_URI` | Yes | Neo4j connection URI |
| `MILVUS_HOST` | Yes | Milvus host address |
| `ZHIPU_API_KEY` | Recommended | Zhipu AI API key for LLM |
| `ALLOWED_HOSTS` | Yes | CORS allowed origins |

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure specific `ALLOWED_HOSTS` (not `["*"]`)
- [ ] Set strong `JWT_SECRET` (min 32 chars)
- [ ] Configure proper database credentials
- [ ] Set up HTTPS/TLS
- [ ] Configure rate limiting
- [ ] Set up monitoring and logging

## Migration from Node.js

This backend replaces the previous Node.js + Python split architecture. Key changes:

### API Compatibility

- All endpoints now at `/api/v1/*` prefix
- Authentication uses OAuth 2.0 + HttpOnly cookies (no localStorage tokens)
- SSE streaming for chat responses (same format as before)
- RFC 7807 Problem Detail error format

### Authentication Changes

- **Previous**: JWT in localStorage, passed via Authorization header
- **Current**: HttpOnly cookies with OAuth 2.0 flow
- **Migration**: Frontend updated in Phase 14 (AuthContext)

### Frontend Integration

The frontend (React) was updated in Phase 14-15 to use:
- AuthContext for cookie-based auth
- API service layer with Axios interceptors
- SSE service for streaming chat

## Architecture

### Request Flow

```
Frontend (React) → FastAPI Gateway → Services → Database/Cache/Vector Store
                    ↓
                Middleware Chain:
                1. RequestLoggingMiddleware
                2. CORSMiddleware
                3. AuthMiddleware (on protected routes)
                4. Error Handler → RFC 7807 response
```

### Service Layer

- `auth_service.py` - Authentication business logic
- `paper_service.py` - Paper CRUD operations
- `storage_service.py` - File storage abstraction
- `task_service.py` - Background task management

### Database Connections

- **PostgreSQL** - Primary data storage (SQLAlchemy async)
- **Redis** - Session storage, caching, rate limiting
- **Neo4j** - Knowledge graph, entity relationships
- **Milvus** - Vector embeddings for RAG

## Contributing

See project root README for contribution guidelines.

## License

MIT License - See LICENSE file for details.