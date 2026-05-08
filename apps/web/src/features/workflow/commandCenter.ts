import type { ChatSession } from '@/app/hooks/useSessions';
import type { ImportJob } from '@/services/importApi';
import type { KnowledgeBase } from '@/services/kbApi';
import type { RecentPaperProgress } from '@/services/dashboardApi';
import type { KnowledgeRunSummary } from '@/features/kb/types/workspace';
import { buildFreshChatHref } from '@/features/chat/chatHandoff';

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
    returnTo?: string;
    origin?: ChatHandoffState['origin'];
    evidenceCount?: number;
  };
};

export type ChatHandoffState = {
  origin: 'dashboard' | 'search' | 'kb' | 'read' | 'notes' | 'compare' | 'review';
  promptDraft: string;
  evidence?: Array<{
    handoffId?: string;
    paperId: string;
    sourceChunkId?: string;
    pageNum?: number;
    claim?: string;
    dimensionId?: string;
    sectionPath?: string;
    contentType?: string;
    text?: string;
    citationJumpUrl?: string;
    title?: string;
  }>;
  returnTo?: string;
};

type CommandLocale = {
  isZh: boolean;
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
      return '已进入队列';
    case 'resolving':
      return '正在解析来源';
    case 'downloading':
      return '正在下载 PDF';
    case 'parsing':
      return '正在解析文档';
    case 'indexing':
      return '正在建立证据索引';
    case 'completed_fulltext_ready':
      return '全文已就绪';
    case 'completed_metadata_only':
      return '仅元数据可用';
    case 'failed':
      return '导入失败';
    case 'cancelled':
      return '导入已取消';
    default:
      return '可查看导入状态';
  }
}

function getLatestUpdatedAt(...values: Array<string | undefined | null>): string {
  const sorted = values
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => new Date(right).getTime() - new Date(left).getTime());
  return sorted[0] || new Date(0).toISOString();
}

