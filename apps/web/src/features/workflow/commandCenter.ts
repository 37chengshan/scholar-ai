import type { ChatSession } from '@/app/hooks/useSessions';
import type { ImportJob } from '@/services/importApi';
import type { KnowledgeBase } from '@/services/kbApi';
import type { RecentPaperProgress } from '@/services/dashboardApi';
import type { KnowledgeRunSummary } from '@/features/kb/types/workspace';

export type ResearchCommandItem = {
  id: string;
  category: 'chat' | 'kb' | 'read' | 'review' | 'compare';
  priority: 'blocked' | 'active' | 'ready' | 'recent';
  title: string;
  statusLabel: string;
  reason: string;
  targetHref: string;
  targetSurface: 'dashboard' | 'search' | 'kb' | 'read' | 'chat' | 'notes' | 'compare' | 'review';
  metadata?: {
    kbId?: string;
    paperId?: string;
    runId?: string;
    noteId?: string;
    paperIds?: string[];
  };
};

export type ChatHandoffState = {
  origin: 'dashboard' | 'search' | 'kb' | 'read' | 'notes' | 'compare' | 'review';
  promptDraft: string;
  evidence?: Array<{
    paperId: string;
    sourceChunkId?: string;
    pageNum?: number;
    claim?: string;
  }>;
  returnTo?: string;
};

export interface ChatHandoffNavigationState {
  handoff: ChatHandoffState;
}

const PRIORITY_RANK: Record<ResearchCommandItem['priority'], number> = {
  blocked: 0,
  active: 1,
  ready: 2,
  recent: 3,
};

const KB_STEP_RANK: Record<string, number> = {
  'kb-dedupe': 0,
  'kb-import': 1,
  'kb-parse': 2,
  'kb-evidence': 3,
  'kb-chat': 4,
};

function summarizeImportStage(stage?: string | null): string {
  switch (stage) {
    case 'queued':
      return 'Import queued';
    case 'resolving':
      return 'Resolving source';
    case 'downloading':
      return 'Downloading PDF';
    case 'parsing':
      return 'Parsing document';
    case 'indexing':
      return 'Building evidence index';
    case 'completed_fulltext_ready':
      return 'Full text is ready';
    case 'completed_metadata_only':
      return 'Metadata only';
    case 'failed':
      return 'Import failed';
    case 'cancelled':
      return 'Import cancelled';
    default:
      return 'Import status available';
  }
}

function getLatestUpdatedAt(...values: Array<string | undefined | null>): string {
  const sorted = values
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => new Date(right).getTime() - new Date(left).getTime());
  return sorted[0] || new Date(0).toISOString();
}

export function sortResearchCommands<T extends ResearchCommandItem>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const priorityDelta = PRIORITY_RANK[left.priority] - PRIORITY_RANK[right.priority];
    if (priorityDelta !== 0) {
      return priorityDelta;
    }

    if (left.category === 'kb' && right.category === 'kb') {
      const leftStep = KB_STEP_RANK[left.id.split(':')[1] || 'kb-chat'] ?? 99;
      const rightStep = KB_STEP_RANK[right.id.split(':')[1] || 'kb-chat'] ?? 99;
      if (leftStep !== rightStep) {
        return leftStep - rightStep;
      }
    }

    return left.title.localeCompare(right.title);
  });
}

