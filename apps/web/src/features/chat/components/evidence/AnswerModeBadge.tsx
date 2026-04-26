interface AnswerModeBadgeProps {
  mode: 'full' | 'partial' | 'abstain';
}

const modeStyles: Record<AnswerModeBadgeProps['mode'], string> = {
  full: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/40',
  partial: 'bg-amber-500/15 text-amber-700 border-amber-500/40',
  abstain: 'bg-rose-500/15 text-rose-700 border-rose-500/40',
};

export function AnswerModeBadge({ mode }: AnswerModeBadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] ${modeStyles[mode]}`}>
      {mode}
    </span>
  );
}
