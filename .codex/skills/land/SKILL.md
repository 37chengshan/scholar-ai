---
name: land
description: Merge a ScholarAI Symphony PR only after review approval and green checks, then complete the Linear ticket.
---

# Land Skill

Use this skill only when the Linear issue is already in `Merging`.

## Preconditions

- The PR is open.
- Required PR checks are green.
- There are no unresolved actionable review comments.
- Human approval is present.

## Steps

1. Inspect the PR state and current checks.
2. If checks or review state are not ready, stop and keep the issue out of `Done`.
3. Merge the PR using the repository's normal GitHub merge path.
4. Confirm the PR is actually merged.
5. Update the Linear issue to `Done`.

## Guardrails

- Do not merge from any other issue state.
- Do not mark the issue `Done` before the merge is confirmed.
- If new review changes are requested during this stage, move the issue back to `Rework`.
