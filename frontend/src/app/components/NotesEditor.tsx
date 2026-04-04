/**
 * Notes Editor Component
 *
 * Simple textarea-based notes editor:
 * - Auto-save every 30 seconds
 * - Controlled component with parent state
 * - Minimal UI for note-taking
 *
 * Requirements: PAGE-06 (Read page notes editor)
 */

import { useState, useEffect } from 'react';

interface NotesEditorProps {
  content: string;
  onSave: (content: string) => void;
}

export function NotesEditor({ content, onSave }: NotesEditorProps) {
  const [value, setValue] = useState(content);

  // Update local state when prop changes
  useEffect(() => {
    setValue(content);
  }, [content]);

  // Auto-save every 30s
  useEffect(() => {
    const timer = setInterval(() => {
      if (value !== content) {
        onSave(value);
      }
    }, 30000);
    return () => clearInterval(timer);
  }, [value, content, onSave]);

  return (
    <div className="h-full flex flex-col">
      <div className="p-2 border-b font-medium">Notes</div>
      <textarea
        value={value}
        onChange={e => setValue(e.target.value)}
        className="flex-1 p-3 border-0 resize-none focus:outline-none"
        placeholder="Add your notes here..."
      />
    </div>
  );
}