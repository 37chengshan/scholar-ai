import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { motion } from "motion/react";
import { Grid, List, Search, Plus, CheckSquare, ArrowUpDown, HardDrive, Loader2, MoreHorizontal, ArrowRight, Download, Pencil, Trash2, PanelRightClose, PanelRightOpen } from "lucide-react";
import { KnowledgeBaseCard } from "../components/KnowledgeBaseCard";
import { CreateKnowledgeBaseDialog } from "../components/CreateKnowledgeBaseDialog";
import { ImportDialog } from "../components/ImportDialog";
import { EmptyState } from "../components/EmptyState";
import { PaperTexture } from "../components/PaperTexture";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Checkbox } from "../components/ui/checkbox";
import { kbApi, KnowledgeBase, KBCreateData, KBStorageStats } from "@/services/kbApi";
import { useUrlState } from "../../hooks/useUrlState";
import { useKnowledgeBases } from "../../hooks/useKnowledgeBases";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { toast } from "sonner";

/**
 * Internal KnowledgeBaseList component that uses Router hooks
 * Extracted to ensure Router context is available
 */
function KnowledgeBaseListContent() {
  const navigate = useNavigate();
  
  // URL-synchronized state (persisted across refresh/navigation)
  const [viewMode, setViewMode] = useUrlState<'card' | 'list'>('view', 'card' as 'card' | 'list');
  const [searchQuery, setSearchQuery] = useUrlState<string>('search', '');
  const [activeTag, setActiveTag] = useUrlState<string>('tag', '全部');
  const [sortBy, setSortBy] = useUrlState<'updated' | 'papers' | 'name'>('sort', 'updated' as 'updated' | 'papers' | 'name');
  
  // Ephemeral state (not URL-synced)
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [importTarget, setImportTarget] = useState<{ id: string; name: string } | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [showInspector, setShowInspector] = useState(true);

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
    category: activeTag === "全部" ? undefined : activeTag,
    sortBy,
  });

  // Extract unique categories from API data (computed from knowledgeBases)
  const apiCategories = knowledgeBases && knowledgeBases.length > 0 
    ? Array.from(new Set(knowledgeBases.map((kb: KnowledgeBase) => kb.category).filter(Boolean)))
    : [];
  const tags = ["全部", ...apiCategories];

  // TODO: FE-04 — When real API data exceeds ~50 items, wrap this grid with react-window's VariableSizeGrid

  // Use API data directly (backend handles search/category/sort filtering)
  const sorted = knowledgeBases;

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
    <div className="flex h-full min-h-0 bg-background">
      <div className="relative flex-1 min-h-0 overflow-y-auto">
        <PaperTexture />

        {/* Toolbar Header — Create button and Storage */}
        <div className="sticky top-0 z-10 bg-background/90 backdrop-blur-sm border-b border-border/70">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-muted/30 p-4 border border-border/70">
            {/* Create button */}
            <div className="flex items-center gap-2 self-start sm:self-center">
              <Button 
                onClick={handleCreate}
                className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground px-5 py-3 font-semibold tracking-wide transition-colors rounded-sm"
              >
                <Plus className="w-5 h-5" />
                创建知识库
              </Button>
              <button
                type="button"
                onClick={() => setShowInspector((value) => !value)}
                className="hidden items-center gap-2 rounded-full border border-border/70 bg-paper-2 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:border-primary/20 hover:text-primary lg:inline-flex"
                aria-pressed={showInspector}
                aria-label={showInspector ? "收起右侧栏" : "展开右侧栏"}
              >
                {showInspector ? <PanelRightClose className="h-3.5 w-3.5" /> : <PanelRightOpen className="h-3.5 w-3.5" />}
                {showInspector ? "收起侧注" : "展开侧注"}
              </button>
            </div>
            
            {/* Search input */}
            <div className="relative w-full sm:w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-5 h-5" />
            <Input
              type="text"
              placeholder="搜索知识库..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-background border border-border pl-10 pr-4 py-3 font-medium placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-0 transition-colors rounded-sm"
            />
          </div>
          
          {/* Category chip filters */}
          <div className="flex items-center gap-2 flex-wrap">
            {tags.map((tag: string) => (
              <button
                key={tag}
                className={`category-chip ${activeTag === tag ? 'active' : ''}`}
                onClick={() => setActiveTag(tag)}
                aria-current={activeTag === tag ? "page" : undefined}
              >
                {tag}
              </button>
            ))}
          </div>
          
          {/* Sort dropdown */}
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as "updated" | "papers" | "name")}>
            <SelectTrigger className="w-36 h-9 text-xs border border-border bg-background font-bold uppercase rounded-sm">
              <ArrowUpDown className="h-3.5 w-3.5 mr-1.5" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated">最近更新</SelectItem>
              <SelectItem value="papers">论文最多</SelectItem>
              <SelectItem value="name">名称 A-Z</SelectItem>
            </SelectContent>
          </Select>
          
          {/* Batch mode toggle */}
          <Button
            variant={isBatchMode ? "default" : "outline"}
            size="sm"
            className="gap-1.5 h-9 text-xs border border-border bg-background font-bold uppercase rounded-sm"
            onClick={() => {
              setIsBatchMode(!isBatchMode);
              if (isBatchMode) setSelectedIds(new Set());
            }}
          >
            <CheckSquare className="h-3.5 w-3.5" />
            批量
          </Button>
          
          {/* View toggle */}
          <div className="flex items-center gap-0.5 border border-border rounded-sm p-0.5 bg-background">
            <Button
              variant={viewMode === "card" ? "default" : "ghost"}
              size="icon"
              className="h-7 w-7"
              onClick={() => setViewMode("card")}
              aria-pressed={viewMode === "card"}
              aria-label="卡片视图"
            >
              <Grid className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant={viewMode === "list" ? "default" : "ghost"}
              size="icon"
              className="h-7 w-7"
              onClick={() => setViewMode("list")}
              aria-pressed={viewMode === "list"}
              aria-label="列表视图"
            >
              <List className="h-3.5 w-3.5" />
            </Button>
