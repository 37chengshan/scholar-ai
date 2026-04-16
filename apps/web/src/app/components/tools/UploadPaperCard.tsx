/**
 * UploadPaperCard Component
 *
 * Displays upload_paper tool result with progress bar and status.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useLanguage } from '../../contexts/LanguageContext';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { FileText, ExternalLink } from 'lucide-react';

interface UploadPaperCardProps {
  result: {
    paper_id?: string;
    filename?: string;
    status?: string;
    progress?: number;
  };
}

export function UploadPaperCard({ result }: UploadPaperCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const getStatusLabel = () => {
    if (result.progress !== undefined && result.progress < 100) {
      return isZh ? '处理中...' : 'Processing...';
    }
    if (result.status === 'completed' || result.progress === 100) {
      return isZh ? '完成' : 'Complete';
    }
    return isZh ? '上传中...' : 'Uploading...';
  };

  const getBadgeVariant = () => {
    if (result.status === 'error') return 'destructive';
    if (result.progress !== undefined && result.progress < 100) return 'default';
    return 'default';
  };

  const filename = result.filename ?? (isZh ? '未知文件' : 'Unknown file');
  const statusLabel = getStatusLabel();
  const progress = result.progress ?? 0;
  const hasPaperId = !!result.paper_id;

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border border-border/50 bg-card">
      <FileText className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{filename}</div>
        <div className="flex items-center gap-2 mt-1.5">
          <Badge variant={getBadgeVariant()} className="text-xs">
            {statusLabel}
          </Badge>
          {hasPaperId && (
            <a
              href={`/read?paperId=${result.paper_id}`}
              className="flex items-center gap-1 text-xs text-primary hover:underline"
            >
              <ExternalLink className="w-3 h-3" />
              {isZh ? '查看论文' : 'View paper'}
            </a>
          )}
        </div>
        {progress > 0 && progress < 100 && (
          <Progress value={progress} className="h-1.5 mt-2" />
        )}
      </div>
    </div>
  );
}
