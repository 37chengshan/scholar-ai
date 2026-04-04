import { PrismaClient } from '@prisma/client';
import { hashPassword } from './src/utils/crypto';

const prisma = new PrismaClient();

async function main() {
  const hashedPassword = await hashPassword('test123456');
  
  try {
    // First delete existing user
    await prisma.user.deleteMany({ where: { email: 'test@scholarai.com' } });
    
    const user = await prisma.user.create({
      data: {
        email: 'test@scholarai.com',
        passwordHash: hashedPassword,
        name: 'Test User',
        emailVerified: true,
      },
    });
    console.log('Test user created:', user.id);
  } catch (e) {
    console.error('Error:', e);
  } finally {
    await prisma.$disconnect();
  }
}

main();
