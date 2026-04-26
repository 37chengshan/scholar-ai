export type TextLayoutFont = {
  family: string;
  size: number;
  weight?: number | string;
  style?: 'normal' | 'italic';
  lineHeight: number;
  letterSpacing?: number;
};

export function toCanvasFont(font: TextLayoutFont): string {
  const style = font.style === 'italic' ? 'italic ' : '';
  const weight = font.weight ? `${font.weight} ` : '';
  return `${style}${weight}${font.size}px ${font.family}`;
}

export const DEFAULT_TEXT_FONT: TextLayoutFont = {
  family: 'ui-sans-serif, system-ui, sans-serif',
  size: 14,
  lineHeight: 20,
  weight: 500,
};
