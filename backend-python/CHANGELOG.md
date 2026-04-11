# ScholarAI Backend API Changelog

All notable changes to the backend API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Lazy initialization for AI services (Milvus, ReRanker, Embedding)
  - Services are now initialized on first use instead of at startup
  - Improves startup time significantly
- Production security validation
  - JWT_SECRET must not use development default in production
  - ALLOWED_HOSTS must not be '*' in production
  - Cookie secure flag auto-enabled in production
- Health check endpoints separation
  - `/health/live`: Kubernetes liveness probe (process alive check)
  - `/health/ready`: Kubernetes readiness probe (service ready check)
- Service layer architecture
  - `MessageService`: Message persistence and retrieval
  - `ChatOrchestrator`: Agent execution and SSE streaming
  - Clear separation between API, Service, and Infrastructure layers
- Legacy module namespace
  - Deprecated `rag_service.py` moved to `app/legacy/`
  - DeprecationWarning added for legacy imports
- API contract documentation
  - OpenAPI export script (`scripts/export_openapi.py`)
  - API contract specification (`docs/API_CONTRACT.md`)

### Changed
- **BREAKING**: Removed `placeholder-user-id` default in `agentic_retrieval.py`
  - `user_id` is now REQUIRED parameter
  - Raises ValueError if not provided
- Cookie settings now environment-aware
  - `secure=True` in production (HTTPS required)
  - `secure=False` in development (HTTP allowed)
- Message persistence moved from `chat.py` to `MessageService`
  - API layer no longer contains database logic
  - Better separation of concerns

### Deprecated
- `app.core.rag_service` module
  - Use `app.services.multimodal_search_service` instead
  - Moved to `app.legacy.rag_service_deprecated`

### Security
- Production environment now validates security settings at startup
  - Prevents deployment with dangerous defaults
  - Fails fast if insecure configuration detected

## [1.0.0] - 2024-01-15

### Added
- Initial unified FastAPI backend
- OAuth 2.0 + Cookie-based authentication
- Session management with PostgreSQL + Redis
- Chat with SSE streaming
- Paper CRUD operations
- PDF upload and processing
- RAG Q&A functionality
- Knowledge graph integration
- External search integration (Semantic Scholar)
- Dashboard statistics
- Notes, Projects, Annotations features
- Reading progress tracking