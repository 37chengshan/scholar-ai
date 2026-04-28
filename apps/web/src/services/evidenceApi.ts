import apiClient from '@/utils/apiClient';
import type { EvidenceSourceDto } from '@scholar-ai/types';

export type EvidenceSourceResponse = EvidenceSourceDto;

export async function getEvidenceSource(sourceChunkId: string): Promise<EvidenceSourceResponse> {
  const response = await apiClient.get<EvidenceSourceResponse>(`/api/v1/evidence/source/${sourceChunkId}`);
  return response.data;
}
