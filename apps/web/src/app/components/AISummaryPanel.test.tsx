import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import type { ReadingCardDoc } from '@/features/read/readingCard';
import { AISummaryPanel } from './AISummaryPanel';
import { LanguageContext } from '../contexts/LanguageContext';

const readingCardDoc: ReadingCardDoc = {
  research_question: {
    title: 'Research Question',
    content: 'How can section-aware extraction improve paper reading?',
    evidence_blocks: [
      {
        evidence_id: 'e-1',
        source_type: 'paper',
        paper_id: 'paper-1',
        source_chunk_id: 'chunk-1',
        page_num: 2,
        section_path: 'introduction',
        content_type: 'text',
        text: 'Question evidence',
        citation_jump_url: '/read/paper-1?page=2&source=evidence&source_id=chunk-1',
      },
    ],
  },
  method: { title: 'Method', content: 'A structured metadata filter pipeline.', evidence_blocks: [] },
  experiment: { title: 'Experiment', content: 'Single-paper QA with page filters.', evidence_blocks: [] },
  result: { title: 'Result', content: 'Users can jump from the card back to the PDF.', evidence_blocks: [] },
  conclusion: { title: 'Conclusion', content: 'Reading cards improve grounded workflows.', evidence_blocks: [] },
  limitation: { title: 'Limitation', content: 'Legacy papers still need backfill.', evidence_blocks: [] },
  key_evidence: [
    {
      label: 'Evidence 1',
      content: 'Users can save evidence to notes.',
      evidence_blocks: [
        {
          evidence_id: 'e-2',
          source_type: 'paper',
          paper_id: 'paper-1',
          source_chunk_id: 'chunk-2',
          page_num: 6,
          section_path: 'results',
          content_type: 'table',
          text: 'Key evidence',
          citation_jump_url: '/read/paper-1?page=6&source=evidence&source_id=chunk-2',
        },
      ],
    },
  ],
};

describe('AISummaryPanel', () => {
  it('renders structured reading card before legacy summary', () => {
    render(
      <LanguageContext.Provider value={{ language: 'zh', setLanguage: () => {} }}>
        <AISummaryPanel
          paperId="p1"
          summary={'# 旧摘要'}
          readingCardDoc={readingCardDoc}
        />
      </LanguageContext.Provider>,
    );

    expect(screen.getByText('Research Question')).toBeInTheDocument();
    expect(screen.getByText('How can section-aware extraction improve paper reading?')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '旧摘要' })).not.toBeInTheDocument();
  });

  it('falls back to markdown summary when reading card is missing', () => {
    render(
      <LanguageContext.Provider value={{ language: 'zh', setLanguage: () => {} }}>
        <AISummaryPanel
          paperId="p1"
          summary={'# 标题\n\n- 要点一\n- 要点二\n\n**加粗内容**'}
        />
      </LanguageContext.Provider>,
    );

    expect(screen.getByRole('heading', { name: '标题' })).toBeInTheDocument();
    expect(screen.getByText('要点一')).toBeInTheDocument();
    expect(screen.getByText('加粗内容')).toBeInTheDocument();
  });

  it('exposes jump and save actions for visible evidence', () => {
    const handleJump = vi.fn();
    const handleSave = vi.fn();

    render(
      <LanguageContext.Provider value={{ language: 'en', setLanguage: () => {} }}>
        <AISummaryPanel
          paperId="p1"
          readingCardDoc={readingCardDoc}
          onJumpCitation={handleJump}
          onSaveEvidence={handleSave}
        />
      </LanguageContext.Provider>,
    );

    fireEvent.click(screen.getByText('p.2'));
    fireEvent.click(screen.getAllByText('Save evidence')[0]);

    expect(handleJump).toHaveBeenCalledTimes(1);
    expect(handleSave).toHaveBeenCalledTimes(1);
    expect(handleSave.mock.calls[0][0]).toBe('How can section-aware extraction improve paper reading?');
  });

  it('saves key evidence with the visible statement instead of the label', () => {
    const handleSave = vi.fn();

    render(
      <LanguageContext.Provider value={{ language: 'en', setLanguage: () => {} }}>
        <AISummaryPanel
          paperId="p1"
          readingCardDoc={readingCardDoc}
          onSaveEvidence={handleSave}
        />
      </LanguageContext.Provider>,
    );

    fireEvent.click(screen.getAllByText('Save evidence')[1]);

    expect(handleSave).toHaveBeenCalledTimes(1);
    expect(handleSave.mock.calls[0][0]).toBe('Users can save evidence to notes.');
  });
});
