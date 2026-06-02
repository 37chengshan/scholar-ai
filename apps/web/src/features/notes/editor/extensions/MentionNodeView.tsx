/**
 * MentionNodeView - React component for rendering mention nodes
 *
 * Renders mentions as styled pill badges with type-specific colors.
 * Paper mentions: blue, Chunk mentions: green, Evidence mentions: amber.
 */

import { NodeViewWrapper } from '@tiptap/react';
import { FileText, Layers, Quote } from 'lucide-react';
import { clsx } from 'clsx';

interface MentionNodeViewProps {
  node: {
    attrs: Record<string, unknown>;
  };
  selected: boolean;
}

const TYPE_STYLES: Record<string, { bg: string; text: string; border: string; Icon: typeof FileText }> = {
  paper: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
    Icon: FileText,
  },
  chunk: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    Icon: Layers,
  },
  evidence: {
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    Icon: Quote,
  },
};

export function MentionNodeView({ node, selected }: MentionNodeViewProps) {
  const attrs = node.attrs as { id?: string; label?: string; type?: string };
  const id = String(attrs.id || '');
  const label = String(attrs.label || '');
  const type = (attrs.type as string) || 'paper';
  const style = TYPE_STYLES[type] || TYPE_STYLES.paper;
  const { Icon } = style;

  return (
    <NodeViewWrapper
      as="span"
      className={clsx(
        'mention-pill inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium align-baseline',
        style.bg,
        style.text,
        style.border,
        selected && 'ring-2 ring-primary/40',
      )}
      data-mention-id={id}
      data-mention-type={type}
    >
      <Icon className="h-3 w-3 shrink-0" />
      <span className="max-w-[160px] truncate">{label}</span>
    </NodeViewWrapper>
  );
}