</div>
          </div>
          
          {/* Storage Status */}
          {storageStats && (
          <div className="flex items-center gap-3 bg-background border border-border/70 px-4 py-3">
            <HardDrive className="w-5 h-5 text-foreground" />
            <div className="flex-1">
              <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                存储统计
              </div>
              <div className="flex items-center gap-4 mt-1">
                <span className="text-sm font-medium">
                  {storageStats.kbCount} 知识库
                </span>
                <span className="text-sm font-medium">
                  {storageStats.paperCount} 论文
                </span>
                <span className="text-sm font-medium">
                  {storageStats.chunkCount.toLocaleString()} 切片
                </span>
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {storageStats.estimatedStorageMB.toLocaleString()} MB / {storageStats.storageLimitMB.toLocaleString()} MB
              </div>
            </div>
            {storageStatsLoading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
          </div>
          )}
        </div>

        {/* Batch action bar */}
        {isBatchMode && selectedIds.size > 0 && (
          <div className="flex items-center gap-3 mt-3 p-3 bg-muted/50 rounded-lg">
            <span className="text-sm text-muted-foreground">
              已选择 {selectedIds.size} 项
            </span>
            <Button variant="outline" size="sm" onClick={handleBatchDelete}>
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              删除
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled
              aria-disabled="true"
              aria-describedby="batch-export-soon-hint"
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />
              导出（即将上线）
            </Button>
            <span id="batch-export-soon-hint" className="text-xs text-muted-foreground">
              批量导出能力即将上线
            </span>
            <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>
              取消选择
            </Button>
          </div>
        )}
        </div>

        {/* Content Area */}
        <div className="container-query max-w-7xl mx-auto px-6 pb-12">
        {loading && (
          <div className="text-center py-12 flex items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
            <span className="text-muted-foreground font-medium">加载中...</span>
          </div>
        )}
        {error && (
          <div className="text-center py-12">
            <div className="text-destructive font-medium mb-4">{error}</div>
            <Button variant="outline" onClick={refetch}>
              重试
            </Button>
          </div>
        )}
        {!loading && !error && sorted.length === 0 ? (
          <EmptyState
            title="暂无知识库"
            description="创建您的第一个知识库，开始组织研究方向"
            action={{
              label: "创建知识库",
              onClick: handleCreate,
            }}
          />
        ) : !loading && !error && viewMode === "card" ? (
          <motion.div 
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 cq-grid-cols gap-8" 
            initial="hidden" 
            animate="visible" 
            variants={{ hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.08 } } }}
          >
            {sorted.map((kb) => (
              <motion.div 
                key={kb.id} 
                variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0, transition: { duration: 0.4 } } }} 
                className="relative"
              >
                {isBatchMode && (
                  <div className="absolute top-3 left-3 z-10" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedIds.has(kb.id)}
                      onCheckedChange={(checked) => {
                        const next = new Set(selectedIds);
                        if (checked) next.add(kb.id);
                        else next.delete(kb.id);
                        setSelectedIds(next);
                      }}
                      className="bg-background"
                    />
                  </div>
                )}
                <KnowledgeBaseCard
                  id={kb.id}
                  name={kb.name}
                  description={kb.description}
                  paperCount={kb.paperCount}
                  chunkCount={kb.chunkCount}
                  entityCount={kb.entityCount}
                  updatedAt={kb.updatedAt}
                  category={kb.category}
                  onEnter={() => handleEnter(kb.id)}
                  onImport={() => handleImport(kb.id, kb.name)}
                  onEdit={() => handleEdit(kb.id, kb.name)}
                  onDelete={() => handleDelete(kb.id, kb.name)}
                />
              </motion.div>
            ))}
          </motion.div>
        ) : (
          <div className="magazine-card-warm rounded-lg p-4">
            <Table>
            <TableHeader>
              <TableRow className="border-b-border/50">
                {isBatchMode && (
                  <TableHead className="w-10">
                    <Checkbox
                      checked={selectedIds.size === sorted.length && sorted.length > 0}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          setSelectedIds(new Set(sorted.map((kb: KnowledgeBase) => kb.id)));
                        } else {
                          setSelectedIds(new Set());
                        }
                      }}
                    />
                  </TableHead>
                )}
                <TableHead className="font-serif">名称</TableHead>
                <TableHead className="text-right tabular-nums">论文</TableHead>
                <TableHead className="text-right tabular-nums">切片</TableHead>
                <TableHead className="text-right tabular-nums">实体</TableHead>
                <TableHead className="text-right tabular-nums">更新</TableHead>
                <TableHead className="w-24"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
{sorted.map((kb: KnowledgeBase) => (
                <TableRow
                  key={kb.id}
                  className="group/row cursor-pointer transition-colors hover:bg-primary/[0.04]"
                  onClick={() => handleEnter(kb.id)}
                  role="link"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleEnter(kb.id);
                    }
                  }}
                >
                  {isBatchMode && (
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selectedIds.has(kb.id)}
                        onCheckedChange={(checked) => {
                          const next = new Set(selectedIds);
                          if (checked) next.add(kb.id);
                          else next.delete(kb.id);
                          setSelectedIds(next);
                        }}
                      />
                    </TableCell>
                  )}
                  <TableCell>
                    <div>
                      <div className="font-medium font-serif group-hover/row:text-primary transition-colors">
                        {kb.name}
                      </div>
                      <div className="text-sm text-muted-foreground line-clamp-1 mt-0.5">
                        {kb.description}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-medium">
                    {kb.paperCount}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {kb.chunkCount.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {kb.entityCount > 0 ? (
                      kb.entityCount.toLocaleString()
                    ) : (
                      <span className="text-muted-foreground/60">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground tabular-nums text-sm">
                    {kb.updatedAt}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 opacity-0 group-hover/row:opacity-100 transition-opacity"
                            onClick={(e) => e.stopPropagation()}
                            aria-label="更多操作"
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEnter(kb.id)}>
                            <ArrowRight className="mr-2 h-4 w-4" />
                            进入知识库
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleImport(kb.id, kb.name)}>
                            <Download className="mr-2 h-4 w-4" />
                            导入论文
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleEdit(kb.id, kb.name)}>
                            <Pencil className="mr-2 h-4 w-4" />
                            编辑信息
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            variant="destructive"
                            onClick={() => handleDelete(kb.id, kb.name)}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            删除知识库
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                      <ArrowRight className="h-4 w-4 text-muted-foreground/30 group-hover/row:text-primary/50 transition-colors flex-shrink-0" />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
        )}
        </div>

        {/* Create Dialog */}
        <CreateKnowledgeBaseDialog
          open={showCreateDialog}
          onOpenChange={setShowCreateDialog}
          onCreate={handleCreateSubmit}
        />

        {/* Import Dialog */}
        {importTarget && (
          <ImportDialog
            open={!!importTarget}
            onOpenChange={(open) => {
              if (!open) setImportTarget(null);
            }}
            knowledgeBaseId={importTarget.id}
            knowledgeBaseName={importTarget.name}
            onImportComplete={refetch}
          />
        )}

        {/* Magazine Masthead Footer */}
        <div className="max-w-7xl mx-auto px-6 py-16 border-t-2 border-border mt-16 bg-muted/30/40">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            {/* Badge label */}
            <div className="inline-block px-3 py-1 bg-primary/10 text-primary font-semibold tracking-wide text-xs rounded-sm">
              知识库
            </div>
            
            {/* Magazine masthead title */}
            <h1 className="text-5xl md:text-7xl font-black font-serif uppercase tracking-tighter text-foreground leading-none">
              Knowledge<br/>
              <span className="text-primary">Repositories</span>
            </h1>
            
            {/* Description */}
            <p className="text-muted-foreground font-medium max-w-xl text-lg font-sans">
              管理您的向量化文档集合。上传、处理和使用高级嵌入模型查询企业知识。
            </p>
          </div>
        </div>
      </div>
      </div>

      {showInspector ? (
      <aside className="hidden lg:flex w-[280px] shrink-0 border-l border-border/50 bg-muted/10 flex-col h-full">
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-serif text-lg font-bold tracking-tight">知识库</h2>
          </div>
          <p className="text-[8px] font-bold tracking-[0.2em] uppercase text-primary">Vol. 4</p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6 flex flex-col gap-8">
          <section className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              Overview
            </h3>
            <div className="mt-1 grid grid-cols-2 gap-2">
              <div className="rounded-sm bg-muted/30 px-3 py-3 flex flex-col gap-1 items-center justify-center border border-border/50">
                <div className="text-[8px] uppercase tracking-[0.2em] text-muted-foreground">Collections</div>
                <div className="font-serif text-2xl font-black text-foreground">{storageStats?.kbCount ?? total}</div>
              </div>
              <div className="rounded-sm bg-muted/30 px-3 py-3 flex flex-col gap-1 items-center justify-center border border-border/50">
                <div className="text-[8px] uppercase tracking-[0.2em] text-muted-foreground">Papers</div>
                <div className="font-serif text-2xl font-black text-foreground">{storageStats?.paperCount ?? "—"}</div>
              </div>
            </div>
            <div className="mt-2 rounded-sm bg-primary/10 px-3 py-2 text-[10px] text-primary/80 border border-primary/20 text-center">
              {storageStats
                ? `已用 ${storageStats.estimatedStorageMB.toLocaleString()} / ${storageStats.storageLimitMB.toLocaleString()} MB`
                : "创建知识库后汇总数据"}
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              Current Filters
            </h3>
            <div className="mt-1 flex flex-wrap gap-1.5">
              <span className="rounded-sm border border-border/50 bg-background px-2 py-0.5 text-[10px] text-foreground/75 font-medium tracking-wide">
                视图 · {viewMode === "card" ? "卡片" : "列表"}
              </span>
              <span className="rounded-sm border border-border/50 bg-background px-2 py-0.5 text-[10px] text-foreground/75 font-medium tracking-wide">
                分类 · {activeTag}
              </span>
              <span className="rounded-sm border border-border/50 bg-background px-2 py-0.5 text-[10px] text-foreground/75 font-medium tracking-wide">
                排序 · {sortBy}
              </span>
              {searchQuery ? (
                <span className="rounded-sm border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] text-primary font-medium tracking-wide shadow-sm shadow-primary/10">
                  搜索 · {searchQuery}
                </span>
              ) : null}
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <div className="flex items-center justify-between text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5">
              <h3>Recent Updates</h3>
              <button
                type="button"
                onClick={handleCreate}
                className="text-primary hover:text-primary/80 hover:underline transition-all"
              >
                新建
              </button>
            </div>
            <div className="mt-1 flex flex-col gap-1">
              {latestKnowledgeBases.length > 0 ? latestKnowledgeBases.map((kb) => (
                <button
                  key={kb.id}
                  type="button"
                  onClick={() => handleEnter(kb.id)}
                  className="w-full rounded-sm bg-background px-3 py-2.5 text-left transition-colors hover:bg-muted/50 border border-transparent hover:border-border/50 group"
                >
                  <div className="line-clamp-1 text-[11px] font-bold text-foreground/80 group-hover:text-primary transition-colors">{kb.name}</div>
                  <div className="mt-0.5 text-[9px] font-mono text-muted-foreground">
                    {kb.paperCount} papers · {kb.chunkCount.toLocaleString()} chunks
                  </div>
                </button>
              )) : (
                <div className="rounded-sm border border-dashed border-border/50 px-3 py-4 text-[10px] text-center text-muted-foreground">
                  暂无内容
                </div>
              )}
            </div>
          </section>
        </div>
      </aside>
      ) : null}
    </div>
  );
}

/**
 * Outer KnowledgeBaseList component wrapper
 * This ensures the Router context is available when KnowledgeBaseListContent is rendered
 */
export function KnowledgeBaseList() {
  return <KnowledgeBaseListContent />;
}
