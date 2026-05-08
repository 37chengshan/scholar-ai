import { useLanguage } from '@/app/contexts/LanguageContext';

interface AnswerModeBadgeProps {
  mode: 'full' | 'partial' | 'abstain';
}

const modeStyles: Record<AnswerModeBadgeProps['mode'], string> = {
  full: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/40',
  partial: 'bg-amber-500/15 text-amber-700 border-amber-500/40',
  abstain: 'bg-rose-500/15 text-rose-700 border-rose-500/40',
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
