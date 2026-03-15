import argon2 from 'argon2';

/**
 * OWASP 2023 recommended Argon2id parameters
 * - Memory: 64 MB (65536 KB)
 * - Iterations: 3
 * - Parallelism: 4 threads
 */
const ARGON2_OPTIONS = {
  type: argon2.argon2id,
  memoryCost: 65536,  // 64 MB
  timeCost: 3,        // 3 iterations
  parallelism: 4,     // 4 parallel threads
} as const;

/**
 * Hash a password using Argon2id
 * @param password - Plain text password
 * @returns Argon2id hash string
 */
export const hashPassword = async (password: string): Promise<string> => {
  try {
    const hash = await argon2.hash(password, ARGON2_OPTIONS);
    return hash;
  } catch (error) {
    throw new Error('Failed to hash password');
  }
};

/**
 * Verify a password against an Argon2id hash
 * Uses constant-time comparison internally to prevent timing attacks
 * @param hash - Stored hash
 * @param password - Plain text password to verify
 * @returns true if password matches, false otherwise
 */
export const verifyPassword = async (
  hash: string,
  password: string
): Promise<boolean> => {
  try {
    return await argon2.verify(hash, password);
  } catch {
    // Return false on any error (invalid hash format, verification failure, etc.)
    return false;
  }
};

/**
 * Check if a hash needs rehashing (for future password policy updates)
 * @param hash - Existing hash
 * @returns true if hash should be updated
 */
export const needsRehash = async (hash: string): Promise<boolean> => {
  try {
    return await argon2.needsRehash(hash, ARGON2_OPTIONS);
  } catch {
    return false;
  }
};
