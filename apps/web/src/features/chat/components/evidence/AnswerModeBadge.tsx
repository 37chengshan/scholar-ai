import { useLanguage } from '@/app/contexts/LanguageContext';

interface AnswerModeBadgeProps {
  mode: 'full' | 'partial' | 'abstain';
}

const modeStyles: Record<AnswerModeBadgeProps['mode'], string> = {
  full: 'bg-[var(--color-success)]/15 text-[var(--color-success)] border-[var(--color-success)]/40',
  partial: 'bg-[var(--color-warning)]/15 text-[var(--color-warning)] border-[var(--color-warning)]/40',
  abstain: 'bg-destructive/15 text-destructive border-destructive/40',
};

export function AnswerModeBadge({ mode }: AnswerModeBadgeProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const modeLabel =
    mode === 'full'
      ? (isZh ? '完整回答' : 'Full answer')
      : mode === 'partial'
        ? (isZh ? '部分回答' : 'Partial answer')
        : (isZh ? '谨慎拒答' : 'Abstain');

  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold tracking-[0.02em] ${modeStyles[mode]}`}>
      {modeLabel}
    </span>
  );
}
