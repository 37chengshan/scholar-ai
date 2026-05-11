import { Download, Trash2 } from 'lucide-react';

import { Button } from '@/app/components/ui/button';

interface KnowledgeBaseBatchActionBarProps {
  selectedCount: number;
  onDelete: () => void;
  onClear: () => void;
}

export function KnowledgeBaseBatchActionBar({
  selectedCount,
  onDelete,
  onClear,
}: KnowledgeBaseBatchActionBarProps) {
  if (selectedCount === 0) {
    return null;
  }

  return (
    <div className="mt-3 flex items-center gap-3 rounded-lg bg-muted/50 p-3">
      <span className="text-sm text-muted-foreground">已选择 {selectedCount} 项</span>
      <Button variant="outline" size="sm" onClick={onDelete}>
        <Trash2 className="mr-1.5 h-3.5 w-3.5" />
        删除
      </Button>
      <Button
        variant="outline"
        size="sm"
        disabled
        aria-disabled="true"
        aria-describedby="batch-export-soon-hint"
      >
        <Download className="mr-1.5 h-3.5 w-3.5" />
        导出（即将上线）
      </Button>
      <span id="batch-export-soon-hint" className="text-xs text-muted-foreground">
        批量导出能力即将上线
      </span>
      <Button variant="ghost" size="sm" onClick={onClear}>
        取消选择
      </Button>
    </div>
  );
}
