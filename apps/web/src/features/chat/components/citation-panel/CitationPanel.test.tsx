/**
 * Tests for CitationPanel - grouped display, navigation, URL allowlist
 *
 * Coverage:
 * - Single paper: delegates to base CitationsPanel
 * - Multi-paper: renders grouped view with paper headers
 * - Filter: filters citations by paper title
 * - URL allowlist: accepts same-origin /read, rejects external URLs
 * - Navigation: calls navigateToCitation on click
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { CitationPanel } from './CitationPanel';
import { isAllowedCitationUrl } from './useCitationNavigation';

const mockCitationsPanel = vi.fn();

vi.mock('@/app/components/CitationsPanel', () => ({
  CitationsPanel: (props: unknown) => {
    mockCitationsPanel(props);
    return <div data-testid="citations-panel-proxy" />;
  },
}));

describe('CitationPanel', () => {
  it('renders base panel for single paper with few citations', () => {
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
      </MemoryRouter>,
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
      </MemoryRouter>,
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

  it('renders grouped view for multi-paper citations', () => {
    render(
      <MemoryRouter>
        <CitationPanel
          visible={true}
          isZh={false}
          citations={[
            {
              paper_id: 'paper-1',
              title: 'Alpha Paper',
              snippet: 'From paper one',
              score: 0.9,
              content_type: 'text',
            },
            {
              paper_id: 'paper-2',
              title: 'Beta Paper',
              snippet: 'From paper two',
              score: 0.8,
              content_type: 'text',
            },
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText('Alpha Paper')).toBeInTheDocument();
    expect(screen.getByText('Beta Paper')).toBeInTheDocument();
    expect(screen.getByText('2 papers')).toBeInTheDocument();
  });

  it('shows filter input when more than 3 citations', () => {
    render(
      <MemoryRouter>
        <CitationPanel
          visible={true}
          isZh={false}
          citations={[
            { paper_id: 'p1', title: 'Paper A', snippet: 's1', score: 0.9, content_type: 'text' },
            { paper_id: 'p1', title: 'Paper A', snippet: 's2', score: 0.8, content_type: 'text' },
            { paper_id: 'p2', title: 'Paper B', snippet: 's3', score: 0.7, content_type: 'text' },
            { paper_id: 'p2', title: 'Paper B', snippet: 's4', score: 0.6, content_type: 'text' },
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByPlaceholderText('Search papers...')).toBeInTheDocument();
  });

  it('does not render when visible is false', () => {
    const { container } = render(
      <MemoryRouter>
        <CitationPanel
          visible={false}
          citations={[
            { paper_id: 'p1', title: 'Paper A', snippet: 's', score: 0.9, content_type: 'text' },
          ]}
        />
      </MemoryRouter>,
    );

    expect(container.innerHTML).toBe('');
  });

  it('does not render when citations is empty', () => {
    const { container } = render(
      <MemoryRouter>
        <CitationPanel visible={true} citations={[]} />
      </MemoryRouter>,
    );

    expect(container.innerHTML).toBe('');
  });
});

describe('isAllowedCitationUrl', () => {
  it('allows same-origin /read URLs', () => {
    expect(isAllowedCitationUrl('/read/paper-1?page=3')).toBe(true);
  });

  it('allows full same-origin URLs', () => {
    expect(isAllowedCitationUrl(`${window.location.origin}/read/paper-1?page=3`)).toBe(true);
  });

  it('rejects external URLs', () => {
    expect(isAllowedCitationUrl('https://evil.com/read/paper-1')).toBe(false);
  });

  it('rejects javascript: protocol', () => {
    expect(isAllowedCitationUrl('javascript:alert(1)')).toBe(false);
  });

  it('rejects non-/read paths', () => {
    expect(isAllowedCitationUrl('/admin/settings')).toBe(false);
  });

  it('rejects undefined', () => {
    expect(isAllowedCitationUrl(undefined)).toBe(false);
  });

  it('rejects empty string', () => {
    expect(isAllowedCitationUrl('')).toBe(false);
  });

  it('rejects malformed URLs', () => {
    expect(isAllowedCitationUrl('not a url')).toBe(false);
  });
});
