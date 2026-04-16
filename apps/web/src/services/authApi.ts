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

interface RawUser {
  id: string;
  email: string;
  name: string;
  avatar?: string | null;
  roles?: string[];
  email_verified?: boolean;
  created_at?: string;
  updated_at?: string;
  emailVerified?: boolean;
  createdAt?: string;
  updatedAt?: string;
}

interface AuthPayload {
  user?: RawUser;
  meta?: {
    request_id?: string;
    timestamp?: string;
  };
}

export interface LoginResult {
  user: User;
  meta?: {
    request_id?: string;
    timestamp?: string;
  };
}

function normalizeUser(raw: RawUser): User {
  return {
    id: raw.id,
    email: raw.email,
    name: raw.name,
    avatar: raw.avatar ?? null,
    roles: raw.roles ?? [],
    emailVerified: raw.emailVerified ?? raw.email_verified ?? false,
    createdAt: raw.createdAt ?? raw.created_at,
    updatedAt: raw.updatedAt ?? raw.updated_at,
  };
}

function extractUserPayload(payload: RawUser | AuthPayload): User {
  if ('user' in payload && payload.user) {
    return normalizeUser(payload.user);
  }

  return normalizeUser(payload as RawUser);
}

/**
 * Login with email and password
 *
 * POST /api/auth/login
 * Backend sets HttpOnly cookies (accessToken + refreshToken)
 *
 * Note: Uses OAuth2 password flow (form-data: username=email, password)
 */
export async function login(email: string, password: string): Promise<LoginResult> {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  const response = await apiClient.post<AuthPayload>('/api/v1/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  return {
    user: extractUserPayload(response.data),
    meta: 'meta' in response.data ? response.data.meta : undefined,
  };
}

/** Logout - Clear session and cookies */
export async function logout(): Promise<void> {
  await apiClient.post('/api/v1/auth/logout');
}

/** Refresh access token */
export async function refresh(): Promise<void> {
  await apiClient.post('/api/v1/auth/refresh');
}

/** Get current authenticated user */
export async function me(): Promise<User> {
  const response = await apiClient.get<RawUser>('/api/v1/auth/me');
  return extractUserPayload(response.data);
}

/** Register new user */
export async function register(
  email: string,
  password: string,
  name: string
): Promise<User> {
  const response = await apiClient.post<AuthPayload>('/api/v1/auth/register', {
    email,
    password,
    name,
  });

  return extractUserPayload(response.data);
}

/** Request password reset */
export async function forgotPassword(email: string): Promise<void> {
  await apiClient.post('/api/v1/auth/forgot-password', { email });
}

/** Reset password with token */
export async function resetPassword(token: string, password: string): Promise<void> {
  await apiClient.post('/api/v1/auth/reset-password', {
    token,
    password,
  });
}
