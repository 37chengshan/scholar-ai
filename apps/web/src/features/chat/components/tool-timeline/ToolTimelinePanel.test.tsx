import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ToolTimelinePanel } from './ToolTimelinePanel';

describe('ToolTimelinePanel', () => {
  it('renders tool call rows', () => {
    render(
      <ToolTimelinePanel
        visible={true}
        timeline={[
          {
            id: 't1',
            tool: 'search',
            label: 'Search Tool',
            status: 'running',
            startedAt: Date.now(),
          },
        ]}
      />
    );

    expect(screen.getByText(/search/i)).toBeInTheDocument();
  });
});
