import jwt from 'jsonwebtoken';
import { v4 as uuidv4 } from 'uuid';
import ms, { StringValue } from 'ms';
import {
  TokenPayload,
  AccessTokenPayload,
  RefreshTokenPayload,
  InternalTokenPayload,
} from '../types/auth';
import {
  JWT_ACCESS_SECRET,
  JWT_REFRESH_SECRET,
  JWT_INTERNAL_PRIVATE_KEY,
  JWT_INTERNAL_PUBLIC_KEY,
  ACCESS_TOKEN_EXPIRES_IN,
  REFRESH_TOKEN_EXPIRES_IN,
  INTERNAL_TOKEN_EXPIRES_IN,
} from '../config/auth';

/**
 * Generate access token (HS256)
 * Short-lived token for API authentication
 */
export const generateAccessToken = (payload: TokenPayload): string => {
  return jwt.sign(
    payload,
    JWT_ACCESS_SECRET,
    {
      expiresIn: ACCESS_TOKEN_EXPIRES_IN as StringValue,
      algorithm: 'HS256',
    }
  );
};

/**
 * Generate refresh token (HS256)
 * Long-lived token for obtaining new access tokens
 */
export const generateRefreshToken = (userId: string): { token: string; jti: string } => {
  const jti = uuidv4();
  const token = jwt.sign(
    { sub: userId, jti, type: 'refresh' },
    JWT_REFRESH_SECRET,
    {
      expiresIn: REFRESH_TOKEN_EXPIRES_IN as StringValue,
      algorithm: 'HS256',
    }
  );
  return { token, jti };
};

/**
 * Generate internal service token (RS256)
 * For Node.js -> Python service authentication
 */
export const generateInternalToken = (): { token: string; jti: string } => {
  const jti = uuidv4();
  const token = jwt.sign(
    {
      sub: 'node-gateway',
      aud: 'python-ai-service',
      jti,
    },
    JWT_INTERNAL_PRIVATE_KEY,
    {
      expiresIn: INTERNAL_TOKEN_EXPIRES_IN as StringValue,
      algorithm: 'RS256',
    }
  );
  return { token, jti };
};

/**
 * Verify access token (HS256)
 * Returns decoded payload or throws
 */
export const verifyAccessToken = (token: string): AccessTokenPayload => {
  return jwt.verify(token, JWT_ACCESS_SECRET, {
    algorithms: ['HS256'],
  }) as AccessTokenPayload;
};

/**
 * Verify refresh token (HS256)
 * Returns userId and jti or throws
 */
export const verifyRefreshToken = (token: string): { sub: string; jti: string } => {
  const payload = jwt.verify(token, JWT_REFRESH_SECRET, {
    algorithms: ['HS256'],
  }) as RefreshTokenPayload;

  return { sub: payload.sub, jti: payload.jti };
};

/**
 * Verify internal service token (RS256)
 * Used by Python service to verify calls from Node.js
 */
export const verifyInternalToken = (token: string): InternalTokenPayload => {
  return jwt.verify(token, JWT_INTERNAL_PUBLIC_KEY, {
    algorithms: ['RS256'],
    audience: 'python-ai-service',
  }) as InternalTokenPayload;
};

/**
 * Decode token without verification (for debugging)
 * Does NOT verify signature - use with caution
 */
export const decodeToken = (token: string): jwt.JwtPayload | null => {
  return jwt.decode(token) as jwt.JwtPayload | null;
};

/**
 * Get token expiration time in milliseconds
 */
export const getTokenExpiryMs = (expiryString: string): number => {
  const msValue = ms(expiryString as StringValue);
  if (typeof msValue === 'undefined' || msValue === undefined) {
    throw new Error(`Invalid expiry string: ${expiryString}`);
  }
  return msValue;
};
