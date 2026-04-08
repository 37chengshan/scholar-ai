import { PrismaClient } from '@prisma/client';
import { randomUUID } from 'crypto';

describe('Notes Schema - Cross-Paper Support', () => {
  const prisma = new PrismaClient();

  beforeAll(async () => {
    await prisma.$connect();
  });

  afterAll(async () => {
    await prisma.$disconnect();
  });

  afterEach(async () => {
    await prisma.notes.deleteMany();
  });

  describe('Notes model with paperIds array', () => {
    it('should create a note with multiple paperIds', async () => {
      const testUser = await prisma.users.create({
        data: {
          id: randomUUID(),
          email: `test-${Date.now()}@example.com`,
          name: 'Test User',
          passwordHash: 'testhash',
        },
      });

      const paper1 = await prisma.papers.create({
        data: {
          id: randomUUID(),
          title: 'Test Paper 1',
          userId: testUser.id,
          keywords: ['test'],
        },
      });

      const paper2 = await prisma.papers.create({
        data: {
          id: randomUUID(),
          title: 'Test Paper 2',
          userId: testUser.id,
          keywords: ['test'],
        },
      });

      const note = await prisma.notes.create({
        data: {
          userId: testUser.id,
          title: 'Cross-Paper Notes',
          content: 'Comparing methodologies across papers',
          tags: ['comparison', 'methodology'],
          paperIds: [paper1.id, paper2.id],
        },
      });

      expect(note).toBeDefined();
      expect(note.paperIds).toEqual([paper1.id, paper2.id]);
      expect(note.paperIds).toHaveLength(2);

      await prisma.papers.deleteMany({ where: { userId: testUser.id } });
      await prisma.users.delete({ where: { id: testUser.id } });
    });

    it('should create a note with empty paperIds array', async () => {
      const testUser = await prisma.users.create({
        data: {
          id: randomUUID(),
          email: `test-${Date.now()}@example.com`,
          name: 'Test User',
          passwordHash: 'testhash',
        },
      });

      const note = await prisma.notes.create({
        data: {
          userId: testUser.id,
          title: 'Standalone Note',
          content: 'General research notes',
          tags: ['general'],
          paperIds: [],
        },
      });

      expect(note).toBeDefined();
      expect(note.paperIds).toEqual([]);
      expect(note.paperIds).toHaveLength(0);

      await prisma.users.delete({ where: { id: testUser.id } });
    });

    it('should query notes by paperId', async () => {
      const testUser = await prisma.users.create({
        data: {
          id: randomUUID(),
          email: `test-${Date.now()}@example.com`,
          name: 'Test User',
          passwordHash: 'testhash',
        },
      });

      const paper = await prisma.papers.create({
        data: {
          id: randomUUID(),
          title: 'Test Paper for Query',
          userId: testUser.id,
          keywords: ['test'],
        },
      });

      const note1 = await prisma.notes.create({
        data: {
          userId: testUser.id,
          title: 'Note 1',
          content: 'Content 1',
          tags: ['test'],
          paperIds: [paper.id],
        },
      });

      const note2 = await prisma.notes.create({
        data: {
          userId: testUser.id,
          title: 'Note 2',
          content: 'Content 2',
          tags: ['test'],
          paperIds: [paper.id],
        },
      });

      const note3 = await prisma.notes.create({
        data: {
          userId: testUser.id,
          title: 'Note 3',
          content: 'Content 3',
          tags: ['test'],
          paperIds: [],
        },
      });

      const notesForPaper = await prisma.notes.findMany({
        where: {
          paperIds: {
            has: paper.id,
          },
        },
      });

      expect(notesForPaper).toHaveLength(2);
      expect(notesForPaper.map(n => n.id)).toContain(note1.id);
      expect(notesForPaper.map(n => n.id)).toContain(note2.id);
      expect(notesForPaper.map(n => n.id)).not.toContain(note3.id);

      await prisma.papers.deleteMany({ where: { userId: testUser.id } });
      await prisma.users.delete({ where: { id: testUser.id } });
    });

    it('should update paperIds array', async () => {
      const testUser = await prisma.users.create({
        data: {
          id: randomUUID(),
          email: `test-${Date.now()}@example.com`,
          name: 'Test User',
          passwordHash: 'testhash',
        },
      });

      const paper1 = await prisma.papers.create({
        data: {
          id: randomUUID(),
          title: 'Paper 1',
          userId: testUser.id,
          keywords: ['test'],
        },
      });

      const paper2 = await prisma.papers.create({
        data: {
          id: randomUUID(),
          title: 'Paper 2',
          userId: testUser.id,
          keywords: ['test'],
        },
      });

      const paper3 = await prisma.papers.create({
        data: {
          id: randomUUID(),
          title: 'Paper 3',
          userId: testUser.id,
          keywords: ['test'],
        },
      });

      const note = await prisma.notes.create({
        data: {
          userId: testUser.id,
          title: 'Update Test Note',
          content: 'Content',
          tags: ['test'],
          paperIds: [paper1.id],
        },
      });

      const updatedNote = await prisma.notes.update({
        data: {
          paperIds: { push: paper2.id },
        },
        where: { id: note.id },
      });

      expect(updatedNote.paperIds).toEqual([paper1.id, paper2.id]);

      const finalNote = await prisma.notes.update({
        data: {
          paperIds: [paper2.id, paper3.id],
        },
        where: { id: note.id },
      });

      expect(finalNote.paperIds).toEqual([paper2.id, paper3.id]);

      await prisma.papers.deleteMany({ where: { userId: testUser.id } });
      await prisma.users.delete({ where: { id: testUser.id } });
    });
  });
});
