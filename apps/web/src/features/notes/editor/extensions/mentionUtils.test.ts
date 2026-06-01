import { describe, expect, it } from 'vitest';

import {
  extractMentions,
  validateMentionReference,
  cleanupOrphanedMentions,
  groupMentionsByType,
} from './mentionUtils';

describe('mentionUtils', () => {
  describe('extractMentions', () => {
    it('extracts mentions from a simple document', () => {
      const doc = {
        type: 'doc' as const,
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'See ' },
              { type: 'mention', attrs: { id: 'paper-1', label: 'Paper A', type: 'paper' } },
              { type: 'text', text: ' for details.' },
            ],
          },
        ],
      };

      const mentions = extractMentions(doc);
      expect(mentions).toHaveLength(1);
      expect(mentions[0]).toEqual({ id: 'paper-1', label: 'Paper A', type: 'paper' });
    });

    it('extracts multiple mentions of different types', () => {
      const doc = {
        type: 'doc' as const,
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'mention', attrs: { id: 'paper-1', label: 'Paper A', type: 'paper' } },
              { type: 'text', text: ' and ' },
              { type: 'mention', attrs: { id: 'chunk-1', label: 'Chunk B', type: 'chunk' } },
              { type: 'text', text: ' and ' },
              { type: 'mention', attrs: { id: 'ev-1', label: 'Evidence C', type: 'evidence' } },
            ],
          },
        ],
      };

      const mentions = extractMentions(doc);
      expect(mentions).toHaveLength(3);
      expect(mentions.map((m) => m.type)).toEqual(['paper', 'chunk', 'evidence']);
    });

    it('handles null/undefined doc', () => {
      expect(extractMentions(null)).toEqual([]);
      expect(extractMentions(undefined)).toEqual([]);
    });

    it('handles doc with no mentions', () => {
      const doc = {
        type: 'doc' as const,
        content: [
          { type: 'paragraph', content: [{ type: 'text', text: 'No mentions here' }] },
        ],
      };
      expect(extractMentions(doc)).toEqual([]);
    });

    it('handles mention with missing attrs gracefully', () => {
      const doc = {
        type: 'doc' as const,
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'mention', attrs: {} },
              { type: 'mention', attrs: { id: 'x', label: 'X', type: 'paper' } },
            ],
          },
        ],
      };

      const mentions = extractMentions(doc);
      expect(mentions).toHaveLength(1);
      expect(mentions[0].id).toBe('x');
    });
  });

  describe('validateMentionReference', () => {
    it('returns true for known IDs', () => {
      const knownIds = new Set(['paper-1', 'chunk-1']);
      expect(validateMentionReference({ id: 'paper-1', label: 'X', type: 'paper' }, knownIds)).toBe(true);
    });

    it('returns false for unknown IDs', () => {
      const knownIds = new Set(['paper-1']);
      expect(validateMentionReference({ id: 'paper-999', label: 'X', type: 'paper' }, knownIds)).toBe(false);
    });
  });

  describe('cleanupOrphanedMentions', () => {
    it('replaces orphaned mentions with text', () => {
      const doc = {
        type: 'doc' as const,
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'See ' },
              { type: 'mention', attrs: { id: 'paper-1', label: 'Paper A', type: 'paper' } },
              { type: 'text', text: ' and ' },
              { type: 'mention', attrs: { id: 'paper-999', label: 'Deleted Paper', type: 'paper' } },
            ],
          },
        ],
      };

      const validIds = new Set(['paper-1']);
      const cleaned = cleanupOrphanedMentions(doc, validIds);

      const paragraph = cleaned.content[0];
      const nodeTypes = paragraph.content?.map((n) => n.type) || [];
      const nodeTexts = paragraph.content?.map((n) => n.text || '') || [];

      // Valid mention should remain as mention
      expect(nodeTypes).toContain('mention');
      // Orphaned mention should be converted to text
      expect(nodeTexts).toContain('Deleted Paper');
      // The orphaned node should be type 'text' not 'mention'
      const orphanNode = paragraph.content?.find((n) => n.text === 'Deleted Paper');
      expect(orphanNode?.type).toBe('text');
    });
  });

  describe('groupMentionsByType', () => {
    it('groups mentions by type', () => {
      const mentions = [
        { id: 'p1', label: 'Paper 1', type: 'paper' as const },
        { id: 'c1', label: 'Chunk 1', type: 'chunk' as const },
        { id: 'p2', label: 'Paper 2', type: 'paper' as const },
        { id: 'e1', label: 'Evidence 1', type: 'evidence' as const },
      ];

      const groups = groupMentionsByType(mentions);
      expect(groups.paper).toHaveLength(2);
      expect(groups.chunk).toHaveLength(1);
      expect(groups.evidence).toHaveLength(1);
    });

    it('returns empty groups for empty input', () => {
      const groups = groupMentionsByType([]);
      expect(groups.paper).toHaveLength(0);
      expect(groups.chunk).toHaveLength(0);
      expect(groups.evidence).toHaveLength(0);
    });
  });
});
