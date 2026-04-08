/**
 * Notes Editor Component with TipTap Rich Text Editor
 *
 * Features:
 * - Rich text editing with TipTap
 * - Basic formatting: bold, lists, code blocks
 * - Auto-save every 30 seconds
 * - Controlled component with parent state
 * - Cross-paper association support with search
 *
 * Requirements: D-06, D-07
 */

import { useState, useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Button } from './ui/button';
import { Separator } from './ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from './ui/tooltip';
import { Bold, List, ListOrdered, Code, Paperclip, Loader2 } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';
import { clsx } from 'clsx';

interface LinkedPaper {
  id: string;
  title: string;
  authors: string[];
  year: number;
}

interface NotesEditorProps {
  content: string;
  onSave: (content: string) => void;
  paperId?: string;
  linkedPapers?: LinkedPaper[];
  onLinkPaper?: () => void;
  onUnlinkPaper?: (paperId: string) => void;
  showLinkPicker?: boolean;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  searchResults?: any[];
  searching?: boolean;
  onLinkPaperSelect?: (paperId: string) => void;
}

export function NotesEditor({ 
  content, 
  onSave, 
  paperId,
  linkedPapers = [],
  onLinkPaper,
  onUnlinkPaper,
  showLinkPicker = false,
  searchQuery = '',
  onSearchChange,
  searchResults = [],
  searching = false,
  onLinkPaperSelect
}: NotesEditorProps) {
  const [isSaving, setIsSaving] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        bold: false,
        list: false,
        codeBlock: false,
      }),
      StarterKit.extensionBold,
      StarterKit.extensionBulletList,
      StarterKit.extensionOrderedList,
      StarterKit.extensionCodeBlock,
    ],
    content: content,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      // Debounce save
      clearTimeout(saveTimeout);
      saveTimeout = setTimeout(() => {
        onSave(html);
      }, 300);
    },
    editorProps: {
      attributes: {
        class: 'prose prose-sm focus:outline-none p-3 h-full overflow-auto',
      },
    },
  });

  let saveTimeout: NodeJS.Timeout;

  // Update editor content when prop changes
  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content);
    }
  }, [content, editor]);

  // Auto-save every 30s
  useEffect(() => {
    const timer = setInterval(() => {
      if (editor) {
        const html = editor.getHTML();
        if (html !== content) {
          setIsSaving(true);
          onSave(html);
          setTimeout(() => setIsSaving(false), 500);
        }
      }
    }, 30000);
    return () => clearInterval(timer);
  }, [editor, content, onSave]);

  if (!editor) {
    return <div className="p-4">Loading editor...</div>;
  }

  return (
    <TooltipProvider>
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="p-2 border-b space-y-2">
          <div className="font-medium text-sm">Notes</div>
          
          {/* Toolbar */}
          <div className="flex items-center gap-1 flex-wrap">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => editor.chain().focus().toggleBold().run()}
                  className={editor.isActive('bold') ? 'bg-muted' : ''}
                >
                  <Bold className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Bold</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => editor.chain().focus().toggleBulletList().run()}
                  className={editor.isActive('bulletList') ? 'bg-muted' : ''}
                >
                  <List className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Bullet List</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => editor.chain().focus().toggleOrderedList().run()}
                  className={editor.isActive('orderedList') ? 'bg-muted' : ''}
                >
                  <ListOrdered className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Numbered List</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => editor.chain().focus().toggleCodeBlock().run()}
                  className={editor.isActive('codeBlock') ? 'bg-muted' : ''}
                >
                  <Code className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Code Block</TooltipContent>
            </Tooltip>

            <Separator orientation="vertical" className="h-6 mx-1" />

            {/* Link Paper Button */}
            {onLinkPaper && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onLinkPaper}
                  >
                    <Paperclip className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Link Paper</TooltipContent>
              </Tooltip>
            )}
          </div>

          {/* Linked Papers Display */}
          {linkedPapers.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {linkedPapers.map(paper => (
                <div
                  key={paper.id}
                  className="inline-flex items-center gap-1 bg-muted px-2 py-0.5 rounded text-xs"
                >
                  <span className="truncate max-w-[120px]">{paper.title}</span>
                  {onUnlinkPaper && (
                    <button
                      onClick={() => onUnlinkPaper(paper.id)}
                      className="hover:text-destructive text-muted-foreground"
                      title="Unlink paper"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Link Paper Picker with Search */}
          {showLinkPicker && (
            <div className="pt-1 border-t space-y-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => onSearchChange?.(e.target.value)}
                placeholder="Search papers to link..."
                className="w-full text-xs p-1.5 border rounded focus:outline-none focus:ring-1 focus:ring-primary"
                autoFocus
              />
              
              <ScrollArea className="h-48">
                {searching ? (
                  <div className="flex items-center justify-center py-4 text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    <span className="text-xs">Searching...</span>
                  </div>
                ) : searchResults.length > 0 ? (
                  <div className="space-y-1">
                    {searchResults.map(paper => (
                      <button
                        key={paper.id}
                        onClick={() => onLinkPaperSelect?.(paper.id)}
                        className="w-full text-left p-2 hover:bg-muted rounded text-xs transition-colors group"
                      >
                        <div className="font-medium line-clamp-1 group-hover:text-primary">
                          {paper.title}
                        </div>
                        <div className="text-muted-foreground text-[10px] mt-0.5">
                          {paper.authors?.slice(0, 2).join(', ')}
                          {paper.authors?.length > 2 ? ` +${paper.authors.length - 2}` : ''}
                          {' • '}{paper.year || 'n.d.'}
                        </div>
                      </button>
                    ))}
                  </div>
                ) : searchQuery.trim().length >= 2 ? (
                  <div className="text-center py-4 text-muted-foreground text-xs">
                    No papers found
                  </div>
                ) : (
                  <div className="text-center py-4 text-muted-foreground text-xs">
                    Type to search papers
                  </div>
                )}
              </ScrollArea>
            </div>
          )}
        </div>

        {/* Editor Content */}
        <div className="flex-1 overflow-hidden">
          <EditorContent editor={editor} className="h-full" />
        </div>

        {/* Status Bar */}
        <div className="px-3 py-1 border-t text-xs text-muted-foreground flex justify-between">
          <span>{isSaving ? 'Saving...' : 'Saved'}</span>
          <span>{editor.storage.characterCount?.words() || 0} words</span>
        </div>
      </div>
    </TooltipProvider>
  );
}
