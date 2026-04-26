import { useEffect, useMemo, useState } from 'react';
import { DEFAULT_TEXT_FONT, TextLayoutFont } from './font';
import { measureText, TextMeasureResult } from './measure';

export function useFontsReady(): boolean {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof document === 'undefined' || !('fonts' in document)) {
      setReady(true);
      return;
    }

    const fontSet = (document as Document & { fonts: FontFaceSet }).fonts;
    fontSet.ready.then(() => setReady(true)).catch(() => setReady(true));
  }, []);

  return ready;
}

export function useElementWidth<T extends HTMLElement>(initialWidth = 640) {
  const [element, setElement] = useState<T | null>(null);
  const [width, setWidth] = useState(initialWidth);

  useEffect(() => {
    if (!element || typeof ResizeObserver === 'undefined') {
      return;
    }
    const obs = new ResizeObserver((entries) => {
      const next = entries[0]?.contentRect.width;
      if (next && next > 0) {
        setWidth(next);
      }
    });
    obs.observe(element);
    return () => obs.disconnect();
  }, [element]);

  return { width, setElement };
}

export function useTextMeasure(text: string, width: number, font: TextLayoutFont = DEFAULT_TEXT_FONT): TextMeasureResult {
  return useMemo(() => measureText({ text, width, font, whiteSpace: 'pre-wrap' }), [text, width, font]);
}
