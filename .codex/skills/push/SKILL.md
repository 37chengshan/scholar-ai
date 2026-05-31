---
name: push
description: Push the current branch, create or update the ScholarAI PR, and keep the PR aligned with Symphony workflow requirements.
---

# Push Skill

Use this skill after the branch is validated and ready for review.

## Steps

1. Confirm the required validation for the changed scope is green.
2. Push the current branch to `origin`.
3. Create or update the PR using `scripts/pr_create_with_template_check.sh`.
4. Ensure the PR body fully satisfies `.github/pull_request_template.md`.
5. Add the `symphony` label if it is missing.
6. Attach the PR URL to the Linear issue and refresh the workpad.

## Guardrails

- Do not create a PR with `gh pr create` directly when the template-check script is available.
- Do not push if validation is currently failing.
- Do not move the issue to `Human Review` until PR feedback and checks are clean.
