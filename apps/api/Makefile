.PHONY: help db-migrate db-history db-check db-stamp db-reset db-diff db-diff-strict preflight preflight-strict

ENV ?= development

help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | awk -F: '{printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

db-migrate:    ## Run Alembic migrations
	alembic upgrade head

db-history:    ## Show migration history
	alembic history --verbose

db-check:      ## Check for pending migrations
	alembic check

db-stamp:      ## Stamp current DB as at head (after manual init)
	alembic stamp head

db-diff:       ## Run schema diff check (report only)
	@PYTHONPATH=. python scripts/schema_diff_check.py --report

db-diff-strict:  ## Run schema diff check (strict: fails on any diff)
	@PYTHONPATH=. python scripts/schema_diff_check.py --strict

db-reset:      ## Reset DB (⚠️ DEV ONLY - destroys all data)
ifneq ($(ENV),development)
	$(error db-reset is only allowed when ENV=development)
endif
	@echo "⚠️  Resetting database (ENV=development)..."
	alembic downgrade base && alembic upgrade head
	@echo "✅ DB reset complete"

preflight:     ## Run runtime preflight checks (report only)
	@PYTHONPATH=. python scripts/preflight_check.py

preflight-strict:  ## Run runtime preflight checks (fail on errors)
	@PYTHONPATH=. python scripts/preflight_check.py --strict
