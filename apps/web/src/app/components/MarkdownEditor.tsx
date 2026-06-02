import { useState } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { simpleMarkdownToHtml } from '../../lib/markdown-utils';

interface MarkdownEditorProps {
  value: string;
  onChange: (content: string) => void;
  placeholder?: string;
  onSave?: () => void;
}

/**
 * MarkdownEditor Component
 *
 * Simple textarea + preview for Markdown notes (D-08).
 * Supports basic Markdown syntax:
 * - Headers (# ## ###)
 * - Lists (- * 1.)
 * - Links ([text](url))
 * - Code blocks (```)
 * - Bold/Italic (**text** *text*)
 *
 * Note: react-markdown dependency needs to be installed:
 * cd scholar-ai/frontend && npm install react-markdown
 */
export function MarkdownEditor({ value, onChange, placeholder, onSave }: MarkdownEditorProps) {
  const { language } = useLanguage();
  const isZh = language === "zh";
  const [showPreview, setShowPreview] = useState(false);

  const t = {
    write: isZh ? "编辑" : "Write",
    preview: isZh ? "预览" : "Preview",
    placeholder: placeholder || (isZh ? "在此输入 Markdown 笔记..." : "Write your notes in Markdown..."),
    saved: isZh ? "已保存" : "Saved",
    saving: isZh ? "保存中..." : "Saving...",
  };

  return (
    <div className="h-full flex flex-col bg-surface border border-border rounded-sm">
      {/* Tab Bar */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setShowPreview(false)}
          className={`px-4 py-2 text-sm font-semibold transition-colors ${
            !showPreview
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          {t.write}
        </button>
        <button
          onClick={() => setShowPreview(true)}
          className={`px-4 py-2 text-sm font-semibold transition-colors ${
            showPreview
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          {t.preview}
        </button>
      </div>

      {/* Editor / Preview */}
      <div className="flex-1 overflow-hidden">
        {!showPreview ? (
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={t.placeholder}
            className="w-full h-full p-4 resize-none border-0 focus:outline-none font-mono text-base bg-surface"
          />
        ) : (
          <div
            className="p-4 prose prose-sm max-w-none overflow-y-auto h-full editorial-reading-surface font-serif"
            dangerouslySetInnerHTML={{ __html: simpleMarkdownToHtml(value) }}
          />
        )}
      </div>

      {/* Status Bar */}
      {onSave && (
        <div className="flex justify-between items-center px-4 py-2 border-t border-border bg-surface-sunken">
          <span className="text-sm text-muted-foreground">
            {value.length} characters
          </span>
          <button
            onClick={onSave}
            className="text-sm font-semibold text-primary hover:underline"
          >
            {t.saved}
          </button>
        </div>
      )}
    </div>
  );
}