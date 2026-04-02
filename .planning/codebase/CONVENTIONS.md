# Coding Conventions

**Analysis Date:** 2026-04-02

## Project Overview

ScholarAI (智读) is an AI paper reading assistant based on Agentic RAG. The codebase consists of two main services:
- **backend-node/**: Node.js/Express API gateway (auth, papers, tasks, orchestration)
- **backend-python/**: Python/FastAPI AI service (PDF parsing, RAG, entity extraction, graph)

## Naming Patterns

### TypeScript (backend-node)

**Files:**
- Routes: `[resource].ts` (e.g., `auth.ts`, `papers.ts`)
- Services: `[service].ts` (e.g., `storage.ts`, `tasks.ts`)
- Utilities: `[utility].ts` (e.g., `jwt.ts`, `crypto.ts`, `logger.ts`)
- Config: `[config].ts` (e.g., `database.ts`, `redis.ts`, `auth.ts`)
- Types: `[domain].ts` (e.g., `auth.ts` for auth types)

**Functions:**
- camelCase: `generateAccessToken()`, `hashPassword()`, `cleanupTestData()`
- Async functions use descriptive names: `cleanupTestData()`, `createAuthenticatedUser()`
- Utility creators: `createError()`, `Errors.unauthorized()`

**Variables/Constants:**
- UPPER_SNAKE for env-based constants: `JWT_ACCESS_SECRET`, `COOKIE_SETTINGS`
- camelCase for local variables
- Private/internal use underscore prefix: None observed

**Types/Interfaces:**
- PascalCase with descriptive names: `TokenPayload`, `AuthRequest`, `ProblemDetail`
- Interface suffix optional: `TaskStatusResponse` (interface-like type)
- Use `type` for unions: `TaskStatus = 'pending' | 'processing_ocr' | ...`

### Python (backend-python)

**Files:**
- Modules: `snake_case.py` (e.g., `entity_extractor.py`, `neo4j_service.py`)
- API routes: `[resource].py` (e.g., `papers.py`, `rag.py`, `entities.py`)
- Tests: `test_*.py` or `*_test.py`

**Functions:**
- snake_case: `extract_entities()`, `build_graph()`, `get_pagerank()`
- Async functions use `async def`: `async def extract(self, text: str)`

**Classes:**
- PascalCase: `EntityExtractor`, `Neo4jService`, `RAGService`

**Constants:**
- UPPER_SNAKE at module level: `EXTRACTION_PROMPT`, `ARGON2_OPTIONS`

## Code Style

### TypeScript

**Formatting:**
- ESLint configured (`backend-node/package.json` shows eslint script)
- Single quotes for strings
- Semicolons required
- 2-space indentation

**Key Style Rules:**
- Explicit return types on functions
- Strict TypeScript enabled (`strict: true` in `tsconfig.json`)
- No implicit any
- Force consistent casing in file names

**Import Organization:**
1. External dependencies first
2. Internal absolute imports (`../utils/logger`)
3. Same-directory relative imports

Example from `backend-node/src/index.ts`:
```typescript
import express, { RequestHandler } from 'express';
import cors from 'cors';
// ... external imports
import { errorHandler } from './middleware/errorHandler';
import { logger } from './utils/logger';
// ... internal imports
```

### Python

**Formatting:**
- Black for code formatting (in `requirements.txt`)
- isort for import sorting (in `requirements.txt`)
- Line length: 100 (inferred from sample files)

**Import Organization:**
1. Standard library
2. Third-party packages
3. Local app imports

Example from `backend-python/app/core/entity_extractor.py`:
```python
import os
from typing import Dict, List, Optional, Any

import litellm
import structlog

from app.core.neo4j_service import Neo4jService
```

## Error Handling

### TypeScript

**Pattern: RFC 7807 Problem Details**
- Consistent error format across all APIs
- Custom error types in `/backend-node/src/types/auth.ts`
- Error helper functions in `/backend-node/src/middleware/errorHandler.ts`

**Usage:**
```typescript
// Create error
throw Errors.validation('Invalid email format');

// Or manual error construction
res.status(400).json({
  success: false,
  error: {
    type: ErrorTypes.VALIDATION_ERROR,
    title: 'Validation Error',
    status: 400,
    detail: errors,
    instance: req.path,
    requestId: uuidv4(),
    timestamp: new Date().toISOString(),
  },
});
```

**Error Types:**
- `INVALID_CREDENTIALS`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `NOT_FOUND`
- `VALIDATION_ERROR`
- `CONFLICT`
- `INTERNAL_ERROR`
- `SERVICE_UNAVAILABLE`

**Error Response Structure:**
```typescript
interface ApiErrorResponse {
  success: false;
  error: ProblemDetail;  // RFC 7807 format
}
```

### Python

**Pattern: Try-catch with structured logging**
- Use `structlog` for structured logging
- Catch specific exceptions, log and re-raise

Example from `backend-python/app/core/tasks.py`:
```python
import structlog
logger = structlog.get_logger()

try:
    result = await some_operation()
except Exception as e:
    logger.error("Operation failed", error=str(e))
    raise RuntimeError("Failed to complete operation")
```

## Logging

**TypeScript (backend-node):**
- Framework: Winston
- Location: `/backend-node/src/utils/logger.ts`
- Format: JSON with colors in development
- Structured logging with metadata

```typescript
logger.info({
  message: 'User registered',
  userId: user.id,
  email: user.email,
});
```

**Python (backend-python):**
- Framework: structlog
- Location: `/backend-python/app/utils/logger.py`
- Structured JSON logging

```python
logger = structlog.get_logger()
logger.info("Service starting", service="ai-service", version="1.0.0")
logger.error("Operation failed", error=str(e), paper_id=paper_id)
```

## Comments

**When to Comment:**
- JSDoc/TSDoc for public APIs and complex functions
- Chinese comments allowed for project-specific context
- Section headers with `// ==========` for test organization

**Examples:**
```typescript
/**
 * Authentication middleware
 * Validates JWT access token from cookies or Authorization header
 * Checks Redis blacklist for revoked tokens
 */
