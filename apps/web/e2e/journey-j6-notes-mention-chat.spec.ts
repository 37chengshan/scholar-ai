import { test } from '@playwright/test';

test.describe('J6: Notes -> @ Chat Session', () => {
  test('J6: notes mention chat session via @ trigger', async ({ page }) => {
    // Chat-Notes bridge API is not yet implemented.
    // Phase 5.0-6 closeout explicitly marked Chat-to-Notes bridge as out of scope.
    // Bridge verification (scripts/evals/verify_chat_notes_bridge.py) confirmed
    // no endpoints exist for POST /api/v1/sessions/:id/notes or
    // GET /api/v1/notes/:id/chat-sessions.
    //
    // This journey will be enabled once the bridge API is implemented.
    test.skip(true, 'Chat-Notes bridge API not implemented (j6_bridge_available=false)');
  });
});
