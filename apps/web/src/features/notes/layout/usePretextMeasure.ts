/**
 * usePretextMeasure - Hook for pretext-based text measurement
 *
 * Provides text height measurement without DOM reflow using the pretext library.
 * Debounces re-measurement on resize (250ms).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { prepare, layout, type PreparedText } from '@chenglou/pretext';

interface UsePretextMeasureOptions {
  text: string;
  width: number;
  lineHeight?: number;
  fontSize?: string;
  fontFamily?: string;
}

interface UsePretextMeasureReturn {
  height: number;
  lineCount: number;
  prepared: PreparedText | null;
}

export function usePretextMeasure({
  text,
  width,
  lineHeight = 24,
  fontSize = '15px',
  fontFamily = 'Inter, system-ui, sans-serif',
}: UsePretextMeasureOptions): UsePretextMeasureReturn {
  const [measureResult, setMeasureResult] = useState({ height: 0, lineCount: 0 });
  const preparedRef = useRef<PreparedText | null>(null);
  const lastTextRef = useRef<string>('');
  const lastFontRef = useRef<string>('');

  const fontString = `${fontSize} ${fontFamily}`;

  // Prepare text (cached - only re-run when text or font changes)
  const prepared = useMemo(() => {
    if (!text || width <= 0) return null;

    const textChanged = text !== lastTextRef.current;
    const fontChanged = fontString !== lastFontRef.current;

    if (textChanged || fontChanged || !preparedRef.current) {
      preparedRef.current = prepare(text, fontString);
      lastTextRef.current = text;
      lastFontRef.current = fontString;
    }

    return preparedRef.current;
  }, [text, fontString, width]);

  // Layout (cheap - pure arithmetic)
  const recalculate = useCallback(() => {
    if (!prepared || width <= 0) {
      setMeasureResult({ height: 0, lineCount: 0 });
      return;
    }

    const result = layout(prepared, width, lineHeight);
    setMeasureResult({ height: result.height, lineCount: result.lineCount });
  }, [prepared, width, lineHeight]);

  useEffect(() => {
    recalculate();
  }, [recalculate]);

  // Debounced resize handler
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;

    const handleResize = () => {
      clearTimeout(timer);
      timer = setTimeout(recalculate, 250);
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(timer);
    };
  }, [recalculate]);

  return {
    height: measureResult.height,
    lineCount: measureResult.lineCount,
    prepared,
  };
}
