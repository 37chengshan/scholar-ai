/**
 * Notes List Component
 *
 * Displays notes in multiple views:
 * - Time view: Simple list sorted by createdAt
 * - Paper view: Grouped by paperId
 * - Tag view: Grouped by tag
 *
 * Cross-paper notes appear in multiple groups in paper/tag views.
 */

import type { Note } from '@/services/notesApi';
import { NoteCard } from './NoteCard';
import { FileText, Hash } from 'lucide-react';

interface NotesListProps {
  notes: Note[];
  viewMode: 'time' | 'paper' | 'tag';
  loading: boolean;
  paperTitles?: Map<string, string>;
  onNoteClick?: (note: Note) => void;
}

export function NotesList({
  notes,
  viewMode,
  loading,
  paperTitles,
  onNoteClick,
}: NotesListProps) {
  // Loading state
  if (loading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Loading notes...
      </div>
    );
  }

  // Empty state
  if (notes.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No notes yet
      </div>
    );
  }

  // Time view: Simple list
  if (viewMode === 'time') {
    return (
      <div className="space-y-3">
        {notes.map(note => (
          <NoteCard
            key={note.id}
            note={note}
            onClick={() => onNoteClick?.(note)}
            paperTitles={paperTitles}
          />
        ))}
      </div>
    );
  }

  // Paper view: Group by paperId
  if (viewMode === 'paper') {
    const notesByPaper = notes.reduce((acc, note) => {
      note.paperIds.forEach(paperId => {
        if (!acc[paperId]) {
          acc[paperId] = [];
        }
        acc[paperId].push(note);
      });
      return acc;
    }, {} as Record<string, Note[]>);

    // Notes without paper association
    const ungroupedNotes = notes.filter(note => note.paperIds.length === 0);

    return (
      <div className="space-y-6">
        {/* Paper groups */}
        {Object.entries(notesByPaper).map(([paperId, paperNotes]) => (
          <div key={paperId}>
            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              <span className="truncate max-w-[300px]">
                {paperTitles?.get(paperId) || `Paper: ${paperId.slice(0, 8)}...`}
              </span>
              <span className="text-muted-foreground text-sm">
                ({paperNotes.length} notes)
              </span>
            </h3>
            <div className="space-y-2 pl-4">
              {paperNotes.map(note => (
                <NoteCard
                  key={note.id}
                  note={note}
                  onClick={() => onNoteClick?.(note)}
                  paperTitles={paperTitles}
                />
              ))}
            </div>
          </div>
        ))}

        {/* Ungrouped notes */}
        {ungroupedNotes.length > 0 && (
          <div>
            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              <span>General Notes</span>
              <span className="text-muted-foreground text-sm">
                ({ungroupedNotes.length} notes)
              </span>
            </h3>
            <div className="space-y-2 pl-4">
              {ungroupedNotes.map(note => (
                <NoteCard
                  key={note.id}
                  note={note}
                  onClick={() => onNoteClick?.(note)}
                  paperTitles={paperTitles}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Tag view: Group by tag
  if (viewMode === 'tag') {
    const notesByTag = notes.reduce((acc, note) => {
      note.tags.forEach(tag => {
        if (!acc[tag]) {
          acc[tag] = [];
        }
        acc[tag].push(note);
      });
      return acc;
    }, {} as Record<string, Note[]>);

    // Notes without tags
    const untaggedNotes = notes.filter(note => note.tags.length === 0);

    // Sort tags alphabetically
    const sortedTags = Object.keys(notesByTag).sort();

    return (
      <div className="space-y-6">
        {/* Tag groups */}
        {sortedTags.map(tag => (
          <div key={tag}>
            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
              <Hash className="w-5 h-5" />
              #{tag}
              <span className="text-muted-foreground text-sm">
                ({notesByTag[tag].length} notes)
              </span>
            </h3>
            <div className="space-y-2 pl-4">
              {notesByTag[tag].map(note => (
                <NoteCard
                  key={note.id}
                  note={note}
                  onClick={() => onNoteClick?.(note)}
                  paperTitles={paperTitles}
                />
              ))}
            </div>
          </div>
        ))}

        {/* Untagged notes */}
        {untaggedNotes.length > 0 && (
          <div>
            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
              <Hash className="w-5 h-5" />
              <span>Untagged</span>
              <span className="text-muted-foreground text-sm">
                ({untaggedNotes.length} notes)
              </span>
            </h3>
            <div className="space-y-2 pl-4">
              {untaggedNotes.map(note => (
                <NoteCard
                  key={note.id}
                  note={note}
                  onClick={() => onNoteClick?.(note)}
                  paperTitles={paperTitles}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Fallback: time view
  return (
    <div className="space-y-3">
      {notes.map(note => (
        <NoteCard
          key={note.id}
          note={note}
          onClick={() => onNoteClick?.(note)}
          paperTitles={paperTitles}
        />
      ))}
    </div>
  );
}