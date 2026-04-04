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
import type { LoginResponse, User } from '@/types';

/**
 * Login with email and password
 *
 * POST /api/auth/login
 * Backend sets HttpOnly cookies (accessToken + refreshToken)
 *
 * @param email - User email
 * @param password - User password
 * @returns Login response with user data
 */
export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/api/auth/login', {
    email,
    password,
  });

  return response.data;
}

/**
 * Logout - Clear session and cookies
 *
 * POST /api/auth/logout
 * Backend clears cookies and invalidates tokens
 */
export async function logout(): Promise<void> {
  await apiClient.post('/api/auth/logout');
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
  await apiClient.post('/api/auth/refresh');
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
  }>('/api/auth/me');

  return response.data.data;
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
  }>('/api/auth/register', {
    email,
    password,
    name,
  });

  return response.data.data;
}