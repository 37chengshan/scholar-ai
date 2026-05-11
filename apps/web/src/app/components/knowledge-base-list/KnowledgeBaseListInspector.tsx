import type { KnowledgeBase, KBStorageStats } from '@/services/kbApi';
import { getKnowledgeBaseDisplayMetadata } from '@/app/lib/knowledgeBaseDisplay';

import type { KnowledgeBaseSortKey, KnowledgeBaseStatusFilter } from './types';

interface KnowledgeBaseListInspectorProps {
  storageStats: KBStorageStats | null;
  totalKnowledgeBases: number;
  latestKnowledgeBases: KnowledgeBase[];
  viewMode: 'card' | 'list';
  searchQuery: string;
  statusFilter: KnowledgeBaseStatusFilter;
  sortBy: KnowledgeBaseSortKey;
  statusFilterLabels: Record<KnowledgeBaseStatusFilter, string>;
  sortLabels: Record<KnowledgeBaseSortKey, string>;
  onCreate: () => void;
  onEnter: (id: string) => void;
}

export function KnowledgeBaseListInspector({
  storageStats,
  totalKnowledgeBases,
  latestKnowledgeBases,
  viewMode,
  searchQuery,
  statusFilter,
  sortBy,
  statusFilterLabels,
  sortLabels,
  onCreate,
  onEnter,
}: KnowledgeBaseListInspectorProps) {
  return (
    <aside className="hidden h-full w-full flex-col bg-muted/10 lg:flex">
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border/50 bg-background/80 px-5 py-4 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <h2 className="font-serif text-lg font-bold tracking-tight">知识库</h2>
        </div>
        <p className="text-[8px] font-bold uppercase tracking-[0.2em] text-primary">知识库视图</p>
      </div>

      <div className="flex flex-1 flex-col gap-8 overflow-y-auto px-5 py-6">
        <section className="flex flex-col gap-3">
          <h3 className="flex items-center gap-1.5 border-b border-border/50 pb-1.5 font-serif text-[9px] font-bold uppercase tracking-[0.3em] tracking-tight text-muted-foreground">
            概览
          </h3>
          <div className="mt-1 grid grid-cols-2 gap-2">
            <div className="flex flex-col items-center justify-center gap-1 rounded-sm border border-border/50 bg-muted/30 px-3 py-3">
              <div className="text-[8px] uppercase tracking-[0.2em] text-muted-foreground">库数量</div>
              <div className="font-serif text-2xl font-black text-foreground">{storageStats?.kbCount ?? totalKnowledgeBases}</div>
            </div>
            <div className="flex flex-col items-center justify-center gap-1 rounded-sm border border-border/50 bg-muted/30 px-3 py-3">
              <div className="text-[8px] uppercase tracking-[0.2em] text-muted-foreground">论文数</div>
              <div className="font-serif text-2xl font-black text-foreground">{storageStats?.paperCount ?? '—'}</div>
            </div>
          </div>
          <div className="mt-2 rounded-sm border border-primary/20 bg-primary/10 px-3 py-2 text-center text-[10px] text-primary/80">
            {storageStats
              ? `已用 ${storageStats.estimatedStorageMB.toLocaleString()} / ${storageStats.storageLimitMB.toLocaleString()} MB`
              : '创建知识库后汇总数据'}
          </div>
        </section>

        <section className="flex flex-col gap-3">
          <h3 className="flex items-center gap-1.5 border-b border-border/50 pb-1.5 font-serif text-[9px] font-bold uppercase tracking-[0.3em] tracking-tight text-muted-foreground">
            当前筛选
          </h3>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <span className="rounded-sm border border-border/50 bg-background px-2 py-0.5 text-[10px] font-medium tracking-wide text-foreground/75">
              视图 · {viewMode === 'card' ? '卡片' : '列表'}
            </span>
            <span className="rounded-sm border border-border/50 bg-background px-2 py-0.5 text-[10px] font-medium tracking-wide text-foreground/75">
              状态 · {statusFilterLabels[statusFilter]}
            </span>
            <span className="rounded-sm border border-border/50 bg-background px-2 py-0.5 text-[10px] font-medium tracking-wide text-foreground/75">
              排序 · {sortLabels[sortBy]}
            </span>
            {searchQuery ? (
              <span className="rounded-sm border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-medium tracking-wide text-primary shadow-sm shadow-primary/10">
                搜索 · {searchQuery}
              </span>
            ) : null}
          </div>
        </section>

        <section className="flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-border/50 pb-1.5 text-[9px] font-bold uppercase tracking-[0.3em] text-muted-foreground">
            <h3>最近更新</h3>
            <button
              type="button"
              onClick={onCreate}
              className="text-primary transition-all hover:text-primary/80 hover:underline"
            >
              新建
            </button>
          </div>
          <div className="mt-1 flex flex-col gap-1">
            {latestKnowledgeBases.length > 0 ? latestKnowledgeBases.map((kb) => {
              const display = getKnowledgeBaseDisplayMetadata(kb);
              return (
                <button
                  key={kb.id}
                  type="button"
                  onClick={() => onEnter(kb.id)}
                  className="group w-full rounded-sm border border-transparent bg-background px-3 py-2.5 text-left transition-colors hover:border-border/50 hover:bg-muted/50"
                >
                  <div className="line-clamp-1 text-[11px] font-bold text-foreground/80 transition-colors group-hover:text-primary">
                    {display.displayName}
                  </div>
                  <div className="mt-0.5 text-[9px] font-mono text-muted-foreground">
                    {kb.paperCount} 篇论文 · {kb.chunkCount.toLocaleString()} 个分块
                  </div>
                </button>
              );
            }) : (
              <div className="rounded-sm border border-dashed border-border/50 px-3 py-4 text-center text-[10px] text-muted-foreground">
                暂无内容
              </div>
            )}
          </div>
        </section>
      </div>
    </aside>
  );
}
