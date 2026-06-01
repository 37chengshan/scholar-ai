import { describe, expect, it } from 'vitest';

import {
  EditorBlockType,
  BLOCK_TYPE_LABELS,
  ALLOWED_NODE_TYPES,
  ALLOWED_HEADING_LEVELS,
  isValidContentDoc,
} from './editorTypes';

describe('editorTypes', () => {
  describe('EditorBlockType enum', () => {
    it('defines all expected block types', () => {
      expect(EditorBlockType.Paragraph).toBe('paragraph');
      expect(EditorBlockType.Heading1).toBe('heading1');
      expect(EditorBlockType.Heading2).toBe('heading2');
      expect(EditorBlockType.Heading3).toBe('heading3');
      expect(EditorBlockType.CodeBlock).toBe('codeBlock');
      expect(EditorBlockType.Blockquote).toBe('blockquote');
      expect(EditorBlockType.Callout).toBe('callout');
      expect(EditorBlockType.BulletList).toBe('bulletList');
      expect(EditorBlockType.OrderedList).toBe('orderedList');
    });
  });

  describe('BLOCK_TYPE_LABELS', () => {
    it('has labels for all block types', () => {
      for (const blockType of Object.values(EditorBlockType)) {
        expect(BLOCK_TYPE_LABELS[blockType]).toBeDefined();
        expect(BLOCK_TYPE_LABELS[blockType].length).toBeGreaterThan(0);
      }
    });
  });

  describe('ALLOWED_NODE_TYPES', () => {
    it('includes all standard node types', () => {
      expect(ALLOWED_NODE_TYPES.has('doc')).toBe(true);
      expect(ALLOWED_NODE_TYPES.has('paragraph')).toBe(true);
      expect(ALLOWED_NODE_TYPES.has('heading')).toBe(true);
      expect(ALLOWED_NODE_TYPES.has('codeBlock')).toBe(true);
      expect(ALLOWED_NODE_TYPES.has('blockquote')).toBe(true);
      expect(ALLOWED_NODE_TYPES.has('callout')).toBe(true);
      expect(ALLOWED_NODE_TYPES.has('mention')).toBe(true);
      expect(ALLOWED_NODE_TYPES.has('text')).toBe(true);
    });

    it('does not include script or dangerous types', () => {
      expect(ALLOWED_NODE_TYPES.has('script')).toBe(false);
      expect(ALLOWED_NODE_TYPES.has('iframe')).toBe(false);
      expect(ALLOWED_NODE_TYPES.has('object')).toBe(false);
    });
  });

  describe('ALLOWED_HEADING_LEVELS', () => {
    it('allows levels 1-3', () => {
      expect(ALLOWED_HEADING_LEVELS.has(1)).toBe(true);
      expect(ALLOWED_HEADING_LEVELS.has(2)).toBe(true);
      expect(ALLOWED_HEADING_LEVELS.has(3)).toBe(true);
    });

    it('rejects levels outside 1-3', () => {
      expect(ALLOWED_HEADING_LEVELS.has(0)).toBe(false);
      expect(ALLOWED_HEADING_LEVELS.has(4)).toBe(false);
      expect(ALLOWED_HEADING_LEVELS.has(-1)).toBe(false);
    });
  });

  describe('isValidContentDoc', () => {
    it('validates a simple doc with paragraphs', () => {
      const doc = {
        type: 'doc',
        content: [
          { type: 'paragraph', content: [{ type: 'text', text: 'Hello' }] },
        ],
      };
      expect(isValidContentDoc(doc)).toBe(true);
    });

    it('validates a doc with headings', () => {
      const doc = {
        type: 'doc',
        content: [
          { type: 'heading', attrs: { level: 1 }, content: [{ type: 'text', text: 'Title' }] },
          { type: 'paragraph', content: [{ type: 'text', text: 'Body' }] },
        ],
      };
      expect(isValidContentDoc(doc)).toBe(true);
    });

    it('validates a doc with code blocks', () => {
      const doc = {
        type: 'doc',
        content: [
          { type: 'codeBlock', content: [{ type: 'text', text: 'const x = 1;' }] },
        ],
      };
      expect(isValidContentDoc(doc)).toBe(true);
    });

    it('validates a doc with callouts', () => {
      const doc = {
        type: 'doc',
        content: [
          { type: 'callout', attrs: { variant: 'info' }, content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Note' }] }] },
        ],
      };
      expect(isValidContentDoc(doc)).toBe(true);
    });

    it('validates a doc with mentions', () => {
      const doc = {
        type: 'doc',
        content: [
          { type: 'mention', attrs: { id: 'paper-1', label: 'Paper Title', type: 'paper' } },
        ],
      };
      expect(isValidContentDoc(doc)).toBe(true);
    });

    it('rejects null/undefined', () => {
      expect(isValidContentDoc(null)).toBe(false);
      expect(isValidContentDoc(undefined)).toBe(false);
    });

    it('rejects non-doc types', () => {
      expect(isValidContentDoc({ type: 'paragraph', content: [] })).toBe(false);
    });

    it('rejects unknown node types', () => {
      const doc = {
        type: 'doc',
        content: [
          { type: 'script', content: [] },
        ],
      };
      expect(isValidContentDoc(doc)).toBe(false);
    });

    it('rejects invalid heading levels', () => {
      const doc = {
        type: 'doc',
        content: [
          { type: 'heading', attrs: { level: 5 }, content: [] },
        ],
      };
      expect(isValidContentDoc(doc)).toBe(false);
    });

    it('rejects mentions with missing attrs', () => {
      const doc = {
        type: 'doc',
        content: [
          { type: 'mention', attrs: { id: 'x' } },
        ],
      };
      expect(isValidContentDoc(doc)).toBe(false);
    });

    it('rejects mentions with invalid type', () => {
      const doc = {
        type: 'doc',
        content: [
          { type: 'mention', attrs: { id: 'x', label: 'X', type: 'invalid' } },
        ],
      };
      expect(isValidContentDoc(doc)).toBe(false);
    });
  });
});
