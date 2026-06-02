/**
 * BackLinksPanel - Shows notes that reference the current note
 *
 * Displays a list of notes that contain mentions or links to the
 * currently selected note, enabling bidirectional navigation.
 */

import { useMemo } from 'react';
import { Link } from 'react-router';
import { ArrowLeftRight, FileText } from 'lucide-react';

import type { Note } from '@/services/notesApi';
import { extractMentions } from '@/features/notes/editor/extensions/mentionUtils';
import { normalizeEditorDocument } from '@/features/notes/content';
import { buildNoteDisplayTitle } from '@/features/notes/notePresentation';

interface BackLinksPanelProps {
  currentNoteId: string;
  allNotes: Note[];
  paperTitleMap: Map<string, string>;
  onSelectNote: (note: Note) => void;
}

export function BackLinksPanel({
  currentNoteId,
  allNotes,
  paperTitleMap,
  onSelectNote,
}: BackLinksPanelProps) {
  const backLinks = useMemo(() => {
    const results: Array<{ note: Note; mentionLabel: string }> = [];

    for (const note of allNotes) {
      if (note.id === currentNoteId) continue;

      const doc = normalizeEditorDocument(note.contentDoc || note.content);
      const mentions = extractMentions(doc);

      // Check if any mention references the current note
      const hasReference = mentions.some((m) => m.id === currentNoteId);
      if (hasReference) {
        const mention = mentions.find((m) => m.id === currentNoteId);
        results.push({
          note,
          mentionLabel: mention?.label || note.title,
        });
      }
    }

    return results;
  }, [allNotes, currentNoteId]);

  if (backLinks.length === 0) {
    return null;
  }

  return (
    <section className="mt-4 rounded-xl border border-border/60 bg-muted/10 p-4">
      <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        <ArrowLeftRight className="h-3.5 w-3.5" />
        <span>引用此笔记 ({backLinks.length})</span>
      </div>
      <div className="space-y-2">
        {backLinks.map(({ note, mentionLabel }) => (
          <button
            key={note.id}
            type="button"
            className="flex w-full items-center gap-2 rounded-lg border border-border/40 bg-background px-3 py-2 text-left text-sm transition-colors hover:border-primary/30 hover:bg-primary/5"
            onClick={() => onSelectNote(note)}
          >
            <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium">
                {buildNoteDisplayTitle(note, paperTitleMap)}
              </p>
              <p className="truncate text-[10px] text-muted-foreground">
                引用了: {mentionLabel}
              </p>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
