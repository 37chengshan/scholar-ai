import { TextLayoutFont } from './font';
import { measureText } from './measure';

export interface ShrinkwrapResult {
  width: number;
  height: number;
}

export function computeBubbleShrinkwrap(text: string, maxWidth: number, font: TextLayoutFont, horizontalPadding = 24, verticalPadding = 18): ShrinkwrapResult {
  const measured = measureText({ text, width: maxWidth, font, whiteSpace: 'pre-wrap' });
  const width = Math.min(maxWidth, Math.max(140, measured.maxLineWidth + horizontalPadding));
  const height = measured.height + verticalPadding;
  return { width, height };
}
