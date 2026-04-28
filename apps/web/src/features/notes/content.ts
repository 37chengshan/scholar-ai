import type { EditorDocument } from './ownership';

export function isEditorDocument(value: unknown): value is EditorDocument {
  return Boolean(
    value
    && typeof value === 'object'
    && (value as { type?: unknown }).type === 'doc'
    && Array.isArray((value as { content?: unknown }).content),
  );
}

export function parseMaybeEditorDocument(value: unknown): EditorDocument | null {
  if (isEditorDocument(value)) {
    return value;
  }

  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return isEditorDocument(parsed) ? parsed : null;
    } catch {
      return null;
    }
  }

  return null;
}

export function textToEditorDocument(text: string): EditorDocument {
  return {
    type: 'doc',
    content: [
      {
        type: 'paragraph',
        content: text ? [{ type: 'text', text }] : [],
      },
    ],
  };
}

export function normalizeEditorDocument(value: unknown): EditorDocument {
  return parseMaybeEditorDocument(value) ?? textToEditorDocument(String(value ?? ''));
}

export function extractEditorPlainText(value: unknown, maxLength?: number): string {
  const doc = normalizeEditorDocument(value);
  const texts: string[] = [];

  const walk = (nodes: Array<Record<string, unknown>>) => {
    for (const node of nodes) {
      if (typeof node.text === 'string') {
        texts.push(node.text);
      }
      if (Array.isArray(node.content)) {
        walk(node.content as Array<Record<string, unknown>>);
      }
    }
  };

  walk(doc.content as Array<Record<string, unknown>>);

  const cleaned = texts
    .join(' ')
    .replace(/\[\[pdf:[^:]+:page:\d+\]\]/g, '')
    .trim();

  return maxLength && cleaned.length > maxLength
    ? `${cleaned.slice(0, maxLength)}...`
    : cleaned;
}