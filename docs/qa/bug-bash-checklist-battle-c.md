# Battle C Bug Bash Checklist

## Chat Core

- [ ] New conversation shows idle state before first run.
- [ ] Normal response transitions through planning / executing / completed.
- [ ] Session switch clears previous run header and workflow state.

## Scope

- [ ] `paperId` scope shows paper banner and paper workflow scope.
- [ ] `kbId` scope shows KB banner and KB workflow scope.
- [ ] Invalid scope shows error state without crashing chat.

## Controls

- [ ] Confirmation-required flow shows waiting state consistently in Chat and Workflow Shell.
- [ ] Local stop exits running state cleanly.
- [ ] Failed run exposes recoverable tasks in Workflow Shell.

## Evidence And Artifacts

- [ ] Evidence appears in Chat right panel during or after a run.
- [ ] Workflow Shell artifacts panel reflects evidence / artifacts from the same run.

## Legacy Surfaces

- [ ] `/dashboard` redirects to `/knowledge-bases`.
- [ ] Notes is reachable only through contextual flows that still depend on it.
- [ ] No primary navigation entry points reintroduce Dashboard or Notes.