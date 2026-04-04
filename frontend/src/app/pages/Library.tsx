import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router";
import { FileText, Folder, Star, Filter, Search, Clock, SortDesc, Calendar, Tag, ChevronLeft, ChevronRight, Plus, X, Trash2 } from "lucide-react";
import { motion } from "motion/react";
import { useLanguage } from "../contexts/LanguageContext";
import { Badge } from "../components/ui/badge";
import { usePapers } from "../../hooks/usePapers";
import { useProjects } from "../../hooks/useProjects";
import * as papersApi from "../../services/papersApi";
import { toast } from "sonner";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationPrevious,
  PaginationNext,
} from "../components/ui/pagination";
import { ListSkeleton } from "../components/Skeleton";
import { NoPapersState } from "../components/EmptyState";
import { LibraryFilters } from "../components/LibraryFilters";

export function Library() {
  const { language } = useLanguage();
  const isZh = language === "zh";
  const navigate = useNavigate();

  // Search state with debounce
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce search input (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Use the usePapers hook
  const { papers, total, page, totalPages, loading, error, setPage, refetch, updatePaperLocal } = usePapers({
    limit: 20,
    search: debouncedSearch || undefined,
  });

  // Apply LibraryFilters to papers
  const filteredPapers = papers.filter(paper => {
    if (libraryFilters.starred && !paper.starred) return false;
    if (libraryFilters.author && !paper.authors?.some(a => a.toLowerCase().includes(libraryFilters.author!.toLowerCase()))) return false;
    if (libraryFilters.projectId) {
      // TODO: Filter by project when project assignment is implemented
      return false;
    }
    return true;
  });

  // Calculate starred count from filtered papers
  const starredCount = filteredPapers.filter(p => p.starred).length;
  
  // Calculate recent count (papers with reading progress)
  const recentCount = papers.filter(p => p.progress && p.progress > 0).length;

  // Toggle star handler with optimistic update
  const handleToggleStar = useCallback(async (paperId: string, currentStarred: boolean) => {
    const newStarred = !currentStarred;
    
    // Optimistic update - immediately update local state
    updatePaperLocal(paperId, { starred: newStarred });
    
    try {
      // Call API
      await papersApi.toggleStar(paperId, newStarred);
      
      // Show success toast
      toast.success(
        isZh 
          ? (newStarred ? "已添加到收藏" : "已取消收藏")
          : (newStarred ? "Added to starred" : "Removed from starred")
      );
    } catch (error: any) {
      // Revert on error
      updatePaperLocal(paperId, { starred: currentStarred });
      toast.error(isZh ? "操作失败" : "Failed to update starred status");
      console.error('Failed to toggle star:', error);
    }
  }, [isZh, updatePaperLocal]);

  // Projects hook
  const { projects, loading: projectsLoading, createProject, deleteProject } = useProjects();
  
  // Selected project filter
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  
  // Create project dialog state
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);
  
  // Context menu state
  const [contextMenu, setContextMenu] = useState<{
    paperId: string;
    paper: any;
    x: number;
    y: number;
  } | null>(null);

  // Filter state for LibraryFilters
  const [libraryFilters, setLibraryFilters] = useState<{
    starred?: boolean;
    author?: string;
    projectId?: string;
  }>({});

  // Handle create project
  const handleCreateProject = useCallback(async () => {
    if (!newProjectName.trim()) {
      toast.error(isZh ? "请输入项目名称" : "Please enter project name");
      return;
    }
    
    try {
      setCreatingProject(true);
      await createProject(newProjectName.trim());
      setShowCreateProject(false);
      setNewProjectName("");
      toast.success(isZh ? "项目创建成功" : "Project created");
    } catch (error: any) {
      toast.error(isZh ? "创建失败" : "Failed to create project");
    } finally {
      setCreatingProject(false);
    }
  }, [newProjectName, createProject, isZh]);
  
  // Context menu handlers
  const handleContextMenu = useCallback((e: React.MouseEvent, paper: any) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      paperId: paper.id,
      paper,
      x: e.clientX,
      y: e.clientY,
    });
  }, []);
  
  const handleContextMenuAction = useCallback(async (action: string, paperId: string) => {
    setContextMenu(null);
    
    switch (action) {
      case 'open':
        navigate(`/read/${paperId}`);
        break;
      case 'delete':
        try {
          await papersApi.remove(paperId);
          toast.success(isZh ? "论文已删除" : "Paper deleted");
          refetch();
        } catch (error: any) {
          toast.error(isZh ? "删除失败" : "Failed to delete paper");
        }
        break;
      case 'star':
        // Star toggle is already handled by handleToggleStar
        const paper = papers.find(p => p.id === paperId);
        if (paper) {
          handleToggleStar(paperId, paper.starred || false);
        }
        break;
    }
  }, [navigate, isZh, refetch, papers, handleToggleStar]);
  
  const closeContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  const t = {
    index: isZh ? "索引" : "Index",
    vol: isZh ? "第四卷" : "Vol. 4",
    collections: isZh ? "合集" : "Collections",
    recent: isZh ? "最近查看" : "Recent",
    allPapers: isZh ? "所有文献" : "All Papers",
    starred: isZh ? "已加星标" : "Starred",
    projects: isZh ? "项目" : "Projects",
    new: isZh ? "新建" : "New",
    documents: isZh ? "文档库" : "Documents",
    showing: isZh ? `显示 ${total} 个结果` : `Showing ${total} results`,
    searchPlaceholder: isZh ? "搜索标题、作者..." : "Search titles, authors...",
    openReader: isZh ? "打开阅读器" : "Open Reader",
    details: isZh ? "详细信息" : "Details",
    refine: isZh ? "筛选" : "Refine",
    clear: isZh ? "清空" : "Clear",
    sortBy: isZh ? "排序方式" : "Sort By",
    dateAdded: isZh ? "添加日期" : "Date Added",
    publication: isZh ? "出版日期" : "Publication",
    authorAZ: isZh ? "作者 (A-Z)" : "Author (A-Z)",
    year: isZh ? "年份" : "Year",
    older: isZh ? "更早" : "Older",
    tags: isZh ? "标签" : "Tags",
    noPapers: isZh ? "暂无论文" : "No papers found",
    noPapersDesc: isZh ? "上传您的第一篇论文开始使用" : "Upload your first paper to get started",
    tagNames: isZh ? ["Transformer", "大语言模型", "视觉", "对齐", "RLHF", "智能体"] : ["Transformers", "LLM", "Vision", "Alignment", "RLHF", "Agents"],
    previous: isZh ? "上一页" : "Previous",
    next: isZh ? "下一页" : "Next",
    pageOf: isZh ? "第" : "Page",
    pageOfTotal: isZh ? "页，共" : "of",
    pageTotal: isZh ? "页" : "",
  };

  return (
    <div className="h-full flex font-sans bg-background text-foreground relative selection:bg-primary selection:text-primary-foreground">
      {/* Column 1: Collections (Left - Compact) */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[220px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
          <h2 className="font-serif text-xl font-black tracking-tight leading-none mb-1">{t.index}</h2>
          <p className="text-[8px] font-bold tracking-[0.2em] uppercase text-primary">{t.vol}</p>
        </div>

        <div className="flex-1 overflow-y-auto py-5 flex flex-col gap-6 px-4">
          <div>
            <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{t.collections}</div>
            <div className="flex flex-col gap-0.5">
              <button className="flex items-center gap-2.5 px-2 py-2 rounded-sm hover:bg-muted transition-colors text-foreground/80 hover:text-primary group">
                <Clock className="w-3.5 h-3.5 text-primary/70 group-hover:text-primary" />
                <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left">{t.recent}</span>
                <span className="text-[9px] font-mono text-muted-foreground group-hover:text-primary">{recentCount}</span>
              </button>
              <button className="flex items-center gap-2.5 px-2 py-2 rounded-sm bg-primary text-primary-foreground transition-colors group shadow-sm shadow-primary/20">
                <FileText className="w-3.5 h-3.5 text-primary-foreground/90" />
                <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left">{t.allPapers}</span>
                <span className="text-[9px] font-mono text-primary-foreground/70">{total}</span>
              </button>
              <button className="flex items-center gap-2.5 px-2 py-2 rounded-sm hover:bg-muted transition-colors text-foreground/80 hover:text-primary group">
                <Star className="w-3.5 h-3.5 text-primary/70 group-hover:text-primary" />
                <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left">{t.starred}</span>
                <span className="text-[9px] font-mono text-muted-foreground group-hover:text-primary">{starredCount}</span>
              </button>
            </div>
          </div>

          <div>
            <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5 flex justify-between items-center">
              <span>{t.projects}</span>
              <span 
                onClick={() => setShowCreateProject(true)}
                className="text-primary cursor-pointer hover:underline underline-offset-2"
              >
                {t.new}
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              {projectsLoading ? (
                <div className="px-2 py-2 text-[9px] text-muted-foreground">
                  {isZh ? "加载中..." : "Loading..."}
                </div>
              ) : projects.length === 0 ? (
                <div className="px-2 py-2 text-[9px] text-muted-foreground">
                  {isZh ? "暂无项目" : "No projects"}
                </div>
              ) : (
                projects.map((project) => (
                  <button 
                    key={project.id} 
                    onClick={() => setSelectedProjectId(selectedProjectId === project.id ? null : project.id)}
                    className={`flex items-center gap-2.5 px-2 py-1.5 rounded-sm transition-colors group ${
                      selectedProjectId === project.id 
                        ? "bg-primary/10 text-primary" 
                        : "hover:bg-muted text-foreground/70 hover:text-primary"
                    }`}
                  >
                    <Folder className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary" />
                    <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left truncate">{project.name}</span>
                    <span className="text-[9px] font-mono text-muted-foreground group-hover:text-primary">{project.paperCount}</span>
                  </button>
                ))
              )}
            </div>
            
            {/* Create Project Dialog */}
            {showCreateProject && (
              <div className="mt-3 p-3 bg-card border border-border/50 rounded-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest">
                    {isZh ? "新建项目" : "New Project"}
                  </span>
                  <X 
                    className="w-3 h-3 text-muted-foreground cursor-pointer hover:text-primary"
                    onClick={() => {
                      setShowCreateProject(false);
                      setNewProjectName("");
                    }}
                  />
                </div>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder={isZh ? "项目名称" : "Project name"}
                  className="w-full bg-muted/50 border border-border/50 rounded-sm px-2 py-1 text-xs mb-2"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleCreateProject();
                    if (e.key === 'Escape') {
                      setShowCreateProject(false);
                      setNewProjectName("");
                    }
                  }}
                />
                <button
                  onClick={handleCreateProject}
                  disabled={creatingProject || !newProjectName.trim()}
                  className="w-full bg-primary text-primary-foreground text-[9px] font-bold uppercase tracking-widest py-1.5 rounded-sm hover:bg-primary/90 disabled:opacity-50"
                >
                  {creatingProject ? (isZh ? "创建中..." : "Creating...") : (isZh ? "创建" : "Create")}
                </button>
              </div>
)}
            
            {/* Context Menu */}
            {contextMenu && (
              <>
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={closeContextMenu}
                />
                <div
                  className="fixed z-50 bg-card border border-border/50 rounded-sm shadow-lg py-1 min-w-[120px]"
                  style={{ left: contextMenu.x, top: contextMenu.y }}
                >
                  <button
                    onClick={() => handleContextMenuAction('open', contextMenu.paperId)}
                    className="w-full px-3 py-1.5 text-left text-xs font-bold uppercase tracking-widest hover:bg-muted transition-colors flex items-center gap-2"
                  >
                    <FileText className="w-3 h-3" />
                    {isZh ? "打开" : "Open"}
                  </button>
                  <button
                    onClick={() => handleContextMenuAction('star', contextMenu.paperId)}
                    className="w-full px-3 py-1.5 text-left text-xs font-bold uppercase tracking-widest hover:bg-muted transition-colors flex items-center gap-2"
                  >
                    <Star className="w-3 h-3" />
                    {isZh ? "星标" : "Star"}
                  </button>
                  <button
                    onClick={() => handleContextMenuAction('delete', contextMenu.paperId)}
                    className="w-full px-3 py-1.5 text-left text-xs font-bold uppercase tracking-widest hover:bg-muted transition-colors flex items-center gap-2 text-destructive"
                  >
                    <Trash2 className="w-3 h-3" />
                    {isZh ? "删除" : "Delete"}
                  </button>
                </div>
              </>
            )}
        </div>
      </div>
      </motion.div>

      {/* Column 2: Papers Grid (Middle - Dense) */}
      <div className="flex-1 flex flex-col h-full bg-background min-w-[500px]">
        <div className="px-6 py-4 border-b border-border/50 bg-background/90 backdrop-blur-md sticky top-0 z-10 flex flex-col gap-4 shadow-sm">
          <div className="flex justify-between items-center">
            <div className="flex items-baseline gap-3">
              <h2 className="font-serif text-2xl font-black tracking-tight">{t.documents}</h2>
              <span className="text-[9px] font-mono tracking-[0.2em] text-muted-foreground">{t.showing}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative w-64">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t.searchPlaceholder}
                  className="w-full bg-muted/50 border border-border/50 rounded-sm pl-9 pr-4 py-1.5 text-xs font-sans placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary transition-all"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-muted/10 p-5">
          {loading ? (
            <ListSkeleton count={6} />
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <FileText className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-sm font-medium">{error}</p>
            </div>
          ) : papers.length === 0 && !debouncedSearch ? (
            <NoPapersState onUpload={() => navigate('/upload')} isZh={isZh} />
          ) : papers.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <FileText className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-sm font-medium">{isZh ? "未找到匹配的论文" : "No papers match your search"}</p>
            </div>
          ) : (
            <>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="grid grid-cols-1 xl:grid-cols-2 gap-5"
              >
                {filteredPapers.map((paper) => (
                  <div
                    key={paper.id}
                    onClick={() => navigate(`/read/${paper.id}`)}
                    onContextMenu={(e) => handleContextMenu(e, paper)}
                    className="p-5 border border-border/50 bg-card rounded-sm flex flex-col gap-3 group hover:border-primary/50 hover:shadow-md transition-all duration-300 relative overflow-hidden cursor-pointer"
                  >
                    <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary/0 via-primary/0 to-primary/0 group-hover:via-primary/50 transition-colors duration-500" />

<div className="flex justify-between items-start">
                       <div className="flex items-center gap-2">
                         <span className="text-[8px] font-bold uppercase tracking-widest bg-primary/10 text-primary px-1.5 py-0.5 rounded-sm">{paper.venue || '—'}</span>
                         <span className="text-[9px] font-mono text-muted-foreground">{paper.year || '—'}</span>
                       </div>
                       <Star
                         onClick={(e) => {
                           e.stopPropagation();
                           handleToggleStar(paper.id, paper.starred || false);
                         }}
                         className={`w-3.5 h-3.5 transition-colors cursor-pointer ${
                           paper.starred ? "fill-primary text-primary" : "text-muted-foreground hover:text-primary"
                         }`}
                       />
                     </div>

                    <div className="flex flex-col gap-1.5">
                      <h3 className="font-serif font-black text-xl leading-tight group-hover:text-primary transition-colors tracking-tight line-clamp-2">
                        {paper.title}
                      </h3>
                      <p className="font-sans text-[11px] font-medium text-foreground/80 line-clamp-1 truncate">{paper.authors?.join(', ') || '—'}</p>
                    </div>

                    <div className="flex gap-4 mt-2">
                      <div className="w-14 h-20 bg-muted border border-border/50 rounded-sm flex-shrink-0 relative overflow-hidden group-hover:shadow-sm">
                        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1707256786130-6d028236813f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxhY2FkZW1pYyUyMHBhcGVyJTIwY292ZXJ8ZW58MXx8fHwxNzc1MTk4MzcxfDA&ixlib=rb-4.1.0&q=80&w=1080')] bg-cover opacity-20 grayscale group-hover:grayscale-0 group-hover:opacity-50 transition-all duration-700" />
                      </div>
                      <p className="font-serif text-xs text-foreground/70 leading-[1.6] line-clamp-4 italic border-l-2 border-primary/20 pl-3 flex-1 h-fit">
                        {paper.abstract || '—'}
                      </p>
                    </div>

                    <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border/30 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="text-[9px] font-bold uppercase tracking-widest bg-foreground text-background px-3 py-1.5 rounded-sm hover:bg-primary transition-colors shadow-sm">
                        {t.openReader}
                      </button>
                      <button className="text-[9px] font-bold uppercase tracking-widest border border-foreground/20 text-foreground px-3 py-1.5 rounded-sm hover:bg-muted transition-colors">
                        {t.details}
                      </button>
                    </div>
                  </div>
                ))}
              </motion.div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-6">
                  <Pagination>
                    <PaginationContent>
                      <PaginationItem>
                        <PaginationPrevious
                          onClick={() => page > 1 && setPage(page - 1)}
                          className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                        />
                      </PaginationItem>
                      <PaginationItem>
                        <PaginationLink isActive>
                          {t.pageOf} {page} {t.pageOfTotal} {totalPages} {t.pageTotal}
                        </PaginationLink>
                      </PaginationItem>
                      <PaginationItem>
                        <PaginationNext
                          onClick={() => page < totalPages && setPage(page + 1)}
                          className={page >= totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                        />
                      </PaginationItem>
                    </PaginationContent>
                  </Pagination>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Column 3: Filters & Refinement (Right - Compact) */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[240px] border-l border-border/50 flex flex-col h-full bg-muted/10 flex-shrink-0"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-primary" />
            <h2 className="font-serif text-lg font-bold tracking-tight">{t.refine}</h2>
          </div>
          <button className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-primary transition-colors">{t.clear}</button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6 flex flex-col gap-8">

          {/* LibraryFilters Component */}
          <LibraryFilters filters={libraryFilters} onFilterChange={setLibraryFilters} />

          {/* Sorting */}
          <div className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <SortDesc className="w-3 h-3" /> {t.sortBy}
            </h3>
            <div className="flex flex-col gap-1.5 mt-1">
              <label className="flex items-center gap-2.5 cursor-pointer group">
                <input type="radio" name="sort" className="accent-primary w-3.5 h-3.5" defaultChecked />
                <span className="text-xs font-bold uppercase tracking-widest text-foreground/80 group-hover:text-primary transition-colors">{t.dateAdded}</span>
              </label>
              <label className="flex items-center gap-2.5 cursor-pointer group">
                <input type="radio" name="sort" className="accent-primary w-3.5 h-3.5" />
                <span className="text-xs font-bold uppercase tracking-widest text-foreground/80 group-hover:text-primary transition-colors">{t.publication}</span>
              </label>
              <label className="flex items-center gap-2.5 cursor-pointer group">
                <input type="radio" name="sort" className="accent-primary w-3.5 h-3.5" />
                <span className="text-xs font-bold uppercase tracking-widest text-foreground/80 group-hover:text-primary transition-colors">{t.authorAZ}</span>
              </label>
            </div>
          </div>

          {/* Tags / Keywords */}
          <div className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Tag className="w-3 h-3" /> {t.tags}
            </h3>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {t.tagNames.map((tag) => (
                <span key={tag} className="font-sans text-[9px] font-bold uppercase tracking-[0.1em] border border-border/50 text-foreground/70 px-2 py-1 rounded-sm hover:bg-primary hover:text-primary-foreground hover:border-primary transition-colors cursor-pointer shadow-sm bg-card">
                  {tag}
                </span>
              ))}
            </div>
          </div>

        </div>
      </motion.div>
    </div>
  );
}