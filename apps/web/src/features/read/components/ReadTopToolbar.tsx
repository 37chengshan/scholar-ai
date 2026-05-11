import {
  ChevronLeft,
  ChevronRight,
  FileText,
  Maximize2,
  MessageSquare,
  Minimize2,
  PanelRightClose,
  PanelRightOpen,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import type { NavigateFunction } from 'react-router';

import { navigateToChatWithHandoff } from '@/features/chat/chatHandoff';

import { Button } from '@/app/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/app/components/ui/tooltip';

interface ReadTopToolbarProps {
  id: string;
  isZh: boolean;
  title: string;
  currentPage: number;
  totalPages: number | null;
  pageInputValue: string;
  scale: number;
  isFullscreen: boolean;
  isPanelOpen: boolean;
  linkedNoteId: string | null;
  sourceId: string;
  navigate: NavigateFunction;
  onPageInputChange: (value: string) => void;
  onPageInputSubmit: () => void;
  onGoPrevPage: () => void;
  onGoNextPage: () => void;
  onZoomOut: () => void;
  onZoomIn: () => void;
  onToggleFullscreen: () => void;
  onTogglePanel: () => void;
}

export function ReadTopToolbar({
  id,
  isZh,
  title,
  currentPage,
  totalPages,
  pageInputValue,
  scale,
  isFullscreen,
  isPanelOpen,
  linkedNoteId,
  sourceId,
  navigate,
  onPageInputChange,
  onPageInputSubmit,
  onGoPrevPage,
  onGoNextPage,
  onZoomOut,
  onZoomIn,
  onToggleFullscreen,
  onTogglePanel,
}: ReadTopToolbarProps) {
  return (
    <div className="magazine-toolbar flex shrink-0 items-center gap-3 border-b border-border/50 bg-background/95 px-4 py-3 backdrop-blur-sm">
      <div className="min-w-0">
        <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">
          {isZh ? '专注阅读' : 'Focused Reading'}
        </div>
        <h1
          className="mt-2 max-w-xs truncate font-serif text-lg font-semibold text-foreground"
          title={title}
        >
          {title || (isZh ? '未命名论文' : 'Untitled Paper')}
        </h1>
      </div>

      <div className="flex-1" />

      <Button
        variant="outline"
        size="sm"
        className="h-7 gap-1.5 text-[11px]"
        onClick={() => {
          navigateToChatWithHandoff(
            navigate,
            { paperId: id },
            {
              origin: 'read',
              promptDraft: isZh
                ? `基于《${title || '当前论文'}》和我当前阅读位置，帮我继续分析关键证据、贡献和疑问。`
                : `Using "${title || 'this paper'}" and my current reading context, help me continue analyzing the key evidence, contributions, and open questions.`,
              evidence: sourceId
                ? [{ paperId: id, sourceChunkId: sourceId, pageNum: currentPage }]
                : [{ paperId: id, pageNum: currentPage }],
              returnTo: `/read/${id}?page=${currentPage}`,
            },
          );
        }}
      >
        <MessageSquare className="h-3.5 w-3.5" />
        {isZh ? '继续问' : 'Continue in Chat'}
      </Button>

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={onGoPrevPage}
          disabled={currentPage <= 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <input
          value={pageInputValue}
          onChange={(event) => onPageInputChange(event.target.value)}
          onBlur={onPageInputSubmit}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.currentTarget.blur();
            }
          }}
          className="h-7 w-12 rounded border border-border/60 bg-background px-1 text-center text-xs tabular-nums text-foreground"
          aria-label={isZh ? '输入页码' : 'Input page number'}
        />
        <span className="min-w-[72px] text-center text-xs tabular-nums text-muted-foreground">
          {currentPage} / {totalPages ?? (isZh ? '加载中' : '...')}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={onGoNextPage}
          disabled={totalPages !== null && currentPage >= totalPages}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex items-center gap-1">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={onZoomOut}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{isZh ? '缩小' : 'Zoom out'}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
        <span className="min-w-[48px] text-center text-xs text-muted-foreground">
          {Math.round(scale * 100)}%
        </span>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={onZoomIn}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{isZh ? '放大' : 'Zoom in'}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={onToggleFullscreen}
            >
              {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{isZh ? '全屏' : 'Fullscreen'}</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={onTogglePanel}
            >
              {isPanelOpen ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {isPanelOpen
              ? isZh
                ? '收起面板'
                : 'Collapse panel'
              : isZh
                ? '展开面板'
                : 'Expand panel'}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
