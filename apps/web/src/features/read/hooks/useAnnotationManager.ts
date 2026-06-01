/**
 * useAnnotationManager Hook
 *
 * Manages annotation selection state and refresh logic.
 */

import { useState, useCallback } from 'react';
import type { Annotation } from '@/services/annotationsApi';
import * as annotationsApi from '@/services/annotationsApi';

type SelectionPosition = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export function useAnnotationManager(paperId: string | undefined) {
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [selectedText, setSelectedText] = useState('');
  const [selectionPosition, setSelectionPosition] =
    useState<SelectionPosition | null>(null);
  const [activeAnnotationId, setActiveAnnotationId] = useState<string | null>(
    null,
  );

  const handleAnnotationCreated = useCallback(async () => {
    if (!paperId) return;
    const data = await annotationsApi.list(paperId);
    setAnnotations(data);
    setSelectedText('');
    setSelectionPosition(null);
  }, [paperId]);

  return {
    annotations,
    setAnnotations,
    selectedText,
    setSelectedText,
    selectionPosition,
    setSelectionPosition,
    activeAnnotationId,
    setActiveAnnotationId,
    handleAnnotationCreated,
  };
}
