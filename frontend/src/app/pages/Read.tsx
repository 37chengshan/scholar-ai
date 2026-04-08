/**
 * Read Page
 *
 * Paper reading interface with:
 * - PDF viewer with pagination and zoom
 * - Section navigation (IMRaD structure)
 * - Annotation toolbar for highlights
 * - Notes editor with auto-save
 * - Reading progress tracking
 * - Cross-paper note association
 *
 * Requirements: PAGE-06, D-07
 */

import { useState, useEffect } from 'react';
import { useParams } from 'react-router';
import { PDFViewer } from '../components/PDFViewer';
import { SectionTree } from '../components/SectionTree';
import { AnnotationToolbar } from '../components/AnnotationToolbar';
import { NotesEditor } from '../components/NotesEditor';
import * as papersApi from '@/services/papersApi';
import * as annotationsApi from '@/services/annotationsApi';
import type { Annotation } from '@/services/annotationsApi';
import { toast } from 'sonner';
import { useLanguage } from '../contexts/LanguageContext';

interface LinkedPaper {
  id: string;
  title: string;
  authors: string[];
  year: number;
}

export function Read() {
  const { id } = useParams<{ id: string }>();
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const [paper, setPaper] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [linkedPapers, setLinkedPapers] = useState<LinkedPaper[]>([]);
  const [showLinkPicker, setShowLinkPicker] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  // Load paper data
  useEffect(() => {
    async function loadPaper() {
      if (!id) {
        console.error('No paper ID provided');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        console.log('Loading paper:', id);
        const data = await papersApi.get(id);
        console.log('Paper loaded:', data);
        setPaper(data);

        // Load annotations
        const annotationData = await annotationsApi.list(id);
        setAnnotations(annotationData);

        // Load linked papers from reading notes metadata
        if (data.linkedPapers && Array.isArray(data.linkedPapers)) {
          setLinkedPapers(data.linkedPapers);
        }
      } catch (error) {
        console.error('Failed to load paper:', error);
      } finally {
        setLoading(false);
      }
    }

    loadPaper();
  }, [id]);

  // Search papers for linking
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!searchQuery.trim() || searchQuery.length < 2) {
        setSearchResults([]);
        return;
      }

      setSearching(true);
      try {
        const results = await papersApi.list({ search: searchQuery, limit: 5 });
        // Filter out current paper
        setSearchResults(results.filter((p: any) => p.id !== id));
      } catch (error) {
        console.error('Failed to search papers:', error);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery, id]);

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

  const handleLinkPaper = async (paperId: string) => {
    if (!id) return;
    
    try {
      // Check if already linked
      if (linkedPapers.some(p => p.id === paperId)) {
        toast.error(isZh ? '该论文已关联' : 'Paper already linked');
        return;
      }

      // Get paper details
      const paperData = await papersApi.get(paperId);
      const newLinkedPaper: LinkedPaper = {
        id: paperId,
        title: paperData.title,
        authors: paperData.authors || [],
        year: paperData.year || new Date().getFullYear(),
      };

      setLinkedPapers([...linkedPapers, newLinkedPaper]);
      setSearchQuery('');
      setSearchResults([]);
      setShowLinkPicker(false);
      
      toast.success(isZh ? '已关联论文' : 'Paper linked');
    } catch (error) {
      console.error('Failed to link paper:', error);
      toast.error(isZh ? '关联失败' : 'Failed to link paper');
    }
  };

  const handleUnlinkPaper = async (paperId: string) => {
    if (!id) return;
    
    setLinkedPapers(linkedPapers.filter(p => p.id !== paperId));
    toast.success(isZh ? '已取消关联' : 'Paper unlinked');
  };

  if (loading || !paper) {
    return <div className="flex items-center justify-center h-full">{isZh ? '加载中...' : 'Loading...'}</div>;
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
          paperId={id}
          linkedPapers={linkedPapers}
          onLinkPaper={() => setShowLinkPicker(!showLinkPicker)}
          onUnlinkPaper={handleUnlinkPaper}
          showLinkPicker={showLinkPicker}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          searchResults={searchResults}
          searching={searching}
          onLinkPaperSelect={handleLinkPaper}
        />
      </div>
    </div>
  );
}
