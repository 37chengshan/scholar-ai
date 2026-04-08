/**
 * Notes Page Component
 *
 * Main notes list page with:
 * - Multi-view toggle (time/paper/tag)
 * - Notes list with filtering
 * - Cross-paper notes support
 * - Search/filter capabilities (future)
 *
 * Requirements: D-08, D-09
 */

import { useState } from 'react';
import { useNotes } from '@/hooks/useNotes';
import { NotesList } from '@/app/components/notes/NotesList';
import { ViewToggle } from '@/app/components/notes/ViewToggle';
import { Button } from '@/app/components/ui/button';
import { FileText, Plus } from 'lucide-react';

export function Notes() {
  const [viewMode, setViewMode] = useState<'time' | 'paper' | 'tag'>('time');
  const { notes, loading, error } = useNotes();

  // TODO: Future features
  // - Search functionality
  // - Filter by paper/tag
  // - Create note button (navigate to editor)
  // - Pagination for large lists

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Notes</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {notes.length} notes • {viewMode === 'time' ? 'chronological' : viewMode === 'paper' ? 'by paper' : 'by tag'}
          </p>
        </div>

        <div className="flex gap-2">
          {/* View Toggle */}
          <ViewToggle value={viewMode} onChange={setViewMode} />

          {/* Create Note Button */}
          <Button variant="default" size="sm" className="flex items-center gap-1">
            <Plus className="w-4 h-4" />
            New Note
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="text-center py-8 text-destructive">
          <p>Error loading notes: {error}</p>
          <Button variant="outline" size="sm" className="mt-2" onClick={() => window.location.reload()}>
            Retry
          </Button>
        </div>
      )}

      {/* Notes List */}
      {!error && (
        <NotesList
          notes={notes}
          viewMode={viewMode}
          loading={loading}
        />
      )}

      {/* Empty State */}
      {!loading && !error && notes.length === 0 && (
        <div className="text-center py-12">
          <div className="text-muted-foreground mb-4">
            <FileText className="w-16 h-16 mx-auto opacity-50" />
          </div>
          <h3 className="font-semibold text-lg mb-2">No Notes Yet</h3>
          <p className="text-muted-foreground text-sm mb-4">
            Start creating notes while reading papers to organize your thoughts
          </p>
          <Button variant="outline" onClick={() => window.location.href = '/library'}>
            Go to Library
          </Button>
        </div>
      )}
    </div>
  );
}