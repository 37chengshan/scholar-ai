import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { WorkspaceShell } from './WorkspaceShell';

function stubMatchMedia(matches: boolean) {
  const listeners = new Set<(event: MediaQueryListEvent) => void>();

  vi.stubGlobal('matchMedia', vi.fn().mockImplementation(() => ({
    matches,
    media: '(max-width: 767px)',
    onchange: null,
    addEventListener: (_: string, listener: (event: MediaQueryListEvent) => void) => {
      listeners.add(listener);
    },
    removeEventListener: (_: string, listener: (event: MediaQueryListEvent) => void) => {
      listeners.delete(listener);
    },
    dispatchEvent: vi.fn(),
  })));

  return listeners;
}

describe('WorkspaceShell', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('stacks panels on narrow screens', async () => {
    stubMatchMedia(true);

    const { container } = render(
      <WorkspaceShell
        layoutId="test"
        sidebar={<div>Sidebar</div>}
        main={<div>Main</div>}
        inspector={<div>Inspector</div>}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('Main')).toBeInTheDocument();
    });

    expect(container.querySelector('[data-panel-group]')).toBeNull();
    expect(screen.getByText('Sidebar')).toBeInTheDocument();
    expect(screen.getByText('Inspector')).toBeInTheDocument();
  });
});
