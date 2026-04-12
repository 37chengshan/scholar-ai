/**
 * API Client with Axios Interceptors
 *
 * Centralized Axios instance configured for Cookie-based authentication:
 * - withCredentials: true (enables automatic Cookie handling)
 * - Request/response logging in development
 * - 401 error handling with token refresh
 * - Network retry with exponential backoff
 * - Toast notifications for errors
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import toast from 'react-hot-toast';
import { API_BASE_URL, API_CONFIG } from '@/config/api';

/**
 * Custom AuthError class for authentication failures
 *
 * Used when refresh token fails and session is expired.
 * Frontend should handle this by redirecting to login via React Router,
 * NOT by window.location (which breaks SPA navigation).
 */
export class AuthError extends Error {
  constructor(message: string = 'Session expired') {
    super(message);
    this.name = 'AuthError';
  }
}

/**
 * Axios instance with Cookie-based authentication
 *
 * Critical: withCredentials: true enables automatic Cookie handling
 * No Authorization headers needed - Cookies are sent automatically
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_CONFIG.timeout,
  withCredentials: true, // CRITICAL: Enables Cookie-based auth
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor
 *
 * In development mode, log outgoing requests for debugging.
 * No auth headers added - Cookies are sent automatically via withCredentials.
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Log requests in development mode
    if (import.meta.env.DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
        data: config.data,
        params: config.params,
      });
    }

    // Mark refresh requests to prevent infinite loop
    if (config.url?.includes('/auth/refresh')) {
      config.metadata = { ...config.metadata, isRefreshRequest: true };
    }

    return config;
  },
  (error: AxiosError) => {
    // Log request setup errors
    if (import.meta.env.DEV) {
      console.error('[API Request Error]', error);
    }

    return Promise.reject(error);
  }
);

/**
 * Response interceptor - Error handling and token refresh
 *
 * Handles:
 * 1. Unified response unwrapping (extracts data from { success, data } format)
 * 2. Network errors with retry logic
 * 3. 401 errors with token refresh and retry
 * 4. All other errors with toast notifications
 */
apiClient.interceptors.response.use(
  (response) => {
    // Unified response unwrapping
    // Backend returns { success: boolean, data: T } format
    // Extract data for easier consumption in services
    if (response.data?.success && response.data?.data !== undefined) {
      response.data = response.data.data;
    }

    // Log successful responses in development
    if (import.meta.env.DEV) {
      console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
        status: response.status,
        data: response.data,
      });
    }

    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { 
      _retry?: number;
      metadata?: { isRefreshRequest?: boolean };
    };

    // Log errors in development
    if (import.meta.env.DEV) {
      console.error('[API Response Error]', {
        url: originalRequest?.url,
        status: error.response?.status,
        message: error.message,
        data: error.response?.data,
      });
    }

    // Case 1: Network error (no response) - Retry with exponential backoff
    if (!error.response) {
      const retryCount = originalRequest?._retry ? 1 : 0;

      if (retryCount < API_CONFIG.maxRetries) {
        originalRequest._retry = retryCount + 1;

        const delay = API_CONFIG.retryDelayBase * Math.pow(2, retryCount);

        if (import.meta.env.DEV) {
          console.log(`[API Retry] Network error, retrying in ${delay}ms (attempt ${retryCount + 1}/${API_CONFIG.maxRetries})`);
        }

        // Wait before retrying
        await new Promise((resolve) => setTimeout(resolve, delay));

        return apiClient.request(originalRequest);
      }

      // Max retries exhausted
      toast.error('网络连接失败，请检查您的网络连接');
      return Promise.reject(error);
    }

    // Case 2: 401 Unauthorized - Token refresh logic
    if (error.response.status === 401 && !originalRequest._retry) {
      // CRITICAL: Don't redirect/refresh for auth check endpoints
      // These endpoints are expected to return 401 when not logged in
      const isAuthCheckEndpoint = 
        originalRequest?.url?.includes('/auth/me') ||
        originalRequest?.url?.includes('/auth/login') ||
        originalRequest?.url?.includes('/auth/register');
      
      if (isAuthCheckEndpoint) {
        // Just reject, don't trigger refresh or redirect
        return Promise.reject(error);
      }
      
      // CRITICAL: Check if this is a refresh request itself
      // If refresh fails with 401, don't retry - throw AuthError
      if (originalRequest?.metadata?.isRefreshRequest || originalRequest?.url?.includes('/auth/refresh')) {
        if (import.meta.env.DEV) {
          console.error('[API Token Refresh] Refresh request failed with 401, throwing AuthError');
        }
        
        toast.error('会话已过期，请重新登录');
        throw new AuthError('Session expired - refresh token invalid');
      }

      originalRequest._retry = 1;

      try {
        // Attempt to refresh token
        await apiClient.post('/api/v1/auth/refresh');

        if (import.meta.env.DEV) {
          console.log('[API Token Refresh] Token refreshed successfully');
        }

        // Retry original request with new token (Cookie auto-updated)
        return apiClient.request(originalRequest);
      } catch (refreshError: any) {
        // Refresh failed - session expired
        if (import.meta.env.DEV) {
          console.error('[API Token Refresh] Refresh failed:', refreshError);
        }

        toast.error('会话已过期，请重新登录');
        throw new AuthError('Session expired - refresh failed');
      }
    }

    // Case 3: All other errors - Extract error message and show toast
    const errorData = error.response?.data as any;
    const errorMessage = errorData?.error?.detail || errorData?.message || '请求失败';

    toast.error(errorMessage);

    return Promise.reject(error);
  }
);

export default apiClient;

/**
 * Type helper for API responses
 *
 * Backend returns standardized format:
 * {
 *   success: boolean,
 *   data: T,
 *   meta?: { requestId, timestamp }
 * }
 */
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    requestId: string;
    timestamp: string;
  };
}

/**
 * Type helper for API errors
 *
 * Backend returns RFC 7807 ProblemDetail format:
 * {
 *   success: false,
 *   error: {
 *     type: string,
 *     title: string,
 *     status: number,
 *     detail: string,
 *     requestId: string,
 *     timestamp: string
 *   }
 * }
 */
export interface ApiError {
  success: false;
  error: {
    type: string;
    title: string;
    status: number;
    detail: string;
    requestId?: string;
    timestamp?: string;
  };
}
