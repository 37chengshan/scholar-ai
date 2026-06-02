/**
 * CalloutExtension - Custom TipTap node for callout blocks
 *
 * Supports variants: info, warning, tip, important
 * Renders as a styled blockquote with icon indicator.
 */

import { Node, mergeAttributes } from '@tiptap/core';

export interface CalloutOptions {
  HTMLAttributes: Record<string, unknown>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    callout: {
      toggleCallout: (variant?: string) => ReturnType;
    };
  }
}

export const CalloutExtension = Node.create<CalloutOptions>({
  name: 'callout',

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  content: 'block+',
  group: 'block',
  defining: true,

  addAttributes() {
    return {
      variant: {
        default: 'info',
        parseHTML: (element) => element.getAttribute('data-variant') || 'info',
        renderHTML: (attributes) => ({
          'data-variant': attributes.variant,
        }),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-callout]',
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, {
        'data-callout': '',
        class: 'callout-block rounded-lg border-l-4 border-primary/40 bg-primary/5 px-4 py-3 my-2',
      }),
      0,
    ];
  },

  addCommands() {
    return {
      toggleCallout:
        (variant = 'info') =>
        ({ commands }) => {
          return commands.toggleNode(this.name, 'paragraph', { variant });
        },
    };
  },

  addKeyboardShortcuts() {
    return {
      'Mod-Shift-c': () => this.editor.commands.toggleCallout(),
    };
  },
});
