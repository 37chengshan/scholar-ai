import { useCallback } from "react";
import { clsx } from "clsx";
import { Trash2, Star, FolderPlus, CheckSquare, X } from "lucide-react";
import { useLanguage } from "../contexts/LanguageContext";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "./ui/dialog";
import { Button } from "./ui/button";

interface BatchActionBarProps {
  selectedCount: number;
  onSelectAll: () => void;
  onClear: () => void;
  onBatchStar: () => void;
  onBatchDelete: () => void;
  onBatchAddToProject: () => void;
  isStarred?: boolean;
}

/**
 * BatchActionBar Component
 *
 * Displays batch operation toolbar when in batch mode (D-02).
 * Shows selection count and provides bulk actions:
 * - Select all / Clear selection
 * - Batch star/unstar
 * - Batch delete
 * - Batch add to project
 */
export function BatchActionBar({
  selectedCount,
  onSelectAll,
  onClear,
  onBatchStar,
  onBatchDelete,
  onBatchAddToProject,
  isStarred,
}: BatchActionBarProps) {
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    selected: isZh ? `已选择 ${selectedCount} 篇` : `${selectedCount} selected`,
    selectAll: isZh ? "全选" : "Select All",
    clear: isZh ? "清空" : "Clear",
    batchStar: isZh ? "批量星标" : "Batch Star",
    batchUnstar: isZh ? "批量取消星标" : "Batch Unstar",
    batchDelete: isZh ? "批量删除" : "Batch Delete",
    batchAddToProject: isZh ? "添加到项目" : "Add to Project",
  };

  return (
    <div className="flex items-center justify-between bg-primary/5 border border-primary/20 rounded-sm px-4 py-2">
      <div className="flex items-center gap-3">
        <span className="text-[9px] font-bold uppercase tracking-widest text-primary">
          {t.selected}
        </span>
        <button
          onClick={onSelectAll}
          className="text-[9px] font-bold uppercase tracking-widest text-foreground/80 hover:text-primary transition-colors flex items-center gap-1"
        >
          <CheckSquare className="w-3 h-3" />
          {t.selectAll}
        </button>
        <button
          onClick={onClear}
          className="text-[9px] font-bold uppercase tracking-widest text-foreground/80 hover:text-primary transition-colors flex items-center gap-1"
        >
          <X className="w-3 h-3" />
          {t.clear}
        </button>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onBatchStar}
          disabled={selectedCount === 0}
          className={clsx(
            "flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
            isStarred
              ? "bg-muted text-foreground hover:bg-primary/10"
              : "bg-muted text-foreground hover:bg-primary/10"
          )}
        >
          <Star className="w-3 h-3" />
          {isStarred ? t.batchUnstar : t.batchStar}
        </button>
        <button
          onClick={onBatchAddToProject}
          disabled={selectedCount === 0}
          className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest bg-muted text-foreground px-3 py-1.5 rounded-sm hover:bg-primary/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <FolderPlus className="w-3 h-3" />
          {t.batchAddToProject}
        </button>
        <button
          onClick={onBatchDelete}
          disabled={selectedCount === 0}
          className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest bg-muted text-destructive px-3 py-1.5 rounded-sm hover:bg-destructive/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Trash2 className="w-3 h-3" />
          {t.batchDelete}
        </button>
      </div>
    </div>
  );
}

interface BatchProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projects: { id: string; name: string }[];
  selectedProjectId: string | null;
  onProjectChange: (projectId: string) => void;
  onConfirm: () => void;
  isConfirming: boolean;
}

/**
 * BatchProjectDialog Component
 *
 * Dialog for selecting a project when batch adding papers.
 */
export function BatchProjectDialog({
  open,
  onOpenChange,
  projects,
  selectedProjectId,
  onProjectChange,
  onConfirm,
  isConfirming,
}: BatchProjectDialogProps) {
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    title: isZh ? "添加到项目" : "Add to Project",
    description: isZh ? `选择要将 ${selectedProjectId ? '已选论文' : '论文'} 添加到的项目` : "Select a project to add the selected papers to",
    selectProject: isZh ? "选择项目" : "Select a project",
    noProjects: isZh ? "暂无项目，请先创建项目" : "No projects available",
    cancel: isZh ? "取消" : "Cancel",
    confirm: isZh ? "确认添加" : "Confirm",
    confirming: isZh ? "添加中..." : "Adding...",
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{t.title}</DialogTitle>
          <DialogDescription>
            {t.description}
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          {projects.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t.noProjects}</p>
          ) : (
            <div className="space-y-2">
              {projects.map((project) => (
                <label
                  key={project.id}
                  className="flex items-center gap-3 p-3 border border-border/50 rounded-sm cursor-pointer hover:bg-muted transition-colors"
                >
                  <input
                    type="radio"
                    name="project"
                    checked={selectedProjectId === project.id}
                    onChange={() => onProjectChange(project.id)}
                    className="accent-primary w-4 h-4"
                  />
                  <span className="text-sm font-medium">{project.name}</span>
                </label>
              ))}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t.cancel}
          </Button>
          <Button
            onClick={onConfirm}
            disabled={selectedProjectId === null || isConfirming}
          >
            {isConfirming ? t.confirming : t.confirm}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