function buildChatTargetHref(scope: {
  paperId?: string;
  kbId?: string;
  paperIds?: string[];
}): string {
  const href = buildFreshChatHref(scope);
  const [pathname, search = ''] = href.split('?');
  const params = new URLSearchParams(search);
  params.set('handoff', '1');
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
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
      title: failedJob ? '导入需要处理' : runningJob ? '导入进行中' : '开始添加论文',
      statusLabel: failedJob ? '已阻塞' : runningJob ? summarizeImportStage(runningJob.stage) : importJobs.length > 0 ? '最近导入已完成' : '可开始',
      reason: failedJob
        ? (failedJob.error?.message || '最近一次导入未能完成，需要人工处理。')
        : runningJob
          ? 'ScholarAI 正在处理最新导入任务。'
          : importJobs.length > 0
            ? '最新导入已经完成，可以进入工作区检查结果。'
            : '先把论文来源送入这个知识库。',
      targetHref: `/knowledge-bases/${kb.id}?tab=${importJobs.length > 0 ? 'import-status' : 'uploads'}`,
      targetSurface: 'kb',
      metadata: { kbId: kb.id },
    },
    {
      id: `${kb.id}:kb-dedupe`,
      category: 'kb',
      priority: dedupeJob ? 'blocked' : importJobs.length > 0 ? 'ready' : 'ready',
      title: dedupeJob ? '发现重复内容，等待确认' : '重复检查',
      statusLabel: dedupeJob ? '待确认' : '正常',
      reason: dedupeJob
        ? '有来源与现有馆藏匹配，需要你决定如何处理。'
        : importJobs.length > 0
          ? '当前没有导入任务被重复检查阻塞。'
          : '首次导入后，这里会显示重复检查结果。',
      targetHref: `/knowledge-bases/${kb.id}?tab=import-status`,
      targetSurface: 'kb',
      metadata: { kbId: kb.id },
    },
    {
      id: `${kb.id}:kb-parse`,
      category: 'kb',
      priority: failedJob ? 'blocked' : runningJob ? 'active' : hasPapers && !hasEvidence ? 'active' : hasEvidence ? 'ready' : 'ready',
      title: hasEvidence ? '解析与索引已完成' : runningJob ? '正在准备可检索内容' : '解析与索引',
      statusLabel: hasEvidence ? '已建立索引' : runningJob ? summarizeImportStage(runningJob.stage) : hasPapers ? '等待索引完成' : '等待内容',
      reason: hasEvidence
        ? '当前知识库已经具备可用于证据检索的切片索引。'
        : runningJob
          ? '最新导入仍在向可检索证据阶段推进。'
          : hasPapers
            ? '论文已经存在，但证据切片还未完全就绪。'
            : '至少导入一篇论文后，解析流程才会开始。',
      targetHref: `/knowledge-bases/${kb.id}?tab=${hasEvidence ? 'search' : 'import-status'}`,
      targetSurface: 'kb',
      metadata: { kbId: kb.id },
    },
    {
      id: `${kb.id}:kb-evidence`,
      category: 'kb',
      priority: hasEvidence ? 'ready' : hasPapers ? 'active' : 'ready',
      title: hasEvidence ? '证据已就绪' : '证据准备',
      statusLabel: hasEvidence ? '可用于证据检索' : hasPapers ? '正在准备证据' : '尚未开始',
      reason: hasEvidence
        ? '当前工作区已经可以进行检索与证据定位。'
        : hasPapers
          ? '馆藏中已有论文，但证据仍在准备中。'
          : '首次成功导入后，这里的检索与证据视图才会启用。',
      targetHref: `/knowledge-bases/${kb.id}?tab=${hasEvidence ? 'search' : 'papers'}`,
      targetSurface: 'kb',
      metadata: { kbId: kb.id },
    },
    {
      id: `${kb.id}:kb-chat`,
      category: latestRun ? 'review' : 'kb',
      priority: latestRun?.status === 'failed' ? 'blocked' : hasEvidence ? 'ready' : hasPapers ? 'active' : 'ready',
      title: latestRun ? '综述与问答已就绪' : '问答与综述',
      statusLabel: latestRun?.status === 'failed' ? '综述受阻' : hasEvidence ? '可进入问答/综述' : hasPapers ? '等待证据完成' : '需要论文',
      reason: latestRun?.status === 'failed'
        ? '最近一次综述运行失败，需要跟进处理。'
        : latestRun
          ? '可以打开最近一次综述运行，或直接进入该知识库的问答。'
          : hasEvidence
            ? '现在可以围绕整个知识库提问，或开始撰写综述草稿。'
            : hasPapers
              ? '先完成证据准备，再进入稳定的问答或综述流程。'
              : '先导入论文，这个知识库才能支持问答与综述。',
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

export function buildChatCommand(session: ChatSession, locale: CommandLocale): ResearchCommandItem {
  const { isZh } = locale;
  return {
    id: `chat:${session.id}`,
    category: 'chat',
    priority: session.messageCount > 0 ? 'active' : 'ready',
    title: session.title,
    statusLabel: session.messageCount > 0 ? (isZh ? '进行中' : 'In progress') : (isZh ? '可继续' : 'Ready'),
    reason: session.messageCount > 0
      ? (isZh
          ? `这个会话已经有 ${session.messageCount} 条消息上下文，可以直接继续。`
          : `Continue the session with ${session.messageCount} messages already in context.`)
      : (isZh ? '这个会话已经准备好承接下一个研究问题。' : 'This session is ready for the next research question.'),
    targetHref: `/chat?session=${session.id}`,
    targetSurface: 'chat',
    metadata: { },
  };
}

export function buildHandoffCommand(params: {
  scope: {
    paperId?: string;
    kbId?: string;
    paperIds?: string[];
  };
  handoff: ChatHandoffState;
  locale: CommandLocale;
}): ResearchCommandItem {
  const { scope, handoff, locale } = params;
  const { isZh } = locale;
  const targetHref = buildChatTargetHref(scope);
  const evidenceCount = handoff.evidence?.length || 0;

  return {
    id: `handoff:${handoff.origin}:${scope.paperId || scope.kbId || (scope.paperIds || []).join(',') || 'global'}`,
    category: 'chat',
    priority: 'active',
    title: isZh ? '继续预填的对话交接' : 'Continue prepared Chat handoff',
    statusLabel: isZh ? '可进入对话' : 'Ready in Chat',
    reason: evidenceCount > 0
      ? (isZh
          ? `来自${handoff.origin}的追问已经预填，并携带 ${evidenceCount} 条证据引用。`
          : `A ${handoff.origin} follow-up is prefilled and carries ${evidenceCount} evidence reference${evidenceCount > 1 ? 's' : ''}.`)
      : (isZh
          ? `来自${handoff.origin}的追问已经预填，发送前可先检查。`
          : `A ${handoff.origin} follow-up is prefilled and waiting for review before sending.`),
    targetHref,
    targetSurface: 'chat',
    metadata: {
      kbId: scope.kbId,
      paperId: scope.paperId,
      paperIds: scope.paperIds,
      returnTo: handoff.returnTo,
      origin: handoff.origin,
      evidenceCount,
    },
  };
}

export function buildRecentReadCommand(paper: RecentPaperProgress, locale: CommandLocale): ResearchCommandItem {
  const { isZh } = locale;
  return {
    id: `read:${paper.id}`,
    category: 'read',
    priority: 'recent',
    title: paper.title,
    statusLabel: paper.progress !== null && paper.progress !== undefined
      ? (isZh ? `已读 ${paper.progress}%` : `${paper.progress}% read`)
      : (isZh ? `第 ${paper.currentPage} 页` : `Page ${paper.currentPage}`),
    reason: isZh
      ? `从第 ${paper.currentPage} 页继续${paper.pageCount ? `，共 ${paper.pageCount} 页。` : '。'}`
      : `Resume from page ${paper.currentPage}${paper.pageCount ? ` of ${paper.pageCount}` : ''}.`,
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
  locale: CommandLocale;
}): ResearchCommandItem | null {
  const { kbId, kbName, run, fallbackPaperIds, locale } = params;
  const { isZh } = locale;

  if (run && kbId) {
    return {
      id: `review:${run.id}`,
      category: 'review',
      priority: run.status === 'failed' ? 'blocked' : run.status === 'running' ? 'active' : 'ready',
      title: kbName ? (isZh ? `${kbName} 综述` : `${kbName} review`) : (isZh ? '综述草稿' : 'Review draft'),
      statusLabel: run.status === 'failed'
        ? (isZh ? '失败' : 'failed')
        : run.status === 'running'
          ? (isZh ? '进行中' : 'running')
          : (isZh ? '可继续' : 'ready'),
      reason: run.status === 'failed'
        ? (isZh ? '最近一次综述运行需要先处理，再继续后续工作。' : 'The latest review run needs attention before you continue.')
        : run.status === 'running'
          ? (isZh ? '综述运行仍在进行中，打开后可以检查证据和步骤。' : 'A review run is still in progress; open it to inspect evidence and steps.')
          : (isZh ? '打开最近一次综述运行，从当前证据稿继续。' : 'Open the latest review run and continue from draft evidence.'),
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
      title: isZh ? '比较最近阅读集' : 'Compare recent reading set',
      statusLabel: isZh ? '可开始' : 'Ready',
      reason: isZh
        ? '用最近阅读过的论文作为多论文比较的起点。'
        : 'Use the most recent reading context as a starting point for multi-paper comparison.',
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
