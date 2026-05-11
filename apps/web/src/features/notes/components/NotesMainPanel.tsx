import { Link } from 'react-router';

import type { Note } from '@/services/notesApi';
import { NotesEditor } from '@/app/components/NotesEditor';
import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { LinkedEvidenceList } from '@/features/notes/components/LinkedEvidenceList';
import { buildNoteDisplayTitle, buildSummaryDisplayTitle } from '@/features/notes/notePresentation';
import type { ReadingSummaryProjection } from '@/features/notes/ownership';
import { normalizeEditorDocument } from '@/features/notes/content';
import { FileText, Sparkles } from 'lucide-react';
import type { ReactNode } from 'react';

interface NotesMainPanelProps {
  selectedNote: Note | null;
  selectedSummary: ReadingSummaryProjection | null;
  selectedNoteDisplayTitle: string;
  editingTitle: boolean;
  draftTitle: string;
  editorContent: any;
  paperIdFilter: string | null;
  paperTitleMap: Map<string, string>;
  saveIndicator: ReactNode;
  onDraftTitleChange: (value: string) => void;
  onStartEditingTitle: () => void;
  onCommitTitle: () => void;
  onCancelEditingTitle: () => void;
  onInsertPaperReference: () => void;
  onEditorChange: (json: any) => void;
}

export function NotesMainPanel({
  selectedNote,
  selectedSummary,
  selectedNoteDisplayTitle,
  editingTitle,
  draftTitle,
  editorContent,
  paperIdFilter,
  paperTitleMap,
  saveIndicator,
  onDraftTitleChange,
  onStartEditingTitle,
  onCommitTitle,
  onCancelEditingTitle,
  onInsertPaperReference,
  onEditorChange,
}: NotesMainPanelProps) {
  if (selectedNote) {
    return (
      <div className="flex h-full min-h-0 flex-col rounded-bl-lg rounded-tl-lg border-l border-border/20 bg-background">
        <div className="flex items-center justify-between border-b border-border/50 bg-background/60 px-5 py-3 backdrop-blur-sm">
          <div>
            {editingTitle ? (
              <Input
                value={draftTitle}
                onChange={(event) => onDraftTitleChange(event.target.value)}
                className="h-8 w-[320px] text-sm"
                onBlur={onCommitTitle}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.currentTarget.blur();
                  }
                  if (event.key === 'Escape') {
                    onCancelEditingTitle();
                  }
                }}
                autoFocus
              />
            ) : (
              <button
                type="button"
                className="text-left text-sm font-semibold tracking-tight hover:text-primary"
                onClick={onStartEditingTitle}
              >
                {selectedNoteDisplayTitle}
              </button>
            )}
            <div className="mt-1 flex items-center gap-2">
              {selectedNote.paperIds.length > 0 ? (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <FileText className="h-3 w-3" />
                  <span>关联 {selectedNote.paperIds.length} 篇论文</span>
                </div>
              ) : null}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {paperIdFilter ? (
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-[10px]"
                onClick={onInsertPaperReference}
              >
                插入论文引用
              </Button>
            ) : null}
            {saveIndicator}
          </div>
        </div>

        <div className="flex-1 overflow-auto bg-background p-6">
          <div className="mx-auto max-w-4xl">
            <LinkedEvidenceList
              evidence={selectedNote.linkedEvidence || []}
              noteTitle={buildNoteDisplayTitle(selectedNote, paperTitleMap)}
              noteId={selectedNote.id}
            />
            <NotesEditor
              content={editorContent}
              onChange={onEditorChange}
              placeholder="开始写笔记... 使用 [[pdf:paperId:page:5]] 引用论文"
            />
          </div>
        </div>
      </div>
    );
  }

  if (selectedSummary) {
    return (
      <div className="flex h-full min-h-0 flex-col rounded-bl-lg rounded-tl-lg border-l border-border/20 bg-background">
        <div className="flex items-center justify-between border-b border-border/50 bg-background/60 px-5 py-3 backdrop-blur-sm">
          <div>
            <h3 className="font-serif text-sm font-medium tracking-tight">
              {buildSummaryDisplayTitle(selectedSummary.title, selectedSummary.readingNotes)}
            </h3>
            <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="secondary" className="h-4 text-[10px]">
                <Sparkles className="mr-0.5 h-2.5 w-2.5" />
                系统生成摘要
              </Badge>
              <span>来自论文摘要卡片的系统生成内容</span>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to={`/read/${selectedSummary.paperId}`}>打开论文</Link>
          </Button>
        </div>

        <div className="flex-1 overflow-auto bg-background px-6 py-5">
          <div className="mx-auto max-w-3xl rounded-xl border border-amber-200/60 bg-amber-50/30 p-6 shadow-xs">
            <p className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
              系统摘要
            </p>
            <NotesEditor
              content={normalizeEditorDocument(selectedSummary.readingNotes)}
              onChange={() => {}}
              readOnly
              hideToolbar
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-gradient-to-b from-background to-slate-50/30 text-muted-foreground">
      <FileText className="mb-3 h-12 w-12 opacity-30" />
      <p className="text-sm font-medium">选择内容开始编辑</p>
      <p className="mt-2 text-xs text-muted-foreground/60">
        从左侧选择一条笔记继续编辑，或打开论文摘要继续沉淀到当前笔记。
      </p>
    </div>
  );
}