export function buildKnowledgeBaseReadinessItems(params: {
  kb: KnowledgeBase;
  importJobs: ImportJob[];
  runs: KnowledgeRunSummary[];
}): ResearchCommandItem[] {
  const { kb, importJobs, runs } = params;
  const runningJob = importJobs.find((job) => job.status === 'created' || job.status === 'running');
  const failedJob = importJobs.find((job) => job.status === 'failed');
  const dedupeJob = importJobs.find(
    (job) => job.status === 'awaiting_user_action' || job.dedupe.status === 'awaiting_decision',
  );
  const latestRun = [...runs].sort((left, right) => {
    const leftAt = new Date(left.updatedAt || 0).getTime();
    const rightAt = new Date(right.updatedAt || 0).getTime();
    return rightAt - leftAt;
  })[0];
  const hasEvidence = kb.chunkCount > 0;
  const hasPapers = kb.paperCount > 0;

  return sortResearchCommands([
    {
      id: `${kb.id}:kb-import`,
      category: 'kb',
      priority: failedJob ? 'blocked' : runningJob ? 'active' : importJobs.length > 0 ? 'ready' : 'ready',
      title: failedJob ? 'Import needs attention' : runningJob ? 'Import has been accepted' : 'Import entry point',
      statusLabel: failedJob ? 'Blocked' : runningJob ? summarizeImportStage(runningJob.stage) : importJobs.length > 0 ? 'Recent imports completed' : 'Ready',
      reason: failedJob
        ? (failedJob.error?.message || 'A recent import failed before completion.')
        : runningJob
          ? 'ScholarAI is already processing the newest import task.'
          : importJobs.length > 0
            ? 'The latest import finished; open the workspace to inspect what landed.'
            : 'Start by sending a source into this knowledge base.',
      targetHref: `/knowledge-bases/${kb.id}?tab=${importJobs.length > 0 ? 'import-status' : 'uploads'}`,
      targetSurface: 'kb',
      metadata: { kbId: kb.id },
    },
    {
      id: `${kb.id}:kb-dedupe`,
      category: 'kb',
      priority: dedupeJob ? 'blocked' : importJobs.length > 0 ? 'ready' : 'ready',
      title: dedupeJob ? 'Dedupe decision is waiting' : 'Dedupe state',
      statusLabel: dedupeJob ? 'Needs decision' : 'Clear',
      reason: dedupeJob
        ? 'A source matches existing library content and needs your decision.'
        : importJobs.length > 0
          ? 'No import is currently blocked on duplicate resolution.'
          : 'Duplicate checks will appear here after the first import.',
      targetHref: `/knowledge-bases/${kb.id}?tab=import-status`,
      targetSurface: 'kb',
      metadata: { kbId: kb.id },
    },
    {
      id: `${kb.id}:kb-parse`,
      category: 'kb',
      priority: failedJob ? 'blocked' : runningJob ? 'active' : hasPapers && !hasEvidence ? 'active' : hasEvidence ? 'ready' : 'ready',
      title: hasEvidence ? 'Parsing and indexing completed' : runningJob ? 'Parsing and indexing in progress' : 'Parsing and indexing state',
      statusLabel: hasEvidence ? 'Indexed' : runningJob ? summarizeImportStage(runningJob.stage) : hasPapers ? 'Pending index' : 'Waiting for content',
      reason: hasEvidence
        ? 'The knowledge base already has indexed chunks that can support evidence workflows.'
        : runningJob
          ? 'The newest import is still moving toward searchable evidence.'
          : hasPapers
            ? 'Papers exist, but evidence chunks are not fully ready yet.'
            : 'Import at least one paper before parsing can begin.',
      targetHref: `/knowledge-bases/${kb.id}?tab=${hasEvidence ? 'search' : 'import-status'}`,
      targetSurface: 'kb',
      metadata: { kbId: kb.id },
    },
    {
      id: `${kb.id}:kb-evidence`,
      category: 'kb',
      priority: hasEvidence ? 'ready' : hasPapers ? 'active' : 'ready',
      title: hasEvidence ? 'Evidence is ready to inspect' : 'Evidence readiness',
      statusLabel: hasEvidence ? 'Evidence-ready' : hasPapers ? 'Preparing evidence' : 'Not started',
      reason: hasEvidence
        ? 'Local retrieval and evidence drill-down are ready in this workspace.'
        : hasPapers
          ? 'The library has papers, but evidence still needs to be prepared.'
          : 'Search and evidence views will unlock after the first successful import.',
      targetHref: `/knowledge-bases/${kb.id}?tab=${hasEvidence ? 'search' : 'papers'}`,
      targetSurface: 'kb',
      metadata: { kbId: kb.id },
    },
    {
      id: `${kb.id}:kb-chat`,
      category: latestRun ? 'review' : 'kb',
      priority: latestRun?.status === 'failed' ? 'blocked' : hasEvidence ? 'ready' : hasPapers ? 'active' : 'ready',
      title: latestRun ? 'Review and chat are ready to continue' : 'Chat and review handoff',
      statusLabel: latestRun?.status === 'failed' ? 'Review blocked' : hasEvidence ? 'Ready for Chat / Review' : hasPapers ? 'Waiting for evidence' : 'Needs papers',
      reason: latestRun?.status === 'failed'
        ? 'The latest review run failed and needs follow-up.'
        : latestRun
          ? 'Open the latest review run or jump into KB-scoped chat from one place.'
          : hasEvidence
            ? 'You can now ask KB-scoped questions or start a review draft.'
            : hasPapers
              ? 'Finish evidence preparation before starting robust chat or review flows.'
              : 'Import papers first so this knowledge base can support chat and review.',
      targetHref: latestRun
        ? `/knowledge-bases/${kb.id}?tab=review&runId=${latestRun.id}`
        : `/knowledge-bases/${kb.id}?tab=${hasEvidence ? 'chat' : 'uploads'}`,
      targetSurface: latestRun ? 'review' : 'kb',
      metadata: { kbId: kb.id, runId: latestRun?.id },
    },
  ]);
}

