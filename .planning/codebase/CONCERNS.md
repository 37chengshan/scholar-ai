# Codebase Concerns

**Analysis Date:** 2026-04-02

## Tech Debt

### Placeholder/Mock Implementations

**RAG Query System (Python):**
- Issue: Core RAG functionality returns mock responses instead of actual PaperQA2 integration
- Files:
  - `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/api/rag.py` (line 128-143)
  - `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/streaming.py` (line 357-366)
- Impact: Users receive placeholder answers instead of AI-generated responses based on paper content
- Fix approach: Integrate actual PaperQA2 or similar RAG system, remove mock_answer generation

**RAG Service (Simplified):**
- Issue: RAGService.query() returns context preview instead of LLM-generated answer
- File: `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/rag_service.py` (lines 250-254)
- Impact: Poor user experience - users see raw chunk previews instead of synthesized answers
- Fix approach: Integrate with litellm for actual LLM-based answer generation

**Query Routes (Node):**
- Issue: All query endpoints return hardcoded placeholder responses
- File: `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/queries.ts` (lines 22, 44, 61)
- Impact: Query system non-functional from API perspective
- Fix approach: Wire to Python RAG service, implement actual data retrieval

**Search Suggestions:**
- Issue: Search suggestions endpoint returns empty array
- File: `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/search.ts` (line 204)
- Impact: No autocomplete functionality for search
- Fix approach: Implement suggestion logic based on user history/popular queries

**Citation Mapping:**
- Issue: Citation numbers not mapped to actual paper chunks
- File: `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/streaming.py` (line 265)
- Impact: Citations in responses lack proper source attribution
- Fix approach: Implement chunk-to-citation mapping in streaming handler

**IMRaD Extraction:**
- Issue: IMRaD extraction marked as TODO
- File: `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/docling_service.py` (line 273)
- Impact: Paper structure extraction may be incomplete
- Fix approach: Implement LLM-based section header analysis

**User Statistics:**
- Issue: User statistics endpoint not implemented
- File: `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/users.ts` (line 60)
- Impact: Dashboard cannot show user activity metrics
- Fix approach: Aggregate user paper/query data from database

### Architecture Concerns

**Dual Backend Complexity:**
- Issue: System split between Node.js (API gateway) and Python (AI services)
- Files: Entire `/backend-node/` and `/backend-python/` directories
- Impact: Increased operational complexity, potential latency in service calls, harder debugging
- Safe modification: Always check both services when modifying cross-cutting features
- Test coverage: E2E tests exist but may not cover all inter-service scenarios

**Async Pattern Inconsistency:**
- Issue: Python codebase uses both `async/await` and synchronous patterns
- Files: Multiple files in `/backend-python/app/`
- Impact: Potential blocking operations in async contexts
- Safe modification: Always use async database drivers, wrap sync calls in asyncio.to_thread

## Known Bugs

### Storage Deletion Error Handling

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/papers.ts` (lines 830-840)

- Issue: Storage deletion failure logged but not propagated to user
- Current behavior: Paper deleted from DB, but file may remain in object storage
- Impact: Orphaned files in storage, potential data leakage on multi-tenant systems
- Workaround: Manual storage cleanup scripts
- Fix: Move storage deletion before DB deletion or implement transaction rollback

### Token Blacklist Race Condition

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/middleware/auth.ts` (lines 54-76)

- Issue: Token blacklist check and token verification are separate operations
- Impact: Brief window where revoked tokens might be accepted (Redis latency)
- Fix: Combine operations or use Redis transactions

### Pagination Query Parameter Injection Risk

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/papers.ts` (lines 31-33)

- Issue: Query parameters parsed with `as string` type assertion
- Risk: Potential for unexpected input types if request crafted manually
- Fix: Use Zod validation for all query parameters consistently

## Security Considerations

### Local Storage Path Traversal

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/services/storage.ts` (lines 58-62)

- Risk: `storageKey` sanitization may be bypassed with encoded characters
- Current mitigation: Basic `replace` for `../` and `./`
- Recommendation: Use a whitelist approach or path normalization library

### Error Message Information Leakage

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/middleware/errorHandler.ts` (lines 101-107)

- Risk: Stack traces exposed in development mode via `_legacy` field
- Current mitigation: Only in NODE_ENV=development
- Recommendation: Remove legacy field entirely before production

### Hardcoded Model Names

**Files:**
- `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/agentic_retrieval.py` (lines 373, 468)
- `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/query_decomposer.py`

- Risk: Model names hardcoded (gpt-4o-mini, gpt-4o)
- Impact: Cannot switch models without code change; model deprecation breaks system
- Fix: Move to configuration files with environment overrides

### Internal Token Generation

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/utils/jwt.ts` (implied from usage in search.ts line 329)

- Risk: Internal service tokens may lack proper expiration or rotation
- Fix: Verify internal tokens have short expiration and are rotated regularly

## Performance Bottlenecks

### Database Query N+1 Risk

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/papers.ts` (lines 41-58)

- Pattern: Processing task joined with paper list query
- Risk: Could become N+1 if processingTask requires additional lookups
- Current: Mitigated by Prisma's join, but monitor with large datasets

### Vector Search Without Index Optimization

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/rag_service.py` (lines 71-81)

