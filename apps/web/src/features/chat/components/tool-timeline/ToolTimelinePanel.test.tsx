import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ToolTimelinePanel } from './ToolTimelinePanel';

describe('ToolTimelinePanel', () => {
  it('renders collapsed summary before expanding tool rows', () => {
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

    expect(screen.getByText(/调用 1 个工具中/i)).toBeInTheDocument();
  });
});
