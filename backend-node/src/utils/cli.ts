import { prisma } from '../config/database';
import { hashPassword } from './crypto';
import { logger } from './logger';

/**
 * CLI tool for admin password reset
 * Usage: npm run admin:reset-password -- --email=user@example.com [--password=newpass123]
 */

interface ResetPasswordArgs {
  email: string;
  password?: string;
}

/**
 * Parse command line arguments
 */
const parseArgs = (): ResetPasswordArgs => {
  const args = process.argv.slice(2);
  const result: ResetPasswordArgs = { email: '' };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--email=')) {
      result.email = arg.substring(8);
    } else if (arg.startsWith('--password=')) {
      result.password = arg.substring(11);
    } else if (arg === '--email' && i + 1 < args.length) {
      result.email = args[++i];
    } else if (arg === '--password' && i + 1 < args.length) {
      result.password = args[++i];
    }
  }

  return result;
};

/**
 * Generate a secure random password
 */
const generateSecurePassword = (): string => {
  const length = 16;
  const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
  let password = '';

  // Ensure at least one of each required character type
  password += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[Math.floor(Math.random() * 26)]; // uppercase
  password += 'abcdefghijklmnopqrstuvwxyz'[Math.floor(Math.random() * 26)]; // lowercase
  password += '0123456789'[Math.floor(Math.random() * 10)]; // number

  // Fill the rest randomly
  for (let i = 3; i < length; i++) {
    password += charset[Math.floor(Math.random() * charset.length)];
  }

  // Shuffle the password
  return password.split('').sort(() => Math.random() - 0.5).join('');
};

/**
 * Reset user password
 */
const resetPassword = async (args: ResetPasswordArgs): Promise<void> => {
  const { email, password: providedPassword } = args;

  if (!email) {
    console.error('Error: Email is required');
    console.error('Usage: npm run admin:reset-password -- --email=user@example.com [--password=newpass123]');
    process.exit(1);
  }

  try {
    // Find user by email
    const user = await prisma.users.findUnique({
      where: { email },
    });

    if (!user) {
      console.error(`Error: User with email "${email}" not found`);
      process.exit(1);
    }

    // Generate password if not provided
    const newPassword = providedPassword || generateSecurePassword();

    // Validate password requirements
    if (newPassword.length < 8) {
      console.error('Error: Password must be at least 8 characters');
      process.exit(1);
    }
    if (!/[A-Z]/.test(newPassword)) {
      console.error('Error: Password must contain at least one uppercase letter');
      process.exit(1);
    }
    if (!/[a-z]/.test(newPassword)) {
      console.error('Error: Password must contain at least one lowercase letter');
      process.exit(1);
    }
    if (!/[0-9]/.test(newPassword)) {
      console.error('Error: Password must contain at least one number');
      process.exit(1);
    }

    // Hash the new password
    const passwordHash = await hashPassword(newPassword);

    // Update user's password
    await prisma.users.update({
      where: { id: user.id },
      data: { passwordHash: passwordHash },
    });

    // Delete all existing refresh tokens for this user
    await prisma.refresh_tokens.deleteMany({
      where: { userId: user.id },
    });

    logger.info({
      message: 'Password reset via CLI',
      userId: user.id,
      email: user.email,
      admin: 'CLI',
    });

    console.log('\n✅ Password reset successful');
    console.log(`Email: ${email}`);
    if (!providedPassword) {
      console.log(`New password: ${newPassword}`);
      console.log('\nPlease share this password securely with the user.');
    } else {
      console.log('Password has been updated.');
    }
    console.log('\nNote: All existing refresh tokens have been revoked.');

  } catch (error) {
    console.error('Error resetting password:', error instanceof Error ? error.message : 'Unknown error');
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
};

// Run if called directly
if (require.main === module) {
  const args = parseArgs();
  resetPassword(args);
}

export { resetPassword };
