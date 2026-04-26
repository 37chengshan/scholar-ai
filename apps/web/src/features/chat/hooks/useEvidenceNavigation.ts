import { useCallback } from 'react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { getEvidenceSource } from '@/services/evidenceApi';
import { saveEvidenceNote } from '@/services/notesApi';
import type { EvidenceBlock } from '@/features/chat/components/workspaceTypes';

export function useEvidenceNavigation(isZh: boolean) {
  const navigate = useNavigate();

  const jumpToSource = useCallback(async (sourceChunkId: string, fallbackPaperId?: string, fallbackPage?: number) => {
    if (!sourceChunkId) {
      return;
    }
    try {
      const source = await getEvidenceSource(sourceChunkId);
      if (source.read_url) {
        navigate(source.read_url);
        return;
      }
      const paperId = source.paper_id || fallbackPaperId;
      if (!paperId) {
        throw new Error('missing-paper-id');
      }
      const page = source.page_num || fallbackPage || 1;
      navigate(`/read/${paperId}?page=${page}&source=chat&source_id=${sourceChunkId}`);
    } catch {
      toast.error(isZh ? '证据跳转失败' : 'Failed to open evidence source');
    }
  }, [isZh, navigate]);

  const saveEvidence = useCallback(async (claim: string, block: EvidenceBlock) => {
    if (!block.source_chunk_id || !block.paper_id) {
      return;
    }

    try {
      await saveEvidenceNote({
        claim,
        source_chunk_id: block.source_chunk_id,
        paper_id: block.paper_id,
        page_num: block.page_num || undefined,
        section_path: block.section_path || undefined,
        content: block.content,
        citation: {
          source_chunk_id: block.source_chunk_id,
          paper_id: block.paper_id,
          page_num: block.page_num,
          section_path: block.section_path,
          content_type: block.content_type,
        },
      });
      toast.success(isZh ? '已保存到笔记' : 'Saved to notes');
    } catch {
      toast.error(isZh ? '保存证据失败' : 'Failed to save evidence');
    }
  }, [isZh]);

  return {
    jumpToSource,
    saveEvidence,
  };
}
