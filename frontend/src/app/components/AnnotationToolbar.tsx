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
    // In a real implementation, this would capture selected text
    // For now, create a simple annotation
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
    <div className="flex items-center gap-2 p-2 bg-gray-100 rounded">
      <span className="text-sm font-medium">Highlight:</span>
      {colors.map(c => (
        <button
          key={c}
          onClick={() => setColor(c)}
          className={`w-6 h-6 rounded ${color === c ? 'ring-2 ring-black' : ''}`}
          style={{ backgroundColor: c }}
          aria-label={`Select color ${c}`}
        />
      ))}
      <button
        onClick={handleHighlight}
        disabled={isCreating}
        className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Add Highlight
      </button>
    </div>
  );
}