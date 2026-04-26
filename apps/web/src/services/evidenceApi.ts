import apiClient from '@/utils/apiClient';

export interface EvidenceSourceResponse {
  source_chunk_id: string;
  paper_id: string;
  page_num?: number;
  section_path?: string;
  content_type?: string;
  anchor_text?: string;
  content?: string;
  pdf_url?: string;
  read_url?: string;
}

export async function getEvidenceSource(sourceChunkId: string): Promise<EvidenceSourceResponse> {
  const response = await apiClient.get<EvidenceSourceResponse>(`/api/v1/evidence/source/${sourceChunkId}`);
  return response.data;
}
