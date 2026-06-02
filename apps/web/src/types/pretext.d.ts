/**
 * Type declarations for @chenglou/pretext
 *
 * Matches the actual API exported from layout.d.ts.
 */

declare module '@chenglou/pretext' {
  type WhiteSpaceMode = 'normal' | 'pre' | 'pre-wrap' | 'pre-line';
  type WordBreakMode = 'normal' | 'break-all' | 'keep-all';

  type PrepareOptions = {
    whiteSpace?: WhiteSpaceMode;
    wordBreak?: WordBreakMode;
    letterSpacing?: number;
  };

  type PreparedText = {
    readonly __brand: true;
  };

  type LayoutResult = {
    lineCount: number;
    height: number;
  };

  type PreparedTextWithSegments = PreparedText & {
    segments: string[];
  };

  type LayoutCursor = {
    segmentIndex: number;
    graphemeIndex: number;
  };

  type LayoutLine = {
    text: string;
    width: number;
    start: LayoutCursor;
    end: LayoutCursor;
  };

  type LayoutLineRange = {
    width: number;
    start: LayoutCursor;
    end: LayoutCursor;
  };

  type LayoutLinesResult = LayoutResult & {
    lines: LayoutLine[];
  };

  type LineStats = {
    lineCount: number;
    maxLineWidth: number;
  };

  export function prepare(
    text: string,
    font: string,
    options?: PrepareOptions,
  ): PreparedText;

  export function prepareWithSegments(
    text: string,
    font: string,
    options?: PrepareOptions,
  ): PreparedTextWithSegments;

  export function layout(
    prepared: PreparedText,
    maxWidth: number,
    lineHeight: number,
  ): LayoutResult;

  export function layoutWithLines(
    prepared: PreparedTextWithSegments,
    maxWidth: number,
    lineHeight: number,
  ): LayoutLinesResult;

  export function materializeLineRange(
    prepared: PreparedTextWithSegments,
    line: LayoutLineRange,
  ): LayoutLine;

  export function walkLineRanges(
    prepared: PreparedTextWithSegments,
    maxWidth: number,
    onLine: (line: LayoutLineRange) => void,
  ): number;

  export function measureLineStats(
    prepared: PreparedTextWithSegments,
    maxWidth: number,
  ): LineStats;

  export function measureNaturalWidth(
    prepared: PreparedTextWithSegments,
  ): number;

  export function layoutNextLine(
    prepared: PreparedTextWithSegments,
    start: LayoutCursor,
    maxWidth: number,
  ): LayoutLine | null;

  export function layoutNextLineRange(
    prepared: PreparedTextWithSegments,
    start: LayoutCursor,
    maxWidth: number,
  ): LayoutLineRange | null;

  export function clearCache(): void;

  export function setLocale(locale?: string): void;
}
