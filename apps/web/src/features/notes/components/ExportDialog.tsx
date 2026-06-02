/**
 * ExportDialog - Export notes to Markdown or BibTeX
 *
 * Provides format selection, content preview, and download functionality.
 */

import { useCallback, useMemo, useState } from 'react';
import { Download, FileText, BookOpen, Copy, Check } from 'lucide-react';

import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from '@/app/components/ui/alert-dialog';
import { Button } from '@/app/components/ui/button';
import { Badge } from '@/app/components/ui/badge';
import type { Note } from '@/services/notesApi';
import { extractEditorPlainText, normalizeEditorDocument } from '@/features/notes/content';
import { extractMentions } from '@/features/notes/editor/extensions/mentionUtils';
import { buildNoteDisplayTitle } from '@/features/notes/notePresentation';

type ExportFormat = 'markdown' | 'bibtex';

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  note: Note;
  paperTitleMap: Map<string, string>;
}

export function ExportDialog({
  open,
  onOpenChange,
  note,
  paperTitleMap,
}: ExportDialogProps) {
  const [format, setFormat] = useState<ExportFormat>('markdown');
  const [copied, setCopied] = useState(false);

  const title = buildNoteDisplayTitle(note, paperTitleMap);

  const exportContent = useMemo(() => {
    if (format === 'markdown') return generateMarkdown(note, title);
    return generateBibTeX(note, title);
  }, [format, note, title]);

  const handleDownload = useCallback(() => {
    const ext = format === 'markdown' ? 'md' : 'bib';
    const mimeType = format === 'markdown' ? 'text/markdown' : 'text/x-bibtex';
    const blob = new Blob([exportContent], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sanitizeFilename(title)}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportContent, format, title]);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(exportContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [exportContent]);

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            导出笔记
          </AlertDialogTitle>
          <AlertDialogDescription>
            选择格式并预览导出内容
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-4">
          {/* Format selector */}
          <div className="flex gap-2">
            <Button
              variant={format === 'markdown' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFormat('markdown')}
              className="gap-1.5"
            >
              <FileText className="h-3.5 w-3.5" />
              Markdown
            </Button>
            <Button
              variant={format === 'bibtex' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFormat('bibtex')}
              className="gap-1.5"
            >
              <BookOpen className="h-3.5 w-3.5" />
              BibTeX
            </Button>
          </div>

          {/* Preview */}
          <div className="max-h-[400px] overflow-auto rounded-lg border border-border bg-muted/30 p-4">
            <pre className="whitespace-pre-wrap font-mono text-xs leading-5 text-foreground">
              {exportContent}
            </pre>
          </div>

          {/* Metadata */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="text-[10px]">
              {format === 'markdown' ? '.md' : '.bib'}
            </Badge>
            <span>{exportContent.length} 字符</span>
            {note.linkedEvidence && note.linkedEvidence.length > 0 && (
              <span>· {note.linkedEvidence.length} 条关联证据</span>
            )}
          </div>
        </div>

        <AlertDialogFooter className="gap-2">
          <AlertDialogCancel>关闭</AlertDialogCancel>
          <Button variant="outline" size="sm" onClick={handleCopy} className="gap-1.5">
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? '已复制' : '复制'}
          </Button>
          <Button size="sm" onClick={handleDownload} className="gap-1.5">
            <Download className="h-3.5 w-3.5" />
            下载
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function generateMarkdown(note: Note, title: string): string {
  const lines: string[] = [];

  lines.push(`# ${title}`);
  lines.push('');

  if (note.paperIds.length > 0) {
    lines.push(`**关联论文:** ${note.paperIds.join(', ')}`);
    lines.push('');
  }

  if (note.tags.length > 0) {
    lines.push(`**标签:** ${note.tags.join(', ')}`);
    lines.push('');
  }

  lines.push('---');
  lines.push('');

  const body = extractEditorPlainText(note.contentDoc || note.content);
  lines.push(body);

  if (note.linkedEvidence && note.linkedEvidence.length > 0) {
    lines.push('');
    lines.push('## 关联证据');
    lines.push('');
    for (const evidence of note.linkedEvidence) {
      lines.push(`> ${evidence.text}`);
      if (evidence.source_chunk_id) {
        lines.push(`> — 来源: ${evidence.source_chunk_id}`);
      }
      lines.push('');
    }
  }

  // Extract mentions
  const doc = normalizeEditorDocument(note.contentDoc || note.content);
  const mentions = extractMentions(doc);
  if (mentions.length > 0) {
    lines.push('## 引用');
    lines.push('');
    for (const mention of mentions) {
      lines.push(`- @${mention.type}:${mention.label} (${mention.id})`);
    }
  }

  return lines.join('\n');
}

function generateBibTeX(note: Note, title: string): string {
  const lines: string[] = [];
  const key = sanitizeFilename(title).replace(/[^a-zA-Z0-9]/g, '').slice(0, 40);

  lines.push(`@article{${key},`);
  lines.push(`  title = {${title}},`);
  lines.push(`  note = {${extractEditorPlainText(note.contentDoc || note.content, 500)}},`);

  if (note.paperIds.length > 0) {
    lines.push(`  keywords = {${note.tags.join(', ')}},`);
  }

  lines.push(`  year = {${new Date(note.createdAt).getFullYear()}},`);
  lines.push('}');

  return lines.join('\n');
}

function sanitizeFilename(name: string): string {
  return name.replace(/[<>:"/\\|?*]/g, '_').slice(0, 100);
}
