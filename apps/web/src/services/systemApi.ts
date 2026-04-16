import apiClient from '@/utils/apiClient';
import { API_BASE_URL } from '@/config/api';

export interface StorageMetric {
  used: string;
  total: string;
  percentage: number;
}

export interface SystemStorageResponse {
  vectorDB: StorageMetric;
  fileStorage: StorageMetric;
}

export interface SystemLog {
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
  timestamp: string;
}

export async function getStorageInfo(): Promise<SystemStorageResponse> {
  const response = await apiClient.get<SystemStorageResponse>('/api/v1/system/storage');
  return response.data;
}

export function createSystemLogsEventSource(): EventSource {
  return new EventSource(`${API_BASE_URL}/api/v1/system/logs/stream`, {
    withCredentials: true,
  });
}
