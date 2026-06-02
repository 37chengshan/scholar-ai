---
name: pull
description: Sync the current issue branch with ScholarAI's default origin base branch and record evidence in the workpad.
---

# Pull Skill

Use this skill before any code edits and again before final handoff if the branch has drifted.

## Steps

1. Fetch `origin` with pruning.
2. Resolve the default base branch from `origin/HEAD`.
3. Merge the latest `origin/<base>` into the current branch.
4. Resolve conflicts immediately if they occur.
5. Record the result in the Linear workpad `Notes` section:
   - merge source
   - `clean` or `conflicts resolved`
   - resulting HEAD short SHA

## Guardrails

- Do not guess the default base branch.
- Do not leave the branch in a conflicted state.
- Do not proceed to implementation if the merge is unresolved.
