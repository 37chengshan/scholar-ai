import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { CitationPanel } from './CitationPanel';

const mockCitationsPanel = vi.fn();

vi.mock('@/app/components/CitationsPanel', () => ({
  CitationsPanel: (props: unknown) => {
    mockCitationsPanel(props);
    return <div data-testid="citations-panel-proxy" />;
  },
}));

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

    expect(screen.getByTestId('citations-panel-proxy')).toBeInTheDocument();
  });

  it('preserves canonical source navigation fields', () => {
    render(
      <MemoryRouter>
        <CitationPanel
          visible={true}
          citations={[
            {
              paper_id: 'paper-1',
              source_chunk_id: 'chunk-1',
              source_id: '466045819771397281',
              citation_jump_url: '/read/paper-1?page=3&source=chat&source_id=chunk-1',
              page_num: 3,
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

    expect(mockCitationsPanel).toHaveBeenCalledWith(
      expect.objectContaining({
        citations: [
          expect.objectContaining({
            source_chunk_id: 'chunk-1',
            source_id: 'chunk-1',
            citation_jump_url: '/read/paper-1?page=3&source=chat&source_id=chunk-1',
            chunk_id: '466045819771397281',
          }),
        ],
      }),
    );
  });
});
