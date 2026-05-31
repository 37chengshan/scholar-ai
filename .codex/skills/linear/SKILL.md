---
name: linear
description: Maintain ScholarAI Symphony Linear issue state and the single Codex Workpad comment by using linear_graphql.
---

# Linear Skill

Use this skill whenever the workflow requires reading or writing Linear issue state.

## Required behavior

1. Use `linear_graphql` as the primary Linear interface.
2. Keep exactly one persistent issue comment titled `## Codex Workpad`.
3. Reuse that comment for all plan, validation, progress, blocker, and handoff updates.
4. Do not post separate summary comments when the workpad can be updated in place.

## State transitions

- `Todo` -> move to `In Progress` before implementation work starts.
- `In Progress` -> active execution.
- `Human Review` -> waiting only; do not code.
- `Merging` -> only after approval and green checks.
- `Rework` -> restart from a fresh branch and a fresh workpad.
- `Done` -> only after merge is complete.

## Workpad rules

- Header must be `## Codex Workpad`.
- Include the environment stamp code fence line: `<hostname>:<abs-workdir>@<short-sha>`.
- Keep `Plan`, `Acceptance Criteria`, `Validation`, and `Notes` current.
- Add `Confusions` only if something was genuinely unclear during execution.

## Minimum operations

- Query the issue by explicit ticket identifier or ID.
- Query existing comments and reuse the active workpad when present.
- Create the workpad only if no active `## Codex Workpad` comment exists.
- Update issue state only when the workflow bar for that state is met.
- Attach or update the PR URL on the issue once a PR exists.

## Blocking policy

- If required Linear access is missing, stop and report that blocker in the workpad.
- Do not silently continue without Linear writes once the workflow depends on them.
