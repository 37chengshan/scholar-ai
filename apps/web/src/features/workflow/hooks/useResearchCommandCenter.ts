import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as sessionsApi from '@/services/sessionsApi';
import { getRecentPapers } from '@/services/dashboardApi';
import { kbApi } from '@/services/kbApi';
import { importApi } from '@/services/importApi';
import { kbReviewApi } from '@/services/kbReviewApi';
import {
  buildChatCommand,
  buildKnowledgeBaseReadinessItems,
  buildRecentReadCommand,
  buildReviewOrCompareCommand,
  pickPrimaryResearchCommand,
  sortResearchCommands,
  type ResearchCommandItem,
} from '@/features/workflow/commandCenter';

export function useResearchCommandCenter() {
  const sessionsQuery = useQuery({
    queryKey: ['dashboard', 'sessions'],
    queryFn: () => sessionsApi.listSessions(8, 'active'),
    staleTime: 45_000,
  });

  const recentPapersQuery = useQuery({
    queryKey: ['dashboard', 'recent-papers'],
    queryFn: () => getRecentPapers(4),
    staleTime: 45_000,
  });

  const knowledgeBasesQuery = useQuery({
    queryKey: ['dashboard', 'knowledge-bases'],
    queryFn: () => kbApi.list({ limit: 4, offset: 0, sortBy: 'updated' }),
    staleTime: 45_000,
  });

  const kbIds = useMemo(
    () => (knowledgeBasesQuery.data?.knowledgeBases || []).map((kb) => kb.id),
    [knowledgeBasesQuery.data?.knowledgeBases],
  );

  const importsAndRunsQuery = useQuery({
    queryKey: ['dashboard', 'kb-command-data', kbIds],
    enabled: kbIds.length > 0,
    staleTime: 30_000,
    queryFn: async () => {
      const knowledgeBases = knowledgeBasesQuery.data?.knowledgeBases || [];
      const results = await Promise.all(
        knowledgeBases.map(async (kb) => {
          const [jobs, runs] = await Promise.all([
            importApi.list(kb.id, { limit: 12 })
              .then((response) => response.data?.jobs || [])
              .catch(() => []),
            kbReviewApi.listRuns(kb.id, { limit: 5, offset: 0 })
              .then((response) => response.items || [])
              .catch(() => []),
          ]);

          return {
            kb,
            importJobs: jobs,
            runs: runs.map((run) => ({
              id: run.id,
              title: `Run ${run.id.slice(0, 8)} (${run.status})`,
              status: run.status,
              updatedAt: run.updatedAt,
            })),
          };
        }),
      );

      return results;
    },
  });

  const commands = useMemo(() => {
    const items: ResearchCommandItem[] = [];

    const chatCommand = sessionsQuery.data?.[0] ? buildChatCommand(sessionsQuery.data[0]) : null;
    if (chatCommand) {
      items.push(chatCommand);
    }

    const primaryKnowledgeCommand = importsAndRunsQuery.data
      ?.map(({ kb, importJobs, runs }) => pickPrimaryResearchCommand(buildKnowledgeBaseReadinessItems({ kb, importJobs, runs })))
      .find(Boolean) || null;
    if (primaryKnowledgeCommand) {
      items.push(primaryKnowledgeCommand);
    }

    const recentReadCommand = recentPapersQuery.data?.[0] ? buildRecentReadCommand(recentPapersQuery.data[0]) : null;
    if (recentReadCommand) {
      items.push(recentReadCommand);
    }

    const reviewCommand = importsAndRunsQuery.data
      ?.map(({ kb, runs }) =>
        buildReviewOrCompareCommand({
          kbId: kb.id,
          kbName: kb.name,
          run: runs[0] || null,
        }),
      )
      .find(Boolean) || buildReviewOrCompareCommand({
        fallbackPaperIds: (recentPapersQuery.data || []).slice(0, 3).map((paper) => paper.id),
      });

    if (reviewCommand) {
      items.push(reviewCommand);
    }

    return sortResearchCommands(items);
  }, [importsAndRunsQuery.data, recentPapersQuery.data, sessionsQuery.data]);

  const knowledgeReadinessByKb = useMemo(() => {
    return (importsAndRunsQuery.data || []).map(({ kb, importJobs, runs }) => ({
      kb,
      items: buildKnowledgeBaseReadinessItems({ kb, importJobs, runs }),
    }));
  }, [importsAndRunsQuery.data]);

  return {
    commands,
    knowledgeReadinessByKb,
    sessions: sessionsQuery.data || [],
    recentPapers: recentPapersQuery.data || [],
    knowledgeBases: knowledgeBasesQuery.data?.knowledgeBases || [],
    loading:
      sessionsQuery.isLoading
      || recentPapersQuery.isLoading
      || knowledgeBasesQuery.isLoading
      || importsAndRunsQuery.isLoading,
  };
}
