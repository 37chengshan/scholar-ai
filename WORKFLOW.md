---
tracker:
  kind: linear
  api_key: $LINEAR_API_KEY
  project_slug: "scholar-ai"
  active_states:
    - Todo
    - In Progress
    - Merging
    - Rework
  terminal_states:
    - Closed
    - Cancelled
    - Canceled
    - Duplicate
    - Done
polling:
  interval_ms: 5000
workspace:
  root: $SYMPHONY_WORKSPACE_ROOT
hooks:
  after_create: |
    git clone git@github.com:37chengshan/scholar-ai.git .
  before_run: |
    git remote get-url origin >/dev/null
    git fetch --all --prune
  before_remove: |
    rm -rf test-results playwright-report coverage .pytest_cache .ruff_cache .mypy_cache .cache >/dev/null 2>&1 || true
agent:
  max_concurrent_agents: 1
  max_turns: 20
  max_retry_backoff_ms: 300000
codex:
  command: codex --config shell_environment_policy.inherit=all app-server
  approval_policy: never
  thread_sandbox: workspace-write
  turn_sandbox_policy:
    type: workspaceWrite
---

You are working on a Linear ticket `{{ issue.identifier }}` for the ScholarAI repository.

{% if attempt %}
Continuation context:

- This is retry attempt #{{ attempt }} because the ticket is still in an active state.
- Resume from the existing workspace instead of restarting from scratch.
- Do not repeat already-completed investigation or validation unless new code changes require it.
{% endif %}

Issue context:

- Identifier: `{{ issue.identifier }}`
- Title: `{{ issue.title }}`
- Current status: `{{ issue.state }}`
- Labels: `{{ issue.labels }}`
- URL: `{{ issue.url }}`

Description:
{% if issue.description %}
{{ issue.description }}
{% else %}
No description provided.
{% endif %}

## Operating posture

1. This is an unattended orchestration session. Do not ask a human to take follow-up actions unless you are blocked by missing required auth, permissions, or secrets.
2. Work only inside the provided repository copy. Do not edit files outside the workspace.
3. Follow the repository contract in `AGENTS.md`, `README.md`, `docs/specs/`, and `docs/plans/`.
4. If you need subagents:
   - frontend subagents must use `gpt5.4`
   - backend subagents must use `gpt5.3-codex`
   - clean them up when their work is done
5. Do not use `browser-use`. For browser-heavy inspection prefer MCP / Chrome DevTools MCP, with Computer Use only as a visual fallback.

## Related skills

- `linear`: Linear issue reads/writes and the single workpad comment.
- `pull`: sync the branch with the default `origin` base branch and record evidence.
- `commit`: create focused conventional commits.
- `push`: publish the branch, create or update the PR, and keep the PR labeled `symphony`.
- `land`: merge only when the issue is in `Merging`.
- `scholar-verify`: run ScholarAI's required validation matrix for the changed scope.

## Status map

- `Backlog` -> out of scope for this workflow; stop and wait.
- `Todo` -> move to `In Progress`, create or refresh the workpad, then execute.
- `In Progress` -> continue execution from the current workpad.
- `Human Review` -> do not code; wait for a human decision or new review feedback.
- `Merging` -> explicitly open and follow `.codex/skills/land/SKILL.md`.
- `Rework` -> close the old PR, remove the old workpad, create a fresh branch from the default `origin` base branch, and restart from execution kickoff.
- `Done` -> terminal; do nothing.

## Required Linear behavior

1. Use exactly one persistent Linear comment titled `## Codex Workpad`.
2. Reuse that comment for all progress, checklist, and handoff notes.
3. Keep the workpad structured like this:

````md
## Codex Workpad

```text
<hostname>:<abs-workdir>@<short-sha>
```

### Plan
- [ ] 1. Parent task
  - [ ] 1.1 Child task

### Acceptance Criteria
- [ ] Criterion

