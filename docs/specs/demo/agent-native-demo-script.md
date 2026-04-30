# Agent-Native Demo Script

## Goal

Show that Chat is now a coherent agent-native product path, with Workflow Shell reflecting the same run state instead of a route-derived placeholder.

## Demo Flow

1. Log in and land on `/chat`.
2. Start a general conversation and point out the run header entering planning / executing.
3. Open the Workflow Shell and show that the active run id and status match the chat run.
4. Send a scoped run using a paper or KB context and show the scope banner and Workflow Shell stay aligned.
5. Trigger a confirmation-required path and show pending actions move the run into `waiting_for_user`.
6. Show evidence appearing in the right panel and corresponding artifacts in the Workflow Shell.
7. Stop the run and confirm the UI exits the running state cleanly.
8. Visit `/dashboard` to show compatibility redirect instead of the old dashboard surface.
9. Visit a contextual Notes entry from Read or Library to show Notes remains available without being a primary product surface.

## Talk Track

- Battle C did not invent a new runtime.
- Battle C made the existing runtime become the real source of truth on the main Chat path.
- Legacy Dashboard code was removed; Notes was intentionally kept as contextual capability only.