/**
 * Authentication API Service
 *
 * Cookie-based authentication API calls:
 * - login(): Authenticate with email/password
 * - logout(): Clear session
 * - refresh(): Refresh access token
 * - me(): Get current user info
 *
 * All endpoints use Cookie-based auth (no localStorage).
 * Cookies are automatically sent via apiClient withCredentials.
 */

import apiClient from '@/utils/apiClient';
import type { User } from '@/types';

export interface LoginResult {
  user: User;
  meta?: {
    request_id?: string;
    timestamp?: string;
  };
}

/**
 * Login with email and password
 *
 * POST /api/auth/login
 * Backend sets HttpOnly cookies (accessToken + refreshToken)
 *
 * Note: Uses OAuth2 password flow (form-data: username=email, password)
 *
 * @param email - User email
 * @param password - User password
 * @returns Login response with user data
 */
export async function login(email: string, password: string): Promise<LoginResult> {
  // OAuth2 password flow requires form-data with 'username' field
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  const response = await apiClient.post<LoginResult>('/api/v1/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  return response.data as LoginResult;
}

/**
 * Logout - Clear session and cookies
 *
 * POST /api/auth/logout
 * Backend clears cookies and invalidates tokens
 */
export async function logout(): Promise<void> {
  await apiClient.post('/api/v1/auth/logout');
}

/**
 * Refresh access token
 *
 * POST /api/auth/refresh
 * Backend rotates refresh token and sets new cookies
 *
 * Note: This is automatically called by apiClient interceptor on 401 errors.
 * Manual calls are rarely needed.
 */
export async function refresh(): Promise<void> {
  await apiClient.post('/api/v1/auth/refresh');
}

/**
 * Get current authenticated user
 *
 * GET /api/auth/me
 * Returns user info if valid session exists
 *
 * @returns Current user data
 */
export async function me(): Promise<User> {
  const response = await apiClient.get<{
    success: boolean;
    data: User;
  }>('/api/v1/auth/me');

  return response.data as unknown as User;
}

/**
 * Register new user
 *
 * POST /api/auth/register
 *
 * @param email - User email
 * @param password - User password (min 8 chars, requires uppercase, lowercase, number)
 * @param name - User display name
 * @returns Created user data
 */
export async function register(
  email: string,
  password: string,
  name: string
): Promise<User> {
  const response = await apiClient.post<{
    success: boolean;
    data: User;
  }>('/api/v1/auth/register', {
    email,
    password,
    name,
  });

  return response.data as unknown as User;
}

/**
 * Request password reset
 *
 * POST /api/auth/forgot-password
 * Sends reset link to user's email
 *
 * @param email - User email
 */
export async function forgotPassword(email: string): Promise<void> {
  await apiClient.post('/api/v1/auth/forgot-password', { email });
}

/**
 * Reset password with token
 *
 * POST /api/auth/reset-password
 * Validates token and updates password
 *
 * @param token - Reset token from email link
 * @param password - New password (min 8 chars)
 */
export async function resetPassword(token: string, password: string): Promise<void> {
  await apiClient.post('/api/v1/auth/reset-password', {
    token,
    password,
  });
}
