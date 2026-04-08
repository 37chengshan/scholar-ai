/**
 * UploadHistoryList Component
 *
 * Displays a list of upload history records with:
 * - Empty state when no records
 * - Scrollable list of UploadHistoryCard components
 * - Loading state
 *
 * Per D-01: Expandable details, failure details, safe deletion
 * Per D-02: Progress display, history tracking
 * Per UI-SPEC: Empty state with bilingual text
 */

import { FileText } from 'lucide-react';
import { ScrollArea } from '@/app/components/ui/scroll-area';
import { useLanguage } from '@/app/contexts/LanguageContext';
import { UploadHistoryCard } from './UploadHistoryCard';
import type { UploadHistoryRecord } from '@/services/uploadHistoryApi';

/**
 * Component props
 */
interface UploadHistoryListProps {
  records: UploadHistoryRecord[];
  onDelete: (id: string) => void;
  isLoading: boolean;
}

/**
 * UploadHistoryList Component
 *
 * @param props - Component props
 * @returns JSX element
 */
export function UploadHistoryList({ records, onDelete, isLoading }: UploadHistoryListProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const t = {
    emptyTitle: isZh ? '暂无上传历史' : 'No Upload History',
    emptyDesc: isZh
      ? '您还没有上传任何论文，点击上方上传按钮开始添加您的第一篇论文。'
      : 'You haven\'t uploaded any papers yet. Click the upload button above to add your first paper.',
    loading: isZh ? '加载中...' : 'Loading...',
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <div className="animate-pulse">{t.loading}</div>
      </div>
    );
  }

  // Empty state
  if (records.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <FileText className="w-12 h-12 mb-4 opacity-30" />
        <p className="text-[11px] font-bold uppercase tracking-widest mb-2">{t.emptyTitle}</p>
        <p className="text-[10px] text-center max-w-[280px] leading-relaxed">{t.emptyDesc}</p>
      </div>
    );
  }

  // Record list
  return (
    <ScrollArea className="flex-1">
      <div className="flex flex-col gap-2 pr-2">
        {records.map((record) => (
          <UploadHistoryCard
            key={record.id}
            record={record}
            onDelete={onDelete}
          />
        ))}
      </div>
    </ScrollArea>
  );
}

export type { UploadHistoryListProps };