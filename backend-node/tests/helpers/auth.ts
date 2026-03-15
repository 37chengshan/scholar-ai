import jwt from 'jsonwebtoken';

const JWT_ACCESS_SECRET = process.env.JWT_ACCESS_SECRET || 'test-access-secret';
const JWT_REFRESH_SECRET = process.env.JWT_REFRESH_SECRET || 'test-refresh-secret';

export interface TestTokenPayload {
  userId: string;
  email: string;
  role?: string;
}

/**
 * Generate a test access token
 */
export function generateTestAccessToken(payload: TestTokenPayload): string {
  return jwt.sign(
    {
      userId: payload.userId,
      email: payload.email,
      role: payload.role || 'user',
      type: 'access',
    },
    JWT_ACCESS_SECRET,
    { expiresIn: '15m' }
  );
}

/**
 * Generate a test refresh token
 */
export function generateTestRefreshToken(userId: string): string {
  return jwt.sign(
    {
      userId,
      type: 'refresh',
    },
    JWT_REFRESH_SECRET,
    { expiresIn: '7d' }
  );
}

/**
 * Generate both access and refresh tokens for testing
 */
export function generateTestTokens(payload: TestTokenPayload): {
  accessToken: string;
  refreshToken: string;
} {
  return {
    accessToken: generateTestAccessToken(payload),
    refreshToken: generateTestRefreshToken(payload.userId),
  };
}

/**
 * Default test user for authenticated requests
 */
export const testUser: TestTokenPayload = {
  userId: 'test-user-id-123',
  email: 'test@example.com',
  role: 'user',
};

/**
 * Default admin test user
 */
export const testAdmin: TestTokenPayload = {
  userId: 'test-admin-id-456',
  email: 'admin@example.com',
  role: 'admin',
};
