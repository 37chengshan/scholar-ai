/**
 * Related Notes Component
 *
 * Displays notes related to a specific paper on the paper detail page.
 * Shows:
 * - Notes directly associated with this paper
 * - Cross-paper notes (notes linked to multiple papers)
 * - Preview of note content
 * - Tags and creation date
 *
 * Requirements: D-08
 */

import { Link } from 'react-router-dom';
import { useNotes } from '@/hooks/useNotes';
import type { Note } from '@/services/notesApi';

interface RelatedNotesProps {
  paperId: string;
  maxNotes?: number; // Limit number of notes shown
}

export function RelatedNotes({ paperId, maxNotes = 5 }: RelatedNotesProps) {
  const { notes, loading, error } = useNotes({ paperId });

  if (loading) {
    return (
      <div className="p-4 text-muted-foreground">
        Loading notes...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-muted-foreground text-sm">
        Unable to load notes
      </div>
    );
  }

  if (notes.length === 0) {
    return (
      <div className="p-4 text-muted-foreground text-sm">
        No notes yet.{' '}
        <Link
          to={`/read/${paperId}`}
          className="text-primary hover:underline"
        >
          Add notes while reading
        </Link>
      </div>
    );
  }

  // Limit notes if maxNotes specified
  const displayNotes = notes.slice(0, maxNotes);

  return (
    <div className="space-y-3">
      {/* Header */}
      <h3 className="font-semibold text-lg flex items-center gap-2">
        <span>Related Notes</span>
        <span className="text-muted-foreground text-sm">
          ({notes.length})
        </span>
      </h3>

      {/* Notes list */}
      <div className="space-y-2">
        {displayNotes.map((note) => (
          <NotePreview key={note.id} note={note} />
        ))}
      </div>

      {/* Show more button if there are more notes */}
      {notes.length > maxNotes && (
        <Link
          to={`/notes?paperId=${paperId}`}
          className="text-sm text-primary hover:underline"
        >
          View all {notes.length} notes →
        </Link>
      )}
    </div>
  );
}

/**
 * Individual note preview component
 */
function NotePreview({ note }: { note: Note }) {
  // Strip HTML for preview
  const preview = note.content
    .replace(/<[^>]*>/g, '')
    .slice(0, 100)
    .trim();

  const isCrossPaper = note.paperIds.length > 1;

  return (
    <div className="p-3 border rounded hover:bg-muted/50 transition-colors">
      {/* Title */}
      <h4 className="font-medium text-sm mb-1">{note.title}</h4>

      {/* Cross-paper indicator */}
      {isCrossPaper && (
        <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
          <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-primary/10 text-primary">
            Cross-paper
          </span>
          <span>({note.paperIds.length} papers)</span>
        </div>
      )}

      {/* Content preview */}
      {preview && (
        <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
          {preview}...
        </p>
      )}

      {/* Tags */}
      {note.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {note.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-xs bg-secondary px-1.5 py-0.5 rounded"
            >
              #{tag}
            </span>
          ))}
          {note.tags.length > 3 && (
            <span className="text-xs text-muted-foreground">
              +{note.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Timestamp */}
      <div className="text-xs text-muted-foreground mt-2">
        {new Date(note.createdAt).toLocaleDateString()}
      </div>
    </div>
  );
}