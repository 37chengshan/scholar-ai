import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SearchResultsPanel } from './SearchResultsPanel';

vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

vi.mock('@/app/components/SearchResultCard', () => ({
  SearchResultCard: ({ result }: { result: { title: string } }) => (
    <div data-testid="search-card">{result.title}</div>
  ),
}));

vi.mock('@/app/components/AuthorResultCard', () => ({
  AuthorResultCard: ({ author }: { author: { name: string } }) => (
    <div data-testid="author-card">{author.name}</div>
  ),
}));

vi.mock('@/app/components/EmptyState', () => ({
  NoSearchResultsState: ({ query }: { query: string }) => (
    <div data-testid="no-results">No results for {query}</div>
  ),
}));

const labels = {
  searching: 'Searching...',
  startTyping: 'Start typing',
  authorResults: 'Authors',
  yourLibrary: 'Library',
  externalSources: 'External',
  authorMinChars: 'Enter at least 3 characters',
  externalDegraded: 'External sources degraded',
  emptyLibrary: 'No library results',
  emptyExternal: 'No external results',
  emptyAll: 'No results',
};

describe('SearchResultsPanel', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('shows loading placeholder first, then reveals initial loading state', () => {
    render(
      <SearchResultsPanel
        activeSource="all"
        query="agent"
        loading={true}
        isInitialLoading={true}
        isPageFetching={false}
        error={null}
        results={null}
        authorResults={[]}
        authorLoading={false}
        labels={labels}
        onViewPaper={vi.fn()}
        onAddToLibrary={vi.fn()}
        onContinueInChat={vi.fn()}
        onAuthorClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId('search-initial-loading-placeholder')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(screen.getByTestId('search-initial-loading')).toBeInTheDocument();
  });

  it('keeps current results visible and reveals page loading after delay', () => {
    render(
      <SearchResultsPanel
        activeSource="all"
        query="agent"
        loading={true}
        isInitialLoading={false}
        isPageFetching={true}
        error={null}
        results={{
          internal: [
            {
              id: 'internal-1',
              title: 'Internal one',
              source: 'internal',
            },
          ],
          external: [
            {
              id: 'external-1',
              title: 'External one',
              source: 'arxiv',
            },
          ],
          total: 40,
        }}
        authorResults={[]}
        authorLoading={false}
        labels={labels}
        onViewPaper={vi.fn()}
        onAddToLibrary={vi.fn()}
        onContinueInChat={vi.fn()}
        onAuthorClick={vi.fn()}
      />,
    );

    expect(screen.queryByTestId('search-page-loading')).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(screen.getByTestId('search-page-loading')).toBeInTheDocument();
    expect(screen.getAllByTestId('search-card')).toHaveLength(2);
  });
});
