import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SearchKnowledgeBaseImportModal } from './SearchKnowledgeBaseImportModal';

vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

describe('SearchKnowledgeBaseImportModal', () => {
  it('requires stable selection before confirming import', () => {
    const onSelectKnowledgeBase = vi.fn();
    const onConfirmImport = vi.fn();

    render(
      <SearchKnowledgeBaseImportModal
        open={true}
        loadingKnowledgeBases={false}
        knowledgeBases={[
          { id: 'kb-1', name: 'KB One', paperCount: 2 },
          { id: 'kb-2', name: 'KB Two', paperCount: 5 },
        ]}
        selectedKnowledgeBaseId={null}
        importingPaperId={null}
        labels={{
          title: 'Choose KB',
          loading: 'Loading',
          empty: 'Empty',
          papersUnit: 'papers',
          confirm: 'Confirm import',
          selectPrompt: 'Select one',
        }}
        onClose={vi.fn()}
        onSelectKnowledgeBase={onSelectKnowledgeBase}
        onConfirmImport={onConfirmImport}
      />,
    );

    expect(screen.getByRole('button', { name: 'Confirm import' })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: /KB Two/i }));
    expect(onSelectKnowledgeBase).toHaveBeenCalledWith('kb-2');
    expect(onConfirmImport).not.toHaveBeenCalled();
  });
});
