---
name: commit
description: Create focused conventional commits for ScholarAI Symphony runs.
---

# Commit Skill

Use this skill when the working tree is ready to be captured in a logical commit.

## Rules

1. Use conventional commit prefixes such as `feat`, `fix`, `docs`, `test`, or `chore`.
2. Keep one commit focused on one purpose.
3. Do not mix unrelated docs, runtime, or cleanup changes into the same commit.
4. Do not commit generated runtime artifacts, logs, PID files, or local caches.
5. Commit only after the required validation for the changed scope is green.

## Commit message shape

- `feat(scope): summary`
- `fix(scope): summary`
- `docs(scope): summary`
- `chore(scope): summary`

## Before committing

- Confirm the workpad reflects completed work.
- Confirm the working tree contains only intended files.
