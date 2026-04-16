import apiClient from '@/utils/apiClient';
import type { HttpClient } from '@scholar-ai/sdk';

export const sdkHttpClient: HttpClient = {
  get: async (url, config) => {
    const response = await apiClient.get(url, config);
    return response.data;
  },
  post: async (url, body, config) => {
    const response = await apiClient.post(url, body, config);
    return response.data;
  },
  put: async (url, body, config) => {
    const response = await apiClient.put(url, body, config);
    return response.data;
  },
  patch: async (url, body, config) => {
    const response = await apiClient.patch(url, body, config);
    return response.data;
  },
  delete: async (url, config) => {
    const response = await apiClient.delete(url, config);
    return response.data;
  },
};
