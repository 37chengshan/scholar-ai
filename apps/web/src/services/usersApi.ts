/**
 * Users API Service
 *
 * User profile and settings API calls:
 * - getProfile(): Get user profile
 * - updateProfile(): Update profile info
 * - uploadAvatar(): Upload avatar image
 * - getSettings(): Get user preferences
 * - updateSettings(): Update preferences
 * - changePassword(): Change password (requires re-auth)
 * - getApiKeys(): List API keys
 * - createApiKey(): Create new API key
 * - deleteApiKey(): Delete API key (requires re-auth)
 * - getStats(): Get dashboard statistics
 */

import apiClient from '@/utils/apiClient';
import type { User, UserSettings, ApiKey, DashboardStats } from '@/types';

interface RawUser {
  id: string;
  email: string;
  name: string;
  avatar?: string | null;
  roles?: string[];
  email_verified?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

function normalizeUser(user: RawUser): User {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    avatar: user.avatar ?? null,
    roles: user.roles ?? [],
    emailVerified: user.email_verified ?? false,
    createdAt: user.created_at ?? undefined,
    updatedAt: user.updated_at ?? undefined,
  };
}

/**
 * Get user profile
 *
 * GET /api/users/me
 * Returns current user info
 *
 * @returns User profile
 */
export async function getProfile(): Promise<User> {
  const response = await apiClient.get<RawUser>('/api/v1/users/me');
  return normalizeUser(response.data);
}

/**
 * Update user profile
 *
 * PATCH /api/users/me
 * Updates name, email, or avatar
 *
 * Note: Email change requires uniqueness check
 *
 * @param data - Profile updates
 * @returns Updated user
 */
export async function updateProfile(data: {
  name?: string;
  email?: string;
  avatar?: string | null;
}): Promise<User> {
  const response = await apiClient.patch<RawUser>('/api/v1/users/me', data);
  return normalizeUser(response.data);
}

/**
 * Upload avatar image
 *
 * POST /api/users/me/avatar
 * Uploads avatar to S3/MinIO and updates user.avatar URL
 *
 * @param file - Avatar image file (JPEG, PNG, WebP; max 5MB)
 * @returns Avatar URL
 */
