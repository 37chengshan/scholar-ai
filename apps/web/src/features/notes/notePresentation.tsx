import type { ReactNode } from 'react';

import type { Note } from '@/services/notesApi';
import {
  deriveReadableTitleFromText,
  deriveReadableSummaryPreview,
  extractEditorPlainText,
  isPlaceholderDisplayTitle,
  sanitizeNoteBodyPreview,
} from '@/features/notes/content';
import {
  getPrimaryReadingNoteForPaper,
  isEvidenceCaptureNote,
  READ_WORKSPACE_NOTE_TAG,
} from '@/features/notes/ownership';

export const FOLDER_TAG_PREFIX = 'folder:';
export const PAPER_TAG_PREFIX = 'paper:';
export const PAPER_TITLE_TAG_PREFIX = 'paper-title:';

export function buildPaperDisplayTitle(title: string | null | undefined): string {
  const normalizedTitle = String(title || '').trim();
  if (normalizedTitle && !isPlaceholderDisplayTitle(normalizedTitle)) {
    return normalizedTitle;
  }
  return '未命名论文';
}

export function highlightText(text: string, query: string): ReactNode {
  if (!query.trim()) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);

  return parts.map((part, index) =>
    index % 2 === 1 ? (
      <mark key={index} className="rounded bg-yellow-200 px-0.5 text-inherit">
        {part}
      </mark>
    ) : (
      part
    ),
  );
}

export function humanizeNotePreview(raw: string | null | undefined): string {
  const text = sanitizeNoteBodyPreview(raw || '');
  if (!text) {
    return '暂无正文';
  }
  return text || '暂无正文';
}

export function humanizeSummaryPreview(raw: string | null | undefined): string {
  return deriveReadableSummaryPreview(raw, '系统摘要');
}

export function buildSummaryDisplayTitle(
  title: string | null | undefined,
  _readingNotes: string | null | undefined,
): string {
  return buildPaperDisplayTitle(title);
}

function decodeTagValue(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function getFolderIdFromTags(tags: string[]): string | null {
  const folderTag = tags.find((tag) => tag.startsWith(FOLDER_TAG_PREFIX));
  return folderTag ? folderTag.slice(FOLDER_TAG_PREFIX.length) : null;
}

export function upsertFolderTag(tags: string[], folderId: string): string[] {
  const withoutFolder = tags.filter((tag) => !tag.startsWith(FOLDER_TAG_PREFIX));
  return [...withoutFolder, `${FOLDER_TAG_PREFIX}${folderId}`];
}

export function getDisplayTags(tags: string[]): string[] {
  return tags.filter(
    (tag) =>
      !tag.startsWith(FOLDER_TAG_PREFIX) &&
      !tag.startsWith(PAPER_TAG_PREFIX) &&
      !tag.startsWith(PAPER_TITLE_TAG_PREFIX),
  );
}

export function getPaperTitleTag(tags: string[]): string | null {
  const paperTitleTag = tags.find((tag) => tag.startsWith(PAPER_TITLE_TAG_PREFIX));
  if (!paperTitleTag) {
    return null;
  }
  return decodeTagValue(paperTitleTag.slice(PAPER_TITLE_TAG_PREFIX.length));
}

export function getPaperIdTag(tags: string[]): string | null {
  const paperTag = tags.find((tag) => tag.startsWith(PAPER_TAG_PREFIX));
  return paperTag ? paperTag.slice(PAPER_TAG_PREFIX.length) : null;
}

export function buildNoteDisplayTitle(note: Note, paperTitleMap?: Map<string, string>): string {
  const primaryPaperId = note.paperIds[0] || getPaperIdTag(note.tags);
  const linkedPaperTitle =
    (primaryPaperId && paperTitleMap?.get(primaryPaperId))
    || getPaperTitleTag(note.tags)
    || null;

  if (isEvidenceCaptureNote(note)) {
    return linkedPaperTitle ? `${linkedPaperTitle} · 证据摘录` : '证据摘录';
  }

  if (
    linkedPaperTitle
    && (note.sourceType === 'read' || note.tags.includes(READ_WORKSPACE_NOTE_TAG))
    && isPlaceholderDisplayTitle(note.title)
  ) {
    return `${linkedPaperTitle} · 阅读笔记`;
  }

  if (note.title && !isPlaceholderDisplayTitle(note.title)) {
    return note.title;
  }

  if (linkedPaperTitle) {
    return `${linkedPaperTitle} · 笔记`;
  }

  return deriveReadableTitleFromText(
    extractEditorPlainText(note.contentDoc || note.content, 120),
    note.title || '未命名笔记',
  );
}

export { getPrimaryReadingNoteForPaper };
