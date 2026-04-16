/**
 * DedupeDecisionDialog Component
 *
 * Wave 5: Dialog for handling duplicate paper decisions.
 * Per gpt意见.md Section 2.5: 4 decision options.
 *
 * Options:
 * - reuse_existing: Attach existing paper to KB (no new paper created)
 * - import_as_new_version: Create new version linked to existing paper
 * - force_new_paper: Ignore match, create entirely new paper
 * - cancel: Cancel this import job
 */

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/app/components/ui/dialog';
import { Button } from '@/app/components/ui/button';
import { CheckCircle, Layers, FilePlus, XCircle, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  DedupeDecisionRequest,
  DedupeDecisionType,
  ImportJob,
} from '@/services/importApi';

interface MatchedPaperInfo {
  id: string;
  title: string;
  authors?: string[];
  year?: number | null;
}

interface DedupeDecisionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  job: ImportJob;
  matchedPaper?: MatchedPaperInfo;
  matchType?: string;
  onDecision: (decision: DedupeDecisionRequest) => void;
  isLoading?: boolean;
}

const DECISION_OPTIONS: Array<{
  id: DedupeDecisionType;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}> = [
  {
    id: 'reuse_existing',
    label: '复用已有论文',
    description: '将现有论文添加到知识库，不创建新论文',
    icon: CheckCircle,
    color: 'text-green-600',
  },
  {
    id: 'import_as_new_version',
    label: '作为新版本导入',
    description: '创建新版本并关联到现有论文（适用于同一论文的不同版本）',
    icon: Layers,
    color: 'text-blue-600',
  },
  {
    id: 'force_new_paper',
    label: '强制新建',
    description: '忽略匹配，创建全新的论文实体',
    icon: FilePlus,
    color: 'text-orange-600',
  },
  {
    id: 'cancel',
    label: '取消导入',
    description: '放弃本次导入，保持现状',
    icon: XCircle,
    color: 'text-red-600',
  },
];

export function DedupeDecisionDialog({
  open,
  onOpenChange,
  job,
  matchedPaper,
  matchType,
  onDecision,
  isLoading = false,
}: DedupeDecisionDialogProps) {
  const [selected, setSelected] = useState<DedupeDecisionType | null>(null);

  // Get the title from job preview or raw input
  const importTitle = job.preview?.title || job.source?.rawInput || '未知论文';
  const matchedTitle = matchedPaper?.title || '未知论文';

  // Reset selection when dialog opens
  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      setSelected(null);
    }
    onOpenChange(newOpen);
  };

  // Handle decision submission
  const handleConfirm = () => {
    if (!selected) return;

    onDecision({
      decision: selected,
      matchedPaperId: matchedPaper?.id,
    });
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            发现重复论文
          </DialogTitle>
          <DialogDescription className="text-left pt-2">
            导入的论文「{importTitle}」与知识库中已有的论文匹配。
            请选择如何处理这次导入。
          </DialogDescription>
        </DialogHeader>

        {/* Match info card */}
        {matchedPaper && (
          <div className="bg-muted rounded-lg p-3 mb-4">
            <div className="text-sm font-medium text-muted-foreground mb-1">
              匹配的论文
            </div>
            <div className="font-medium">{matchedTitle}</div>
            {matchedPaper.authors && matchedPaper.authors.length > 0 && (
              <div className="text-sm text-muted-foreground mt-1">
                作者: {matchedPaper.authors.slice(0, 3).join(', ')}
                {matchedPaper.authors.length > 3 && ' 等'}
              </div>
            )}
            {matchedPaper.year && (
              <div className="text-sm text-muted-foreground">
                年份: {matchedPaper.year}
              </div>
            )}
            {matchType && (
              <div className="text-xs text-muted-foreground mt-2 italic">
                匹配方式: {matchType}
              </div>
            )}
          </div>
        )}

        {/* Decision options */}
        <div className="space-y-2">
          {DECISION_OPTIONS.map((option) => (
            <button
              key={option.id}
              onClick={() => setSelected(option.id)}
              disabled={isLoading}
              className={cn(
                'flex items-start gap-3 p-3 rounded-lg border w-full text-left transition-colors',
                'hover:border-primary/50',
                selected === option.id
                  ? 'border-primary bg-primary/10'
                  : 'border-border',
                isLoading && 'opacity-50 cursor-not-allowed'
              )}
            >
              <option.icon className={cn('h-5 w-5 mt-0.5', option.color)} />
              <div className="flex-1">
                <div className="font-medium">{option.label}</div>
                <div className="text-sm text-muted-foreground">
                  {option.description}
                </div>
              </div>
              {selected === option.id && (
                <CheckCircle className="h-4 w-4 text-primary" />
              )}
            </button>
          ))}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isLoading}
          >
            取消
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!selected || isLoading}
          >
            {isLoading ? '处理中...' : '确认选择'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default DedupeDecisionDialog;