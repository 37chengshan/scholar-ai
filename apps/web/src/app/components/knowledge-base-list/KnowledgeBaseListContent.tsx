import { motion } from 'motion/react';
import { ArrowRight, Download, Loader2, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';

import type { KnowledgeBase } from '@/services/kbApi';
import { getKnowledgeBaseDisplayMetadata } from '@/app/lib/knowledgeBaseDisplay';
import { Button } from '@/app/components/ui/button';
import { Checkbox } from '@/app/components/ui/checkbox';
import { KnowledgeBaseCard } from '@/app/components/KnowledgeBaseCard';
import { UnifiedFeedbackState } from '@/app/components/UnifiedFeedbackState';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/app/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/app/components/ui/dropdown-menu';

import type { KnowledgeBaseStatusFilter } from './types';

interface KnowledgeBaseListContentProps {
  knowledgeBases: KnowledgeBase[];
  loading: boolean;
  error: string | null;
  searchQuery: string;
  statusFilter: KnowledgeBaseStatusFilter;
  viewMode: 'card' | 'list';
  isBatchMode: boolean;
  selectedIds: Set<string>;
  onSelectedIdsChange: (next: Set<string>) => void;
  onRetry: () => void;
  onCreate: () => void;
  onEnter: (id: string) => void;
  onImport: (id: string, name: string) => void;
  onEdit: (id: string, name: string) => void;
  onDelete: (id: string, name: string) => void;
}

export function KnowledgeBaseListContent({
  knowledgeBases,
  loading,
  error,
  searchQuery,
  statusFilter,
  viewMode,
  isBatchMode,
  selectedIds,
  onSelectedIdsChange,
  onRetry,
  onCreate,
  onEnter,
  onImport,
  onEdit,
  onDelete,
}: KnowledgeBaseListContentProps) {
  const toggleSelection = (id: string, checked: boolean) => {
    const next = new Set(selectedIds);
    if (checked) {
      next.add(id);
    } else {
      next.delete(id);
    }
    onSelectedIdsChange(next);
  };

  const toggleAllSelection = (checked: boolean) => {
    if (checked) {
      onSelectedIdsChange(new Set(knowledgeBases.map((kb) => kb.id)));
      return;
    }
    onSelectedIdsChange(new Set());
  };

  if (loading) {
    return (
      <div className="py-12 text-center">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="font-medium text-muted-foreground">加载中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <div className="mb-4 font-medium text-destructive">{error}</div>
        <Button variant="outline" onClick={onRetry}>
          重试
        </Button>
      </div>
    );
  }

  if (knowledgeBases.length === 0) {
    return (
      <UnifiedFeedbackState
        status="empty"
        title={searchQuery.trim() || statusFilter !== 'all' ? '当前筛选下没有知识库' : '暂无知识库'}
        message={
          searchQuery.trim() || statusFilter !== 'all'
            ? '调整搜索词或状态筛选，查看其他知识库。'
            : '创建第一个知识库，开始整理论文、导入进度和检索上下文。'
        }
        action={<Button onClick={onCreate}>创建知识库</Button>}
      />
    );
  }

  if (viewMode === 'card') {
    return (
      <motion.div
        className="cq-grid-cols grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: { opacity: 0 },
          visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
        }}
      >
        {knowledgeBases.map((kb) => {
          const display = getKnowledgeBaseDisplayMetadata(kb);
          return (
            <motion.div
              key={kb.id}
              variants={{
                hidden: { opacity: 0, y: 20 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
              }}
              className="relative"
            >
              {isBatchMode ? (
                <div className="absolute left-3 top-3 z-10" onClick={(event) => event.stopPropagation()}>
                  <Checkbox
                    checked={selectedIds.has(kb.id)}
                    onCheckedChange={(checked) => toggleSelection(kb.id, Boolean(checked))}
                    className="bg-background"
                  />
                </div>
              ) : null}
              <KnowledgeBaseCard
                id={kb.id}
                name={display.displayName}
                description={display.displayDescription}
                paperCount={kb.paperCount}
                chunkCount={kb.chunkCount}
                entityCount={kb.entityCount}
                updatedAt={kb.updatedAt}
                onEnter={() => onEnter(kb.id)}
                onImport={() => onImport(kb.id, kb.name)}
                onEdit={() => onEdit(kb.id, kb.name)}
                onDelete={() => onDelete(kb.id, kb.name)}
              />
            </motion.div>
          );
        })}
      </motion.div>
    );
  }

  return (
    <div className="magazine-card-warm rounded-lg p-4">
      <Table>
        <TableHeader>
          <TableRow className="border-b-border/50">
            {isBatchMode ? (
              <TableHead className="w-10">
                <Checkbox
                  checked={selectedIds.size === knowledgeBases.length && knowledgeBases.length > 0}
                  onCheckedChange={(checked) => toggleAllSelection(Boolean(checked))}
                />
              </TableHead>
            ) : null}
            <TableHead className="font-serif">名称</TableHead>
            <TableHead className="text-right tabular-nums">论文</TableHead>
            <TableHead className="text-right tabular-nums">切片</TableHead>
            <TableHead className="text-right tabular-nums">实体</TableHead>
            <TableHead className="text-right tabular-nums">更新</TableHead>
            <TableHead className="w-24" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {knowledgeBases.map((kb) => {
            const display = getKnowledgeBaseDisplayMetadata(kb);
            return (
              <TableRow
                key={kb.id}
                className="group/row cursor-pointer transition-colors hover:bg-primary/[0.04]"
                onClick={() => onEnter(kb.id)}
                role="link"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onEnter(kb.id);
                  }
                }}
              >
                {isBatchMode ? (
                  <TableCell onClick={(event) => event.stopPropagation()}>
                    <Checkbox
                      checked={selectedIds.has(kb.id)}
                      onCheckedChange={(checked) => toggleSelection(kb.id, Boolean(checked))}
                    />
                  </TableCell>
                ) : null}
                <TableCell>
                  <div>
                    <div className="font-serif font-medium transition-colors group-hover/row:text-primary">
                      {display.displayName}
                    </div>
                    <div className="mt-0.5 line-clamp-1 text-sm text-muted-foreground">
                      {display.displayDescription}
                    </div>
                  </div>
                </TableCell>
                <TableCell className="text-right font-medium tabular-nums">{kb.paperCount}</TableCell>
                <TableCell className="text-right tabular-nums">{kb.chunkCount.toLocaleString()}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {kb.entityCount > 0 ? kb.entityCount.toLocaleString() : <span className="text-muted-foreground/60">—</span>}
                </TableCell>
                <TableCell className="text-right text-sm tabular-nums text-muted-foreground">{kb.updatedAt}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 transition-opacity group-hover/row:opacity-100"
                          onClick={(event) => event.stopPropagation()}
                          aria-label="更多操作"
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => onEnter(kb.id)}>
                          <ArrowRight className="mr-2 h-4 w-4" />
                          进入知识库
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onImport(kb.id, kb.name)}>
                          <Download className="mr-2 h-4 w-4" />
                          导入论文
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onEdit(kb.id, kb.name)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          编辑信息
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={() => onDelete(kb.id, kb.name)}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          删除知识库
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <ArrowRight className="h-4 w-4 flex-shrink-0 text-muted-foreground/30 transition-colors group-hover/row:text-primary/50" />
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
