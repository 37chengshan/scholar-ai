import apiClient from '@/utils/apiClient';

export interface RecentPaperProgress {
  id: string;
  title: string;
  authors?: string[] | null;
  year?: number | null;
  starred?: boolean | null;
  status?: string | null;
  pageCount?: number | null;
  currentPage: number;
  lastReadAt?: string | null;
  progress?: number | null;
}

export async function getRecentPapers(limit = 5): Promise<RecentPaperProgress[]> {
  const response = await apiClient.get<{
    success?: boolean;
    data?: RecentPaperProgress[];
  }>('/api/v1/dashboard/recent-papers', {
    params: { limit },
  });

  return response.data?.data || [];
}
