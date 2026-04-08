/**
 * Note Card Component
 *
 * Displays individual note with:
 * - Title
 * - Linked papers (clickable tags)
 * - Custom tags
 * - Creation and update timestamps
 *
 * Cross-paper notes show multiple paper tags.
 */

import { Link } from 'react-router-dom';
import type { Note } from '@/services/notesApi';

interface NoteCardProps {
  note: Note;
  onClick?: () => void;
  paperTitles?: Map<string, string>; // Map of paperId -> title
}

export function NoteCard({ note, onClick, paperTitles }: NoteCardProps) {
  // Format dates
  const createdDate = new Date(note.createdAt).toLocaleDateString();
  const updatedDate = new Date(note.updatedAt).toLocaleDateString();
  const isUpdated = note.updatedAt !== note.createdAt;

  // Strip HTML for preview (first 100 chars)
  const preview = note.content
    .replace(/<[^>]*>/g, '')
    .slice(0, 100)
    .trim();

  return (
    <div
      className="p-4 border rounded-lg hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      {/* Title */}
      <h3 className="font-semibold text-lg mb-2">{note.title}</h3>

      {/* Content Preview */}
      {preview && (
        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
          {preview}...
        </p>
      )}

      {/* Linked Papers */}
      {note.paperIds.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {note.paperIds.map(paperId => (
            <Link
              key={paperId}
              to={`/read/${paperId}`}
              className="inline-flex items-center text-xs bg-muted px-2 py-1 rounded hover:bg-primary/10 transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <span className="truncate max-w-[100px]">
                {paperTitles?.get(paperId) || `Paper: ${paperId.slice(0, 8)}...`}
              </span>
            </Link>
          ))}
        </div>
      )}

      {/* Tags */}
      {note.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {note.tags.map(tag => (
            <span
              key={tag}
              className="text-xs bg-secondary px-2 py-1 rounded"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Timestamps */}
      <div className="text-xs text-muted-foreground">
        Created: {createdDate}
        {isUpdated && (
          <span> • Updated: {updatedDate}</span>
        )}
      </div>
    </div>
  );
}