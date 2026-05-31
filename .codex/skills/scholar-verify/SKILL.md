---
name: scholar-verify
description: Run ScholarAI's required validation matrix for Symphony-driven changes based on the touched surfaces.
---

# Scholar Verify Skill

Use this skill before every push and again before moving a ticket to `Human Review`.

## Scope selection

### Workflow / docs / governance / root automation changes

Run all of:

- `bash scripts/check-runtime-hygiene.sh tracked`
- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-structure-boundaries.sh`
- `bash scripts/check-code-boundaries.sh`
- `bash scripts/check-governance.sh`

Use this bucket when changes touch files such as:

- `WORKFLOW.md`
- `.codex/`
- `scripts/symphony/`
- `AGENTS.md`
- `README.md`
- `docs/specs/`
- other root workflow or governance files

### Frontend changes

Always run:

- `cd apps/web && npm run type-check`

Then run focused or full frontend tests that directly prove the touched behavior.

### Backend changes

Always run:

- `cd apps/api && .venv/bin/python -m pytest -q tests/unit/test_services.py --maxfail=1`

If import/chat contract surfaces changed, also run:

- `cd apps/api && .venv/bin/python -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1`

### Shared packages

If shared package code changes, build the affected package(s):

- `cd packages/types && npm run build`
- `cd packages/sdk && npm run build`

## Reporting

- Record every executed command in the workpad `Validation` section.
- Mark only commands that actually ran as complete.
- If a required check fails, fix it or keep the issue in execution state.
