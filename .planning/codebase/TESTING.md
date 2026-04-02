# Testing Patterns

**Analysis Date:** 2026-04-02

## Overview

The ScholarAI codebase has comprehensive testing across both Node.js and Python backends:
- **backend-node/**: Jest-based E2E tests with Supertest
- **backend-python/**: pytest with async support, fixtures, and mocking

## Test Framework

### Node.js (backend-node)

**Runner:** Jest 30.x with ts-jest preset
- Config: `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/jest.config.js`
- TypeScript support via ts-jest
- Test environment: Node.js

**Assertion Library:** Jest built-in assertions

**Run Commands:**
```bash
cd backend-node
npm test                    # Run all tests
npm run test:watch         # Watch mode
npm run test:coverage      # Coverage report
```

### Python (backend-python)

**Runner:** pytest 7.x with asyncio support
- Config: `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/pytest.ini`
- Async mode: auto
- Verbose output with short traceback

**Assertion Library:** pytest built-in

**Run Commands:**
```bash
cd backend-python
pytest                      # Run all tests
pytest -v                  # Verbose
pytest tests/test_graph/   # Specific directory
pytest -k "test_extract"   # Test name pattern
```

## Test File Organization

### Node.js

**Location:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/tests/`

**Structure:**
```
tests/
├── e2e/                    # End-to-end API tests
│   ├── auth.e2e.test.ts   # Authentication flows
│   ├── papers.e2e.test.ts # Paper upload/processing
│   ├── rbac.e2e.test.ts   # Role-based access control
│   ├── errors.e2e.test.ts # Error handling
│   ├── health.e2e.test.ts # Health checks
│   ├── graph.e2e.test.ts  # Graph API
│   └── pdf-upload-workflow.e2e.test.ts
├── helpers/               # Test utilities
│   ├── auth.ts           # JWT token generation
│   ├── db.ts             # Database cleanup/fixtures
│   └── server.ts         # Test server setup
├── setup.ts              # Global test setup
└── setup-env.js          # Environment setup (pre-TS)
```

**Naming:**
- Files: `**/*.test.ts` or `**/*.spec.ts`
- Test suites: `describe('Feature Name', () => { ... })`
- Tests: `it('should do something', async () => { ... })`

### Python

**Location:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/tests/`

**Structure:**
```
tests/
├── conftest.py                    # Global fixtures
├── e2e/                          # End-to-end tests
│   ├── test_graph_e2e.py
│   ├── test_rag_citations.py
│   └── test_rag_streaming.py
├── test_graph/                   # Graph-specific tests
│   ├── conftest.py              # Graph test fixtures
│   ├── test_entity_extractor.py
│   ├── test_graph_api.py
│   ├── test_graph_builder.py
│   └── test_pagerank.py
├── test_*.py                     # Unit tests
└── fixtures/                     # Test data files
```

**Naming:**
- Files: `test_*.py` or `*_test.py`
- Classes: `Test*` (e.g., `TestEntityExtractor`)
- Functions: `test_*` (e.g., `test_extract_entities_success`)

## Test Structure

### Node.js E2E Pattern

```typescript
import request from 'supertest';
import app from '../../src/index';
import { generateTestUserData, cleanupTestData } from '../helpers/db';

describe('Authentication E2E Tests', () => {
  afterAll(async () => {
    await cleanupTestData();
  });

  describe('POST /api/auth/register', () => {
    it('should register a new user successfully', async () => {
      const testData = generateTestUserData();

      const response = await request(app)
        .post('/api/auth/register')
        .send(testData)
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toMatchObject({
        email: testData.email,
        name: testData.name,
      });
    });
  });
});
```

### Python Unit Test Pattern

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestEntityExtractor:
    @pytest.mark.asyncio
    async def test_extract_entities_success(
        self,
        sample_extraction_text,
        mock_litellm_entity_response
    ):
        from app.core.entity_extractor import EntityExtractor

        extractor = EntityExtractor(model="openai/qwen-plus")

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = mock_litellm_entity_response

            result = await extractor.extract(sample_extraction_text)

            assert "methods" in result
            assert len(result["methods"]) > 0
            mock.assert_called_once()
```

## Test Fixtures

### Node.js Helpers

**Database Helpers** (`/backend-node/tests/helpers/db.ts`):
```typescript
export function generateTestUserData() {
  const timestamp = Date.now();
  const randomId = Math.random().toString(36).substring(2, 8);
  return {
    email: `test-${timestamp}-${randomId}@example.com`,
    password: 'Test123!',
    name: `Test User ${randomId}`,
  };
}

export async function cleanupTestData(): Promise<void> {
  // Deletes test users, tokens, etc.
}
```

**Authentication Helpers** (`/backend-node/tests/helpers/auth.ts`):
```typescript
export function generateTestTokens(payload: TestTokenPayload): {
  accessToken: string;
  refreshToken: string;
} {
  return {
    accessToken: generateTestAccessToken(payload),
    refreshToken: generateTestRefreshToken(payload.userId),
  };
}

export const testUser: TestTokenPayload = {
  userId: 'test-user-id-123',
  email: 'test@example.com',
  role: 'user',
};
```

**Server Helpers** (`/backend-node/tests/helpers/server.ts`):
```typescript
export async function createAuthenticatedUser(role: 'user' | 'admin' = 'user') {
  const agent = createTestAgent();
  const testData = generateTestUserData();

  // Register and login
  await agent.post('/api/auth/register').send(testData).expect(201);
  await agent.post('/api/auth/login').send({ ... }).expect(200);

  return { agent, user: loginRes.body.data.user, email, password };
}
```

### Python Fixtures

**Global Fixtures** (`/backend-python/tests/conftest.py`):
```python
@pytest.fixture(scope="session")
def app() -> FastAPI:
    from app.main import app as fastapi_app
    return fastapi_app

@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_auth_headers(mock_internal_token: str) -> dict:
    return {
        "Authorization": f"Bearer {mock_internal_token}",
        "X-Internal-Service": "test-service",
    }
```

**Graph Test Fixtures** (`/backend-python/tests/test_graph/conftest.py`):
```python
@pytest.fixture
def sample_entities() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "methods": [{"name": "Transformer", "context": "...", "confidence": 0.95}],
        "datasets": [{"name": "ImageNet", "context": "...", "confidence": 0.95}],
        "metrics": [...],
        "venues": [...],
    }

@pytest.fixture
def mock_neo4j_driver():
    driver = AsyncMock()
    session = AsyncMock()
    # Configure context manager
    session_context = AsyncMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=False)
    driver.session = MagicMock(return_value=session_context)
    return driver, session
```

## Mocking

### Node.js

**Patterns:**
- Module-level mocking in Jest config
- Environment variable mocking in setup files
- No extensive mocking of external services (E2E focused)

**Environment Setup:**
```typescript
// tests/setup-env.js
process.env.OSS_ENDPOINT = process.env.OSS_ENDPOINT || 'local';
process.env.LOCAL_STORAGE_PATH = '...';
```

### Python

**Patterns:**
- `unittest.mock` for synchronous mocks
- `AsyncMock` for async functions
- `patch` decorator for module-level mocking
- Fixtures for reusable mocks

**Example:**
```python
@pytest.fixture
def mock_litellm():
    mock = AsyncMock()
    mock_response = {
        "choices": [{"message": {"content": "..."}}],
        "usage": {"total_tokens": 500}
    }
    mock.acompletion.return_value = mock_response
    return mock

# Usage in test
with patch("litellm.acompletion", new_callable=AsyncMock) as mock:
    mock.return_value = mock_litellm_entity_response
    result = await extractor.extract(text)
```

## Coverage

### Node.js

**Configuration:**
```javascript
// jest.config.js
collectCoverageFrom: [
  'src/**/*.ts',
  '!src/**/*.d.ts',
  '!src/index.ts',
],
coverageDirectory: 'coverage',
coverageReporters: ['text', 'lcov', 'html'],
```

**View Coverage:**
```bash
npm run test:coverage
# Opens HTML report in coverage/
```

### Python

**Configuration:**
- Not explicitly configured in pytest.ini
- Can add coverage via pytest-cov

**Run with coverage:**
```bash
pytest --cov=app --cov-report=html
```

## Test Types

### Node.js

**Unit Tests:** Limited - E2E tests dominate

**Integration/E2E Tests:** Comprehensive
- Authentication flows (register, login, logout, refresh)
- Paper upload and processing workflow
- RBAC and permissions
- Error handling (RFC 7807 format)
- Health checks
- Graph API endpoints

**Test Categories:**
- Authentication E2E: `/backend-node/tests/e2e/auth.e2e.test.ts`
- Papers API: `/backend-node/tests/e2e/papers.e2e.test.ts`
- RBAC: `/backend-node/tests/e2e/rbac.e2e.test.ts`
- Errors: `/backend-node/tests/e2e/errors.e2e.test.ts`
- Graph: `/backend-node/tests/e2e/graph.e2e.test.ts`

### Python

**Unit Tests:**
- Entity extraction (`test_graph/test_entity_extractor.py`)
- Graph building (`test_graph/test_graph_builder.py`)
- PageRank calculation (`test_graph/test_pagerank.py`)
- PDF parsing (`test_parse.py`)
- RAG service (`test_rag.py`)

**Integration/E2E Tests:**
- Graph API endpoints (`e2e/test_graph_e2e.py`)
- RAG citations (`e2e/test_rag_citations.py`)
- RAG streaming (`e2e/test_rag_streaming.py`)

## Common Patterns

### Async Testing (Node.js)

```typescript
it('should complete async operation', async () => {
  const result = await someAsyncFunction();
  expect(result).toBeDefined();
});
```

### Async Testing (Python)

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

### Error Testing (Node.js)

```typescript
it('should return 401 for invalid credentials', async () => {
  const response = await request(app)
    .post('/api/auth/login')
    .send({ email: 'wrong', password: 'wrong' })
    .expect(401);

  expect(response.body.success).toBe(false);
  expect(response.body.error.type).toBe('/errors/invalid-credentials');
});
```

### Error Testing (Python)

```python
async def test_invalid_credentials():
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user("wrong", "wrong")
    assert exc_info.value.status_code == 401
