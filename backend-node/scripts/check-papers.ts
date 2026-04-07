import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  const papers = await prisma.papers.findMany({
    where: { userId: 'test-user-001' },
    orderBy: { createdAt: 'desc' },
    take: 5
  });
  
  console.log(`Found ${papers.length} papers for test-user-001:`);
  papers.forEach(p => {
    console.log(`  - ${p.id}: ${p.title} (${p.status})`);
  });
  
  await prisma.$disconnect();
}

main();
