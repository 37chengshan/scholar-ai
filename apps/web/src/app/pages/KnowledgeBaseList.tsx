import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { CreateKnowledgeBaseDialog } from "../components/CreateKnowledgeBaseDialog";
import { ImportDialog } from "../components/ImportDialog";
import { PaperTexture } from "../components/PaperTexture";
import { WorkspaceShell } from "../components/layout/WorkspaceShell";

import { kbApi, KnowledgeBase, KBCreateData, KBStorageStats } from "@/services/kbApi";
import { useUrlState } from "../../hooks/useUrlState";
import { useKnowledgeBases } from "../../hooks/useKnowledgeBases";
import { toast } from "sonner";

import { KnowledgeBaseBatchActionBar } from "@/app/components/knowledge-base-list/KnowledgeBaseBatchActionBar";
import { KnowledgeBaseListContent as KnowledgeBaseListResults } from "@/app/components/knowledge-base-list/KnowledgeBaseListContent";
import { KnowledgeBaseListInspector } from "@/app/components/knowledge-base-list/KnowledgeBaseListInspector";
import { KnowledgeBaseListToolbar } from "@/app/components/knowledge-base-list/KnowledgeBaseListToolbar";
import type { KnowledgeBaseSortKey, KnowledgeBaseStatusFilter } from "@/app/components/knowledge-base-list/types";

/**
 * Internal KnowledgeBaseList component that uses Router hooks
 * Extracted to ensure Router context is available
 */
