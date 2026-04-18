import type { CreateUploadSessionResponse } from '@/services/uploadSessionApi';

export function useInstantUpload() {
  const isInstantImport = (response: CreateUploadSessionResponse): boolean => {
    return Boolean(response.instantImport);
  };

  return {
    isInstantImport,
  };
}
