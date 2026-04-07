import { PrismaClient } from '@prisma/client';
import { hashPassword } from './src/utils/crypto';

const prisma = new PrismaClient();

async function main() {
  const hashedPassword = await hashPassword('test123456');
  
  try {
    await prisma.users.deleteMany({ where: { email: 'test@scholarai.com' } });
    
    const user = await prisma.users.create({
      data: {
        id: crypto.randomUUID(),
        email: 'test@scholarai.com',
        password_hash: hashedPassword,
        name: 'Test User',
        email_verified: true,
        updated_at: new Date(),
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