- Issue: PGVector cosine distance query may not use optimal indexes on large datasets
- Impact: Slow RAG responses with many paper chunks
- Fix: Ensure ivfflat or hnsw indexes created on embedding column

### No Query Result Caching

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/rag_service.py`

- Issue: Every RAG query recomputes embeddings and searches database
- Impact: Repeated identical queries cost unnecessary compute
- Fix: Cache embedding results and/or final answers with TTL

### Redis Connection Pool Exhaustion

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/config/redis.ts` (lines 13-20)

- Issue: Single Redis client instance with default connection pool
- Impact: Under high load, connections may be exhausted
- Fix: Monitor connection pool metrics, implement circuit breaker

## Fragile Areas

### Task Status Progress Mapping

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/papers.ts` (lines 354-363)

- Issue: Hardcoded progress percentages mapped to status strings
- Risk: If Python worker adds new statuses, mapping will be incomplete
- Safe modification: Share status/progress enum between Node and Python
- Test coverage: E2E tests cover this but new statuses won't be tested

### LLM Synthesis Fallback Chain

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/agentic_retrieval.py` (lines 479-489)

- Issue: Complex fallback if LLM synthesis fails
- Fragility: Multiple nested try/except blocks with different error types
- Safe modification: Add structured error logging, test each failure mode
- Test coverage: Unit tests exist but may not cover all failure paths

### External Paper Download Trigger

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/search.ts` (lines 326-352)

- Issue: Async processing triggered without transaction guarantees
- Fragility: Paper created in DB but processing may fail silently
- Safe modification: Implement webhook/queue-based retry for failed triggers

### Convergence Detection

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/agentic_retrieval.py` (lines 278-312)

- Issue: Dual-mode convergence check (simple + LLM) with different sensitivities
- Fragility: May converge too early or run unnecessary rounds
- Safe modification: Tune thresholds based on user feedback metrics

## Scaling Limits

### File Upload Size

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/papers.ts` (line 858)

- Current limit: 50MB for local uploads
- Limit: Large PDFs (high-res scanned) may exceed this
- Scaling path: Implement chunked upload or presigned URL for direct-to-storage

### Conversation History

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/streaming.py` (line 325)

- Current limit: 20 messages (10 exchanges) hardcoded
- Limit: Long research sessions may lose context
- Scaling path: Implement conversation summarization for older messages

### Sub-question Limit

**File:** `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/core/agentic_retrieval.py` (lines 532-534)

- Current limit: Max 7 sub-questions
- Limit: Complex queries may need more granular decomposition
- Scaling path: Make configurable per query type

## Dependencies at Risk

### LiteLLM Version Pinning

**Observation:** LiteLLM used throughout Python backend for LLM calls

- Risk: API changes in LiteLLM major versions
- Impact: All LLM-dependent features break
- Mitigation: Pin to specific version, test upgrades thoroughly

### Prisma Client Version Mismatch

**Risk:** Node.js and Python use different database clients
- Impact: Schema migrations may cause compatibility issues
- Mitigation: Share schema files, version lock both clients

### Redis Key Pattern Dependencies

**Files:**
- `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-node/src/routes/auth.ts`
- `/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python/app/utils/cache.py`

- Risk: Both services use Redis but key patterns may diverge
- Impact: Session/cache inconsistency
- Fix: Document and share key naming conventions

## Missing Critical Features

### Rate Limiting

- Issue: No rate limiting on public endpoints
- Impact: Vulnerable to abuse, excessive costs
- Files: All route files lack rate limiting middleware
- Priority: HIGH

### Request Timeout Configuration

- Issue: No explicit timeouts on external service calls
- Impact: Hanging requests if Python service is slow
- Files: `/backend-node/src/routes/*.ts` - all fetch calls
- Priority: HIGH

### Health Check for Python Service

- Issue: Node backend cannot detect Python service outages
- Impact: Users get 500 errors instead of graceful degradation
- Fix: Implement health checks with circuit breaker pattern

### PDF Processing Queue Monitoring

- Issue: No visibility into task queue depth or processing delays
- Impact: Cannot detect worker backlog or failures
- Files: `/backend-node/src/services/tasks.ts`
- Fix: Add queue metrics endpoint

## Test Coverage Gaps

### Python Service Error Handling

**Untested area:** Node.js routes' handling of Python service failures
- Files: `/backend-node/src/routes/search.ts`, `/backend-node/src/routes/papers.ts`
- What's not tested: Network timeouts, 5xx responses from Python
- Risk: Unhandled promise rejections, server crashes
- Priority: MEDIUM

### Token Blacklist Edge Cases

**Untested area:** Race conditions in token blacklisting
- Files: `/backend-node/src/middleware/auth.ts`
- What's not tested: Concurrent logout/login scenarios
- Risk: Security bypass
- Priority: HIGH

### Storage Service Failures

**Untested area:** Object storage unavailability
- Files: `/backend-node/src/services/storage.ts`
- What's not tested: S3/MinIO connection failures
- Risk: Upload failures not handled gracefully
- Priority: MEDIUM

### Large File Upload Handling

**Untested area:** Files near size limit, malformed PDFs
- Files: `/backend-node/src/routes/papers.ts`
- What's not tested: Edge cases in file validation
- Risk: Crashes or security issues
- Priority: MEDIUM

---

*Concerns audit: 2026-04-02*