export const authenticate = async (...) => { ... }
```

```typescript
// ===========================================================================
// Upload Flow Tests
// ===========================================================================
```

## Function Design

**Size:**
- Functions are generally focused (<50 lines typical)
- Route handlers extract validation logic
- Service functions are atomic

**Parameters:**
- Use destructuring for options objects
- Type annotations required
- Default values for optional parameters

Example:
```typescript
export const createError = (
  message: string,
  statusCode: number,
  code: string
): ApiError => { ... }
```

**Return Values:**
- Explicit return types
- Use union types for multiple return shapes
- Async functions return Promises

## Module Design

**Exports:**
- Named exports preferred
- Router exports: `export { router as authRouter };`
- Utility functions: `export function ...` or `export const ...`

**Barrel Files:**
- Not used; direct imports preferred

**Organization:**
```
src/
  routes/      # Express route handlers
  services/    # Business logic
  middleware/  # Express middleware
  utils/       # Helper functions
  config/      # Configuration
  types/       # TypeScript type definitions
```

## Validation

**TypeScript:**
- Zod for schema validation
- Validation schemas defined at top of route files
- Safe parse pattern:
```typescript
const result = registerSchema.safeParse(req.body);
if (!result.success) {
  const errors = result.error.errors.map((e) => e.message).join(', ');
  // ... handle error
}
```

**Python:**
- Pydantic v2 for data validation
- Type hints throughout

## Security Patterns

**Authentication:**
- JWT tokens with separate access/refresh tokens
- HS256 for access/refresh, RS256 for internal service tokens
- Token blacklisting via Redis
- Cookie-based auth with httpOnly, secure flags

**Password Hashing:**
- Argon2id with OWASP 2023 recommended parameters
- Constant-time comparison

**RBAC:**
- Permission-based access control (resource:action)
- Admin role bypass for all permissions
- Database-backed role/permission system

## API Response Format

**Success Response:**
```typescript
{
  success: true,
  data: T,
  meta: {
    requestId: string,
    timestamp: string,
    pagination?: { page, size, total, totalPages }
  }
}
```

**Error Response:**
```typescript
{
  success: false,
  error: {
    type: string,      // URI reference
    title: string,
    status: number,
    detail?: string,
    instance?: string,
    requestId: string,
    timestamp: string
  }
}
```

## Environment Configuration

**TypeScript:**
- dotenv for environment variables
- Validation at startup
- Defaults for development

**Python:**
- pydantic-settings for configuration
- Environment-based config in `app/core/config.py`

---

*Convention analysis: 2026-04-02*
