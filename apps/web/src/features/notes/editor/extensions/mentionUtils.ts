/**
 * Mention Utilities
 *
 * Functions for extracting, validating, and serializing mention nodes
 * from TipTap editor content documents.
 */

import type { EditorContentDocument, EditorNode, MentionAttrs } from '../editorTypes';

/** Extracted mention with context */
export interface ExtractedMention {
  id: string;
  label: string;
  type: 'paper' | 'chunk' | 'evidence';
}

/**
 * Extract all mentions from a content document.
 * Recursively walks the node tree to find mention nodes.
 * Accepts any object with a content array (compatible with EditorDocument and EditorContentDocument).
 */
export function extractMentions(doc: { type?: string; content?: Array<Record<string, unknown>> } | null | undefined): ExtractedMention[] {
  if (!doc?.content) return [];

  const mentions: ExtractedMention[] = [];
  walkNodes(doc.content as unknown as EditorNode[], mentions);
  return mentions;
}

function walkNodes(nodes: EditorNode[], acc: ExtractedMention[]): void {
  for (const node of nodes) {
    if (node.type === 'mention' && node.attrs) {
      const attrs = node.attrs as Record<string, unknown>;
      if (
        typeof attrs.id === 'string' &&
        typeof attrs.label === 'string' &&
        (attrs.type === 'paper' || attrs.type === 'chunk' || attrs.type === 'evidence')
      ) {
        acc.push({
          id: attrs.id,
          label: attrs.label,
          type: attrs.type,
        });
      }
    }
    if (node.content) {
      walkNodes(node.content, acc);
    }
  }
}

/**
 * Validate that a mention's referenced entity exists.
 * Returns true if the mention ID matches a known entity.
 */
export function validateMentionReference(
  mention: ExtractedMention,
  knownIds: Set<string>,
): boolean {
  return knownIds.has(mention.id);
}

/**
 * Serialize mentions back into a content document.
 * Replaces mention nodes with their label text if the referenced
 * entity no longer exists (soft cleanup).
 */
export function cleanupOrphanedMentions(
  doc: EditorContentDocument,
  validIds: Set<string>,
): EditorContentDocument {
  return {
    ...doc,
    content: doc.content.map((node) => cleanNode(node, validIds)),
  };
}

function cleanNode(node: EditorNode, validIds: Set<string>): EditorNode {
  if (node.type === 'mention' && node.attrs) {
    const attrs = node.attrs as Record<string, unknown>;
    if (typeof attrs.id === 'string' && !validIds.has(attrs.id)) {
      // Replace orphaned mention with plain text
      return {
        type: 'text',
        text: typeof attrs.label === 'string' ? attrs.label : '',
      };
    }
  }

  if (node.content) {
    return {
      ...node,
      content: node.content.map((child) => cleanNode(child, validIds)),
    };
  }

  return node;
}

/**
 * Group mentions by type for display.
 */
export function groupMentionsByType(
  mentions: ExtractedMention[],
): Record<string, ExtractedMention[]> {
  const groups: Record<string, ExtractedMention[]> = {
    paper: [],
    chunk: [],
    evidence: [],
  };

  for (const mention of mentions) {
    const group = groups[mention.type];
    if (group) {
      group.push(mention);
    }
  }

  return groups;
}
