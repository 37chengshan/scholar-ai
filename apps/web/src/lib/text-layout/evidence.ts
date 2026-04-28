import type { EvidenceBlockDto } from '@scholar-ai/types';
import { DEFAULT_TEXT_FONT } from './font';
import { measureText } from './measure';

export function measureEvidenceBlock(
  evidence: Pick<EvidenceBlockDto, 'paper_id' | 'section_path' | 'text'>,
  width: number,
): { height: number; lineCount: number } {
  const meta = [evidence.paper_id, evidence.section_path].filter(Boolean).join(' · ');
  const measured = measureText({
    text: [meta, evidence.text].filter(Boolean).join('\n'),
    width,
    font: DEFAULT_TEXT_FONT,
    whiteSpace: 'pre-wrap',
  });

  return {
    height: measured.height + 40,
    lineCount: measured.lineCount,
  };
}
