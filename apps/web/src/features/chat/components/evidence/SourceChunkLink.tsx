import { useLanguage } from '@/app/contexts/LanguageContext';

interface SourceChunkLinkProps {
  sourceChunkId: string;
  onOpen: (sourceChunkId: string) => void;
}

export function SourceChunkLink({ sourceChunkId, onOpen }: SourceChunkLinkProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  return (
    <button
      type="button"
      onClick={() => onOpen(sourceChunkId)}
      className="text-[11px] font-medium text-primary underline-offset-2 hover:underline"
    >
      {isZh ? '打开原文' : 'Open source'}
    </button>
  );
}
