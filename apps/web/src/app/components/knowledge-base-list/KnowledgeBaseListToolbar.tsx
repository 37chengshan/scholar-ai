import { ArrowUpDown, CheckSquare, Grid, HardDrive, List, Loader2, PanelRightClose, PanelRightOpen, Plus, Search } from 'lucide-react';

import type { KBStorageStats } from '@/services/kbApi';

import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select';

import type { KnowledgeBaseSortKey, KnowledgeBaseStatusFilter } from './types';

interface KnowledgeBaseListToolbarProps {
  viewMode: 'card' | 'list';
  searchQuery: string;
  statusFilter: KnowledgeBaseStatusFilter;
  sortBy: KnowledgeBaseSortKey;
  isBatchMode: boolean;
  showInspector: boolean;
  storageStats: KBStorageStats | null;
  storageStatsLoading: boolean;
  statusFilters: KnowledgeBaseStatusFilter[];
  statusFilterLabels: Record<KnowledgeBaseStatusFilter, string>;
  onCreate: () => void;
  onToggleInspector: () => void;
  onSearchQueryChange: (value: string) => void;
  onStatusFilterChange: (value: KnowledgeBaseStatusFilter) => void;
  onSortByChange: (value: KnowledgeBaseSortKey) => void;
  onToggleBatchMode: () => void;
  onViewModeChange: (value: 'card' | 'list') => void;
}

export function KnowledgeBaseListToolbar({
  viewMode,
  searchQuery,
  statusFilter,
  sortBy,
  isBatchMode,
  showInspector,
  storageStats,
  storageStatsLoading,
  statusFilters,
  statusFilterLabels,
  onCreate,
  onToggleInspector,
  onSearchQueryChange,
  onStatusFilterChange,
  onSortByChange,
  onToggleBatchMode,
  onViewModeChange,
}: KnowledgeBaseListToolbarProps) {
  return (
    <div className="sticky top-0 z-10 border-b border-border/70 bg-background/90 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl px-6 py-4">
        <div className="flex flex-col items-center justify-between gap-4 border border-border/70 bg-muted/30 p-4 sm:flex-row">
          <div className="flex items-center gap-2 self-start sm:self-center">
            <Button
              onClick={onCreate}
              className="flex items-center gap-2 rounded-sm bg-primary px-5 py-3 font-semibold tracking-wide text-primary-foreground transition-colors hover:bg-primary/90"
            >
              <Plus className="h-5 w-5" />
              创建知识库
            </Button>
            <button
              type="button"
              onClick={onToggleInspector}
              className="hidden items-center gap-2 rounded-full border border-border/70 bg-paper-2 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:border-primary/20 hover:text-primary lg:inline-flex"
              aria-pressed={showInspector}
              aria-label={showInspector ? '收起右侧栏' : '展开右侧栏'}
            >
              {showInspector ? <PanelRightClose className="h-3.5 w-3.5" /> : <PanelRightOpen className="h-3.5 w-3.5" />}
              {showInspector ? '收起侧注' : '展开侧注'}
            </button>
          </div>

          <div className="relative w-full sm:w-96">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="text"
              placeholder="搜索知识库..."
              value={searchQuery}
              onChange={(event) => onSearchQueryChange(event.target.value)}
              className="w-full rounded-sm border border-border bg-background py-3 pl-10 pr-4 font-medium placeholder:text-muted-foreground focus:border-primary focus:ring-0"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {statusFilters.map((filterKey) => (
              <button
                key={filterKey}
                type="button"
                className={`category-chip ${statusFilter === filterKey ? 'active' : ''}`}
                onClick={() => onStatusFilterChange(filterKey)}
                aria-current={statusFilter === filterKey ? 'page' : undefined}
              >
                {statusFilterLabels[filterKey]}
              </button>
            ))}
          </div>

          <Select value={sortBy} onValueChange={(value) => onSortByChange(value as KnowledgeBaseSortKey)}>
            <SelectTrigger className="h-9 w-36 rounded-sm border border-border bg-background text-xs font-bold uppercase">
              <ArrowUpDown className="mr-1.5 h-3.5 w-3.5" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated">最近更新</SelectItem>
              <SelectItem value="papers">论文最多</SelectItem>
              <SelectItem value="name">名称 A-Z</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant={isBatchMode ? 'default' : 'outline'}
            size="sm"
            className="h-9 gap-1.5 rounded-sm border border-border bg-background text-xs font-bold uppercase"
            onClick={onToggleBatchMode}
          >
            <CheckSquare className="h-3.5 w-3.5" />
            批量
          </Button>

          <div className="flex items-center gap-0.5 rounded-sm border border-border bg-background p-0.5">
            <Button
              variant={viewMode === 'card' ? 'default' : 'ghost'}
              size="icon"
              className="h-7 w-7"
              onClick={() => onViewModeChange('card')}
              aria-pressed={viewMode === 'card'}
              aria-label="卡片视图"
            >
              <Grid className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="icon"
              className="h-7 w-7"
              onClick={() => onViewModeChange('list')}
              aria-pressed={viewMode === 'list'}
              aria-label="列表视图"
            >
              <List className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        {storageStats ? (
          <div className="mt-4 flex items-center gap-3 border border-border/70 bg-background px-4 py-3">
            <HardDrive className="h-5 w-5 text-foreground" />
            <div className="flex-1">
              <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                存储统计
              </div>
              <div className="mt-1 flex items-center gap-4">
                <span className="text-sm font-medium">{storageStats.kbCount} 知识库</span>
                <span className="text-sm font-medium">{storageStats.paperCount} 论文</span>
                <span className="text-sm font-medium">{storageStats.chunkCount.toLocaleString()} 切片</span>
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {storageStats.estimatedStorageMB.toLocaleString()} MB / {storageStats.storageLimitMB.toLocaleString()} MB
              </div>
            </div>
            {storageStatsLoading ? <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /> : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
