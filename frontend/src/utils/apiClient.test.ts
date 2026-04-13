/**
 * API Client Tests
 *
 * Tests for Axios client configuration:
 * - withCredentials enabled (Cookie-based auth)
 * - Base URL configuration
 * - 401 interceptor and token refresh
 * - Error handling with toast notifications
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import toast from 'react-hot-toast';
import apiClient, { AuthError } from './apiClient';

// Mock toast module
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

// Mock import.meta.env
vi.stubGlobal('import.meta', {
  env: {
    DEV: false,
    VITE_API_BASE_URL: '',
  },
});

describe('apiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should have withCredentials enabled', () => {
    // Verify withCredentials: true for Cookie-based auth
    expect(apiClient.defaults.withCredentials).toBe(true);
  });

  it('should have correct baseURL', () => {
    // Verify baseURL is configured
    expect(apiClient.defaults.baseURL).toBeDefined();
    expect(
      apiClient.defaults.baseURL === '' || /^http/.test(String(apiClient.defaults.baseURL))
    ).toBe(true);
  });

  it('should handle 401 and refresh token', async () => {
    // Setup: Mock apiClient.post for refresh endpoint
    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValueOnce({ data: { success: true } } as any);

    // Setup: Mock apiClient.request for retry
    const requestSpy = vi.spyOn(apiClient, 'request').mockResolvedValueOnce({
      data: { id: 1, name: 'test' },
      status: 200,
    } as any);

    // Create a 401 error with proper AxiosError structure
    // Note: AxiosError constructor signature is (message, code, config, request, response)
    const originalConfig: InternalAxiosRequestConfig & { _retry?: number; metadata?: { isRefreshRequest?: boolean } } = {
      url: '/api/v1/papers',
      method: 'get',
      headers: {},
      _retry: undefined,
      metadata: undefined,
    } as any;

    const errorResponse = {
      status: 401,
      data: { error: { detail: 'Token expired' } },
      statusText: 'Unauthorized',
      headers: {},
      config: originalConfig,
    };

    const error401 = new AxiosError(
      'Request failed with status code 401',
      AxiosError.UNAUTHORIZED,
      originalConfig, // config must be 3rd argument
      undefined,
      errorResponse as any
    );

    // Trigger the response interceptor error handler
    const interceptor = apiClient.interceptors.response['handlers'][0]?.rejected;
    if (interceptor) {
      const result = await interceptor(error401);

      // Verify refresh endpoint was called
      expect(postSpy).toHaveBeenCalledWith('/api/v1/auth/refresh');

      // Verify original request was retried
      expect(requestSpy).toHaveBeenCalled();

      // Verify the result contains the retry response
      expect(result).toBeDefined();
    }
  });

  it('should show toast on error', async () => {
    // Mock toast.error
    const toastErrorSpy = vi.spyOn(toast, 'error');

    // Create a 500 error response with proper structure
    const originalConfig: InternalAxiosRequestConfig = {
      url: '/api/v1/papers',
      method: 'get',
      headers: {},
    } as any;

    const errorResponse = {
      status: 500,
      data: { error: { detail: 'Internal server error' } },
      statusText: 'Internal Server Error',
      headers: {},
      config: originalConfig,
    };

    const error500 = new AxiosError(
      'Request failed with status code 500',
      AxiosError.ERR_BAD_RESPONSE,
      originalConfig, // config must be 3rd argument
      undefined,
      errorResponse as any
    );

    // Trigger the response interceptor error handler
    const interceptor = apiClient.interceptors.response['handlers'][0]?.rejected;

    if (interceptor) {
      // Call interceptor - it should reject and show toast
      await expect(interceptor(error500)).rejects.toBeDefined();

      // Verify toast.error called with error message
      expect(toastErrorSpy).toHaveBeenCalledWith('Internal server error');
    }
  });

  it('should show network error toast on connection failure', async () => {
    // Mock toast.error
    const toastErrorSpy = vi.spyOn(toast, 'error');

    // Mock apiClient.request to simulate network failure on retry
    const requestSpy = vi.spyOn(apiClient, 'request').mockRejectedValueOnce(
      new AxiosError('Network Error', AxiosError.ERR_NETWORK, undefined, undefined, undefined)
    );

    // Create a network error (no response) with _retry set to max to exhaust retries
    // Note: AxiosError constructor signature is (message, code, config, request, response)
    const originalConfig: InternalAxiosRequestConfig & { _retry?: number } = {
      url: '/api/v1/papers',
      method: 'get',
      headers: {},
      _retry: 3, // Max retries exhausted (retryCount >= maxRetries)
    } as any;

    const networkError = new AxiosError(
      'Network Error',
      AxiosError.ERR_NETWORK,
      originalConfig, // config must be 3rd argument
      undefined,
      undefined // No response for network errors
    );

    // Trigger the response interceptor
    const interceptor = apiClient.interceptors.response['handlers'][0]?.rejected;

    if (interceptor) {
      await expect(interceptor(networkError)).rejects.toBeDefined();

      // Verify network error toast was shown
      expect(toastErrorSpy).toHaveBeenCalledWith('网络连接失败，请检查您的网络连接');
    }
  });

  it('should throw AuthError when refresh fails', async () => {
    // Mock toast.error
    const toastErrorSpy = vi.spyOn(toast, 'error');

    // Mock apiClient.post to fail (refresh endpoint returns 401)
    const refreshError = new AxiosError(
      'Request failed with status code 401',
      AxiosError.UNAUTHORIZED,
      {} as any, // config for refresh error
      undefined,
      {
        status: 401,
        data: {},
        statusText: 'Unauthorized',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      } as any
    );
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(refreshError);

    // Create a 401 error from a non-auth endpoint
    const originalConfig: InternalAxiosRequestConfig & { _retry?: number } = {
      url: '/api/v1/papers',
      method: 'get',
      headers: {},
      _retry: undefined,
    } as any;

    const error401 = new AxiosError(
      'Request failed with status code 401',
      AxiosError.UNAUTHORIZED,
      originalConfig, // config must be 3rd argument
      undefined,
      {
        status: 401,
        data: {},
        statusText: 'Unauthorized',
        headers: {},
        config: originalConfig,
      } as any
    );

    const interceptor = apiClient.interceptors.response['handlers'][0]?.rejected;

    if (interceptor) {
      // Should throw AuthError when refresh fails
      await expect(interceptor(error401)).rejects.toThrow(AuthError);

      // Verify toast shows session expired message
      expect(toastErrorSpy).toHaveBeenCalledWith('会话已过期，请重新登录');
    }
  });

  it('should not retry refresh request on 401', async () => {
    // Create a 401 error from the refresh endpoint itself
    const originalConfig: InternalAxiosRequestConfig & { metadata?: { isRefreshRequest?: boolean } } = {
      url: '/api/v1/auth/refresh',
      method: 'post',
      headers: {},
      metadata: { isRefreshRequest: true },
    } as any;

    const error401 = new AxiosError(
      'Request failed with status code 401',
      AxiosError.UNAUTHORIZED,
      originalConfig, // config must be 3rd argument
      undefined,
      {
        status: 401,
        data: {},
        statusText: 'Unauthorized',
        headers: {},
        config: originalConfig,
      } as any
    );

    const interceptor = apiClient.interceptors.response['handlers'][0]?.rejected;

    if (interceptor) {
      // Should throw AuthError immediately without trying to refresh
      await expect(interceptor(error401)).rejects.toThrow(AuthError);
    }
  });

  it('should not trigger refresh for auth check endpoints', async () => {
    // Create a 401 error from /auth/me endpoint
    const originalConfig: InternalAxiosRequestConfig = {
      url: '/api/v1/auth/me',
      method: 'get',
      headers: {},
    } as any;

    const error401 = new AxiosError(
      'Request failed with status code 401',
      AxiosError.UNAUTHORIZED,
      originalConfig, // config must be 3rd argument
      undefined,
      {
        status: 401,
        data: {},
        statusText: 'Unauthorized',
        headers: {},
        config: originalConfig,
      } as any
    );

    const postSpy = vi.spyOn(apiClient, 'post');

    const interceptor = apiClient.interceptors.response['handlers'][0]?.rejected;

    if (interceptor) {
      // Should reject without calling refresh
      await expect(interceptor(error401)).rejects.toBeDefined();

      // Verify refresh was NOT called
      expect(postSpy).not.toHaveBeenCalled();
    }
  });

  it('should include interceptors', () => {
    // Verify interceptors are configured
    expect(apiClient.interceptors.request).toBeDefined();
    expect(apiClient.interceptors.response).toBeDefined();
  });

  it('should unwrap response with success and data fields', async () => {
    // Create a successful response with wrapped format
    const wrappedResponse = {
      data: { success: true, data: { id: 1, name: 'test paper' } },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {} as InternalAxiosRequestConfig,
    };

    const interceptor = apiClient.interceptors.response['handlers'][0]?.fulfilled;

    if (interceptor) {
      const result = interceptor(wrappedResponse);

      // Verify response was unwrapped
      expect(result.data).toEqual({ id: 1, name: 'test paper' });
    }
  });

  it('should use fallback error message when detail not available', async () => {
    const toastErrorSpy = vi.spyOn(toast, 'error');

    // Create error response without detail field
    const originalConfig: InternalAxiosRequestConfig = {
      url: '/api/v1/papers',
      method: 'post',
      headers: {},
    } as any;

    const errorResponse = new AxiosError(
      'Bad Request',
      '400',
      originalConfig, // config must be 3rd argument
      undefined,
      {
        status: 400,
        data: { message: 'Validation failed' },
        statusText: 'Bad Request',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      }
    );

    const interceptor = apiClient.interceptors.response['handlers'][0]?.rejected;

    if (interceptor) {
      await expect(interceptor(errorResponse)).rejects.toBeDefined();

      // Should use fallback message from 'message' field
      expect(toastErrorSpy).toHaveBeenCalledWith('Validation failed');
    }
  });
});
