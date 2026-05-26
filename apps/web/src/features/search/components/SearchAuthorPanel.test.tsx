import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SearchAuthorPanel } from './SearchAuthorPanel';

describe('SearchAuthorPanel', () => {
  it('passes s2PaperId when importing an author paper', () => {
    const onImportPaper = vi.fn();

    render(
      <SearchAuthorPanel
        open={true}
        selectedAuthor={{ authorId: 'author-1', name: 'Author One', paperCount: 1 } as any}
        authorPapers={[
          {
            paperId: 's2-paper-1',
            title: 'Paper One',
            year: 2024,
            citationCount: 10,
          } as any,
        ]}
        loadingAuthorPapers={false}
        labels={{
          searching: 'searching',
          importLabel: 'import',
          emptyText: 'empty',
          citations: 'citations',
        }}
        onClose={() => undefined}
        onImportPaper={onImportPaper}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'import' }));

    expect(onImportPaper).toHaveBeenCalledWith(
      expect.objectContaining({
        externalId: 's2-paper-1',
        s2PaperId: 's2-paper-1',
        source: 'semantic_scholar',
      })
    );
  });
});
