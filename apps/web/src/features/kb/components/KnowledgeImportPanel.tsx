import { ImportQueueList } from '@/app/components/ImportQueueList';
import type { ImportJob } from '@/services/importApi';

interface KnowledgeImportPanelProps {
  importJobs: ImportJob[];
  onJobComplete: () => void;
}

export function KnowledgeImportPanel({ importJobs, onJobComplete }: KnowledgeImportPanelProps) {
  return (
    <div className="flex min-h-[420px] flex-col border border-border/80 bg-paper-1 p-6">
      <div className="mb-4">
        <h3 className="font-serif text-xl font-semibold">论文导入与处理记录</h3>
        <p className="mt-1 text-sm text-muted-foreground">查看导入中的任务和历史处理记录</p>
      </div>
      <ImportQueueList jobs={importJobs} initiallyExpanded={true} onJobComplete={onJobComplete} />
    </div>
  );
}
