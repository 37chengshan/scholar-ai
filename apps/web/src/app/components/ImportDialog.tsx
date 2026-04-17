/**
 * Unified Import Dialog Component
 *
 * Local upload now delegates to UploadWorkspace (chunked upload sessions).
 * External source import keeps resolve -> create import job flow.
 */

import { useState } from 'react';
import { motion } from 'motion/react';
import { ExternalLink, FileText, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';

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
import { Input } from './ui/input';
import { importApi, SourceResolution, SourceType } from '@/services/importApi';
import { ImportPreviewCard } from './ImportPreviewCard';
import { UploadWorkspace } from '@/features/uploads/components/UploadWorkspace';

interface ImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  knowledgeBaseId: string;
  knowledgeBaseName: string;
  onImportComplete?: () => void | Promise<void>;
  prefilledSource?: {
    sourceType: SourceType;
    input: string;
    preview?: SourceResolution['preview'];
  };
}

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
  const [isImporting, setIsImporting] = useState(false);

  const [externalInput, setExternalInput] = useState(prefilledSource?.input || '');
  const [resolveLoading, setResolveLoading] = useState(false);
  const [resolvedPreview, setResolvedPreview] = useState<SourceResolution | null>(null);
  const [resolveError, setResolveError] = useState<string | null>(null);

  const handleResolveSource = async () => {
    if (!externalInput.trim()) {
      toast.error('请输入来源信息');
      return;
    }

    setResolveLoading(true);
    setResolveError(null);
    setResolvedPreview(null);

    try {
      const sourceTypeMap: Record<string, SourceType> = {
        arxiv: 'arxiv',
        'url-doi': 'pdf_url',
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

  const handleImportExternal = async () => {
    if (!resolvedPreview?.resolved || !resolvedPreview.preview) {
      toast.error('请先解析来源');
      return;
    }

    setIsImporting(true);
    try {
      const actualSourceType = resolvedPreview.normalizedSource?.sourceType || activeTab;

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

      if (!response.success || !response.data) {
        throw new Error('创建导入任务失败');
      }

      toast.success('导入任务已创建');
      handleOpenChange(false);
      navigate(`/knowledge-bases/${knowledgeBaseId}`);
      await onImportComplete?.();
    } catch (err: any) {
      toast.error(err.message || '导入失败');
    } finally {
      setIsImporting(false);
    }
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      setExternalInput('');
      setResolvedPreview(null);
      setResolveError(null);
      setIsImporting(false);
    }
    onOpenChange(nextOpen);
  };

  const renderExternalTab = (placeholder: string, helper: string) => (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium text-foreground">来源信息</label>
        <Input
          type="text"
          placeholder={placeholder}
          value={externalInput}
          onChange={(e) => setExternalInput(e.target.value)}
          className="mt-2"
          disabled={isImporting}
        />
        <p className="text-xs text-muted-foreground mt-2">{helper}</p>
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
  );

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[680px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl font-semibold">
            导入论文到「{knowledgeBaseName}」
          </DialogTitle>
          <DialogDescription>
            本地 PDF 使用上传工作台（断点续传 + 秒传判定），外部来源使用解析预览后导入。
          </DialogDescription>
        </DialogHeader>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
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

            <TabsContent value="local" className="mt-4">
              <UploadWorkspace
                knowledgeBaseId={knowledgeBaseId}
                onQueueComplete={async () => {
                  await onImportComplete?.();
                }}
              />
            </TabsContent>
            <TabsContent value="arxiv" className="mt-4">
              {renderExternalTab(
                '输入 arXiv ID 或链接 (如 2501.01234)',
                '支持: 2501.01234, arXiv:2501.01234, https://arxiv.org/abs/2501.01234'
              )}
            </TabsContent>
            <TabsContent value="url-doi" className="mt-4">
              {renderExternalTab('输入 URL 或 DOI', '支持: PDF URL、DOI (10.xxxx/xxxxx)')}
            </TabsContent>
            <TabsContent value="s2" className="mt-4">
              {renderExternalTab('输入 S2 paperId 或链接', '支持: paperId、CorpusId:xxxxx、S2 论文页链接')}
            </TabsContent>
          </Tabs>
        </motion.div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            关闭
          </Button>
          {activeTab !== 'local' && (
            <Button onClick={handleImportExternal} disabled={isImporting || !resolvedPreview?.resolved}>
              {isImporting ? '导入中...' : '确认导入'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ImportDialog;
