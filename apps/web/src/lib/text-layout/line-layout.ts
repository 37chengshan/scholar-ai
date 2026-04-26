import { TextLayoutFont } from './font';
import { measureText } from './measure';

export interface LineLayoutResult {
  lineCount: number;
  lineHeight: number;
  totalHeight: number;
  maxLineWidth: number;
}

export function computeLineLayout(text: string, width: number, font: TextLayoutFont): LineLayoutResult {
  const measured = measureText({ text, width, font, whiteSpace: 'pre-wrap', wordBreak: 'normal' });
  return {
    lineCount: measured.lineCount,
    lineHeight: font.lineHeight,
    totalHeight: measured.height,
    maxLineWidth: measured.maxLineWidth,
  };
}
