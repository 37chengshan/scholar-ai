/**
 * Notes Editor Component with TipTap Rich Text Editor
 *
 * Features:
 * - Rich text editing with TipTap (bold, italic, lists, link)
 * - PDF reference chips rendered inline
 * - Character count display
 * - Controlled component with JSON output (Tiptap format)
 * - readOnly mode support
 *
 * Requirements: D-11, D-13, D-05
 */

import { useEffect, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
import { Button } from './ui/button';
import { Separator } from './ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from './ui/tooltip';
import { Bold, Italic, List, ListOrdered, Link as LinkIcon } from 'lucide-react';
import { clsx } from 'clsx';

interface NotesEditorProps {
  content: any; // Tiptap JSON
  onChange: (json: any) => void;
  placeholder?: string;
  readOnly?: boolean;
  hideToolbar?: boolean;
}

export function NotesEditor({
  content,
  onChange,
  placeholder = '开始写笔记...',
  readOnly = false,
  hideToolbar = false,
}: NotesEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        blockquote: false,
        horizontalRule: false,
        dropcursor: false,
        gapcursor: false,
        hardBreak: false,
      }),
      Link.configure({
        openOnClick: false,
      }),
      Placeholder.configure({
        placeholder,
      }),
      CharacterCount.configure({
        limit: undefined,
      }),
    ],
    content: content,
    editable: !readOnly,
    onUpdate: useCallback(({ editor }: { editor: any }) => {
      onChange(editor.getJSON());
    }, [onChange]),
    editorProps: {
      attributes: {
        class: 'prose prose-sm focus:outline-none max-w-none',
      },
    },
  });

  // Update editor content when prop changes (e.g., switching notes)
  useEffect(() => {
    if (editor && content) {
      const currentJson = editor.getJSON();
      const newJson = typeof content === 'object' ? content : null;
      // Only update if content actually changed (avoid cursor jump)
      if (JSON.stringify(currentJson) !== JSON.stringify(newJson)) {
        editor.commands.setContent(content);
      }
    }
  }, [content, editor]);

  // Toggle readOnly mode
  useEffect(() => {
    if (editor) {
      editor.setEditable(!readOnly);
    }
  }, [editor, readOnly]);

  const handleAddLink = () => {
    if (!editor) return;
    const url = window.prompt('输入链接地址:');
    if (url === null) return; // cancelled
    if (url === '') {
      editor.chain().focus().unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  };

  if (!editor) {
    return <div className="p-4 text-muted-foreground">Loading editor...</div>;
  }

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full bg-white border border-border rounded-lg overflow-hidden">
        {/* Toolbar */}
        {!hideToolbar && (
          <div className="flex items-center gap-1 p-2 border-b border-border bg-muted/30">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => editor.chain().focus().toggleBold().run()}
                className={clsx(
                  'h-8 w-8 p-0',
                  editor.isActive('bold') && 'bg-accent/10 text-accent'
                )}
              >
                <Bold className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>加粗 (Ctrl+B)</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => editor.chain().focus().toggleItalic().run()}
                className={clsx(
                  'h-8 w-8 p-0',
                  editor.isActive('italic') && 'bg-accent/10 text-accent'
                )}
              >
                <Italic className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>斜体 (Ctrl+I)</TooltipContent>
          </Tooltip>

          <Separator orientation="vertical" className="h-6 mx-1" />

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                className={clsx(
                  'h-8 w-8 p-0',
                  editor.isActive('bulletList') && 'bg-accent/10 text-accent'
                )}
              >
                <List className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>无序列表</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
                className={clsx(
                  'h-8 w-8 p-0',
                  editor.isActive('orderedList') && 'bg-accent/10 text-accent'
                )}
              >
                <ListOrdered className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>有序列表</TooltipContent>
          </Tooltip>

          <Separator orientation="vertical" className="h-6 mx-1" />

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleAddLink}
                className={clsx(
                  'h-8 w-8 p-0',
                  editor.isActive('link') && 'bg-accent/10 text-accent'
                )}
              >
                <LinkIcon className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>插入链接</TooltipContent>
          </Tooltip>
          </div>
        )}

        {/* Editor Content */}
        <div className="flex-1 overflow-auto p-4 min-h-[300px]">
          <EditorContent editor={editor} />
        </div>

        {/* Character Count */}
        <div className="px-3 py-1.5 border-t border-border text-xs text-muted-foreground text-right bg-muted/20">
          {editor.storage.characterCount.characters()} 字符
        </div>
      </div>
    </TooltipProvider>
  );
}
