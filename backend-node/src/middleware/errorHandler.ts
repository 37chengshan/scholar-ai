import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { ProblemDetail, ErrorTypes } from '../types/auth';

export interface ApiError extends Error {
  statusCode?: number;
  code?: string;
}

/**
 * Map error codes to RFC 7807 error types
 */
const mapErrorCodeToType = (code: string | undefined): string => {
  const codeMap: Record<string, string> = {
    INVALID_CREDENTIALS: ErrorTypes.INVALID_CREDENTIALS,
    UNAUTHORIZED: ErrorTypes.UNAUTHORIZED,
    FORBIDDEN: ErrorTypes.FORBIDDEN,
    NOT_FOUND: ErrorTypes.NOT_FOUND,
    VALIDATION_ERROR: ErrorTypes.VALIDATION_ERROR,
    CONFLICT: ErrorTypes.CONFLICT,
    INTERNAL_ERROR: ErrorTypes.INTERNAL_ERROR,
    SERVICE_UNAVAILABLE: ErrorTypes.SERVICE_UNAVAILABLE,
    BAD_GATEWAY: ErrorTypes.BAD_GATEWAY,
  };

  return codeMap[code || ''] || ErrorTypes.INTERNAL_ERROR;
};

/**
 * Map HTTP status codes to RFC 7807 error titles
 */
const getErrorTitle = (statusCode: number): string => {
  const titleMap: Record<number, string> = {
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    409: 'Conflict',
    422: 'Unprocessable Entity',
    500: 'Internal Server Error',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
  };

  return titleMap[statusCode] || 'Error';
};

/**
 * Create RFC 7807 Problem Detail response
 */
const createProblemDetail = (
  err: ApiError,
  req: Request,
  requestId: string
): ProblemDetail => {
  const statusCode = err.statusCode || 500;
  const errorType = mapErrorCodeToType(err.code);

  return {
    type: errorType,
    title: getErrorTitle(statusCode),
    status: statusCode,
    detail: err.message || 'An error occurred',
    instance: req.path,
    requestId,
    timestamp: new Date().toISOString(),
  };
};

export const errorHandler = (
  err: ApiError,
  req: Request,
  res: Response,
  _next: NextFunction
) => {
  const statusCode = err.statusCode || 500;
  const message = err.message || 'Internal Server Error';
  const requestId = uuidv4();

  // Log error with structured data
  logger.error({
    error: err.message,
    stack: err.stack,
    statusCode,
    code: err.code,
    requestId,
    path: req.path,
    method: req.method,
  });

  // RFC 7807 format
  const problemDetail = createProblemDetail(err, req, requestId);

  // Response body
  const responseBody: Record<string, unknown> = {
    success: false,
    error: problemDetail,
  };

  // Include legacy format for backward compatibility
  // This will be removed in v2 when all clients migrate
  if (process.env.NODE_ENV === 'development') {
    responseBody._legacy = {
      message,
      code: err.code || 'INTERNAL_ERROR',
      stack: err.stack,
    };
  }

  res.status(statusCode).json(responseBody);
};

/**
 * Create a custom API error
 */
export const createError = (
  message: string,
  statusCode: number,
  code: string
): ApiError => {
  const error = new Error(message) as ApiError;
  error.statusCode = statusCode;
  error.code = code;
  return error;
};

/**
 * Common error creators
 */
export const Errors = {
  unauthorized: (message = 'Unauthorized') =>
    createError(message, 401, 'UNAUTHORIZED'),

  forbidden: (message = 'Forbidden') =>
    createError(message, 403, 'FORBIDDEN'),

  notFound: (message = 'Not Found') =>
    createError(message, 404, 'NOT_FOUND'),

  validation: (message = 'Validation Error') =>
    createError(message, 400, 'VALIDATION_ERROR'),

  conflict: (message = 'Conflict') =>
    createError(message, 409, 'CONFLICT'),

  internal: (message = 'Internal Server Error') =>
    createError(message, 500, 'INTERNAL_ERROR'),

  serviceUnavailable: (message = 'Service Unavailable') =>
    createError(message, 503, 'SERVICE_UNAVAILABLE'),

  invalidCredentials: (message = 'Invalid credentials') =>
    createError(message, 401, 'INVALID_CREDENTIALS'),

  badGateway: (message = 'Bad Gateway') =>
    createError(message, 502, 'BAD_GATEWAY'),
};
