import { Link } from 'react-router';

import type { Note } from '@/services/notesApi';
import { NoteFolderTree, type NoteFolder } from '@/app/components/NoteFolderTree';
import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select';
import { highlightText } from '@/features/notes/notePresentation';
import type { ReadingSummaryProjection } from '@/features/notes/ownership';
import { clsx } from 'clsx';
import {
  Clock,
  FileText,
  FolderOpen,
  Loader2,
  Plus,
  Search,
  Trash2,
} from 'lucide-react';

export interface NotesSummaryItem {
  summary: ReadingSummaryProjection;
  title: string;
  preview: string;
}

export interface NotesListItem {
  note: Note;
  displayTitle: string;
  preview: string;
  paperLabel: string | null;
  displayTag: string | null;
  updatedAtLabel: string;
}

interface ActiveFilterChip {
  key: string;
  label: string;
  onClear: () => void;
}

interface NotesSidebarProps {
  selectedFolderId: string | null;
  selectedNoteId: string | null;
  selectedSummaryPaperId: string | null;
  searchQuery: string;
  tagFilter: string;
  allTags: string[];
  folders: NoteFolder[];
  activeFilterChips: ActiveFilterChip[];
  notesLoading: boolean;
  catalogLoading: boolean;
  summaryItems: NotesSummaryItem[];
  archivedNoteItems: NotesListItem[];
  unarchivedNoteItems: NotesListItem[];
  onCreateNote: () => void;
  onSearchQueryChange: (value: string) => void;
  onTagFilterChange: (value: string) => void;
  onSelectFolder: (folderId: string | null) => void;
  onCreateFolder: (name: string, parentId: string | null) => void;
  onSelectSummary: (summary: ReadingSummaryProjection) => void;
  onSummaryAppend: (summary: ReadingSummaryProjection) => void;
  onSummaryToNote: (summary: ReadingSummaryProjection) => void;
  onSelectNote: (note: Note) => void;
  onDeleteNoteRequest: (noteId: string) => void;
}

