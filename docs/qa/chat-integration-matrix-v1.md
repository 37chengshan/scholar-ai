# Chat Integration Matrix v1

## Scope

Battle C WP1 focuses on validating that the current Chat product path and Workflow Shell share the same agent runtime truth on the main interaction path.

## Scenarios

| ID | Scenario | Scope | Expected Runtime Outcome | Expected UI Outcome | Status |
| --- | --- | --- | --- | --- | --- |
| CI-01 | Normal conversation | General | `run_start` → phase changes → `run_complete(completed)` | Chat header and Workflow Shell show same active run | Verified |
| CI-02 | Single paper scoped run | `paperId` | Active run scope is `single_paper` | Scope banner and Workflow Shell both show paper scope | Verified |
| CI-03 | Full KB scoped run | `kbId` | Active run scope is `full_kb` | Scope banner and Workflow Shell both show KB scope | Verified |
| CI-04 | Confirmation required | General / scoped | `confirmation_required` maps to `waiting_for_user` | Pending actions visible from shared runtime state | Verified |
| CI-05 | Recovery available after failure | General / scoped | `recovery_available` maps to pending actions and recoverable state | Workflow Shell recoverable panel reflects runtime state | Verified |
| CI-06 | Local stop / cancel fallback | General / scoped | Runtime reaches cancelled terminal state even if stream disconnects locally | Chat header no longer remains stuck in running state | Verified |
| CI-07 | Evidence stream | General / scoped | `evidence` accumulates on active run | Right panel and Workflow Shell artifacts reflect evidence | Verified |
| CI-08 | Artifact stream | General / scoped | `artifact` accumulates on active run | Workflow Shell artifacts drawer data uses runtime outputs | Verified |
| CI-09 | Non-chat route fallback | Search / Read / KB | No fake chat run injected | Workflow Shell keeps low-risk route fallback | Verified |
| CI-10 | Dashboard compatibility | `/dashboard` | No dashboard page runtime path remains | Route redirects to `/knowledge-bases` | Verified |
| CI-11 | Notes compatibility | `/notes` and contextual entry points | Notes remains contextual capability only | No top-level nav entry, contextual links remain intact | Verified |
| CI-12 | Session switch reset | Chat sessions | Runtime resets between sessions | Header / shell do not leak previous run state | Verified |

## Notes

- This matrix intentionally does not broaden scope into Search, Read, or Library runtime unification.
- Retry and resume remain bounded by current backend semantics and are tracked in the readiness and bug bash docs.