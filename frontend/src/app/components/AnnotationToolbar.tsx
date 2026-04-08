/**
 * Annotation Toolbar Component
 *
 * Toolbar for creating PDF annotations:
 * - Color picker for highlights
 * - Create highlight button
 * - Integration with annotationsApi
 *
 * Requirements: PAGE-06 (Read page annotation system)
 */

import { useState } from 'react';
import * as annotationsApi from '@/services/annotationsApi';
import { clsx } from 'clsx';

interface AnnotationToolbarProps {
  paperId: string;
  pageNumber: number;
  onAnnotationCreated?: () => void;
}

export function AnnotationToolbar({ paperId, pageNumber, onAnnotationCreated }: AnnotationToolbarProps) {
  const [color, setColor] = useState('#FFEB3B');
  const [isCreating, setIsCreating] = useState(false);

  const colors = ['#FFEB3B', '#4CAF50', '#2196F3', '#FF5722'];

  const handleHighlight = async () => {
    setIsCreating(true);
    try {
      await annotationsApi.create({
        paperId,
        type: 'highlight',
        pageNumber,
        position: { x: 0, y: 0, width: 100, height: 20 },
        color
      });
      onAnnotationCreated?.();
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="flex items-center gap-2 p-2 bg-card border border-border rounded-sm shadow-sm">
      <span className="text-sm font-medium text-foreground">Highlight:</span>
      {colors.map(c => (
        <button
          key={c}
          onClick={() => setColor(c)}
          className={clsx(
            "w-6 h-6 rounded-sm border transition-all",
            color === c 
              ? "border-primary ring-2 ring-primary/20" 
              : "border-border hover:border-primary/50"
          )}
          style={{ backgroundColor: c }}
          aria-label={`Select color ${c}`}
        />
      ))}
      <button
        onClick={handleHighlight}
        disabled={isCreating}
        className={clsx(
          "px-3 py-1.5 bg-primary text-primary-foreground rounded-sm",
          "text-[10px] font-bold uppercase tracking-widest",
          "hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed",
          "shadow-sm shadow-primary/20 transition-colors"
        )}
      >
        {isCreating ? 'Adding...' : 'Add Highlight'}
      </button>
    </div>
  );
}