export function NotesSidebar({
  selectedFolderId,
  selectedNoteId,
  selectedSummaryPaperId,
  searchQuery,
  tagFilter,
  allTags,
  folders,
  activeFilterChips,
  notesLoading,
  catalogLoading,
  summaryItems,
  archivedNoteItems,
  unarchivedNoteItems,
  onCreateNote,
  onSearchQueryChange,
  onTagFilterChange,
  onSelectFolder,
  onCreateFolder,
  onSelectSummary,
  onSummaryAppend,
  onSummaryToNote,
  onSelectNote,
  onDeleteNoteRequest,
}: NotesSidebarProps) {
  const hasAnyContent = summaryItems.length > 0 || archivedNoteItems.length > 0 || unarchivedNoteItems.length > 0;

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <div className="space-y-4 border-b border-border/30 bg-gradient-to-b from-white to-slate-50/50 px-5 py-5">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-xs font-semibold tracking-tight text-foreground">笔记库</h2>
          <Button variant="outline" size="sm" className="h-6 rounded-sm px-2.5 text-[9px] font-bold uppercase tracking-wider shadow-sm" onClick={onCreateNote}>
            <Plus className="mr-1 h-3 w-3" />
            新建
          </Button>
        </div>
        {!selectedFolderId ? (
          <p className="rounded border border-amber-200 bg-amber-50/50 px-2.5 py-1.5 text-[11px] text-amber-800">
            请选择文件夹后再新建笔记。
          </p>
        ) : null}

        <div className="group relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
          <Input
            type="text"
            value={searchQuery}
            onChange={(event) => onSearchQueryChange(event.target.value)}
            placeholder="搜索..."
            className="h-8 rounded border-border/40 bg-background/50 pl-8 text-xs shadow-sm focus-visible:ring-1 focus-visible:ring-primary/50"
          />
        </div>

        {allTags.length > 0 ? (
          <Select value={tagFilter} onValueChange={onTagFilterChange}>
            <SelectTrigger className="h-8 border-border/40 bg-background/50 text-xs shadow-sm focus:ring-1 focus:ring-primary/50">
              <SelectValue placeholder="全部标签" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="text-xs">全部标签</SelectItem>
              {allTags.map((tag) => (
                <SelectItem key={tag} value={tag} className="text-xs">
                  {tag}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : null}
      </div>

      <div className="border-y border-blue-200/40 bg-blue-50/30 px-4 py-3">
        <div className="mb-3 flex items-center justify-between border-b border-blue-200/30 px-1 pb-2 text-[10px] font-semibold text-blue-700/90">
          <span>文件夹</span>
        </div>
        <NoteFolderTree
          folders={folders}
          selectedFolderId={selectedFolderId}
          onSelectFolder={onSelectFolder}
          onCreateFolder={onCreateFolder}
        />
      </div>

      <div className="flex-1 overflow-y-auto border-t border-border/30 bg-background/40">
        {activeFilterChips.length > 0 ? (
          <div className="flex flex-wrap gap-2 border-b border-border/50 bg-background/60 px-3 py-2">
            {activeFilterChips.map((chip) => (
              <button
                key={chip.key}
                type="button"
                onClick={chip.onClear}
                className="inline-flex items-center gap-1 rounded-full border border-border/70 px-2 py-0.5 text-[10px] text-foreground/80 hover:bg-muted"
              >
                <span>{chip.label}</span>
                <span aria-hidden="true">×</span>
              </button>
            ))}
          </div>
        ) : null}

        {(notesLoading || catalogLoading) ? (
          <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            加载中...
          </div>
        ) : null}

        {!notesLoading && !catalogLoading && !hasAnyContent ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <FileText className="mb-3 h-10 w-10 opacity-40" />
            <p className="text-xs font-medium">当前范围内还没有内容</p>
            <p className="mt-1 text-[10px]">先选择文件夹创建笔记，或切换筛选查看其他论文的笔记与摘要。</p>
          </div>
        ) : null}

        {!notesLoading && summaryItems.length > 0 ? (
          <div className="border-b border-border/60 bg-amber-50/30">
            <div className="border-b border-amber-200/30 px-3 py-2.5 text-[10px] font-semibold text-amber-700/90">
              系统摘要
            </div>
            {summaryItems.map(({ summary, title, preview }) => (
              <div
                key={summary.paperId}
                role="button"
                tabIndex={0}
                className={clsx(
                  'group w-full border-l-2 border-l-transparent px-3 py-3 text-left transition-all duration-150',
                  selectedSummaryPaperId === summary.paperId
                    ? 'border-l-primary bg-primary/[0.03]'
                    : 'hover:border-l-primary/30 hover:bg-primary/[0.02]',
                )}
                onClick={() => onSelectSummary(summary)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onSelectSummary(summary);
                  }
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="line-clamp-1 text-xs font-medium text-amber-950">{title}</p>
                    <p className="mt-1 line-clamp-2 text-[11px] text-amber-900/80">
                      {highlightText(preview, searchQuery)}
                    </p>
                    <p className="mt-1 text-[10px] text-amber-800/80">系统摘要 · 只读</p>
                    <div className="mt-2 flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-6 px-2 text-[10px]"
                        onClick={(event) => {
                          event.stopPropagation();
                          onSummaryAppend(summary);
                        }}
                      >
                        加入当前笔记
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-6 px-2 text-[10px]"
                        onClick={(event) => {
                          event.stopPropagation();
                          onSummaryToNote(summary);
                        }}
                      >
                        转为笔记
                      </Button>
                      <Button asChild size="sm" variant="ghost" className="h-6 px-2 text-[10px]">
                        <Link to={`/read/${summary.paperId}?source=notes`}>打开阅读页</Link>
                      </Button>
                    </div>
                  </div>
                  <Badge variant="secondary" className="h-4 shrink-0 px-1 text-[9px]">
                    摘要
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {!notesLoading && (archivedNoteItems.length > 0 || unarchivedNoteItems.length > 0) ? (
          <div className="divide-y divide-border/50">
            {archivedNoteItems.map((item) => (
              <div
                key={item.note.id}
                className={clsx(
                  'group cursor-pointer border-l-2 border-l-transparent p-3 transition-all duration-150',
                  selectedNoteId === item.note.id
                    ? 'border-l-primary bg-primary/[0.03]'
                    : 'hover:border-l-primary/50 hover:bg-primary/[0.02]',
                )}
                onClick={() => onSelectNote(item.note)}
              >
                <div className="flex items-start justify-between gap-1">
                  <h4 className="line-clamp-1 flex-1 text-sm font-medium">
                    {highlightText(item.displayTitle, searchQuery)}
                  </h4>
                  <div className="flex items-center gap-1">
                    <button
                      className="rounded p-0.5 text-muted-foreground/80 transition-colors hover:bg-destructive/10 hover:text-destructive"
                      onClick={(event) => {
                        event.stopPropagation();
                        onDeleteNoteRequest(item.note.id);
                      }}
                      aria-label="删除笔记"
                      title="删除笔记"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>

                {item.paperLabel ? (
                  <div className="mt-1 flex items-center gap-1 text-[10px] text-amber-700">
                    <FolderOpen className="h-3 w-3" />
                    <span className="truncate">{item.paperLabel}</span>
                  </div>
                ) : null}

                <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                  {highlightText(item.preview, searchQuery)}
                </p>

                <div className="mt-1.5 flex items-center gap-2">
                  <Clock className="h-2.5 w-2.5 text-muted-foreground/60" />
                  <span className="text-[10px] text-muted-foreground/60">{item.updatedAtLabel}</span>
                  {item.displayTag ? (
                    <Badge variant="outline" className="h-4 px-1 py-0 text-[9px]">
                      {item.displayTag}
                    </Badge>
                  ) : null}
                </div>
              </div>
            ))}

            {unarchivedNoteItems.length > 0 ? (
              <div className="border-t border-border/60 bg-muted/20">
                <div className="px-3 py-2 text-[10px] font-semibold text-muted-foreground">未归档</div>
                {unarchivedNoteItems.map((item) => (
                  <div
                    key={item.note.id}
                    className={clsx(
                      'group cursor-pointer border-l-2 border-l-transparent p-3 transition-all duration-150',
                      selectedNoteId === item.note.id
                        ? 'border-l-primary bg-primary/[0.03]'
                        : 'hover:border-l-primary/50 hover:bg-primary/[0.02]',
                    )}
                    onClick={() => onSelectNote(item.note)}
                  >
                    <div className="flex items-start justify-between gap-1">
                      <h4 className="line-clamp-1 flex-1 text-sm font-medium">{item.displayTitle}</h4>
                      <button
                        className="rounded p-0.5 text-muted-foreground/80 transition-colors hover:bg-destructive/10 hover:text-destructive"
                        onClick={(event) => {
                          event.stopPropagation();
                          onDeleteNoteRequest(item.note.id);
                        }}
                        aria-label="删除笔记"
                        title="删除笔记"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{item.preview}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
