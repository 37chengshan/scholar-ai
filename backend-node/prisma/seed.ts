import { PrismaClient, Prisma } from '@prisma/client';
import { randomUUID } from 'crypto';

const prisma = new PrismaClient();

// Define roles
const roles = [
  { id: randomUUID(), name: 'user', description: 'Standard user with access to own papers and queries' },
  { id: randomUUID(), name: 'admin', description: 'System administrator with full access' },
];

// Define permissions in resource:action format
const permissions = [
  // Papers permissions
  { id: randomUUID(), resource: 'papers', action: 'create' },
  { id: randomUUID(), resource: 'papers', action: 'read' },
  { id: randomUUID(), resource: 'papers', action: 'update' },
  { id: randomUUID(), resource: 'papers', action: 'delete' },
  // Queries permissions
  { id: randomUUID(), resource: 'queries', action: 'create' },
  { id: randomUUID(), resource: 'queries', action: 'read' },
  // Notes permissions
  { id: randomUUID(), resource: 'notes', action: 'create' },
  { id: randomUUID(), resource: 'notes', action: 'read' },
  { id: randomUUID(), resource: 'notes', action: 'update' },
  { id: randomUUID(), resource: 'notes', action: 'delete' },
  // Chat permissions
  { id: randomUUID(), resource: 'chat', action: 'create' },
  { id: randomUUID(), resource: 'chat', action: 'read' },
  // Sessions permissions
  { id: randomUUID(), resource: 'sessions', action: 'create' },
  { id: randomUUID(), resource: 'sessions', action: 'read' },
  { id: randomUUID(), resource: 'sessions', action: 'delete' },
  // Search permissions
  { id: randomUUID(), resource: 'search', action: 'read' },
  // Annotations permissions
  { id: randomUUID(), resource: 'annotations', action: 'create' },
  { id: randomUUID(), resource: 'annotations', action: 'read' },
  { id: randomUUID(), resource: 'annotations', action: 'update' },
  { id: randomUUID(), resource: 'annotations', action: 'delete' },
  // Reading progress permissions
  { id: randomUUID(), resource: 'reading-progress', action: 'create' },
  { id: randomUUID(), resource: 'reading-progress', action: 'read' },
  { id: randomUUID(), resource: 'reading-progress', action: 'update' },
  // Profile permissions
  { id: randomUUID(), resource: 'profile', action: 'read' },
  { id: randomUUID(), resource: 'profile', action: 'update' },
  // Admin permission
  { id: randomUUID(), resource: 'admin', action: 'all' },
];

// Role to permission mapping
const rolePermissions: Record<string, string[]> = {
  user: [
    'papers:create',
    'papers:read',
    'papers:update',
    'papers:delete',
    'queries:create',
    'queries:read',
    'notes:create',
    'notes:read',
    'notes:update',
    'notes:delete',
    'chat:create',
    'chat:read',
    'sessions:create',
    'sessions:read',
    'sessions:delete',
    'search:read',
    'annotations:create',
    'annotations:read',
    'annotations:update',
    'annotations:delete',
    'reading-progress:create',
    'reading-progress:read',
    'reading-progress:update',
    'profile:read',
    'profile:update',
  ],
  admin: [
    'papers:create',
    'papers:read',
    'papers:update',
    'papers:delete',
    'queries:create',
    'queries:read',
    'notes:create',
    'notes:read',
    'notes:update',
    'notes:delete',
    'chat:create',
    'chat:read',
    'sessions:create',
    'sessions:read',
    'sessions:delete',
    'search:read',
    'annotations:create',
    'annotations:read',
    'annotations:update',
    'annotations:delete',
    'reading-progress:create',
    'reading-progress:read',
    'reading-progress:update',
    'profile:read',
    'profile:update',
    'admin:all',
  ],
};

/**
 * Seed roles into the database
 */
async function seedRoles(): Promise<Map<string, string>> {
  console.log('Seeding roles...');
  const roleMap = new Map<string, string>();

  for (const role of roles) {
    const upserted = await prisma.roles.upsert({
      where: { name: role.name },
      update: { description: role.description },
      create: role,
    });
    roleMap.set(role.name, upserted.id);
    console.log(`  - ${role.name}: ${upserted.id}`);
  }

  return roleMap;
}

/**
 * Seed permissions into the database
 */
async function seedPermissions(): Promise<Map<string, string>> {
  console.log('Seeding permissions...');
  const permissionMap = new Map<string, string>();

  for (const permission of permissions) {
    const key = `${permission.resource}:${permission.action}`;
    const upserted = await prisma.permissions.upsert({
      where: {
        resource_action: {
          resource: permission.resource,
          action: permission.action,
        },
      },
      update: {},
      create: permission,
    });
    permissionMap.set(key, upserted.id);
    console.log(`  - ${key}: ${upserted.id}`);
  }

  return permissionMap;
}

/**
 * Connect permissions to roles
 */
async function connectPermissionsToRoles(
  roleMap: Map<string, string>,
  permissionMap: Map<string, string>
): Promise<void> {
  console.log('Connecting permissions to roles...');

  for (const [roleName, permissionKeys] of Object.entries(rolePermissions)) {
    const roleId = roleMap.get(roleName);
    if (!roleId) {
      console.warn(`  - Role ${roleName} not found, skipping`);
      continue;
    }

    const permissionIds = permissionKeys
      .map((key) => permissionMap.get(key))
      .filter((id): id is string => id !== undefined);

    // Update role with permissions
    await prisma.roles.update({
      where: { id: roleId },
      data: {
        permissions: {
          set: permissionIds.map((id) => ({ id })),
        },
      },
    });

    console.log(`  - ${roleName}: connected ${permissionIds.length} permissions`);
  }
}

/**
 * Main seed function
 */
async function main(): Promise<void> {
  console.log('\n🌱 Starting database seed...\n');

  try {
    // Seed roles first
    const roleMap = await seedRoles();

    // Seed permissions
    const permissionMap = await seedPermissions();

    // Connect permissions to roles
    await connectPermissionsToRoles(roleMap, permissionMap);

    console.log('\n✅ Seed completed successfully!\n');
  } catch (error) {
    console.error('\n❌ Seed failed:', error);
    throw error;
  } finally {
    await prisma.$disconnect();
  }
}

// Run if called directly
if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}

// Export for programmatic use
export { main as seedRolesAndPermissions };
export default main;
