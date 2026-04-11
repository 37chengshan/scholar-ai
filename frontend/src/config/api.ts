/**
 * API Configuration
 *
 * Centralized API base URL configuration for all service endpoints.
 * Uses environment variables when available, falls back to defaults.
 */

/**
 * API Version Prefix
 * All API endpoints should use this prefix to ensure consistency
 */
export const API_PREFIX = '/api/v1';

/**
 * Get API base URL from environment or default
 * Development: http://localhost:4000 (Node.js API Gateway)
 * Production: Configured via VITE_API_BASE_URL env var
 */
export const getApiBaseUrl = (): string => {
  // Check for environment variable (Vite convention)
  const envUrl = import.meta.env.VITE_API_BASE_URL;

  if (envUrl) {
    return envUrl;
  }

  // Development: Use relative path to leverage Vite proxy
  // Vite proxy will forward /api/* to http://localhost:8000
  if (import.meta.env.DEV) {
    return '';
  }

  // Production fallback (should be configured via env)
  return 'https://api.scholarai.com';
};

/**
 * API Base URL constant (computed once)
 */
export const API_BASE_URL = getApiBaseUrl();

/**
 * API Configuration constants
 */
export const API_CONFIG = {
  timeout: 30000, // 30 seconds
  maxRetries: 3,
  retryDelayBase: 1000, // 1 second base delay for exponential backoff
};