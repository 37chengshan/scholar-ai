import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  // Find or create 'user' role
  let userRole = await prisma.roles.findUnique({
    where: { name: 'user' }
  });
  
  if (!userRole) {
    userRole = await prisma.roles.create({
      data: {
        name: 'user',
        description: 'Standard user role'
      }
    });
    console.log('Created user role:', userRole.id);
  }
  
  // Find papers:create permission using resource+action
  const createPermission = await prisma.permissions.findUnique({
    where: {
      resource_action: {
        resource: 'papers',
        action: 'create'
      }
    }
  });
  
  if (createPermission && userRole) {
    console.log('Found permission:', createPermission.id);
    // Update permission to link to role
    await prisma.permissions.update({
      where: { id: createPermission.id },
      data: { role_id: userRole.id }
    });
    console.log('Linked papers:create permission to user role');
  } else if (userRole) {
    // Create permission if not exists
    const newPermission = await prisma.permissions.create({
      data: {
        role_id: userRole.id,
        resource: 'papers',
        action: 'create'
      }
    });
    console.log('Created permission:', newPermission.id);
  }
  
  // Assign role to test user
  const user = await prisma.users.findUnique({
    where: { email: 'test@scholarai.com' }
  });
  
  if (user && userRole) {
    await prisma.user_roles.upsert({
      where: {
        user_id_role_id: {
          user_id: user.id,
          role_id: userRole.id
        }
      },
      update: {},
      create: {
        user_id: user.id,
        role_id: userRole.id
      }
    });
    console.log('Assigned user role to test user');
  }
}

main();
