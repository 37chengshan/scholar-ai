import { describe, expect, it } from 'vitest';

import {
  deriveReadableSummaryPreview,
  deriveReadableTitleFromText,
  isPlaceholderDisplayTitle,
  sanitizeNoteBodyPreview,
  sanitizeSearchSnippet,
} from './content';

describe('notes content helpers', () => {
  it('treats untitled paper fallback as placeholder', () => {
    expect(isPlaceholderDisplayTitle('未命名论文')).toBe(true);
  });

  it('derives a readable title from summary content when fallback is placeholder', () => {
    const summary = `
1. Research Question & Motivation
Problem Addressed: The paper focuses on demonstrating techniques for PDF parsing and parallel extraction.
`;

    expect(deriveReadableTitleFromText(summary, '未命名论文')).toBe(
      'The paper focuses on demonstrating techniques for PDF parsing and parall...',
    );
  });

  it('derives preview text without leaking section-heading boilerplate', () => {
    const summary = `
1. Research Question & Motivation
Problem Addressed: Existing large language models rely on expensive alignment corpora.
2. Method
The paper trains with 1,000 curated examples.
`;

    expect(deriveReadableSummaryPreview(summary)).toBe(
      'Existing large language models rely on expensive alignment corpora.',
    );
  });

  it('falls back when historical summary content is truncated at a heading prefix', () => {
    const summary = `
## 1. Research Question & Motivation
- **Problem Address
`;

    expect(deriveReadableSummaryPreview(summary)).toBe('系统摘要');
  });

  it('treats summary-style sentence titles as placeholders', () => {
    expect(
      isPlaceholderDisplayTitle('The paper focuses on demonstrating techniques for PDF parsing and parallel extraction.'),
    ).toBe(true);
  });

  it('shortens overly verbose summary previews for notes cards', () => {
    const summary = `
Problem Addressed: Existing large language models rely on expensive alignment corpora and large instruction tuning datasets, making iteration slow and costly for research teams.
`;

    expect(deriveReadableSummaryPreview(summary)).toBe(
      'Existing large language models rely on expensive alignment corpora and large instruction...',
    );
  });

  it('strips evidence snapshot scaffolding from note previews', () => {
    const snapshot = `
Claim: 当前阅读证据
Paper: paper-1
Page: 3
Section: introduction

[Paper: LIMA]
[Section: introduction]
[Page:3]
Current reading evidence
LIMA uses a small, high-quality alignment set.
`;

    expect(sanitizeNoteBodyPreview(snapshot)).toBe(
      'LIMA uses a small, high-quality alignment set.',
    );
  });

  it('strips inline bracket metadata prefixes from legacy evidence text', () => {
    expect(
      sanitizeNoteBodyPreview("[Methods:LIMA,Less,More | Datasets:LIMA,GLYPH] LIMA uses a small, high-quality alignment set."),
    ).toBe('LIMA uses a small, high-quality alignment set.');
  });

  it('strips glyph placeholders from search snippets', () => {
    expect(
      sanitizeSearchSnippet("[Paper: LIMA] GLYPH<22> LIMA uses GLYPH<25> a small alignment set."),
    ).toBe('LIMA uses a small alignment set.');
  });
});
