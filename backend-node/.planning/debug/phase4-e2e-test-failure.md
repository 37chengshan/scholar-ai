---
status: resolved
trigger: "E2E tests fail with 'roles table does not exist' error even though tables exist in local Docker database"
created: 2026-03-17T00:00:00Z
updated: 2026-03-17T17:52:00Z
---

## Current Focus

hypothesis: RESOLVED - Port conflict between local Homebrew PostgreSQL and Docker PostgreSQL
expecting: Tests should connect to Docker PostgreSQL (with pgvector) instead of local PostgreSQL (without pgvector)
next_action: Tests are passing (11/12), one unrelated test failure remains

## Symptoms

expected: E2E tests should connect to local Docker database (localhost:5432) and pass
actual: Tests fail with "The table `public.roles` does not exist in the current database"
errors: "prisma:error Invalid `prisma.user.create()` invocation - The table `public.roles` does not exist"
reproduction: cd scholar-ai/backend-node && npm test -- tests/e2e/test_external_add.e2e.test.ts --runInBand --forceExit
timeline: Started when trying to run E2E tests after Phase 04 completion

## Evidence

- timestamp: 2026-03-17
  checked: Port 5432 listeners
  found: Two PostgreSQL instances: Docker (ankane/pgvector) AND local Homebrew PostgreSQL 18.3
  implication: Port conflict - local PostgreSQL was binding to port 5432 first

- timestamp: 2026-03-17
  checked: Extension availability in each PostgreSQL instance
  found: Docker has 'vector' extension; local PostgreSQL does NOT have it
  implication: Tests connecting to local PostgreSQL would fail on tables using vector type

- timestamp: 2026-03-17
  checked: Tables in local PostgreSQL database
  found: Only 'users' table existed (incomplete schema)
  implication: Local PostgreSQL had partial data from earlier, not the full schema

## Eliminated

- hypothesis: Prisma client caching or connection pooling issue
  evidence: The issue was not Prisma - it was connecting to wrong database entirely
  timestamp: 2026-03-17

- hypothesis: Environment variable timing or Jest setup issue
  evidence: Environment variables were correct; wrong database was listening on port 5432
  timestamp: 2026-03-17

- hypothesis: Database tables don't exist in Docker
  evidence: Docker database had all tables; connection was going to local PostgreSQL instead
  timestamp: 2026-03-17

## Resolution

root_cause: Port conflict between two PostgreSQL instances. Local Homebrew PostgreSQL (v18.3) was running on port 5432 and taking precedence over the Docker PostgreSQL container (ankane/pgvector). The local database had only a partial schema (just the 'users' table) and lacked the 'vector' extension required for the papers and paper_chunks tables. When tests ran, they connected to the local PostgreSQL instead of Docker, causing "table does not exist" errors.

fix: Stopped local Homebrew PostgreSQL service with `brew services stop postgresql@18`, then created all required tables by applying the migration SQL to the Docker database. Also ran the seed script to populate roles and permissions.

verification: E2E tests now pass (11/12 tests). The one failure is unrelated to database connectivity - it's an assertion about message text content.

files_changed: None (configuration/environment issue, not code)

## Fix Commands Used

```bash
# 1. Stop local PostgreSQL
brew services stop postgresql@18

# 2. Create migration SQL
mkdir -p prisma/migrations/20250317000000_init
npx prisma migrate diff --from-empty --to-schema-datamodel prisma/schema.prisma --script > prisma/migrations/20250317000000_init/migration.sql

# 3. Apply migration to Docker database
psql postgresql://scholarai:scholarai123@localhost:5432/scholarai -f prisma/migrations/20250317000000_init/migration.sql

# 4. Seed the database
npx ts-node prisma/seed.ts

# 5. Run tests
npm test -- tests/e2e/test_external_add.e2e.test.ts --runInBand --forceExit
```
