/**
 * Annotation Toolbar Component (Highlight Toolbar)
 *
 * Toolbar for creating PDF annotations:
 * - Color picker for highlights (4 colors: yellow, orange, blue, green)
 * - Chinese tooltips for color names per UI-SPEC
 * - Create highlight button
 * - Integration with annotationsApi
 *
 * Requirements: D-08 (Multi-color highlights), PAGE-06 (Read page annotation system)
 */

import { useState } from 'react';
import * as annotationsApi from '@/services/annotationsApi';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { toast } from 'sonner';

interface AnnotationToolbarProps {
  paperId: string;
  pageNumber: number;
  onAnnotationCreated?: () => void;
  selectedText?: string;
  selectionPosition?: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
}

// Color definitions with Chinese names per UI-SPEC
const HIGHLIGHT_COLORS = [
  { hex: '#FFEB3B', zhName: '黄色', enName: 'Yellow' },
  { hex: '#FF5722', zhName: '橙色', enName: 'Orange' },
  { hex: '#2196F3', zhName: '蓝色', enName: 'Blue' },
  { hex: '#4CAF50', zhName: '绿色', enName: 'Green' },
];

export function AnnotationToolbar({
  paperId,
  pageNumber,
  onAnnotationCreated,
  selectedText,
  selectionPosition,
}: AnnotationToolbarProps) {
  const [color, setColor] = useState('#FFEB3B');
  const [isCreating, setIsCreating] = useState(false);
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const handleHighlight = async () => {
    if (!selectionPosition) {
      return;
    }

    setIsCreating(true);
    try {
      await annotationsApi.create({
        paperId,
        type: 'highlight',
        pageNumber,
        position: selectionPosition,
        color,
        content: selectedText || '',
      });
      onAnnotationCreated?.();
    } catch (error) {
      toast.error(isZh ? '添加高亮失败，请重试' : 'Failed to add highlight');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="flex items-center gap-2 p-2 bg-card border border-border rounded-sm shadow-sm" data-testid="annotation-toolbar">
      <span className="text-sm font-medium text-foreground">
        {isZh ? '高亮:' : 'Highlight:'}
      </span>
      {HIGHLIGHT_COLORS.map(c => (
        <button
          key={c.hex}
          onClick={() => setColor(c.hex)}
          data-testid={`color-${c.zhName}`}
          className={clsx(
            "w-6 h-6 rounded-sm border transition-all",
            color === c.hex 
              ? "border-primary ring-2 ring-primary/20" 
              : "border-border hover:border-primary/50"
          )}
          style={{ backgroundColor: c.hex }}
          title={isZh ? c.zhName : c.enName}
          aria-label={isZh ? `选择${c.zhName}高亮` : `Select ${c.enName} highlight`}
        />
      ))}
      <button
        onClick={handleHighlight}
        disabled={isCreating || !selectionPosition}
        className={clsx(
          "px-3 py-1.5 bg-primary text-primary-foreground rounded-sm",
          "text-[10px] font-bold uppercase tracking-widest",
          "hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed",
          "shadow-sm shadow-primary/20 transition-colors"
        )}
      >
        {isCreating 
          ? (isZh ? '添加中...' : 'Adding...') 
          : (isZh ? '添加高亮' : 'Add Highlight')}
      </button>

      {!selectionPosition && (
        <span className="text-[10px] text-muted-foreground">
          {isZh ? '先在 PDF 中选中一段文本' : 'Select text in the PDF first'}
        </span>
      )}
    </div>
  );
}