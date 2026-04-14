/**
 * Import Source Tabs Component
 *
 * Separates source-specific tab content from ImportDialog logic.
 * Contains input forms for: local PDF, arXiv, URL/DOI, Semantic Scholar.
 */

import { useState } from 'react';
import {
  Upload,
  X,
  FileText,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { cn } from './ui/utils';
import { SourceResolution, SourceType } from '@/services/importApi';
import { ImportPreviewCard } from './ImportPreviewCard';

interface FileItem {
  id: string;
  file: File;
  name: string;
  size: number;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  progress: number;
  error?: string;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

interface ImportSourceTabsProps {
  activeTab: string;
  files: FileItem[];
  isImporting: boolean;
  externalInput: string;
  resolvedPreview: SourceResolution | null;
  resolveLoading: boolean;
  resolveError: string | null;
  onFileDrop: (e: React.DragEvent) => void;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile: (id: string) => void;
  onExternalInputChange: (value: string) => void;
  onResolveSource: () => void;
}

export function ImportSourceTabs({
  activeTab,
  files,
  isImporting,
  externalInput,
  resolvedPreview,
  resolveLoading,
  resolveError,
  onFileDrop,
  onFileSelect,
  onRemoveFile,
  onExternalInputChange,
  onResolveSource,
}: ImportSourceTabsProps) {
  // Local PDF tab content
  const renderLocalTab = () => (
    <>
      <div
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
          'border-border/50 hover:border-primary/50 hover:bg-primary/5'
        )}
        onDrop={onFileDrop}
        onDragOver={(e: React.DragEvent) => e.preventDefault()}
      >
        <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
        <p className="text-sm font-medium text-foreground">
          拖拽 PDF 文件到此处
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          或{' '}
          <label className="text-primary cursor-pointer hover:underline">
            点击选择文件
            <input
              type="file"
              accept=".pdf"
              multiple
              className="hidden"
              onChange={onFileSelect}
            />
          </label>
        </p>
        <p className="text-xs text-muted-foreground mt-3">
          支持 PDF 格式 · 单文件最大 50MB · 支持批量上传
        </p>
      </div>

      {files.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-medium text-foreground mb-2">
            已选择 {files.length} 个文件:
          </p>
          <div className="flex flex-col gap-2 max-h-40 overflow-y-auto">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-3 rounded-md border border-border/50 px-3 py-2 bg-card"
              >
                <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                <span className="text-sm flex-1 truncate">{file.name}</span>
                <span className="text-xs text-muted-foreground">
                  {formatFileSize(file.size)}
                </span>
                {file.status === 'uploading' && (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                )}
                {file.status === 'completed' && (
                  <FileText className="h-4 w-4 text-green-500" />
                )}
                {file.status === 'failed' && (
                  <X className="h-4 w-4 text-destructive" />
                )}
                {!isImporting && file.status === 'pending' && (
                  <button
                    type="button"
                    onClick={() => onRemoveFile(file.id)}
                    className="text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );

  // External source tab content (arXiv, URL/DOI, S2)
  const renderExternalTab = (
    label: string,
    placeholder: string,
    helpText: string
  ) => (
    <>
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium text-foreground">{label}</label>
          <Input
            type="text"
            placeholder={placeholder}
            value={externalInput}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => onExternalInputChange(e.target.value)}
            className="mt-2"
            disabled={isImporting}
          />
          <p className="text-xs text-muted-foreground mt-2">{helpText}</p>
        </div>

        <Button
          variant="outline"
          onClick={onResolveSource}
          disabled={resolveLoading || !externalInput.trim() || isImporting}
        >
          {resolveLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              解析中...
            </>
          ) : (
            <>
              <ExternalLink className="h-4 w-4 mr-2" />
              预解析
            </>
          )}
        </Button>

        <ImportPreviewCard
          preview={resolvedPreview?.preview}
          availability={resolvedPreview?.availability}
          resolved={resolvedPreview?.resolved}
          loading={resolveLoading}
          errorMessage={resolveError}
        />
      </div>
    </>
  );

  // Render based on active tab
  switch (activeTab) {
    case 'local':
      return renderLocalTab();

    case 'arxiv':
      return renderExternalTab(
        'arXiv ID 或链接',
        '输入 arXiv ID 或链接 (如 2501.01234)',
        '支持: 2501.01234, arXiv:2501.01234, https://arxiv.org/abs/2501.01234'
      );

    case 'url-doi':
      return renderExternalTab(
        'URL 或 DOI',
        '输入 URL 或 DOI (如 https://... 或 10.xxxx)',
        '支持: PDF URL、DOI (10.xxxx/xxxxx)'
      );

    case 's2':
      return renderExternalTab(
        'Semantic Scholar Paper ID 或链接',
        '输入 S2 paperId 或链接',
        '支持: paperId、CorpusId:xxxxx、S2 论文页链接'
      );

    default:
      return null;
  }
}

export default ImportSourceTabs;