### Validation
- [ ] targeted tests: `<command>`

### Notes
- 2026-05-26 10:00 CST - note

### Confusions
- only include when something was unclear
````

4. Keep the workpad current after every meaningful milestone: reproduction, implementation, validation, PR update, review feedback resolution.
5. If a ticket description includes `Validation`, `Testing`, or `Test Plan`, mirror those requirements into the workpad as mandatory checklist items.

## Execution flow

### Kickoff

1. Read the current issue state and route through the status map.
2. For `Todo`, immediately move the issue to `In Progress` before implementation work.
3. Find or create the single `## Codex Workpad` comment.
4. Refresh the workpad so the plan, acceptance criteria, and validation reflect the actual scope.
5. Reproduce the current issue or capture the baseline behavior first; record concrete evidence in `### Notes`.
6. Run the `pull` skill before code edits and record:
   - merge source(s)
   - result (`clean` or `conflicts resolved`)
   - resulting HEAD short SHA

### Implementation

1. Keep changes minimal and scoped to the request.
2. Respect ScholarAI boundaries:
   - frontend changes only under `apps/web`
   - backend changes only under `apps/api`
   - workflow/orchestration changes only in approved root contract or repo automation locations
3. Update affected source-of-truth docs whenever interfaces, process, or governance rules change.
4. Use the `scholar-verify` skill to choose and run the required validation for the touched surfaces.
5. Before every push, ensure the latest validation for the changed scope is green.

### PR handling

1. If a PR is already attached to the issue, start with a full PR feedback sweep:
   - top-level PR comments
   - inline review comments
   - review summaries and states
2. Treat every actionable reviewer comment as blocking until addressed in code or answered with explicit, justified pushback.
3. Create or update the PR using `scripts/pr_create_with_template_check.sh`.
4. Keep the PR labeled `symphony`.
5. Attach the PR URL to the Linear issue rather than posting separate summary comments.

### Human Review handoff

Move to `Human Review` only when all of these are true:

- the workpad plan is complete and accurate
- required acceptance criteria are met
- required validation is green
- all actionable PR feedback is resolved
- PR checks are green
- PR is linked on the issue

While the issue is in `Human Review`, do not code or modify issue content beyond waiting/polling behavior.

### Rework

Treat `Rework` as a fresh attempt:

1. Re-read the issue and all review feedback.
2. Close the existing PR tied to the issue.
3. Remove the old `## Codex Workpad` comment.
4. Create a fresh branch from the default `origin` base branch.
5. Restart from kickoff with a new workpad and a new plan.

### Merging

When the issue is in `Merging`:

1. Open `.codex/skills/land/SKILL.md`.
2. Follow the `land` skill end-to-end.
3. Do not call `gh pr merge` directly outside that skill flow.
4. Move the issue to `Done` only after the merge completes.

## Validation floor

- Workflow, docs, governance, or root-contract changes:
  - `bash scripts/check-runtime-hygiene.sh tracked`
  - `bash scripts/check-doc-governance.sh`
  - `bash scripts/check-structure-boundaries.sh`
  - `bash scripts/check-code-boundaries.sh`
  - `bash scripts/check-governance.sh`
- Frontend changes:
  - `cd apps/web && npm run type-check`
  - run focused or full frontend tests as needed for the touched surface
- Backend changes:
  - `cd apps/api && .venv/bin/python -m pytest -q tests/unit/test_services.py --maxfail=1`
  - if import/chat contract surfaces changed, also run `cd apps/api && .venv/bin/python -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1`

## Guardrails

- Never create a second workpad comment.
- Never bypass `.github/pull_request_template.md`.
- Never bypass `scripts/pr_create_with_template_check.sh`.
- Never treat `Human Review` as an active coding state.
- Never leave root runtime artifacts in the repository.
- If blocked by missing required non-GitHub auth or permissions, record the blocker concisely in the workpad and stop only after exhausting documented fallbacks.
