/**
 * Unified Import Dialog Component
 *
 * Provides unified import interface with 4 tabs:
 * - 本地 PDF: Local PDF file upload
 * - arXiv: arXiv ID or link
 * - URL / DOI: Direct URL or DOI
 * - Semantic Scholar: S2 paper ID or link
 *
 * Wave 4: Core UI with resolve preview (dedupe dialog deferred to Wave 5)
 */

import { useState, useCallback } from 'react';
import { motion } from 'motion/react';
import {
  Upload,
  X,
  FileText,
  CheckCircle,
  Loader2,
  AlertCircle,
  Clock,
  ExternalLink,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Progress } from './ui/progress';
import { Input } from './ui/input';
import { cn } from './ui/utils';
import { toast } from 'sonner';
import { importApi, SourceResolution, ImportJob, SourceType } from '@/services/importApi';
import { ImportPreviewCard } from './ImportPreviewCard';
import { useNavigate } from 'react-router';

interface ImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  knowledgeBaseId: string;
  knowledgeBaseName: string;
  onImportComplete?: () => void | Promise<void>;
  // prefilledSource reserved for Wave 5 (Search page integration)
  prefilledSource?: {
    sourceType: SourceType;
    input: string;
    preview?: SourceResolution['preview'];
  };
}

interface FileItem {
  id: string;
  file: File;
  name: string;
  size: number;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  progress: number;
  error?: string;
  importJobId?: string;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

// Stage labels for progress display
const STAGE_LABELS: Record<string, string> = {
  awaiting_input: '等待输入',
  resolving_source: '解析来源',
  fetching_metadata: '获取元数据',
  downloading_pdf: '下载 PDF',
  validating_pdf: '验证 PDF',
  hashing_file: '计算哈希',
  dedupe_check: '去重检查',
  awaiting_dedupe_decision: '等待决策',
  materializing_paper: '创建论文',
  attaching_to_kb: '关联知识库',
  parsing: '解析内容',
  chunking: '切分内容',
  embedding: '生成向量',
  indexing: '索引存储',
  finalizing: '完成处理',
  completed: '完成',
};

export function ImportDialog({
  open,
  onOpenChange,
  knowledgeBaseId,
  knowledgeBaseName,
  onImportComplete,
  prefilledSource,
}: ImportDialogProps) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<string>(prefilledSource?.sourceType || 'local');
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isImporting, setIsImporting] = useState(false);

  // External source state
  const [externalInput, setExternalInput] = useState(prefilledSource?.input || '');
  const [resolveLoading, setResolveLoading] = useState(false);
  const [resolvedPreview, setResolvedPreview] = useState<SourceResolution | null>(null);
  const [resolveError, setResolveError] = useState<string | null>(null);

  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (f) => f.type === 'application/pdf'
    );
    addFiles(droppedFiles);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files));
    }
  }, []);

  const addFiles = (fileList: File[]) => {
    const newFiles: FileItem[] = fileList.map((f) => ({
      id: Math.random().toString(36).slice(2, 11),
      file: f,
      name: f.name,
      size: f.size,
      status: 'pending',
      progress: 0,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const setFileState = useCallback(
    (id: string, updater: (file: FileItem) => FileItem) => {
      setFiles((prev) => prev.map((file) => (file.id === id ? updater(file) : file)));
    },
    []
  );

  // Resolve external source (arXiv, DOI, URL, S2)
  const handleResolveSource = async () => {
    if (!externalInput.trim()) {
      toast.error('请输入来源信息');
      return;
    }

    setResolveLoading(true);
    setResolveError(null);
    setResolvedPreview(null);

    try {
      // Determine source type from active tab
      const sourceTypeMap: Record<string, SourceType> = {
        arxiv: 'arxiv',
        'url-doi': 'pdf_url', // Will detect DOI format in backend
        s2: 'semantic_scholar',
      };

      const sourceType = sourceTypeMap[activeTab] || 'pdf_url';

      const response = await importApi.resolve(sourceType, externalInput.trim());

      if (response.success && response.data) {
        if (response.data.resolved) {
          setResolvedPreview(response.data);
          toast.success('来源解析成功');
        } else {
          setResolveError(response.data.errorMessage || '无法解析来源');
        }
      } else {
        setResolveError('解析请求失败');
      }
    } catch (err: any) {
      setResolveError(err.message || '网络错误');
    } finally {
      setResolveLoading(false);
    }
  };

  // Import from external source (after resolve)
  const handleImportExternal = async () => {
    if (!resolvedPreview?.resolved || !resolvedPreview.preview) {
      toast.error('请先解析来源');
      return;
    }

    setIsImporting(true);

    try {
      // Determine actual source type from resolution
      const actualSourceType =
        resolvedPreview.normalizedSource?.sourceType || activeTab;

      const response = await importApi.create(knowledgeBaseId, {
        sourceType: actualSourceType as SourceType,
        payload: {
          input: externalInput.trim(),
          normalizedId: resolvedPreview.normalizedSource?.canonicalId,
          pdfUrl: resolvedPreview.normalizedSource?.canonicalPdfUrl,
        },
        options: {
          dedupePolicy: 'prompt',
          autoAttachToKb: true,
        },
      });

      if (response.success && response.data) {
        const job = response.data;
        toast.success('导入任务已创建');

        // Close dialog and navigate to KB detail page to see progress
        handleOpenChange(false);
        navigate(`/knowledge-bases/${knowledgeBaseId}`);
        await onImportComplete?.();
      } else {
        toast.error('创建导入任务失败');
      }
    } catch (err: any) {
      toast.error(err.message || '导入失败');
    } finally {
      setIsImporting(false);
    }
  };

  // Import local PDF files
  const handleImportLocal = async () => {
    if (files.length === 0) return;

    setIsImporting(true);

    try {
      for (const fileItem of files) {
        if (fileItem.status === 'completed') continue;

        try {
          const { file } = fileItem;

          setFileState(fileItem.id, (current) => ({
            ...current,
            status: 'uploading',
            progress: 5,
            error: undefined,
          }));

          // Step 1: Create ImportJob
          const createResponse = await importApi.create(knowledgeBaseId, {
            sourceType: 'local_file',
            payload: {
              filename: file.name,
              sizeBytes: file.size,
              mimeType: file.type,
            },
            options: {
              dedupePolicy: 'prompt',
              autoAttachToKb: true,
            },
          });

          if (!createResponse.success || !createResponse.data) {
            throw new Error('创建导入任务失败');
          }

          const importJobId = createResponse.data.importJobId;

          setFileState(fileItem.id, (current) => ({
            ...current,
            importJobId,
            progress: 20,
          }));

          // Step 2: Upload file to ImportJob
          const uploadResponse = await importApi.uploadFile(importJobId, file);

          if (!uploadResponse.success) {
            throw new Error('上传文件失败');
          }

          setFileState(fileItem.id, (current) => ({
            ...current,
            progress: 100,
            status: 'completed',
          }));
        } catch (error) {
          const message = error instanceof Error ? error.message : '导入失败';
          setFileState(fileItem.id, (current) => ({
            ...current,
            status: 'failed',
            error: message,
          }));
          throw error;
        }
      }

      // Close dialog and navigate to KB detail page
      handleOpenChange(false);
      navigate(`/knowledge-bases/${knowledgeBaseId}`);
      await onImportComplete?.();
      toast.success(`已创建 ${files.length} 个导入任务`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '导入失败');
    } finally {
      setIsImporting(false);
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setFiles([]);
      setIsImporting(false);
      setExternalInput('');
      setResolvedPreview(null);
      setResolveError(null);
    }
    onOpenChange(open);
  };

  const completedCount = files.filter((f) => f.status === 'completed').length;
  const totalCount = files.length;

  // Get tab content based on active tab
  const renderTabContent = () => {
    switch (activeTab) {
      case 'local':
        return (
          <>
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
                'border-border/50 hover:border-primary/50 hover:bg-primary/5'
              )}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
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
                    onChange={handleFileSelect}
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
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      )}
                      {file.status === 'failed' && (
                        <AlertCircle className="h-4 w-4 text-destructive" />
                      )}
                      {!isImporting && file.status === 'pending' && (
                        <button
                          type="button"
                          onClick={() => removeFile(file.id)}
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

      case 'arxiv':
        return (
          <>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground">
                  arXiv ID 或链接
                </label>
                <Input
                  type="text"
                  placeholder="输入 arXiv ID 或链接 (如 2501.01234)"
                  value={externalInput}
                  onChange={(e) => setExternalInput(e.target.value)}
                  className="mt-2"
                  disabled={isImporting}
                />
                <p className="text-xs text-muted-foreground mt-2">
                  支持: 2501.01234, arXiv:2501.01234, https://arxiv.org/abs/2501.01234
                </p>
              </div>

              <Button
                variant="outline"
                onClick={handleResolveSource}
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

      case 'url-doi':
        return (
          <>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground">
                  URL 或 DOI
                </label>
                <Input
                  type="text"
                  placeholder="输入 URL 或 DOI (如 https://... 或 10.xxxx)"
                  value={externalInput}
                  onChange={(e) => setExternalInput(e.target.value)}
                  className="mt-2"
                  disabled={isImporting}
                />
                <p className="text-xs text-muted-foreground mt-2">
                  支持: PDF URL、DOI (10.xxxx/xxxxx)
                </p>
              </div>

              <Button
                variant="outline"
                onClick={handleResolveSource}
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

      case 's2':
        return (
          <>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground">
                  Semantic Scholar Paper ID 或链接
                </label>
                <Input
                  type="text"
                  placeholder="输入 S2 paperId 或链接"
                  value={externalInput}
                  onChange={(e) => setExternalInput(e.target.value)}
                  className="mt-2"
                  disabled={isImporting}
                />
                <p className="text-xs text-muted-foreground mt-2">
                  支持: paperId、CorpusId:xxxxx、S2 论文页链接
                </p>
              </div>

              <Button
                variant="outline"
                onClick={handleResolveSource}
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

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl font-semibold">
            导入论文到「{knowledgeBaseName}」
          </DialogTitle>
          <DialogDescription>
            选择导入来源，论文将继承知识库的解析和嵌入配置
          </DialogDescription>
        </DialogHeader>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2 }}
        >
          <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-2">
            <TabsList className="grid w-full grid-cols-4 bg-paper-2">
              <TabsTrigger value="local" className="data-[state=active]:bg-paper-1">
                <FileText className="h-3.5 w-3.5 mr-1.5" />
                本地 PDF
              </TabsTrigger>
              <TabsTrigger value="arxiv" className="data-[state=active]:bg-paper-1">
                <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                arXiv
              </TabsTrigger>
              <TabsTrigger value="url-doi" className="data-[state=active]:bg-paper-1">
                <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                URL / DOI
              </TabsTrigger>
              <TabsTrigger value="s2" className="data-[state=active]:bg-paper-1">
                <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                S2
              </TabsTrigger>
            </TabsList>

            <TabsContent value={activeTab} className="mt-4">
              {renderTabContent()}
            </TabsContent>
          </Tabs>

          {/* Import progress for local files */}
          {isImporting && activeTab === 'local' && files.length > 0 && (
            <div className="mt-4 rounded-lg border border-border/50 p-4 bg-card">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-foreground">
                  导入进度: {completedCount}/{totalCount} 完成
                </p>
              </div>
              <Progress
                value={(completedCount / totalCount) * 100}
                className="h-2 mb-3"
              />
              <div className="flex flex-col gap-2 max-h-40 overflow-y-auto">
                {files.map((file) => (
                  <div key={file.id} className="flex items-center gap-3 text-sm">
                    {file.status === 'completed' && (
                      <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                    )}
                    {file.status === 'uploading' && (
                      <Loader2 className="h-4 w-4 animate-spin text-primary flex-shrink-0" />
                    )}
                    {file.status === 'pending' && (
                      <Clock className="h-4 w-4 text-muted-foreground/50 flex-shrink-0" />
                    )}
                    {file.status === 'failed' && (
                      <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />
                    )}
                    <span className="flex-1 truncate">{file.name}</span>
                    {file.status === 'completed' && (
                      <span className="text-xs text-muted-foreground">导入完成</span>
                    )}
                    {file.status === 'uploading' && (
                      <span className="text-xs text-muted-foreground">
                        处理中... {Math.round(file.progress)}%
                      </span>
                    )}
                    {file.status === 'pending' && (
                      <span className="text-xs text-muted-foreground">等待中...</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            取消
          </Button>
          {activeTab === 'local' && (
            <Button
              onClick={handleImportLocal}
              disabled={isImporting || files.length === 0}
            >
              {isImporting ? '导入中...' : `开始导入 (${files.length})`}
            </Button>
          )}
          {activeTab !== 'local' && (
            <Button
              onClick={handleImportExternal}
              disabled={isImporting || !resolvedPreview?.resolved}
            >
              {isImporting ? '导入中...' : '确认导入'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ImportDialog;