```

### Database Cleanup Pattern (Node.js)

```typescript
describe('Feature Tests', () => {
  afterAll(async () => {
    await cleanupTestData();
  });

  it('test case', async () => {
    // Test logic
  });
});
```

### Fixture Usage (Python)

```python
@pytest.fixture
def sample_data():
    return {"key": "value"}

async def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

## Test Data Management

### Node.js

- **Unique test data**: `generateTestUserData()` creates unique emails
- **Cleanup**: `cleanupTestData()` removes test users after suite
- **Agent pattern**: Use `request.agent(app)` for cookie persistence

### Python

- **Fixtures**: Extensive use of pytest fixtures for test data
- **Mock data**: Mock responses for external APIs (LiteLLM, Neo4j)
- **Session-scoped fixtures**: Database connections, app instances

## Setup and Teardown

### Node.js Global Setup

```typescript
// tests/setup.ts
process.env.NODE_ENV = 'test';
process.env.JWT_ACCESS_SECRET = 'test-access-secret';
process.env.JWT_REFRESH_SECRET = 'test-refresh-secret';

jest.setTimeout(10000);

afterAll(async () => {
  if (global.prisma) {
    await global.prisma.$disconnect();
  }
});
```

### Python Conftest

```python
# tests/conftest.py
import os
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_PUBLIC_KEY", "test-public-key")
```

## Best Practices

1. **Isolation**: Each test creates its own data; cleanup after suite
2. **Unique data**: Use timestamps/random strings to avoid conflicts
3. **Agent pattern**: Use Supertest agents for authenticated sessions
4. **Mock external services**: LiteLLM, Neo4j mocked in unit tests
5. **E2E for critical paths**: Full API flows tested end-to-end
6. **Structured assertions**: Assert on response structure, not just status

---

*Testing analysis: 2026-04-02*
