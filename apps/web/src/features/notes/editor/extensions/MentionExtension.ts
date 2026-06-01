/**
 * MentionExtension - @mention support for the editor
 *
 * Provides inline mention nodes for papers, chunks, and evidence.
 * Renders as styled pill badges. Uses TipTap suggestion plugin
 * for the trigger (@) and popover filtering.
 */

import Mention from '@tiptap/extension-mention';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { MentionNodeView } from './MentionNodeView';

export interface MentionSuggestionItem {
  id: string;
  label: string;
  type: 'paper' | 'chunk' | 'evidence';
  description?: string;
}

export const MentionExtension = Mention.configure({
  HTMLAttributes: {
    class: 'mention',
  },
  suggestion: {
    char: '@',
    allowSpaces: true,
    decorationTag: 'span',
    decorationClass: 'mention-decoration',
  },
}).extend({
  addNodeView() {
    return ReactNodeViewRenderer(MentionNodeView);
  },
});
