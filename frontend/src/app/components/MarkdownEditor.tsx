import { useState } from 'react';
import { useLanguage } from '../contexts/LanguageContext';

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

  /**
   * Simple Markdown to HTML converter
   * For full Markdown support, install react-markdown
   */
  const simpleMarkdownToHtml = (text: string): string => {
    return text
      // Headers
      .replace(/^### (.*$)/gim, '<h3 class="text-base font-semibold mt-4 mb-2">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-semibold mt-4 mb-2">$1</h1>')
      // Bold
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // Code blocks
      .replace(/```([\s\S]+?)```/g, '<pre class="bg-muted p-4 rounded-sm font-mono text-sm overflow-x-auto my-4"><code>$1</code></pre>')
      // Inline code
      .replace(/`(.+?)`/g, '<code class="bg-muted px-1 py-0.5 rounded font-mono text-sm">$1</code>')
      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-[#d35400] hover:underline" target="_blank" rel="noopener noreferrer">$1</a>')
      // Lists
      .replace(/^- (.*$)/gim, '<li class="ml-4">$1</li>')
      .replace(/^\* (.*$)/gim, '<li class="ml-4">$1</li>')
      // Line breaks
      .replace(/\n/g, '<br>');
  };

  return (
    <div className="h-full flex flex-col bg-white border border-[#f4ece1] rounded-sm">
      {/* Tab Bar */}
      <div className="flex border-b border-[#f4ece1]">
        <button
          onClick={() => setShowPreview(false)}
          className={`px-4 py-2 text-sm font-semibold transition-colors ${
            !showPreview
              ? 'text-[#d35400] border-b-2 border-[#d35400]'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          {t.write}
        </button>
        <button
          onClick={() => setShowPreview(true)}
          className={`px-4 py-2 text-sm font-semibold transition-colors ${
            showPreview
              ? 'text-[#d35400] border-b-2 border-[#d35400]'
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
            className="w-full h-full p-4 resize-none border-0 focus:outline-none font-mono text-base bg-white"
          />
        ) : (
          <div
            className="p-4 prose prose-sm max-w-none overflow-y-auto h-full"
            dangerouslySetInnerHTML={{ __html: simpleMarkdownToHtml(value) }}
          />
        )}
      </div>

      {/* Status Bar */}
      {onSave && (
        <div className="flex justify-between items-center px-4 py-2 border-t border-[#f4ece1] bg-[#fdfaf6]">
          <span className="text-sm text-muted-foreground">
            {value.length} characters
          </span>
          <button
            onClick={onSave}
            className="text-sm font-semibold text-[#d35400] hover:underline"
          >
            {t.saved}
          </button>
        </div>
      )}
    </div>
  );
}