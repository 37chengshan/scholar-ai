import apiClient from '@/utils/apiClient';

export interface CreateUploadSessionRequest {
  filename: string;
  sizeBytes: number;
  chunkSize: number;
  sha256?: string;
  mimeType?: string;
}

export interface UploadSessionState {
  uploadSessionId: string;
  importJobId: string;
  status: string;
  chunkSize: number;
  totalParts: number;
  uploadedParts: number[];
  missingParts: number[];
  uploadedBytes: number;
  sizeBytes: number;
  progress: number;
  expiresAt: string;
  completedAt?: string | null;
}

export interface CreateUploadSessionResponse {
  instantImport: boolean;
  importJobId?: string;
  paperId?: string;
  matchedImportJobId?: string;
  status?: string;
  session?: UploadSessionState;
}

export const uploadSessionApi = {
  createSession: async (
    importJobId: string,
    request: CreateUploadSessionRequest
  ): Promise<CreateUploadSessionResponse> => {
    const response = await apiClient.post(
      `/api/v1/import-jobs/${importJobId}/upload-sessions`,
      request
    );
    return response.data as CreateUploadSessionResponse;
  },

  getSession: async (sessionId: string): Promise<UploadSessionState> => {
    const response = await apiClient.get(`/api/v1/upload-sessions/${sessionId}`);
    return response.data as UploadSessionState;
  },

  uploadPart: async (
    sessionId: string,
    partNumber: number,
    chunk: Blob
  ): Promise<UploadSessionState> => {
    const response = await apiClient.put(
      `/api/v1/upload-sessions/${sessionId}/parts/${partNumber}`,
      chunk,
      {
        headers: {
          'Content-Type': 'application/octet-stream',
        },
      }
    );
    return response.data as UploadSessionState;
  },

  completeSession: async (sessionId: string): Promise<UploadSessionState> => {
    const response = await apiClient.post(`/api/v1/upload-sessions/${sessionId}/complete`);
    return response.data as UploadSessionState;
  },

  abortSession: async (sessionId: string): Promise<UploadSessionState> => {
    const response = await apiClient.post(`/api/v1/upload-sessions/${sessionId}/abort`);
    return response.data as UploadSessionState;
  },
};

export default uploadSessionApi;
