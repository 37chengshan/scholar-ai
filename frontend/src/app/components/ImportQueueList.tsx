/**
 * Import Queue List Component
 *
 * Embedded in KB detail page showing all import jobs with:
 * - Progress tracking with 5s polling
 * - Status grouping (running, awaiting, completed, failed)
 * - Retry/cancel actions
 * - DedupeDialog placeholder for Wave 5
 *
 * Wave 4: Polling-based (SSE deferred to Wave 5)
 */

import { useState, useEffect, useCallback } from 'react';
import { Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from './ui/button';
import { importApi, ImportJob } from '@/services/importApi';
import { ImportJobRow } from './ImportJobRow';
import { useNavigate } from 'react-router';
import { cn } from './ui/utils';

// Export stage labels for ImportJobRow
export const STAGE_LABELS: Record<string, string> = {
  awaiting_input: '等待输入',
  resolving_source: '解析来源',
  fetching_metadata: '获取元数据',
  downloading_pdf: '下载 PDF',
  validating_pdf: '验证 PDF',
  hashing_file: '计算哈希',
  dedupe_check: '去重检查',
  awaiting_dedupe_decision: '等待决策',
  materializing_paper: '创建论文',
  attaching_to_kb: '关联知识库',
  parsing: '解析内容',
  chunking: '切分内容',
  embedding: '生成向量',
  indexing: '索引存储',
  finalizing: '完成处理',
  completed: '完成',
};

interface ImportQueueListProps {
  kbId: string;
  onJobComplete?: (job: ImportJob) => void;
  initiallyExpanded?: boolean;
}

export function ImportQueueList({
  kbId,
  onJobComplete,
  initiallyExpanded = true,
}: ImportQueueListProps) {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(initiallyExpanded);

  // Poll for updates every 5s for running jobs
  const fetchJobs = useCallback(async () => {
    try {
      const response = await importApi.list(kbId, { limit: 50 });
      if (response.success && response.data) {
        setJobs(response.data.jobs);
        setError(null);
      } else {
        setError('获取导入任务失败');
      }
    } catch (err: any) {
      setError(err.message || '网络错误');
    } finally {
      setLoading(false);
    }
  }, [kbId]);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  // Retry failed job
  const retryJob = async (jobId: string) => {
    try {
      await importApi.retry(jobId);
      // Refresh list immediately after retry
      await fetchJobs();
    } catch (err: any) {
      // Error handled by apiClient interceptor
    }
  };

  // Cancel running job
  const cancelJob = async (jobId: string) => {
    try {
      await importApi.cancel(jobId);
      // Refresh list immediately after cancel
      await fetchJobs();
    } catch (err: any) {
      // Error handled by apiClient interceptor
    }
  };

  // View paper result
  const viewPaper = (paperId: string) => {
    navigate(`/read/${paperId}`);
  };

  // Group jobs by status
  const runningJobs = jobs.filter(
    (j) => j.status === 'running' || j.status === 'queued' || j.status === 'created'
  );
  const awaitingJobs = jobs.filter((j) => j.status === 'awaiting_user_action');
  const completedJobs = jobs.filter((j) => j.status === 'completed');
  const failedJobs = jobs.filter((j) => j.status === 'failed');
  const cancelledJobs = jobs.filter((j) => j.status === 'cancelled');

  // Total counts
  const activeCount = runningJobs.length + awaitingJobs.length;
  const totalCount = jobs.length;

  if (loading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-primary" />
        <span className="ml-2 text-sm text-muted-foreground">加载导入任务...</span>
      </div>
    );
  }

  if (error && jobs.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-red-500">
        {error}
        <Button variant="outline" size="sm" onClick={fetchJobs} className="ml-3">
          重试
        </Button>
      </div>
    );
  }

  if (totalCount === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        暂无导入任务
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Collapsible header */}
      <div
        className="flex items-center justify-between cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <h3 className="text-lg font-medium flex items-center gap-2">
          导入历史
          {activeCount > 0 && (
            <span className="text-xs bg-primary text-white px-2 py-0.5 rounded-full font-bold">
              {activeCount} 个进行中
            </span>
          )}
        </h3>
        <Button variant="ghost" size="sm" className="h-7">
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Job list (collapsible) */}
      {expanded && (
        <div className="space-y-6">
          {/* Running jobs with progress */}
          {runningJobs.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Loader2 className="h-3 w-3 animate-spin" />
                正在处理 ({runningJobs.length})
              </h4>
              <div className="space-y-2">
                {runningJobs.map((job) => (
                  <ImportJobRow
                    key={job.importJobId}
                    job={job}
                    showProgress
                    onCancel={() => cancelJob(job.importJobId)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Awaiting user action - Wave 5 will add DedupeDialog trigger */}
          {awaitingJobs.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-yellow-600 flex items-center gap-2">
                需要确认 ({awaitingJobs.length})
              </h4>
              <div className="space-y-2">
                {awaitingJobs.map((job) => (
                  <ImportJobRow
                    key={job.importJobId}
                    job={job}
                    awaitingAction
                    actionMessage="等待去重决策"
                  />
                ))}
              </div>
              <p className="text-xs text-muted-foreground italic">
                去重决策对话框将在 Wave 5 实现
              </p>
            </div>
          )}

          {/* Recent completed */}
          {completedJobs.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground">
                已完成 ({completedJobs.length})
              </h4>
              <div className="space-y-2">
                {completedJobs.slice(0, 5).map((job) => (
                  <ImportJobRow
                    key={job.importJobId}
                    job={job}
                    showResult
                    onViewResult={
                      job.paper?.paperId
                        ? () => viewPaper(job.paper!.paperId!)
                        : undefined
                    }
                  />
                ))}
                {completedJobs.length > 5 && (
                  <p className="text-xs text-muted-foreground pl-4">
                    还有 {completedJobs.length - 5} 个已完成任务
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Failed with retry */}
          {failedJobs.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-red-600 flex items-center gap-2">
                失败 ({failedJobs.length})
              </h4>
              <div className="space-y-2">
                {failedJobs.map((job) => (
                  <ImportJobRow
                    key={job.importJobId}
                    job={job}
                    showError
                    onRetry={() => retryJob(job.importJobId)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Cancelled (collapsed by default) */}
          {cancelledJobs.length > 0 && (
            <div className="space-y-2 opacity-50">
              <h4 className="text-sm font-medium text-muted-foreground">
                已取消 ({cancelledJobs.length})
              </h4>
              <div className="space-y-2">
                {cancelledJobs.slice(0, 3).map((job) => (
                  <ImportJobRow key={job.importJobId} job={job} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ImportQueueList;