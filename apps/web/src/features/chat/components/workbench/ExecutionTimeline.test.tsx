import { render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ExecutionTimeline } from './ExecutionTimeline';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ExecutionTimeline', () => {
  it('renders timeline items without duplicate key warning when ids are unique', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ExecutionTimeline
        items={[
          { id: 'tl-run-start-1', type: 'phase', label: 'Run started', timestamp: 1, status: 'running' },
          { id: 'tl-phase-2', type: 'phase', label: 'Analyzing', timestamp: 2, status: 'running' },
          { id: 'tl-step-step-1', type: 'step', label: 'Step 1', timestamp: 3, status: 'running' },
          { id: 'tl-done-4', type: 'done', label: 'Run completed', timestamp: 4, status: 'completed' },
        ]}
      />,
    );

    const duplicateKeyWarning = consoleErrorSpy.mock.calls.find((call) =>
      String(call[0]).includes('Encountered two children with the same key'),
    );

    expect(duplicateKeyWarning).toBeUndefined();
    expect(consoleErrorSpy).toBeDefined();
  });
});
