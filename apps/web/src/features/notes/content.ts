import type { EditorDocument } from './ownership';

export function isEditorDocument(value: unknown): value is EditorDocument {
  return Boolean(
    value
    && typeof value === 'object'
    && (value as { type?: unknown }).type === 'doc'
    && Array.isArray((value as { content?: unknown }).content),
  );
}

interface EvidenceSnapshotMetadata {
  paperTitle?: string | null;
  sectionPath?: string | null;
  pageNum?: number | null;
}

function extractPlainTextFromEditorNode(node: Record<string, unknown>, texts: string[]) {
  if (typeof node.text === 'string') {
    texts.push(node.text);
  }
  if (Array.isArray(node.content)) {
    for (const child of node.content as Array<Record<string, unknown>>) {
      extractPlainTextFromEditorNode(child, texts);
    }
  }
}

function extractPlainTextFromEditorDocument(doc: EditorDocument): string {
  const texts: string[] = [];
  for (const node of doc.content as Array<Record<string, unknown>>) {
    extractPlainTextFromEditorNode(node, texts);
  }
  return texts.join(' ').replace(/\[\[pdf:[^:]+:page:\d+\]\]/g, '').trim();
}

const BRACKETED_EVIDENCE_METADATA_RE = /^\[(?<label>[A-Za-z]+):(?<value>[^\]]+)\]\s*/;
const UUID_LIKE_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const PAPER_PLACEHOLDER_RE = /^paper\s+[0-9a-f]{6,8}$/i;
const GENERIC_PLACEHOLDER_RE = /^(?:source|document|paper|untitled|unknown|未命名论文|系统摘要|1(?:\s*\(v\d+\))?)$/i;
const PAPER_PLACEHOLDER_WITH_SUFFIX_RE = /^paper\s+[0-9a-f]{6,8}(?:\s+[·-]\s+.+)?$/i;
const TEST_FILE_STEM_PLACEHOLDER_RE = /^(?:test|sample|demo)(?:[_\-\s].*)?$/i;
const SUMMARY_SUFFIX_RE = /\s*系统摘要\s*$/;
const SECTION_HEADING_TITLE_RE = /^(?:research question(?:\s*&\s*motivation)?|problem address(?:ed)?|motivation|background|overview|method|experiment|result|conclusion|limitation)\b/i;
const SECTION_HEADING_PREFIX_RE = /^(?:research question(?:\s*&\s*motivation)?|problem address(?:ed)?|motivation|background|overview|method|experiment|result|conclusion|limitation)\s*(?:[:\-]\s*|\s+)/i;
const SUMMARY_NOISE_LINE_RE = /^(?:\d+(?:\.\d+)*[\).\s-]*)?(?:research question(?:\s*&\s*motivation)?|problem address(?:ed)?|motivation|background|overview|method|experiment|result|conclusion|limitation|future work)\b[:\s-]*/i;
const SUMMARY_SECTION_BREAK_RE = /\s+\d+(?:\.\d+)*[\).\s-]+(?:research question(?:\s*&\s*motivation)?|problem address(?:ed)?|motivation|background|overview|method|experiment|result|conclusion|limitation|future work)\b[\s:.-]*/i;
const LEADING_MARKDOWN_ENUMERATION_RE = /^(?:#{1,6}\s*)?(?:[-*+]\s+)?(?:\d+(?:\.\d+)*[\).\s-]*)+/i;
const SUMMARY_STYLE_TITLE_PREFIX_RE = /^(?:this paper|the paper|problem addressed|research question|motivation|background|overview|method|results?|conclusion|future work|该论文|本文|研究|提出|主要解决|针对)\b/i;
const SUMMARY_STYLE_TITLE_BODY_RE = /\b(?:focuses on|addresses|demonstrates|introduces|proposes|presents|studies|explores|investigates|describes|evaluates|shows|relies on|suffers from)\b/i;
const INTERNAL_CUE_RE = /\b(?:test(?:ing)?|placeholder|sample|demo|人工智能)\b/i;
const EVIDENCE_STATUS_LINE_RE = /^(?:当前阅读证据|current reading evidence|search evidence|chat citation|answer evidence)$/i;
const LEADING_INLINE_BRACKET_TAG_RE = /^(?:\[[A-Za-z][A-Za-z0-9_,-]*:[^\]]+\]\s*)+/;
const GLYPH_PLACEHOLDER_RE = /GLYPH<\d+>/g;

