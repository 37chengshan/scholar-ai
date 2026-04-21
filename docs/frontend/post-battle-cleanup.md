# Post-Battle Cleanup

## Completed In Battle C

- Chat and Workflow Shell now share the same active run source on the `/chat` route.
- Fake chat workflow hydration was removed from the Chat path.
- Dashboard historical implementation files were physically removed while preserving `/dashboard` compatibility redirect.
- Notes remains off the primary navigation path and continues to be entered from Read and Library context.

## Explicitly Deferred

- Notes page decomposition and data-model cleanup.
- Search / Read / Knowledge Base adoption of the same runtime source used by Chat.
- System-level retry and resume semantics beyond the current backend replay behavior.

## Boundary Decision

Battle C is a productization battle, not a new architecture battle. Cleanup therefore removed dead Dashboard code, but avoided opening a large Notes refactor that would expand scope beyond the approved work packages.