export function pickPrimaryResearchCommand(items: ResearchCommandItem[]): ResearchCommandItem | null {
  return sortResearchCommands(items)[0] ?? null;
}

export function buildChatCommand(session: ChatSession): ResearchCommandItem {
  return {
    id: `chat:${session.id}`,
    category: 'chat',
    priority: session.messageCount > 0 ? 'active' : 'ready',
    title: session.title,
    statusLabel: session.messageCount > 0 ? 'In progress' : 'Ready',
    reason: session.messageCount > 0
      ? `Continue the session with ${session.messageCount} messages already in context.`
      : 'This session is ready for the next research question.',
    targetHref: `/chat?session=${session.id}`,
    targetSurface: 'chat',
    metadata: { },
  };
}

export function buildRecentReadCommand(paper: RecentPaperProgress): ResearchCommandItem {
  return {
    id: `read:${paper.id}`,
    category: 'read',
    priority: 'recent',
    title: paper.title,
    statusLabel: paper.progress !== null && paper.progress !== undefined ? `${paper.progress}% read` : `Page ${paper.currentPage}`,
    reason: `Resume from page ${paper.currentPage}${paper.pageCount ? ` of ${paper.pageCount}` : ''}.`,
    targetHref: `/read/${paper.id}?page=${paper.currentPage || 1}&source=dashboard`,
    targetSurface: 'read',
    metadata: { paperId: paper.id },
  };
}

export function buildReviewOrCompareCommand(params: {
  kbId?: string;
  kbName?: string;
  run?: KnowledgeRunSummary | null;
  fallbackPaperIds?: string[];
}): ResearchCommandItem | null {
  const { kbId, kbName, run, fallbackPaperIds } = params;

  if (run && kbId) {
    return {
      id: `review:${run.id}`,
      category: 'review',
      priority: run.status === 'failed' ? 'blocked' : run.status === 'running' ? 'active' : 'ready',
      title: kbName ? `${kbName} review` : 'Review draft',
      statusLabel: run.status || 'ready',
      reason: run.status === 'failed'
        ? 'The latest review run needs attention before you continue.'
        : run.status === 'running'
          ? 'A review run is still in progress; open it to inspect evidence and steps.'
          : 'Open the latest review run and continue from draft evidence.',
      targetHref: `/knowledge-bases/${kbId}?tab=review&runId=${run.id}`,
      targetSurface: 'review',
      metadata: { kbId, runId: run.id },
    };
  }

  if (fallbackPaperIds && fallbackPaperIds.length >= 2) {
    return {
      id: `compare:${fallbackPaperIds.join(',')}`,
      category: 'compare',
      priority: 'ready',
      title: 'Compare recent reading set',
      statusLabel: 'Ready',
      reason: 'Use the most recent reading context as a starting point for multi-paper comparison.',
      targetHref: `/compare?paper_ids=${fallbackPaperIds.join(',')}`,
      targetSurface: 'compare',
      metadata: { paperIds: fallbackPaperIds },
    };
  }

  return null;
}

export function getCommandUpdatedAt(command: ResearchCommandItem): string {
  return getLatestUpdatedAt(
    command.metadata?.runId,
    command.metadata?.paperId,
    command.metadata?.kbId,
  );
}
