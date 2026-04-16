/**
 * Note List Component with Multi-View Support
 *
 * Features:
 * - Time view: Sort by created/updated date
 * - Paper view: Group by associated papers
 * - Tag view: Group by tags
 * - View switching with smooth transitions
 * - Note card with preview and actions
 *
 * Requirements: D-08, D-09, D-10
 */

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Clock, 
  Tag, 
  FileText, 
  Grid, 
  List,
  Calendar,
  MoreVertical,
  Trash2,
  Edit3,
  ExternalLink,
  Search
} from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader } from './ui/card';
import { Input } from './ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';

export interface Note {
  id: string;
  title: string;
  content: string;
  tags: string[];
  paperIds: string[];
  papers?: Array<{
    id: string;
    title: string;
    authors: string[];
  }>;
  createdAt: string;
  updatedAt: string;
}

interface NoteListProps {
  notes: Note[];
  loading?: boolean;
  onEdit?: (noteId: string) => void;
  onDelete?: (noteId: string) => void;
  onViewNote?: (noteId: string) => void;
}

type ViewMode = 'time' | 'paper' | 'tag';

export function NoteList({ 
  notes, 
  loading = false,
  onEdit,
  onDelete,
  onViewNote
}: NoteListProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState<ViewMode>('time');
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Filter notes by search query
  const filteredNotes = useMemo(() => {
    if (!searchQuery.trim()) return notes;
    
    const query = searchQuery.toLowerCase();
    return notes.filter(note => 
      note.title.toLowerCase().includes(query) ||
      note.content.toLowerCase().includes(query) ||
      note.tags.some(tag => tag.toLowerCase().includes(query)) ||
      note.papers?.some(paper => paper.title.toLowerCase().includes(query))
    );
  }, [notes, searchQuery]);

  // Group notes by view mode
  const groupedNotes = useMemo(() => {
    if (viewMode === 'time') {
      // Sort by updated date, newest first
      return {
        [isZh ? '最近笔记' : 'Recent Notes']: [...filteredNotes].sort(
          (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
        )
      };
    }
    
    if (viewMode === 'paper') {
      // Group by papers
      const groups: Record<string, Note[]> = {};
      
      filteredNotes.forEach(note => {
        if (note.papers && note.papers.length > 0) {
          note.papers.forEach(paper => {
            const key = paper.title;
            if (!groups[key]) {
              groups[key] = [];
            }
            groups[key].push(note);
          });
        } else {
          const key = isZh ? '无关联论文' : 'No Associated Papers';
          if (!groups[key]) {
            groups[key] = [];
          }
          groups[key].push(note);
        }
      });
      
      return groups;
    }
    
    if (viewMode === 'tag') {
      // Group by tags
      const groups: Record<string, Note[]> = {};
      
      filteredNotes.forEach(note => {
        if (note.tags.length > 0) {
          note.tags.forEach(tag => {
            if (!groups[tag]) {
              groups[tag] = [];
            }
            groups[tag].push(note);
          });
        } else {
          const key = isZh ? '无标签' : 'Untagged';
          if (!groups[key]) {
            groups[key] = [];
          }
          groups[key].push(note);
        }
      });
      
      return groups;
    }
    
    return {};
  }, [filteredNotes, viewMode, isZh]);

  const handleDelete = async () => {
    if (!deleteNoteId || !onDelete) return;
    
    setIsDeleting(true);
    try {
      await onDelete(deleteNoteId);
    } catch (error) {
      console.error('Failed to delete note:', error);
    } finally {
      setIsDeleting(false);
      setDeleteNoteId(null);
    }
  };

  const handleNoteClick = (noteId: string) => {
    if (onViewNote) {
      onViewNote(noteId);
    }
  };

  const handlePaperClick = (paperId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/read/${paperId}`);
  };

  const t = {
    search: isZh ? '搜索笔记...' : 'Search notes...',
    timeView: isZh ? '时间' : 'Time',
    paperView: isZh ? '论文' : 'Paper',
    tagView: isZh ? '标签' : 'Tag',
    noNotes: isZh ? '暂无笔记' : 'No notes',
    noNotesDesc: isZh ? '创建您的第一篇笔记' : 'Create your first note',
    deleteTitle: isZh ? '确认删除' : 'Confirm Delete',
    deleteDesc: isZh ? '此操作不可撤销' : 'This action cannot be undone',
    cancel: isZh ? '取消' : 'Cancel',
    delete: isZh ? '删除' : 'Delete',
    deleteing: isZh ? '删除中...' : 'Deleting...',
    edit: isZh ? '编辑' : 'Edit',
    openPaper: isZh ? '打开论文' : 'Open Paper',
    noTitle: isZh ? '无标题' : 'Untitled',
    noTags: isZh ? '无标签' : 'No tags',
    noPapers: isZh ? '无关联论文' : 'No associated papers',
    notes: isZh ? '笔记' : 'Notes',
    updatedAt: isZh ? '更新于' : 'Updated',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">{isZh ? '加载中...' : 'Loading...'}</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with view switcher and search */}
      <div className="p-4 border-b space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-lg font-bold">{t.notes}</h2>
          
          {/* View mode switcher */}
          <div className="flex items-center gap-1 bg-muted/50 rounded-sm p-0.5">
            <button
              onClick={() => setViewMode('time')}
              className={clsx(
                'flex items-center gap-1 px-2 py-1 text-xs font-bold uppercase tracking-widest rounded-sm transition-colors',
                viewMode === 'time' 
                  ? 'bg-background text-foreground shadow-sm' 
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Clock className="w-3 h-3" />
              {t.timeView}
            </button>
            <button
              onClick={() => setViewMode('paper')}
              className={clsx(
                'flex items-center gap-1 px-2 py-1 text-xs font-bold uppercase tracking-widest rounded-sm transition-colors',
                viewMode === 'paper' 
                  ? 'bg-background text-foreground shadow-sm' 
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <FileText className="w-3 h-3" />
              {t.paperView}
            </button>
            <button
              onClick={() => setViewMode('tag')}
              className={clsx(
                'flex items-center gap-1 px-2 py-1 text-xs font-bold uppercase tracking-widest rounded-sm transition-colors',
                viewMode === 'tag' 
                  ? 'bg-background text-foreground shadow-sm' 
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Tag className="w-3 h-3" />
              {t.tagView}
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.search}
            className="pl-9 text-xs"
          />
        </div>
      </div>

      {/* Notes list */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredNotes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
            <FileText className="w-12 h-12 mb-4 opacity-50" />
            <p className="text-sm font-medium">{t.noNotes}</p>
            <p className="text-xs mt-1">{t.noNotesDesc}</p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedNotes).map(([groupName, groupNotes]) => (
              <div key={groupName}>
                {/* Group header */}
                <div className="flex items-center gap-2 mb-3">
                  {viewMode === 'tag' ? (
                    <Badge variant="secondary" className="text-xs">
                      {groupName}
                    </Badge>
                  ) : viewMode === 'paper' ? (
                    <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                  ) : (
                    <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
                  )}
                  <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    {groupName}
                  </h3>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {groupNotes.length}
                  </span>
                </div>

                {/* Notes grid */}
                <AnimatePresence mode="popLayout">
                  <motion.div
                    layout
                    className={clsx(
                      viewMode === 'paper' 
                        ? 'grid grid-cols-1 gap-3' 
                        : 'space-y-2'
                    )}
                  >
                    {groupNotes.map((note) => (
                      <motion.div
                        key={note.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        whileHover={{ scale: 1.01 }}
                        onClick={() => handleNoteClick(note.id)}
                        className={clsx(
                          'border bg-card rounded-sm cursor-pointer transition-all hover:shadow-md hover:border-primary/50',
                          viewMode === 'paper' 
                            ? 'p-4' 
                            : 'p-3'
                        )}
                      >
                        {/* Header */}
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="font-serif font-bold text-sm line-clamp-1 flex-1">
                            {note.title || t.noTitle}
                          </h4>
                          
                          {/* Actions */}
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <button 
                                className="text-muted-foreground hover:text-foreground p-1"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <MoreVertical className="w-3.5 h-3.5" />
                              </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              {onEdit && (
                                <DropdownMenuItem onClick={() => onEdit(note.id)}>
                                  <Edit3 className="w-3.5 h-3.5 mr-2" />
                                  {t.edit}
                                </DropdownMenuItem>
                              )}
                              {note.papers && note.papers.length > 0 && (
                                <DropdownMenuItem onClick={(e) => {
                                  e.stopPropagation();
                                  handlePaperClick(note.papers![0].id, e);
                                }}>
                                  <ExternalLink className="w-3.5 h-3.5 mr-2" />
                                  {t.openPaper}
                                </DropdownMenuItem>
                              )}
                              {onDelete && (
                                <DropdownMenuItem 
                                  onClick={() => setDeleteNoteId(note.id)}
                                  className="text-destructive"
                                >
                                  <Trash2 className="w-3.5 h-3.5 mr-2" />
                                  {t.delete}
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>

                        {/* Content preview */}
                        <div 
                          className="text-xs text-muted-foreground line-clamp-2 mb-3 prose prose-sm"
                          dangerouslySetInnerHTML={{ __html: note.content }}
                        />

                        {/* Meta */}
                        <div className="flex items-center justify-between">
                          {/* Tags */}
                          {note.tags.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {note.tags.slice(0, 3).map(tag => (
                                <Badge key={tag} variant="outline" className="text-[9px] px-1 py-0">
                                  {tag}
                                </Badge>
                              ))}
                              {note.tags.length > 3 && (
                                <span className="text-[9px] text-muted-foreground">
                                  +{note.tags.length - 3}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-[9px] text-muted-foreground">{t.noTags}</span>
                          )}

                          {/* Date */}
                          <div className="flex items-center gap-1 text-[9px] text-muted-foreground">
                            <Clock className="w-2.5 h-2.5" />
                            <span>
                              {t.updatedAt} {new Date(note.updatedAt).toLocaleDateString(isZh ? 'zh-CN' : 'en-US', {
                                month: 'short',
                                day: 'numeric'
                              })}
                            </span>
                          </div>
                        </div>

                        {/* Associated papers (in paper view) */}
                        {viewMode === 'paper' && note.papers && note.papers.length > 1 && (
                          <div className="mt-3 pt-3 border-t flex flex-wrap gap-1">
                            {note.papers.slice(1, 3).map(paper => (
                              <button
                                key={paper.id}
                                onClick={(e) => handlePaperClick(paper.id, e)}
                                className="text-[9px] text-primary hover:underline truncate max-w-[150px]"
                              >
                                + {paper.title}
                              </button>
                            ))}
                            {note.papers.length > 3 && (
                              <span className="text-[9px] text-muted-foreground">
                                +{note.papers.length - 3} {isZh ? '更多' : 'more'}
                              </span>
                            )}
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </motion.div>
                </AnimatePresence>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!deleteNoteId} onOpenChange={(open) => {
        if (!open) setDeleteNoteId(null);
      }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t.deleteTitle}</AlertDialogTitle>
            <AlertDialogDescription>{t.deleteDesc}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t.cancel}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? t.deleteing : t.delete}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
