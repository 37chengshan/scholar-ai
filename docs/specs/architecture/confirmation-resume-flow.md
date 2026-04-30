# Confirmation / Resume / Retry Flow

## Overview

Agent 执行中的确认、恢复、重试机制。

## Confirmation Flow

```
Agent detects dangerous operation
    ↓
RunManager.request_confirmation()
    ↓
SSE: confirmation_required + recovery_available
    ↓
Frontend: ConfirmationDialog + RecoveryBanner
    ↓
User clicks Confirm/Reject
    ↓
POST /api/v1/chat/confirm { session_id, confirmation_id, approved }
    ↓
Backend resumes or cancels the Run
```

## Retry Flow

```
Run fails (agent_error or agent_complete with error)
    ↓
RunManager.fail() → SSE: recovery_available [retry, cancel]
    ↓
Frontend: RecoveryBanner with retry button
    ↓
User clicks Retry
    ↓
POST /api/v1/chat/retry { session_id }
    ↓
Backend re-sends last user message → new SSE stream
```

## Cancel Flow

```
User clicks Cancel (at any point during a run)
    ↓
POST /api/v1/chat/cancel { session_id, run_id }
    ↓
Backend: SSE disconnected, run marked cancelled
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/chat/confirm` | Approve/reject confirmation |
| POST | `/api/v1/chat/retry` | Retry last failed message |
| POST | `/api/v1/chat/cancel` | Cancel active run |

## Frontend Integration

```typescript
import { confirmAction, cancelRun, retryRun } from '@/features/chat/runtime';

// Confirm
await confirmAction(sessionId, confirmationId, true);

// Cancel
await cancelRun(sessionId, runId);

// Retry (returns SSE stream Response)
const res = await retryRun(sessionId);
```