function KnowledgeBaseListPageContent() {
  const navigate = useNavigate();

  const statusFilterLabels: Record<KnowledgeBaseStatusFilter, string> = {
    all: '全部',
    ready: '已就绪',
    indexing: '待索引',
    empty: '待导入',
  };

  const sortLabels: Record<KnowledgeBaseSortKey, string> = {
    updated: '最近更新',
    papers: '论文最多',
    name: '名称 A-Z',
  };
  
  // URL-synchronized state (persisted across refresh/navigation)
  const [viewMode, setViewMode] = useUrlState<'card' | 'list'>('view', 'card' as 'card' | 'list');
  const [searchQuery, setSearchQuery] = useUrlState<string>('search', '');
  const [statusFilter, setStatusFilter] = useUrlState<KnowledgeBaseStatusFilter>('status', 'all' as KnowledgeBaseStatusFilter);
  const [sortBy, setSortBy] = useUrlState<KnowledgeBaseSortKey>('sort', 'updated' as KnowledgeBaseSortKey);
  
  // Ephemeral state (not URL-synced)
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [importTarget, setImportTarget] = useState<{ id: string; name: string } | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [showInspector, setShowInspector] = useState(false);

  // Storage stats state
  const [storageStats, setStorageStats] = useState<KBStorageStats | null>(null);
  const [storageStatsLoading, setStorageStatsLoading] = useState(false);

  // Fetch storage stats on mount
  useEffect(() => {
    const fetchStorageStats = async () => {
      setStorageStatsLoading(true);
      try {
        const response = await kbApi.getStorageStats();
        setStorageStats(response);
      } catch (err) {
        console.error('Failed to fetch storage stats:', err);
      } finally {
        setStorageStatsLoading(false);
      }
    };
    fetchStorageStats();
  }, []);

  // API integration - use real data
  const {
    knowledgeBases,
    total,
    loading,
    error,
    refetch,
    createKB,
    deleteKB,
  } = useKnowledgeBases({
    search: searchQuery,
    sortBy,
  });

  const statusFilters: KnowledgeBaseStatusFilter[] = ['all', 'ready', 'indexing', 'empty'];

  // TODO: FE-04 — When real API data exceeds ~50 items, wrap this grid with react-window's VariableSizeGrid

  const sorted = useMemo(() => {
    switch (statusFilter) {
      case 'ready':
        return knowledgeBases.filter((kb) => kb.chunkCount > 0);
      case 'indexing':
        return knowledgeBases.filter((kb) => kb.paperCount > 0 && kb.chunkCount === 0);
      case 'empty':
        return knowledgeBases.filter((kb) => kb.paperCount === 0);
      case 'all':
      default:
        return knowledgeBases;
    }
  }, [knowledgeBases, statusFilter]);

  // Batch operations - call real API using kbApi
  const handleBatchDelete = async () => {
    try {
      const ids = Array.from(selectedIds);
      if (ids.length === 0) return;
      
      // Call real batch delete API via kbApi
      await kbApi.batchDelete(ids);
      toast.success(`成功删除 ${ids.length} 个知识库`);
      setSelectedIds(new Set());
      await refetch();
    } catch (err: any) {
      toast.error(err.message || '批量删除失败');
    }
  };

  const handleCreate = () => {
    setShowCreateDialog(true);
  };

  const handleCreateSubmit = async (data: any) => {
    try {
      await createKB(data);
      toast.success(`知识库「${data.name}」创建成功`);
      setShowCreateDialog(false);
    } catch (err: any) {
      toast.error(err.message || '创建失败');
    }
  };

  const handleEnter = (id: string) => {
    navigate(`/knowledge-bases/${id}`);
  };

  const handleImport = (id: string, name: string) => {
    setImportTarget({ id, name });
  };

  const handleEdit = async (id: string, name: string) => {
    try {
      // Call real update API via kbApi
      await kbApi.update(id, { name });
      toast.success(`知识库已更新`);
      await refetch();
    } catch (err: any) {
      toast.error(err.message || '更新失败');
    }
  };

  const handleDelete = async (id: string, name: string) => {
    try {
      await deleteKB(id);
      toast.success(`知识库「${name}」已删除`);
    } catch (err: any) {
      toast.error(err.message || '删除失败');
    }
  };

  const latestKnowledgeBases = [...sorted].slice(0, 5);

  return (
    <div className="h-full min-h-0 bg-background">
      <WorkspaceShell
        layoutId="knowledge-base-list"
        main={(
          <div className="relative flex-1 min-h-0 overflow-y-auto">
            <PaperTexture />

            <KnowledgeBaseListToolbar
              viewMode={viewMode}
              searchQuery={searchQuery}
              statusFilter={statusFilter}
              sortBy={sortBy}
              isBatchMode={isBatchMode}
              showInspector={showInspector}
              storageStats={storageStats}
              storageStatsLoading={storageStatsLoading}
              statusFilters={statusFilters}
              statusFilterLabels={statusFilterLabels}
              onCreate={handleCreate}
              onToggleInspector={() => setShowInspector((value) => !value)}
              onSearchQueryChange={setSearchQuery}
              onStatusFilterChange={setStatusFilter}
              onSortByChange={setSortBy}
              onToggleBatchMode={() => {
                setIsBatchMode((value) => !value);
                if (isBatchMode) {
                  setSelectedIds(new Set());
                }
              }}
              onViewModeChange={setViewMode}
            />

            <div className="mx-auto max-w-7xl px-6 pb-12">
              {isBatchMode ? (
                <KnowledgeBaseBatchActionBar
                  selectedCount={selectedIds.size}
                  onDelete={() => void handleBatchDelete()}
                  onClear={() => setSelectedIds(new Set())}
                />
              ) : null}

              <div className="container-query pt-4">
                <KnowledgeBaseListResults
                  knowledgeBases={sorted}
                  loading={loading}
                  error={error}
                  searchQuery={searchQuery}
                  statusFilter={statusFilter}
                  viewMode={viewMode}
                  isBatchMode={isBatchMode}
                  selectedIds={selectedIds}
                  onSelectedIdsChange={setSelectedIds}
                  onRetry={refetch}
                  onCreate={handleCreate}
                  onEnter={handleEnter}
                  onImport={handleImport}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                />
              </div>
            </div>

            <CreateKnowledgeBaseDialog
              open={showCreateDialog}
              onOpenChange={setShowCreateDialog}
              onCreate={handleCreateSubmit}
            />

            {importTarget ? (
              <ImportDialog
                open={Boolean(importTarget)}
                onOpenChange={(open) => {
                  if (!open) {
                    setImportTarget(null);
                  }
                }}
                knowledgeBaseId={importTarget.id}
                knowledgeBaseName={importTarget.name}
                onImportComplete={refetch}
              />
            ) : null}

            <div className="mx-auto mt-16 max-w-7xl border-t-2 border-border bg-muted/30/40 px-6 py-16">
              <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
                <div className="space-y-4">
                  <div className="inline-block rounded-sm bg-primary/10 px-3 py-1 text-xs font-semibold tracking-wide text-primary">
                    知识库
                  </div>
                  <h1 className="font-serif text-5xl font-black leading-none tracking-tighter text-foreground md:text-7xl">
                    知识
                    <br />
                    <span className="text-primary">资料馆</span>
                  </h1>
                  <p className="max-w-xl font-sans text-lg font-medium text-muted-foreground">
                    管理论文馆藏、导入处理进度与检索就绪状态，把文献整理成可持续复用的研究资料库。
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
        inspector={showInspector ? (
          <KnowledgeBaseListInspector
            storageStats={storageStats}
            totalKnowledgeBases={total}
            latestKnowledgeBases={latestKnowledgeBases}
            viewMode={viewMode}
            searchQuery={searchQuery}
            statusFilter={statusFilter}
            sortBy={sortBy}
            statusFilterLabels={statusFilterLabels}
            sortLabels={sortLabels}
            onCreate={handleCreate}
            onEnter={handleEnter}
          />
        ) : undefined}
      />
    </div>
  );
}

/**
 * Outer KnowledgeBaseList component wrapper
 * This ensures the Router context is available when KnowledgeBaseListContent is rendered
 */
export function KnowledgeBaseList() {
  return <KnowledgeBaseListPageContent />;
}
