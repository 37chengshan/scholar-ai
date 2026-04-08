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

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { Button } from './ui/button';
import { Bold, List, ListOrdered, LinkIcon } from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';

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

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
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
        class: 'prose prose-sm max-w-none p-4 min-h-[200px] focus:outline-none',
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
    const url = window.prompt(
      isZh ? '输入链接 URL:' : 'Enter link URL:'
    );
    if (url) {
      editor.chain().focus().setLink({ href: url }).run();
    }
  };

  const handleRemoveLink = () => {
    editor.chain().focus().unsetLink().run();
  };

  return (
    <div className="border rounded-lg" data-testid="rich-text-editor">
      {/* Toolbar */}
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

      {/* Editor Content */}
      <EditorContent editor={editor} className="min-h-[200px]" />
    </div>
  );
}