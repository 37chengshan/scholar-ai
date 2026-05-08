import { useLanguage } from '@/app/contexts/LanguageContext';

interface SourceChunkHighlightProps {
  sourceChunkId: string;
}

export function SourceChunkHighlight({ sourceChunkId }: SourceChunkHighlightProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  if (!sourceChunkId) {
    return null;
  }

  return (
    <div className="mb-2 rounded-md border border-primary/40 bg-primary/10 px-3 py-2 text-xs text-primary">
      {isZh ? '已定位到对应证据片段' : 'Located the referenced evidence excerpt'}
    </div>
  );
}