export async function uploadAvatar(file: File): Promise<{ avatar: string }> {
  const formData = new FormData();
  formData.append('avatar', file);

  const response = await apiClient.post<{ avatar: string }>('/api/v1/users/me/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Get user settings/preferences
 *
 * GET /api/users/me/settings
 * Returns language, defaultModel, theme preferences
 *
 * @returns User settings
 */
export async function getSettings(): Promise<UserSettings> {
  const response = await apiClient.get<UserSettings>('/api/v1/users/me/settings');
  return response.data;
}

/**
 * Update user settings/preferences
 *
 * PATCH /api/users/me/settings
 * Updates language, defaultModel, or theme
 *
 * @param data - Settings updates
 * @returns Updated settings
 */
export async function updateSettings(data: {
  language?: 'zh' | 'en';
  defaultModel?: string;
  theme?: 'light' | 'dark';
}): Promise<UserSettings> {
  const response = await apiClient.patch<UserSettings>('/api/v1/users/me/settings', data);
  return response.data;
}

/**
 * Change password
 *
 * PATCH /api/users/me/password
 * Requires re-authentication with currentPassword
 *
 * Note: After password change, all refresh tokens are invalidated
 * User must log in again with new password
 *
 * @param currentPassword - Current password (for re-auth)
 * @param newPassword - New password (min 8 chars)
 */
export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<{ message: string }> {
  const response = await apiClient.patch<{ message: string }>('/api/v1/users/me/password', {
    currentPassword,
    newPassword,
  });

  return response.data;
}

/**
 * Get user API keys
 *
 * GET /api/users/me/api-keys
 * Returns list of user's API keys (prefix only, not full key)
 *
 * @returns API keys list
 */
export async function getApiKeys(): Promise<ApiKey[]> {
  const response = await apiClient.get<ApiKey[]>('/api/v1/users/me/api-keys');
  return response.data;
}

/**
 * Create new API key
 *
 * POST /api/users/me/api-keys
 * Generates new API key (sk_live_xxxx format)
 *
 * IMPORTANT: Full key is returned ONLY on creation.
 * Save it securely - it cannot be retrieved again.
 *
 * @param name - API key name/description
 * @returns Created key with full key string (save immediately!)
 */
export async function createApiKey(name: string): Promise<{
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  key: string; // Full key - SAVE THIS!
  message: string;
}> {
  const response = await apiClient.post<{
    id: string;
    name: string;
    prefix: string;
    createdAt: string;
    key: string;
    message: string;
  }>('/api/v1/users/me/api-keys', {
    name,
  });

  return response.data;
}

/**
 * Delete API key
 *
 * DELETE /api/users/me/api-keys/:keyId
 * Requires re-authentication with currentPassword
 *
 * @param keyId - API key ID
 * @param currentPassword - Current password (for re-auth)
 */
export async function deleteApiKey(
  keyId: string,
  currentPassword: string
): Promise<void> {
  await apiClient.delete(`/api/v1/users/me/api-keys/${keyId}`, {
    data: {
      currentPassword,
    },
  });
}

/**
 * Get user dashboard statistics
 *
 * GET /api/v1/dashboard/stats - Returns paper/query/token counts
 * GET /api/v1/dashboard/trends - Returns weekly time-series data
 *
 * Note: Stats are for the current authenticated user.
 * Some fields are not yet available from backend:
 * - entityCount: Backend has per-paper entity counts but not user-level aggregate
 * - subjectDistribution: Backend API not yet implemented
 *
 * @param userId - User ID (not used, stats are for current user)
 * @returns Dashboard statistics
 */
export async function getStats(userId: string): Promise<DashboardStats> {
  // Fetch main stats
  const statsResponse = await apiClient.get<{
    totalPapers: number;
    starredPapers: number;
    processingPapers: number;
    completedPapers: number;
    queriesCount: number;
    sessionsCount: number;
    projectsCount: number;
    llmTokens: number;
  }>('/api/v1/dashboard/stats');

  // Fetch weekly trends
  const trendsResponse = await apiClient.get<{
    dataPoints: Array<{ date: string; papers: number; queries: number }>;
    period: string;
  }>('/api/v1/dashboard/trends?period=weekly');

  const statsData = statsResponse.data;
  const trendsData = trendsResponse.data;

  return {
    paperCount: statsData.totalPapers,
    // Backend limitation: Entity counts are per-paper only (GET /api/v1/entities/{paper_id}/status)
    // User-level aggregate entity count requires a new endpoint or aggregation across all papers
    entityCount: 0,
    llmTokens: statsData.llmTokens,
    queryCount: statsData.queriesCount,
    sessionCount: statsData.sessionsCount,
    weeklyTrend: trendsData.dataPoints.map((dp) => ({
      date: dp.date,
      papers: dp.papers,
      queries: dp.queries,
      tokens: 0, // Backend trends API does not include per-day tokens
    })),
    // Backend limitation: Subject distribution requires paper classification/keywords aggregation
    // Not yet implemented in backend API
    subjectDistribution: [],
    storageUsage: {
      vectorDB: { used: 0, total: 0 },
      blobStorage: { used: 0, total: 0 },
    },
  } as DashboardStats;
}

/**
 * Get monthly token usage
 *
 * GET /api/v1/token-usage/token-usage/monthly
 * Returns aggregated token usage for current month
 *
 * @param year - Year (optional, default current year)
 * @param month - Month (optional, default current month)
 * @returns Monthly token usage statistics
 */
export async function getMonthlyTokenUsage(
  year?: number,
  month?: number
): Promise<{
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  totalCostCny: number;
  requestCount: number;
  dailyBreakdown: Array<{
    date: string;
    tokens: number;
    cost: number;
    requests: number;
  }>;
}> {
  const params = new URLSearchParams();
  if (year) params.append('year', year.toString());
  if (month) params.append('month', month.toString());

  const response = await apiClient.get<{
    total_tokens: number;
    input_tokens: number;
    output_tokens: number;
    total_cost_cny: number;
    request_count: number;
    daily_breakdown: Array<{
      date: string;
      tokens: number;
      cost: number;
      requests: number;
    }>;
  }>(`/api/v1/token-usage/token-usage/monthly${params.toString() ? `?${params.toString()}` : ''}`);

  // apiClient interceptor already unwraps { success, data } -> data
  const data = response.data;

  return {
    totalTokens: data.total_tokens,
    inputTokens: data.input_tokens,
    outputTokens: data.output_tokens,
    totalCostCny: data.total_cost_cny,
    requestCount: data.request_count,
    dailyBreakdown: data.daily_breakdown,
  };
}
