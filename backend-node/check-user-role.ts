import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const user = await prisma.user.findUnique({
    where: { email: 'test@scholarai.com' },
    include: {
      userRoles: {
        include: {
          role: {
            include: {
              permissions: true
            }
          }
        }
      }
    }
  });
  
  console.log('User:', user?.id);
  console.log('Roles:', user?.userRoles.map(ur => ({
    role: ur.role.name,
    permissions: ur.role.permissions.map(p => p.name)
  })));
}

main();
