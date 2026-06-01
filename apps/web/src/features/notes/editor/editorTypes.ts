/**
 * Editor Types for ScholarAI Rich Text Editor
 *
 * Defines block types, editor props, and content document types
 * for the TipTap-based rich text editor.
 */

/** Supported block types in the editor */
export enum EditorBlockType {
  Paragraph = 'paragraph',
  Heading1 = 'heading1',
  Heading2 = 'heading2',
  Heading3 = 'heading3',
  CodeBlock = 'codeBlock',
  Blockquote = 'blockquote',
  Callout = 'callout',
  BulletList = 'bulletList',
  OrderedList = 'orderedList',
}

/** Block type labels for toolbar display */
export const BLOCK_TYPE_LABELS: Record<EditorBlockType, string> = {
  [EditorBlockType.Paragraph]: '正文',
  [EditorBlockType.Heading1]: '标题 1',
  [EditorBlockType.Heading2]: '标题 2',
  [EditorBlockType.Heading3]: '标题 3',
  [EditorBlockType.CodeBlock]: '代码块',
  [EditorBlockType.Blockquote]: '引用',
  [EditorBlockType.Callout]: '提示框',
  [EditorBlockType.BulletList]: '无序列表',
  [EditorBlockType.OrderedList]: '有序列表',
};

/** Editor content document structure (TipTap JSON) */
export interface EditorContentDocument {
  type: 'doc';
  content: EditorNode[];
}

/** Generic editor node */
export interface EditorNode {
  type: string;
  content?: EditorNode[];
  text?: string;
  marks?: EditorMark[];
  attrs?: Record<string, unknown>;
}

/** Editor mark (bold, italic, link, etc.) */
export interface EditorMark {
  type: string;
  attrs?: Record<string, unknown>;
}

/** Mention node attributes */
export interface MentionAttrs {
  id: string;
  label: string;
  type: 'paper' | 'chunk' | 'evidence';
}

/** Link node attributes */
export interface LinkAttrs {
  href: string;
  target?: string;
}

/** Callout node attributes */
export interface CalloutAttrs {
  variant: 'info' | 'warning' | 'tip' | 'important';
}

/** Editor component props */
export interface ScholarAIEditorProps {
  content: EditorContentDocument | null;
  onChange: (doc: EditorContentDocument) => void;
  placeholder?: string;
  readOnly?: boolean;
  hideToolbar?: boolean;
  className?: string;
}

/** Allowed contentDoc node types for API validation */
export const ALLOWED_NODE_TYPES = new Set([
  'doc',
  'paragraph',
  'heading',
  'codeBlock',
  'blockquote',
  'callout',
  'mention',
  'text',
  'hardBreak',
  'bulletList',
  'orderedList',
  'listItem',
]);

/** Allowed heading levels */
export const ALLOWED_HEADING_LEVELS = new Set([1, 2, 3]);

/**
 * Validates that a contentDoc only contains allowed node types.
 * Returns true if valid, false otherwise.
 */
export function isValidContentDoc(doc: unknown): doc is EditorContentDocument {
  if (!doc || typeof doc !== 'object') return false;
  const d = doc as Record<string, unknown>;
  if (d.type !== 'doc' || !Array.isArray(d.content)) return false;
  return (d.content as unknown[]).every(isValidNode);
}

function isValidNode(node: unknown): boolean {
  if (!node || typeof node !== 'object') return false;
  const n = node as Record<string, unknown>;
  if (typeof n.type !== 'string') return false;
  if (!ALLOWED_NODE_TYPES.has(n.type)) return false;

  if (n.type === 'heading') {
    const level = (n.attrs as Record<string, unknown>)?.level;
    if (typeof level === 'number' && !ALLOWED_HEADING_LEVELS.has(level)) return false;
  }

  if (n.type === 'mention') {
    const attrs = n.attrs as Record<string, unknown> | undefined;
    if (!attrs || typeof attrs.id !== 'string' || typeof attrs.label !== 'string') return false;
    const validTypes = new Set(['paper', 'chunk', 'evidence']);
    if (!validTypes.has(attrs.type as string)) return false;
  }

  if (Array.isArray(n.content)) {
    return (n.content as unknown[]).every(isValidNode);
  }

  return true;
}
