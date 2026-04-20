import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AISummaryPanel } from './AISummaryPanel';
import { LanguageContext } from '../contexts/LanguageContext';

describe('AISummaryPanel', () => {
  it('renders markdown content instead of plain text block', () => {
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
});
