/**
 * ScholarAIEditor - Rich Text Editor for Notes
 *
 * TipTap-based editor with block types: paragraph, heading 1-3,
 * code block, blockquote, callout. Supports bold, italic, links,
 * bullet/ordered lists.
 */

import { useCallback, useEffect, useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
import { clsx } from 'clsx';

import { Button } from '@/app/components/ui/button';
import { Separator } from '@/app/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/app/components/ui/tooltip';
import { LinkUrlDialog } from '@/app/components/LinkUrlDialog';
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Link as LinkIcon,
  Quote,
  Code,
  Heading1,
  Heading2,
  Heading3,
  Info,
} from 'lucide-react';

import type { ScholarAIEditorProps, EditorContentDocument } from './editorTypes';
import { CalloutExtension } from './extensions/CalloutExtension';
import { MentionExtension } from './extensions/MentionExtension';
import { SmartLinkExtension } from './extensions/SmartLinkExtension';

export function ScholarAIEditor({
  content,
  onChange,
  placeholder = '开始写笔记...',
  readOnly = false,
  hideToolbar = false,
  className,
}: ScholarAIEditorProps) {
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        codeBlock: {},
        blockquote: {},
        horizontalRule: false,
        dropcursor: false,
        gapcursor: false,
      }),
      Link.configure({ openOnClick: false }),
      Placeholder.configure({ placeholder }),
      CharacterCount.configure({ limit: undefined }),
      CalloutExtension,
      MentionExtension,
      SmartLinkExtension,
    ],
    content: content as object,
    editable: !readOnly,
    onUpdate: useCallback(({ editor: ed }: { editor: any }) => {
      onChange(ed.getJSON() as EditorContentDocument);
    }, [onChange]),
    editorProps: {
      attributes: {
        class: 'editorial-reading-surface prose prose-sm max-w-none text-[15px] leading-7 text-foreground focus:outline-none',
      },
    },
  });

  // Sync content when prop changes (e.g., switching notes)
  useEffect(() => {
    if (editor && content) {
      const currentJson = JSON.stringify(editor.getJSON());
      const newJson = JSON.stringify(content);
      if (currentJson !== newJson) {
        editor.commands.setContent(content as object);
      }
    }
  }, [content, editor]);

  // Sync readOnly mode
  useEffect(() => {
    if (editor) editor.setEditable(!readOnly);
  }, [editor, readOnly]);

  if (!editor) {
    return <div className="p-4 text-muted-foreground">Loading editor...</div>;
  }

  const handleAddLink = () => setLinkDialogOpen(true);

  const isActive = (name: string, attrs?: Record<string, unknown>) => editor.isActive(name, attrs);

  return (
    <>
      <TooltipProvider>
        <div className={clsx('flex h-full flex-col overflow-hidden rounded-lg border border-border bg-white', className)}>
          {!hideToolbar && (
            <div className="flex flex-wrap items-center gap-0.5 border-b border-border bg-muted/30 p-1.5">
              {/* Text formatting */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleBold().run()}
                    className={clsx('h-7 w-7 p-0', isActive('bold') && 'bg-accent/10 text-accent')}>
                    <Bold className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>加粗 (Ctrl+B)</TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleItalic().run()}
                    className={clsx('h-7 w-7 p-0', isActive('italic') && 'bg-accent/10 text-accent')}>
                    <Italic className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>斜体 (Ctrl+I)</TooltipContent>
              </Tooltip>

              <Separator orientation="vertical" className="mx-1 h-5" />

              {/* Headings */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                    className={clsx('h-7 w-7 p-0', isActive('heading', { level: 1 }) && 'bg-accent/10 text-accent')}>
                    <Heading1 className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>标题 1</TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                    className={clsx('h-7 w-7 p-0', isActive('heading', { level: 2 }) && 'bg-accent/10 text-accent')}>
                    <Heading2 className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>标题 2</TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
                    className={clsx('h-7 w-7 p-0', isActive('heading', { level: 3 }) && 'bg-accent/10 text-accent')}>
                    <Heading3 className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>标题 3</TooltipContent>
              </Tooltip>

              <Separator orientation="vertical" className="mx-1 h-5" />

              {/* Lists */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleBulletList().run()}
                    className={clsx('h-7 w-7 p-0', isActive('bulletList') && 'bg-accent/10 text-accent')}>
                    <List className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>无序列表</TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleOrderedList().run()}
                    className={clsx('h-7 w-7 p-0', isActive('orderedList') && 'bg-accent/10 text-accent')}>
                    <ListOrdered className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>有序列表</TooltipContent>
              </Tooltip>

              <Separator orientation="vertical" className="mx-1 h-5" />

              {/* Block types */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleCodeBlock().run()}
                    className={clsx('h-7 w-7 p-0', isActive('codeBlock') && 'bg-accent/10 text-accent')}>
                    <Code className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>代码块</TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleBlockquote().run()}
                    className={clsx('h-7 w-7 p-0', isActive('blockquote') && 'bg-accent/10 text-accent')}>
                    <Quote className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>引用</TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().toggleCallout().run()}
                    className={clsx('h-7 w-7 p-0', isActive('callout') && 'bg-accent/10 text-accent')}>
                    <Info className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>提示框</TooltipContent>
              </Tooltip>

              <Separator orientation="vertical" className="mx-1 h-5" />

              {/* Link */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" onClick={handleAddLink}
                    className={clsx('h-7 w-7 p-0', isActive('link') && 'bg-accent/10 text-accent')}>
                    <LinkIcon className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>插入链接</TooltipContent>
              </Tooltip>
            </div>
          )}

          <div className="min-h-[300px] flex-1 overflow-auto bg-background/35 p-4">
            <EditorContent editor={editor} />
          </div>

          <div className="flex items-center justify-end border-t border-border bg-muted/20 px-3 py-1.5 text-xs text-muted-foreground">
            {editor.storage.characterCount.characters()} 字符
          </div>
        </div>
      </TooltipProvider>

      <LinkUrlDialog
        open={linkDialogOpen}
        onOpenChange={setLinkDialogOpen}
        title="插入链接"
        description="输入链接地址后，当前选中文本会附加该链接。"
        inputLabel="链接地址"
        placeholder="https://example.com"
        confirmLabel="确认插入"
        clearLabel="移除链接"
        cancelLabel="取消"
        initialValue={String(editor.getAttributes('link').href || '')}
        onConfirm={(value) => {
          editor.chain().focus().extendMarkRange('link').setLink({ href: value }).run();
        }}
        onClear={isActive('link') ? () => editor.chain().focus().unsetLink().run() : undefined}
      />
    </>
  );
}