function cleanEvidenceSpacing(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function stripLooseMarkdownMarkers(text: string): string {
  return text
    .replace(/\*\*/g, '')
    .replace(/__/g, '')
    .replace(/`/g, '')
    .replace(/^\*+\s*/g, '')
    .replace(/^_+\s*/g, '');
}

function stripSummaryHeadingPrefixes(text: string): string {
  let cleaned = cleanEvidenceSpacing(stripLooseMarkdownMarkers(text));
  while (SUMMARY_NOISE_LINE_RE.test(cleaned)) {
    const next = cleanEvidenceSpacing(cleaned.replace(SUMMARY_NOISE_LINE_RE, ''));
    if (!next || next === cleaned) {
      break;
    }
    cleaned = next;
  }
  cleaned = cleanEvidenceSpacing(cleaned.replace(LEADING_MARKDOWN_ENUMERATION_RE, ''));
  return cleaned;
}

export function parseEvidenceSnapshot(raw: string | null | undefined): {
  metadata: EvidenceSnapshotMetadata;
  text: string;
} {
  const source = String(raw || '').trim();
  if (!source) {
    return { metadata: {}, text: '' };
  }

  const metadata: EvidenceSnapshotMetadata = {};
  let remaining = source;

  while (true) {
    const match = remaining.match(BRACKETED_EVIDENCE_METADATA_RE);
    if (!match?.groups) {
      break;
    }

    const label = match.groups.label.toLowerCase();
    const value = cleanEvidenceSpacing(match.groups.value);

    if (label === 'paper' && value) {
      metadata.paperTitle = value;
    } else if (label === 'section' && value) {
      metadata.sectionPath = value;
    } else if (label === 'page' && value) {
      const pageNum = Number.parseInt(value, 10);
      if (Number.isFinite(pageNum) && pageNum > 0) {
        metadata.pageNum = pageNum;
      }
    }

    remaining = remaining.slice(match[0].length).trimStart();
  }

  return {
    metadata,
    text: cleanEvidenceSpacing(remaining),
  };
}

export function normalizeEvidenceText(raw: string | null | undefined): string {
  const source = String(raw || '').trim();
  if (!source) {
    return '';
  }

  const maybeDoc = parseMaybeEditorDocument(source);
  if (maybeDoc) {
    return cleanEvidenceSpacing(extractPlainTextFromEditorDocument(maybeDoc));
  }

  const { text } = parseEvidenceSnapshot(source);
  return text || cleanEvidenceSpacing(source);
}

export function sanitizeNoteBodyPreview(raw: string | null | undefined): string {
  const source = String(raw || '').trim();
  if (!source) {
    return '';
  }

  const maybeDoc = parseMaybeEditorDocument(source);
  const textSource = maybeDoc ? extractPlainTextFromEditorDocument(maybeDoc) : source;

  const cleanedLines = textSource
    .split(/\n+/)
    .map((line) =>
      cleanEvidenceSpacing(
        line
          .replace(LEADING_INLINE_BRACKET_TAG_RE, '')
          .replace(GLYPH_PLACEHOLDER_RE, ' ')
      ),
    )
    .filter((line) => Boolean(line))
    .filter((line) => !/^\[(?:Paper|Section|Page):[^\]]+\]$/i.test(line))
    .filter((line) => !EVIDENCE_STATUS_LINE_RE.test(line))
    .filter((line) => !/^(?:Claim|Evidence|Paper|Page|Section|Comment):\s*/i.test(line));

  return cleanEvidenceSpacing(cleanedLines.join(' '));
}

export function sanitizeSearchSnippet(raw: string | null | undefined): string {
  const cleaned = sanitizeNoteBodyPreview(raw);
  if (!cleaned) {
    return '';
  }
  return cleaned.length > 320 ? `${cleaned.slice(0, 320).trim()}...` : cleaned;
}

export function resolveEvidenceDisplayTitle(
  title: string | null | undefined,
  fallbackText?: string | null | undefined,
): string {
  const normalizedTitle = cleanEvidenceSpacing(String(title || ''));
  const fallback = parseEvidenceSnapshot(fallbackText).metadata.paperTitle?.trim() || '';

  if (normalizedTitle && !UUID_LIKE_RE.test(normalizedTitle)) {
    return normalizedTitle;
  }

  if (fallback) {
    return fallback;
  }

  return normalizedTitle || 'source';
}

export function isPlaceholderDisplayTitle(title: string | null | undefined): boolean {
  const normalizedTitle = cleanEvidenceSpacing(String(title || ''));
  if (!normalizedTitle) {
    return true;
  }
  if (UUID_LIKE_RE.test(normalizedTitle)) {
    return true;
  }
  if (PAPER_PLACEHOLDER_RE.test(normalizedTitle)) {
    return true;
  }
  if (PAPER_PLACEHOLDER_WITH_SUFFIX_RE.test(normalizedTitle)) {
    return true;
  }
  if (TEST_FILE_STEM_PLACEHOLDER_RE.test(normalizedTitle)) {
    return true;
  }
  if (GENERIC_PLACEHOLDER_RE.test(normalizedTitle)) {
    return true;
  }
  if (SUMMARY_STYLE_TITLE_PREFIX_RE.test(normalizedTitle)) {
    return true;
  }
  if (INTERNAL_CUE_RE.test(normalizedTitle)) {
    return true;
  }
  if (normalizedTitle.length >= 48 && SUMMARY_STYLE_TITLE_BODY_RE.test(normalizedTitle)) {
    return true;
  }
  return normalizedTitle.length < 4;
}

export function deriveReadableTitleFromText(
  raw: string | null | undefined,
  fallbackTitle?: string | null | undefined,
): string {
  const fallback = cleanEvidenceSpacing(String(fallbackTitle || ''));
  if (fallback && !isPlaceholderDisplayTitle(fallback)) {
    return fallback;
  }

  const source = normalizeEvidenceText(raw);
  if (!source) {
    return fallback || '未命名内容';
  }

  const lines = source
    .split(/\n+/)
    .map((line) => cleanEvidenceSpacing(line))
    .filter((line) => Boolean(line));

  let firstMeaningfulLine = lines.find((line) => !SUMMARY_NOISE_LINE_RE.test(line));
  if (!firstMeaningfulLine) {
    firstMeaningfulLine = lines
      .map((line) => cleanEvidenceSpacing(line.replace(SUMMARY_NOISE_LINE_RE, '')))
      .find((line) => Boolean(line));
  }

  if (!firstMeaningfulLine) {
    return fallback && !isPlaceholderDisplayTitle(fallback) ? fallback : '系统摘要';
  }

  let cleaned = firstMeaningfulLine
    .replace(/^#{1,6}\s+/g, '')
    .replace(/^\d+(?:\.\d+)*[\).\s-]+/g, '')
    .replace(/\*\*/g, '')
    .replace(/__/g, '')
    .replace(/^[-*+]\s+/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  cleaned = stripLooseMarkdownMarkers(cleaned);

  while (SECTION_HEADING_TITLE_RE.test(cleaned)) {
    const next = cleaned.replace(SECTION_HEADING_PREFIX_RE, '').trim();
    if (!next || next === cleaned) {
      break;
    }
    cleaned = next;
  }

  if (/^[A-Z][a-z]+\s+[A-Z][a-z]+:/.test(cleaned)) {
    cleaned = cleaned.replace(/^[A-Z][a-z]+\s+[A-Z][a-z]+:\s*/, '').trim();
  }

  if (
    !cleaned
    || GENERIC_PLACEHOLDER_RE.test(cleaned)
    || PAPER_PLACEHOLDER_RE.test(cleaned)
    || PAPER_PLACEHOLDER_WITH_SUFFIX_RE.test(cleaned)
    || SECTION_HEADING_TITLE_RE.test(cleaned)
  ) {
    return fallback && !isPlaceholderDisplayTitle(fallback) ? fallback : '系统摘要';
  }

  return cleaned.length > 72 ? `${cleaned.slice(0, 72).trim()}...` : cleaned;
}

export function deriveReadableSummaryPreview(
  raw: string | null | undefined,
  fallback = '系统摘要',
): string {
  const source = normalizeEvidenceText(raw);
  if (!source) {
    return fallback;
  }

  const lines = source
    .split(/\n+/)
    .map((line) =>
      cleanEvidenceSpacing(
        line
          .replace(/^#{1,6}\s+/g, '')
          .replace(/\*\*([^*]+)\*\*/g, '$1')
          .replace(/__([^_]+)__/g, '$1')
          .replace(/\*([^*]+)\*/g, '$1')
          .replace(/_([^_]+)_/g, '$1')
          .replace(/^[-*+]\s+/g, ''),
      ),
    )
    .map((line) => stripSummaryHeadingPrefixes(line))
    .filter((line) => Boolean(line));

  const previewSource = lines.find((line) => !SECTION_HEADING_TITLE_RE.test(line)) || lines[0];
  if (!previewSource) {
    return fallback;
  }

  const preview = cleanEvidenceSpacing(previewSource.split(SUMMARY_SECTION_BREAK_RE)[0] || '');
  if (!preview || SECTION_HEADING_TITLE_RE.test(preview)) {
    return fallback;
  }
  return preview.length > 88 ? `${preview.slice(0, 88).trim()}...` : preview;
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

function createTextNode(text: string) {
  return { type: 'text', text };
}

function createParagraphNode(text: string) {
  return {
    type: 'paragraph',
    content: text ? [createTextNode(text)] : [],
  };
}

function sanitizeInlineMarkdown(text: string): string {
  return normalizeEvidenceText(
    text
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
  );
}

function markdownToEditorDocument(markdown: string): EditorDocument {
  const normalized = markdown.replace(/\r\n/g, '\n').trim();
  if (!normalized) {
    return { type: 'doc', content: [createParagraphNode('')] };
  }

  const lines = normalized.split('\n');
  const content: Array<Record<string, unknown>> = [];
  let paragraphBuffer: string[] = [];
  let listBuffer: string[] = [];
  let listType: 'bulletList' | 'orderedList' | null = null;

  const flushParagraph = () => {
    const text = paragraphBuffer.join(' ').replace(/\s+/g, ' ').trim();
    if (text) {
      content.push(createParagraphNode(text));
    }
    paragraphBuffer = [];
  };

  const flushList = () => {
    if (!listType || listBuffer.length === 0) {
      listBuffer = [];
      listType = null;
      return;
    }

    content.push({
      type: listType,
      content: listBuffer.map((item) => ({
        type: 'listItem',
        content: [createParagraphNode(item)],
      })),
    });
    listBuffer = [];
    listType = null;
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();

    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }

    const headingMatch = trimmed.match(/^#{1,6}\s+(.*)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      content.push(createParagraphNode(sanitizeInlineMarkdown(headingMatch[1].trim())));
      continue;
    }

    const bulletMatch = trimmed.match(/^[-*+]\s+(.*)$/);
    if (bulletMatch) {
      flushParagraph();
      if (listType && listType !== 'bulletList') {
        flushList();
      }
      listType = 'bulletList';
      listBuffer.push(sanitizeInlineMarkdown(bulletMatch[1].trim()));
      continue;
    }

    const orderedMatch = trimmed.match(/^\d+\.\s+(.*)$/);
    if (orderedMatch) {
      flushParagraph();
      if (listType && listType !== 'orderedList') {
        flushList();
      }
      listType = 'orderedList';
      listBuffer.push(sanitizeInlineMarkdown(orderedMatch[1].trim()));
      continue;
    }

    if (listType) {
      flushList();
    }
    paragraphBuffer.push(sanitizeInlineMarkdown(trimmed));
  }

  flushParagraph();
  flushList();

  return {
    type: 'doc',
    content: content.length > 0 ? content : [createParagraphNode('')],
  };
}

export function textToEditorDocument(text: string): EditorDocument {
  return markdownToEditorDocument(text);
}

export function plainTextToEditorDocument(text: string): EditorDocument {
  return {
    type: 'doc',
    content: [createParagraphNode(text)],
  };
}

export function normalizeEditorDocument(value: unknown): EditorDocument {
  return parseMaybeEditorDocument(value) ?? textToEditorDocument(String(value ?? ''));
}

export function extractEditorPlainText(value: unknown, maxLength?: number): string {
  const doc = normalizeEditorDocument(value);
  const cleaned = extractPlainTextFromEditorDocument(doc);

  const normalized = normalizeEvidenceText(cleaned);

  return maxLength && normalized.length > maxLength
    ? `${normalized.slice(0, maxLength)}...`
    : normalized;
}
