import apiClient from '@/utils/apiClient';

export interface RecentPaper {
  id: string;
  title: string;
  authors: string[];
  year?: number;
  currentPage: number;
  lastReadAt: string;
  progress: number;
}

export interface RecentSession {
  id: string;
  title?: string;
  createdAt: string;
  lastActivityAt: string;
  messageCount: number;
}

interface SessionsPayload {
  sessions: RecentSession[];
  total: number;
  limit: number;
}

export async function getRecentPapers(limit = 3): Promise<RecentPaper[]> {
  const response = await apiClient.get<RecentPaper[]>(`/api/v1/dashboard/recent-papers?limit=${limit}`);
  return (response.data || []).map((paper) => ({
    id: paper.id,
    title: paper.title,
    authors: paper.authors || [],
    year: paper.year,
    currentPage: paper.currentPage,
    lastReadAt: paper.lastReadAt || '',
    progress: paper.progress ?? 0,
  }));
}

export async function getRecentSessions(limit = 3): Promise<RecentSession[]> {
  const response = await apiClient.get<SessionsPayload>(`/api/v1/sessions?limit=${Math.max(limit, 20)}&status=active`);
  const sessions = response.data.sessions || [];

  return sessions
    .slice()
    .map((session) => ({
      id: session.id,
      title: session.title,
      createdAt: session.createdAt || '',
      lastActivityAt: session.lastActivityAt || '',
      messageCount: session.messageCount,
    }))
    .sort((a, b) => {
      const aTime = a.lastActivityAt ? new Date(a.lastActivityAt).getTime() : 0;
      const bTime = b.lastActivityAt ? new Date(b.lastActivityAt).getTime() : 0;
      return bTime - aTime;
    })
    .slice(0, limit);
}
