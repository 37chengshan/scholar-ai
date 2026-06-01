import * as pretextRuntime from '@chenglou/pretext';
import { textMeasureCache } from './cache';
import { TextLayoutFont, toCanvasFont } from './font';

export type TextMeasureInput = {
  text: string;
  width: number;
  font: TextLayoutFont;
  whiteSpace?: 'normal' | 'pre-wrap';
  wordBreak?: 'normal' | 'keep-all';
};

export type TextMeasureResult = {
  height: number;
  lineCount: number;
  maxLineWidth: number;
};

function getContext(): CanvasRenderingContext2D | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const canvas = document.createElement('canvas');
  return canvas.getContext('2d');
}

function fallbackMeasure(input: TextMeasureInput): TextMeasureResult {
  const ctx = getContext();
  const width = Math.max(1, Math.floor(input.width));
  if (!ctx) {
    const charsPerLine = Math.max(8, Math.floor(width / Math.max(6, input.font.size * 0.55)));
    const lineCount = Math.max(1, Math.ceil((input.text || '').length / charsPerLine));
    return {
      lineCount,
      height: lineCount * input.font.lineHeight,
      maxLineWidth: width,
    };
  }

  ctx.font = toCanvasFont(input.font);
  const paragraphs = (input.text || '').split('\n');
  let lineCount = 0;
  let maxLineWidth = 0;

  paragraphs.forEach((paragraph) => {
    const words = paragraph.split(/\s+/).filter(Boolean);
    if (words.length === 0) {
      lineCount += 1;
      return;
    }

    let current = '';
    words.forEach((word) => {
      const candidate = current ? `${current} ${word}` : word;
      const candidateWidth = ctx.measureText(candidate).width;
      if (candidateWidth <= width || !current) {
        current = candidate;
        maxLineWidth = Math.max(maxLineWidth, candidateWidth);
        return;
      }
      lineCount += 1;
      maxLineWidth = Math.max(maxLineWidth, ctx.measureText(current).width);
      current = word;
    });

    if (current) {
      lineCount += 1;
      maxLineWidth = Math.max(maxLineWidth, ctx.measureText(current).width);
    }
  });

  return {
    lineCount: Math.max(1, lineCount),
    height: Math.max(1, lineCount) * input.font.lineHeight,
    maxLineWidth,
  };
}

function runPretext(input: TextMeasureInput): TextMeasureResult | null {
  const runtime = pretextRuntime as Record<string, unknown> | undefined;
  if (!runtime || typeof runtime.prepare !== 'function' || typeof runtime.layout !== 'function') {
    return null;
  }

  try {
    const prepared = runtime.prepare(input.text, toCanvasFont(input.font), {
      whiteSpace: input.whiteSpace || 'pre-wrap',
      wordBreak: input.wordBreak || 'normal',
      letterSpacing: input.font.letterSpacing || 0,
    });
    const laid = runtime.layout(prepared, input.width, input.font.lineHeight);
    return {
      lineCount: Math.max(1, laid.lineCount),
      height: Number(laid.height || laid.lineCount * input.font.lineHeight),
      maxLineWidth: input.width,
    };
  } catch {
    return null;
  }
}

export function measureText(input: TextMeasureInput): TextMeasureResult {
  const cacheKey = [
    input.text,
    Math.round(input.width),
    input.font.family,
    input.font.size,
    input.font.weight || '',
    input.font.style || '',
    input.font.lineHeight,
    input.font.letterSpacing || 0,
    input.whiteSpace || 'normal',
    input.wordBreak || 'normal',
  ].join('|');

  const cached = textMeasureCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const measured = runPretext(input) || fallbackMeasure(input);
  textMeasureCache.set(cacheKey, measured);
  return measured;
}
