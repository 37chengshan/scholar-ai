/**
 * Notes Editor Component with TipTap Rich Text Editor
 *
 * Features:
 * - Rich text editing with TipTap
 * - Basic formatting: bold, lists, code blocks
 * - Auto-save every 30 seconds
 * - Controlled component with parent state
 * - Cross-paper association support
 *
 * Requirements: D-06, D-07
 */

import { useState, useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Button } from './ui/button';
import { Separator } from './ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from './ui/tooltip';
import { Bold, List, ListOrdered, Code, Link, Paperclip } from 'lucide-react';

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
  onLinkPaper?: (paperId: string) => void;
  onUnlinkPaper?: (paperId: string) => void;
}

export function NotesEditor({ 
  content, 
  onSave, 
  paperId,
  linkedPapers = [],
  onLinkPaper,
  onUnlinkPaper 
}: NotesEditorProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [showLinkPicker, setShowLinkPicker] = useState(false);

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
                    onClick={() => setShowLinkPicker(!showLinkPicker)}
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
                  <span className="truncate max-w-[150px]">{paper.title}</span>
                  {onUnlinkPaper && (
                    <button
                      onClick={() => onUnlinkPaper(paper.id)}
                      className="hover:text-destructive"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Link Paper Picker */}
          {showLinkPicker && onLinkPaper && (
            <div className="pt-1 border-t">
              <input
                type="text"
                placeholder="Search papers to link..."
                className="w-full text-xs p-1 border rounded"
                onKeyDown={async (e) => {
                  if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                    // TODO: Implement paper search
                    console.log('Search for paper:', e.currentTarget.value);
                    setShowLinkPicker(false);
                  }
                }}
                onBlur={() => setTimeout(() => setShowLinkPicker(false), 200)}
              />
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
