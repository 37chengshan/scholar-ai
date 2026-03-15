import { Request } from 'express';

/**
 * JWT Token Payloads
 */

export interface TokenPayload {
  sub: string;      // userId
  email: string;
  roles: string[];
  jti: string;      // unique token ID
}

export interface AccessTokenPayload extends TokenPayload {
  iat: number;
  exp: number;
}

export interface RefreshTokenPayload {
  sub: string;      // userId
  jti: string;      // unique token ID
  type: 'refresh';
  iat: number;
  exp: number;
}

export interface InternalTokenPayload {
  sub: string;      // service identifier (e.g., 'node-gateway')
  aud: string;      // audience (e.g., 'python-ai-service')
  jti: string;      // unique token ID
  iat: number;
  exp: number;
}

/**
 * Express Request with Auth User
 */

export interface AuthRequest extends Request {
  user?: {
    sub: string;
    email: string;
    roles: string[];
    jti: string;
  };
}

/**
 * RFC 7807 Problem Details
 * https://tools.ietf.org/html/rfc7807
 */

export interface ProblemDetail {
  type: string;      // URI reference to error documentation
  title: string;     // Human-readable summary
  status: number;    // HTTP status code
  detail?: string;   // Detailed explanation
  instance?: string; // Request path
  requestId: string; // For log correlation
  timestamp: string; // ISO 8601 format
}

/**
 * API Response Types
 */

export interface ApiSuccessResponse<T = unknown> {
  success: true;
  data: T;
  meta: {
    requestId: string;
    timestamp: string;
    pagination?: {
      page: number;
      size: number;
      total: number;
      totalPages: number;
    };
  };
}

export interface ApiErrorResponse {
  success: false;
  error: ProblemDetail;
}

export type ApiResponse<T = unknown> = ApiSuccessResponse<T> | ApiErrorResponse;

/**
 * Error Types (RFC 7807)
 */

export const ErrorTypes = {
  INVALID_CREDENTIALS: '/errors/invalid-credentials',
  UNAUTHORIZED: '/errors/unauthorized',
  FORBIDDEN: '/errors/forbidden',
  NOT_FOUND: '/errors/not-found',
  VALIDATION_ERROR: '/errors/validation-error',
  CONFLICT: '/errors/conflict',
  INTERNAL_ERROR: '/errors/internal-error',
  SERVICE_UNAVAILABLE: '/errors/service-unavailable',
} as const;

export type ErrorType = typeof ErrorTypes[keyof typeof ErrorTypes];

/**
 * Cookie Settings
 */

export interface CookieSettings {
  httpOnly: boolean;
  secure: boolean;
  sameSite: 'strict' | 'lax' | 'none';
  path: string;
  maxAge: number;    // milliseconds
}

/**
 * JWT Configuration
 */

export interface JwtConfig {
  accessSecret: string;
  refreshSecret: string;
  internalPrivateKey: string;
  internalPublicKey: string;
  accessTokenExpiresIn: number;    // milliseconds
  refreshTokenExpiresIn: number;   // milliseconds
  internalTokenExpiresIn: number;  // milliseconds
}
