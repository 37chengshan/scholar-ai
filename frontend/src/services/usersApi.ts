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

/**
 * Get user profile
 *
 * GET /api/users/me
 * Returns current user info
 *
 * @returns User profile
 */
export async function getProfile(): Promise<User> {
  const response = await apiClient.get<{
    success: boolean;
    data: User;
  }>('/api/users/me');

  return response.data.data;
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
  avatar?: string;
}): Promise<User> {
  const response = await apiClient.patch<{
    success: boolean;
    data: User;
  }>('/api/users/me', data);

  return response.data.data;
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

  const response = await apiClient.post<{
    success: boolean;
    data: { avatar: string };
  }>('/api/users/me/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data.data;
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
  const response = await apiClient.get<{
    success: boolean;
    data: UserSettings;
  }>('/api/users/me/settings');

  return response.data.data;
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
  const response = await apiClient.patch<{
    success: boolean;
    data: UserSettings;
  }>('/api/users/me/settings', data);

  return response.data.data;
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
  const response = await apiClient.patch<{
    success: boolean;
    data: { message: string };
  }>('/api/users/me/password', {
    currentPassword,
    newPassword,
  });

  return response.data.data;
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
  const response = await apiClient.get<{
    success: boolean;
    data: ApiKey[];
  }>('/api/users/me/api-keys');

  return response.data.data;
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
    success: boolean;
    data: {
      id: string;
      name: string;
      prefix: string;
      createdAt: string;
      key: string;
      message: string;
    };
  }>('/api/users/me/api-keys', {
    name,
  });

  return response.data.data;
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
  await apiClient.delete(`/api/users/me/api-keys/${keyId}`, {
    data: {
      currentPassword,
    },
  });
}

/**
 * Get user dashboard statistics
 *
 * GET /api/users/:id/stats
 * Returns paper count, query count, LLM tokens, weekly trend, etc.
 *
 * Note: Only own stats accessible (or admin)
 *
 * @param userId - User ID
 * @returns Dashboard statistics
 */
export async function getStats(userId: string): Promise<DashboardStats> {
  const response = await apiClient.get<{
    success: boolean;
    data: DashboardStats;
  }>(`/api/users/${userId}/stats`);

  return response.data.data;
}