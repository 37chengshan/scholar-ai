import type { HttpClient } from '../client/http';
import type { EvidenceSourceDto } from '@scholar-ai/types';

export interface EvidenceApi {
  getSource: (sourceChunkId: string) => Promise<EvidenceSourceDto>;
}

export function createEvidenceApi(client: HttpClient): EvidenceApi {
  return {
    getSource: (sourceChunkId) => client.get<EvidenceSourceDto>(`/api/v1/evidence/source/${sourceChunkId}`),
  };
}
