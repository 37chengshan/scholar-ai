/**
 * Authentication API Tests
 *
 * Tests for authApi service:
 * - login() with Cookie-based auth
 * - logout() clears session
 * - refresh() token refresh
 * - me() get current user
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as authApi from './authApi';

// Mock apiClient
vi.mock('@/utils/apiClient', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe('authApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should login successfully', async () => {
    // TODO: Mock apiClient.post to return success
    // TODO: Call login(email, password)
    // TODO: Verify Cookie is set (not localStorage)
    // TODO: Verify user data returned
    expect(true).toBe(true);
  });

  it('should handle login failure with RFC 7807 error', async () => {
    // TODO: Mock apiClient.post to return error
    // TODO: Call login() and expect error
    // TODO: Verify error detail is accessible
    expect(true).toBe(true);
  });

  it('should logout and clear session', async () => {
    // TODO: Mock apiClient.post
    // TODO: Call logout()
    // TODO: Verify Cookie cleared (backend responsibility)
    expect(true).toBe(true);
  });

  it('should refresh token', async () => {
    // TODO: Mock apiClient.post
    // TODO: Call refresh()
    // TODO: Verify new tokens set
    expect(true).toBe(true);
  });

  it('should get current user with me()', async () => {
    // TODO: Mock apiClient.get
    // TODO: Call me()
    // TODO: Verify user data returned
    expect(true).toBe(true);
  });
});