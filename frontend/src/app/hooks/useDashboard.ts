/**
 * useDashboard Hook
 *
 * Manages dashboard statistics and trend data fetching.
 *
 * Features:
 * - Fetches user stats from backend API
 * - Weekly trend data for charts
 * - Subject distribution for pie chart
 * - Loading and error states
 * - Auto-refresh capability
 *
 * Per PAGE-02: Dashboard is landing page after login showing key metrics
 */

import { useState, useEffect } from 'react';
import * as usersApi from '@/services/usersApi';

export interface DashboardStats {
  paperCount: number;
  entityCount: number;
  llmTokens: number;
  queryCount: number;
  sessionCount: number;
  weeklyTrend: Array<{
    date: string;
    papers: number;
    queries: number;
    tokens: number;
  }>;
  subjectDistribution: Array<{
    name: string;
    value: number;
  }>;
  storageUsage: {
    vectorDB: { used: number; total: number };
    blobStorage: { used: number; total: number };
  };
}

export function useDashboard(userId?: string) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    async function loadStats() {
      try {
        setLoading(true);
        setError(null);
        const data = await usersApi.getStats(userId);
        setStats(data);
      } catch (err: any) {
        console.error('Failed to load dashboard stats:', err);
        setError(err.response?.data?.error?.detail || err.message || 'Failed to load stats');
      } finally {
        setLoading(false);
      }
    }

    loadStats();
  }, [userId]);

  /**
   * Refresh stats manually
   */
  const refresh = async () => {
    if (!userId) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await usersApi.getStats(userId);
      setStats(data);
    } catch (err: any) {
      console.error('Failed to refresh dashboard stats:', err);
      setError(err.response?.data?.error?.detail || err.message || 'Failed to refresh stats');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Get weekly trend data formatted for Recharts
   */
  const weeklyTrendData = stats?.weeklyTrend?.map((item) => ({
    name: new Date(item.date).toLocaleDateString('en-US', { weekday: 'short' }),
    uv: item.papers,
    queries: item.queries,
    tokens: Math.floor(item.tokens / 1000), // Convert to K
  })) || [];

  /**
   * Get subject distribution data formatted for Recharts PieChart
   */
  const subjectDistData = stats?.subjectDistribution?.map((item) => ({
    name: item.name,
    value: item.value,
  })) || [];

  return {
    stats,
    loading,
    error,
    refresh,
    weeklyTrendData,
    subjectDistData,
  };
}