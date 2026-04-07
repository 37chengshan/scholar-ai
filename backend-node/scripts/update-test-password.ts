import { PrismaClient } from '@prisma/client';
import argon2 from 'argon2';

const prisma = new PrismaClient();

async function main() {
  const newPassword = 'TestPassword123!';
  const hash = await argon2.hash(newPassword);
  
  console.log('New hash:', hash);
  
  await prisma.users.update({
    where: { email: 'test@example.com' },
    data: { passwordHash: hash }
  });
  
  console.log('Password updated successfully');
  
  await prisma.$disconnect();
}

main();
