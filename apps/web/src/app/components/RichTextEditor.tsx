/**
 * Rich Text Editor Component with TipTap
 *
 * Features:
 * - Bold formatting
 * - Bullet and numbered lists
 * - Link insertion
 * - Placeholder support
 * - Clean toolbar UI
 *
 * Requirements: D-07 (Rich text editor with bold, lists, links)
 */

import { useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { Button } from './ui/button';
import { Bold, List, ListOrdered, LinkIcon } from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { LinkUrlDialog } from './LinkUrlDialog';

interface RichTextEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
}

export function RichTextEditor({
  content,
  onChange,
  placeholder,
}: RichTextEditorProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        link: false,
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-primary underline hover:text-primary/80',
        },
      }),
      Placeholder.configure({
        placeholder: placeholder || (isZh ? '开始编写笔记...' : 'Start writing notes...'),
      }),
    ],
    content: content,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class:
          'editorial-reading-surface prose prose-sm max-w-none p-4 min-h-[200px] text-[15px] leading-7 text-foreground focus:outline-none',
      },
    },
  });

  if (!editor) {
    return (
      <div className="p-4 text-muted-foreground">
        {isZh ? '加载编辑器...' : 'Loading editor...'}
      </div>
    );
  }

  const handleAddLink = () => {
    setLinkDialogOpen(true);
  };

  const handleRemoveLink = () => {
    editor.chain().focus().unsetLink().run();
  };

  return (
    <>
      <div className="border rounded-lg" data-testid="rich-text-editor">
        <div className="border-b p-2 flex gap-1 flex-wrap">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => editor.chain().focus().toggleBold().run()}
            className={clsx(editor.isActive('bold') ? 'bg-muted' : '')}
            title={isZh ? '加粗' : 'Bold'}
          >
            <Bold className="h-4 w-4" />
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            className={clsx(editor.isActive('bulletList') ? 'bg-muted' : '')}
            title={isZh ? '无序列表' : 'Bullet List'}
          >
            <List className="h-4 w-4" />
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            className={clsx(editor.isActive('orderedList') ? 'bg-muted' : '')}
            title={isZh ? '有序列表' : 'Numbered List'}
          >
            <ListOrdered className="h-4 w-4" />
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={editor.isActive('link') ? handleRemoveLink : handleAddLink}
            className={clsx(editor.isActive('link') ? 'bg-muted' : '')}
            title={isZh ? (editor.isActive('link') ? '移除链接' : '添加链接') : (editor.isActive('link') ? 'Remove Link' : 'Add Link')}
          >
            <LinkIcon className="h-4 w-4" />
          </Button>
        </div>

        <EditorContent editor={editor} className="min-h-[200px]" />
      </div>

      <LinkUrlDialog
        open={linkDialogOpen}
        onOpenChange={setLinkDialogOpen}
        title={isZh ? '添加链接' : 'Add link'}
        description={isZh ? '输入要插入到当前文本中的链接地址。' : 'Enter the URL to attach to the selected text.'}
        inputLabel={isZh ? '链接地址' : 'Link URL'}
        placeholder={isZh ? 'https://example.com' : 'https://example.com'}
        confirmLabel={isZh ? '插入链接' : 'Insert link'}
        clearLabel={isZh ? '移除链接' : 'Remove link'}
        cancelLabel={isZh ? '取消' : 'Cancel'}
        initialValue={String(editor.getAttributes('link').href || '')}
        onConfirm={(value) => {
          editor.chain().focus().extendMarkRange('link').setLink({ href: value }).run();
        }}
        onClear={editor.isActive('link') ? handleRemoveLink : undefined}
      />
    </>
  );
}
