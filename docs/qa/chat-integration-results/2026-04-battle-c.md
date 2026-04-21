# Battle C Chat Integration Results

## Summary

Battle C validated the product path where Chat is the primary authenticated landing flow and Workflow Shell mirrors the same active run state instead of a synthetic placeholder.

## Result Snapshot

| Area | Result | Evidence |
| --- | --- | --- |
| Chat runtime wiring | Pass | Chat consumes Battle B runtime events through `useRuntime` |
| Workflow Shell source of truth | Pass | `/chat` no longer hydrates `chat-active-run` placeholder |
| Scope consistency | Pass | Chat scope store and Workflow scope mapping are aligned |
| Evidence and artifacts visibility | Pass | Right panel and Workflow Shell derive from runtime evidence/artifacts |
| Dashboard cleanup | Pass | Dead dashboard page/hook/service/mock files removed; redirect preserved |
| Notes compatibility | Pass with constraint | Notes stays as contextual capability, not a primary navigation surface |

## Constraints Confirmed

- Search, Read, and Knowledge Base views still use low-risk fallback hydration outside Chat.
- Retry and resume remain limited by the current backend contract that replays the last user message.
- Notes was not re-architected in this battle.

## Follow-up Candidates

1. Promote retry and resume from compatibility behavior to a stricter run-aware control plane.
2. Extend shared runtime hydration beyond Chat once Battle C release readiness is complete.