# Agent-Native Readiness Checklist

## Product Path

- [x] `/chat` is the authenticated default route.
- [x] Chat header reflects active run phase from Battle B runtime state.
- [x] Workflow Shell uses real Chat runtime state on `/chat`.
- [x] Scope banner and Workflow Shell describe the same paper / KB / global scope.

## Recovery And Controls

- [x] Confirmation-required state is visible through shared runtime state.
- [x] Recovery-available state is visible through shared runtime state.
- [x] Local cancel does not leave UI stuck in running state.
- [ ] Retry / resume semantics are fully run-aware end-to-end.

## Legacy Surface Cleanup

- [x] Dashboard remains compatibility-only via redirect.
- [x] Dead Dashboard implementation files removed.
- [x] Notes remains contextual, not primary navigation.

## Validation

- [x] Chat runtime reducer tests updated.
- [x] Workflow hydration tests added.
- [ ] Expanded Playwright critical-path coverage completed.
- [ ] Bug bash checklist executed and signed off.