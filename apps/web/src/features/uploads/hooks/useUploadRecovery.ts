import { uploadSessionApi, UploadSessionState } from '@/services/uploadSessionApi';

export function useUploadRecovery() {
  const recoverSession = async (sessionId: string): Promise<UploadSessionState> => {
    return uploadSessionApi.getSession(sessionId);
  };

  return {
    recoverSession,
  };
}
