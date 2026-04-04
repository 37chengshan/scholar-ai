/**
 * Read Page
 *
 * Paper reading interface with:
 * - PDF viewer with pagination and zoom
 * - Section navigation (IMRaD structure)
 * - Annotation toolbar for highlights
 * - Notes editor with auto-save
 * - Reading progress tracking
 *
 * Requirements: PAGE-06
 */

import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { PDFViewer } from '../components/PDFViewer';
import { SectionTree } from '../components/SectionTree';
import { AnnotationToolbar } from '../components/AnnotationToolbar';
import { NotesEditor } from '../components/NotesEditor';
import * as papersApi from '@/services/papersApi';
import * as annotationsApi from '@/services/annotationsApi';
import type { Annotation } from '@/services/annotationsApi';

export function Read() {
  const { id } = useParams<{ id: string }>();
  const [paper, setPaper] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);

  // Load paper data
  useEffect(() => {
    async function loadPaper() {
      if (!id) return;

      try {
        setLoading(true);
        const data = await papersApi.get(id);
        setPaper(data);

        // Load annotations
        const annotationData = await annotationsApi.list(id);
        setAnnotations(annotationData);
      } catch (error) {
        console.error('Failed to load paper:', error);
      } finally {
        setLoading(false);
      }
    }

    loadPaper();
  }, [id]);

  const handlePageChange = async (page: number) => {
    setCurrentPage(page);
    // Save reading progress
    try {
      await fetch(`/api/reading-progress/${id}`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ currentPage: page }),
      });
    } catch (error) {
      console.error('Failed to save reading progress:', error);
    }
  };

  const handleAnnotationCreated = async () => {
    if (!id) return;
    const annotationData = await annotationsApi.list(id);
    setAnnotations(annotationData);
  };

  const handleNotesSave = async (content: string) => {
    if (!id) return;
    try {
      await papersApi.update(id, { readingNotes: content });
    } catch (error) {
      console.error('Failed to save notes:', error);
    }
  };

  if (loading || !paper) {
    return <div className="flex items-center justify-center h-full">Loading...</div>;
  }

  return (
    <div className="flex h-full">
      {/* Left: Section tree */}
      <div className="w-64 border-r">
        <SectionTree
          imrad={paper.imradJson}
          onPageSelect={setCurrentPage}
          currentPage={currentPage}
        />
      </div>

      {/* Center: PDF + Toolbar */}
      <div className="flex-1 flex flex-col">
        <AnnotationToolbar
          paperId={id!}
          pageNumber={currentPage}
          onAnnotationCreated={handleAnnotationCreated}
        />
        <div className="flex-1">
          <PDFViewer
            fileUrl={`/api/papers/${id}/pdf`}
            initialPage={1}
            onPageChange={handlePageChange}
          />
        </div>
      </div>

      {/* Right: Notes */}
      <div className="w-80 border-l">
        <NotesEditor
          content={paper.readingNotes || ''}
          onSave={handleNotesSave}
        />
      </div>
    </div>
  );
}