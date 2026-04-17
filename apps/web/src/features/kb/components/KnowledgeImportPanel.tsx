import { ImportQueueList } from '@/app/components/ImportQueueList';
import type { ImportJob } from '@/services/importApi';

interface KnowledgeImportPanelProps {
  importJobs: ImportJob[];
  onJobComplete: () => void;
}

export function KnowledgeImportPanel({ importJobs, onJobComplete }: KnowledgeImportPanelProps) {
  return (
    <div className="bg-white border-2 border-zinc-900 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)] p-6 min-h-[420px] flex flex-col">
      <div className="mb-4">
        <h3 className="font-serif text-xl font-semibold">论文导入与处理记录</h3>
        <p className="text-sm text-zinc-500 mt-1">查看导入中的任务和历史处理记录</p>
      </div>
      <ImportQueueList jobs={importJobs} initiallyExpanded={true} onJobComplete={onJobComplete} />
    </div>
  );
}
