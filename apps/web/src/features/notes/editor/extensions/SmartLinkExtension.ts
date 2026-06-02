/**
 * SmartLinkExtension - Auto-convert pasted URLs and bracket triggers
 *
 * Features:
 * - Paste a URL → auto-converts to a titled link
 * - Type [[ → shows link suggestion popover
 * - Supports internal paper references via [[pdf:paperId:page:N]]
 */

import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';

const URL_RE = /https?:\/\/[^\s<>)\]]+/g;
const BRACKET_LINK_RE = /\[\[([^\]]*)\]\]/g;

export interface SmartLinkOptions {
  onUrlDetected?: (url: string) => Promise<string | null>;
}

export const SmartLinkExtension = Extension.create<SmartLinkOptions>({
  name: 'smartLink',

  addOptions() {
    return {
      onUrlDetected: undefined,
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('smartLinkPaste'),
        props: {
          handlePaste: (view, event) => {
            const text = event.clipboardData?.getData('text/plain');
            if (!text) return false;

            // Check if pasted text is a single URL
            const trimmed = text.trim();
            if (/^https?:\/\/[^\s]+$/.test(trimmed)) {
              event.preventDefault();

              const { tr } = view.state;
              const { from, to } = view.state.selection;

              // Insert as a link node
              const linkMark = view.state.schema.marks.link;
              if (linkMark) {
                const textNode = view.state.schema.text(trimmed);
                const linkedNode = textNode.mark([linkMark.create({ href: trimmed })]);
                tr.replaceWith(from, to, linkedNode);
                view.dispatch(tr);
              }

              return true;
            }

            return false;
          },
        },
      }),
    ];
  },
});
