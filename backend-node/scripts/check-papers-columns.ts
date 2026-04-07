import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  const result = await prisma.$queryRaw<Array<{column_name: string, data_type: string}>>
    `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'papers' ORDER BY ordinal_position`;
  
  console.log('papers table columns:');
  result.forEach(col => {
    console.log(`  ${col.column_name}: ${col.data_type}`);
  });
  
  await prisma.$disconnect();
}

main();
