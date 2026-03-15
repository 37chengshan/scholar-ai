import { config } from 'dotenv';
import ms, { StringValue } from 'ms';

config();

/**
 * Validate that a required environment variable is set
 */
const requireEnv = (name: string): string => {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
};

/**
 * Parse duration string (e.g., '15m', '7d') to milliseconds
 */
const parseDuration = (value: string | undefined, defaultValue: StringValue): number => {
  const str = value || defaultValue;
  const result = ms(str as StringValue);
  if (typeof result !== 'number') {
    throw new Error(`Invalid duration string: ${str}`);
  }
  return result;
};

// JWT Secrets
export const JWT_ACCESS_SECRET = requireEnv('JWT_ACCESS_SECRET');
export const JWT_REFRESH_SECRET = requireEnv('JWT_REFRESH_SECRET');
export const JWT_INTERNAL_PRIVATE_KEY = requireEnv('JWT_INTERNAL_PRIVATE_KEY');
export const JWT_INTERNAL_PUBLIC_KEY = requireEnv('JWT_INTERNAL_PUBLIC_KEY');

// Token expiry times (in string format for jsonwebtoken)
export const ACCESS_TOKEN_EXPIRES_IN = process.env.ACCESS_TOKEN_EXPIRES_IN || '15m';
export const REFRESH_TOKEN_EXPIRES_IN = process.env.REFRESH_TOKEN_EXPIRES_IN || '7d';
export const INTERNAL_TOKEN_EXPIRES_IN = process.env.INTERNAL_TOKEN_EXPIRES_IN || '5m';

// Token expiry times in milliseconds (for cookie maxAge)
export const ACCESS_TOKEN_EXPIRY_MS = parseDuration(
  process.env.ACCESS_TOKEN_EXPIRES_IN,
  '15m'
);
export const REFRESH_TOKEN_EXPIRY_MS = parseDuration(
  process.env.REFRESH_TOKEN_EXPIRES_IN,
  '7d'
);
export const INTERNAL_TOKEN_EXPIRY_MS = parseDuration(
  process.env.INTERNAL_TOKEN_EXPIRES_IN,
  '5m'
);

// Cookie settings
export const COOKIE_SETTINGS = {
  accessToken: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict' as const,
    path: '/',
    maxAge: ACCESS_TOKEN_EXPIRY_MS,
  },
  refreshToken: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict' as const,
    path: '/api/auth/refresh',
    maxAge: REFRESH_TOKEN_EXPIRY_MS,
  },
};

// Redis key prefixes
export const REDIS_KEY_PREFIXES = {
  REFRESH_TOKEN: 'refresh:',
  BLACKLIST: 'blacklist:',
};

// Validation
if (JWT_INTERNAL_PRIVATE_KEY.includes('\\n')) {
  // Replace escaped newlines with actual newlines
  process.env.JWT_INTERNAL_PRIVATE_KEY = JWT_INTERNAL_PRIVATE_KEY.replace(/\\n/g, '\n');
}

if (JWT_INTERNAL_PUBLIC_KEY.includes('\\n')) {
  process.env.JWT_INTERNAL_PUBLIC_KEY = JWT_INTERNAL_PUBLIC_KEY.replace(/\\n/g, '\n');
}
