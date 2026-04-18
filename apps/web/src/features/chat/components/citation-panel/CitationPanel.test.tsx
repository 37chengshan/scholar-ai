import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router';
import { CitationPanel } from './CitationPanel';

describe('CitationPanel', () => {
  it('renders citation titles', () => {
    render(
      <MemoryRouter>
        <CitationPanel
          visible={true}
          citations={[
            {
              paper_id: 'paper-1',
              title: 'Paper One',
              authors: ['A'],
              year: 2024,
              snippet: 'Snippet',
              score: 0.9,
              content_type: 'text',
            },
          ]}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('Paper One')).toBeInTheDocument();
  });
});
