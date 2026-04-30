# Agent Runtime State Machine

## Overview

ScholarAI 的 Agent-Native Chat 使用确定性状态机管理 Run 生命周期。

## Phase Transitions

```
idle → planning → executing → verifying → completed
                          ↘ waiting_for_user ↗
                          ↘ failed
                          ↘ cancelled
```

### Valid Transitions

| From | To |
|------|----|
| idle | planning |
| planning | executing, failed, cancelled |
| executing | verifying, waiting_for_user, failed, cancelled |
| waiting_for_user | executing, cancelled |
| verifying | completed, failed |
| completed | _(terminal)_ |
| failed | _(terminal, but recoverable via retry)_ |
| cancelled | _(terminal)_ |

## Models

### Run
Top-level container. One Run per user message. Contains:
- `run_id`, `session_id`, `message_id`
- `phase` (current state machine phase)
- `steps[]` (ordered execution steps)
- `confirmation` (pending confirmation request)

### RunStep
A discrete unit of work within a Run:
- Types: `analyze`, `retrieve`, `read`, `tool_call`, `synthesize`, `verify`, `confirm`
- Status: `pending`, `running`, `completed`, `failed`, `skipped`, `waiting`

### ToolEvent
A tool invocation within a step:
- Types: `call`, `result`, `error`
- Links to `run_id` and `step_id`

### FinalSummary
Structured output at Run completion:
- `answer` — final text response
- `citations[]` — evidence sources
- `artifacts[]` — produced artifacts
- `answer_evidence_consistency` — quality score (0–1)
- `low_confidence_reasons[]` — transparency

## SSE Event Protocol

### New Events

| Event | Direction | Purpose |
|-------|-----------|---------|
| `run_start` | Server → Client | Run lifecycle begins |
| `run_phase_change` | Server → Client | Phase transition |
| `step_start` | Server → Client | Step begins |
| `step_complete` | Server → Client | Step ends |
| `run_complete` | Server → Client | Run ends with FinalSummary |
| `recovery_available` | Server → Client | Retry/cancel actions available |
| `evidence` | Server → Client | Evidence item collected |
| `artifact` | Server → Client | Artifact produced |

### Existing Events (unchanged)

`session_start`, `routing_decision`, `phase`, `reasoning`, `message`,
`tool_call`, `tool_result`, `citation`, `confirmation_required`, `done`,
`error`, `heartbeat`, `cancel`

## Frontend Architecture

```
SSE Stream
    ↓
sseEventAdapter (normalize)
    ↓
useChatStream (existing: buffers, reasoning, content)
    ↓                         ↓
chatStreamReducer      useRuntime.ingestEvent()
(legacy state)         (Run protocol events)
                              ↓
                        runReducer → AgentRun
                              ↓
                        Resolvers (pure functions)
                              ↓
                        Workbench Components
```
