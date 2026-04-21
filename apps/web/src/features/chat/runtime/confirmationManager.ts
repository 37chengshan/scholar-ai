/**
 * Confirmation Manager — API calls for confirm/reject/retry/cancel.
 *
 * Per 战役 B WP7: confirmation/resume/retry/cancel are system-level capabilities.
 */

import { API_BASE_URL } from '@/config/api';

const BASE = `${API_BASE_URL}/api/v1/chat`;

async function postJSON(url: string, body: Record<string, unknown>): Promise<unknown> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export async function confirmAction(
  sessionId: string,
  confirmationId: string,
  approved: boolean,
  messageId?: string,
): Promise<Response> {
  // Confirmation returns an SSE stream, so return raw Response
  const res = await fetch(`${BASE}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      session_id: sessionId,
      confirmation_id: confirmationId,
      approved,
      message_id: messageId,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Confirmation failed: ${res.status} ${text}`);
  }
  return res;
}

export async function cancelRun(
  sessionId: string,
  runId?: string,
): Promise<void> {
  await postJSON(`${BASE}/cancel`, {
    session_id: sessionId,
    run_id: runId,
  });
}

export async function retryRun(
  sessionId: string,
  mode?: string,
  scope?: string,
): Promise<Response> {
  // Retry returns an SSE stream
  const res = await fetch(`${BASE}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      session_id: sessionId,
      mode,
      scope,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Retry failed: ${res.status} ${text}`);
  }
  return res;
}
