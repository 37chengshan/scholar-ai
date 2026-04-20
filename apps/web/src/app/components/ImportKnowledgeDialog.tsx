import { useState, useCallback } from "react";
import { motion } from "motion/react";
import { Upload, X, FileText, CheckCircle, Loader2, AlertCircle, Clock } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Button } from "../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Progress } from "../components/ui/progress";
import { cn } from "../components/ui/utils";
import { toast } from "sonner";
import { kbApi, importApi } from "@/services/kbApi";

interface ImportKnowledgeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  knowledgeBaseId: string;
  knowledgeBaseName: string;
  onImportComplete?: () => void | Promise<void>;
}

interface FileItem {
  id: string;
  file: File;
  name: string;
  size: number;
  status: "pending" | "uploading" | "completed" | "failed";
  progress: number;
  error?: string;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export function ImportKnowledgeDialog({
  open,
  onOpenChange,
  knowledgeBaseId,
  knowledgeBaseName,
  onImportComplete,
}: ImportKnowledgeDialogProps) {
  const [activeTab, setActiveTab] = useState("local");
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isImporting, setIsImporting] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (f) => f.type === "application/pdf"
    );
    addFiles(droppedFiles);
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        addFiles(Array.from(e.target.files));
      }
    },
    []
  );

  const addFiles = (fileList: File[]) => {
    const newFiles: FileItem[] = fileList.map((f) => ({
      id: Math.random().toString(36).slice(2, 11),
      file: f,
      name: f.name,
      size: f.size,
      status: "pending",
      progress: 0,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const setFileState = useCallback((id: string, updater: (file: FileItem) => FileItem) => {
    setFiles((prev) => prev.map((file) => (file.id === id ? updater(file) : file)));
  }, []);

  const pollImportJobStatus = useCallback(async (importJobId: string, fileId: string) => {
    const maxAttempts = 60;

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const response = await importApi.get(importJobId);
      if (!response.success || !response.data) {
        throw new Error("获取导入任务状态失败");
      }

      const normalizedStatus = String(response.data.status).toLowerCase();
      const progress = typeof response.data.progress === "number" ? response.data.progress : 0;

      if (normalizedStatus === "completed") {
        setFileState(fileId, (file) => ({
          ...file,
          status: "completed",
          progress: 100,
        }));
        return;
      }

      if (normalizedStatus === "failed" || normalizedStatus === "cancelled") {
        throw new Error(response.data.error?.message || "处理失败");
      }

      setFileState(fileId, (file) => ({
        ...file,
        status: "uploading",
        progress: Math.max(file.progress, Math.min(progress, 99)),
      }));

      await new Promise((resolve) => setTimeout(resolve, 2000));
    }

    throw new Error("处理超时，请稍后刷新查看");
  }, [setFileState]);

  const handleImport = async () => {
    if (activeTab !== "local") {
      toast.info("当前轮次仅接通本地 PDF 导入");
      return;
    }

    if (files.length === 0) return;

    setIsImporting(true);

    try {
      for (const fileItem of files) {
        if (fileItem.status === "completed") continue;

        try {
          const { file } = fileItem;

          setFileState(fileItem.id, (current) => ({
            ...current,
            status: "uploading",
            progress: 5,
            error: undefined,
          }));

          const response = await kbApi.uploadPdf(knowledgeBaseId, file);
          if (!response.importJobId) {
            throw new Error("导入任务创建失败");
          }

          setFileState(fileItem.id, (current) => ({
            ...current,
            progress: 40,
          }));

          await pollImportJobStatus(response.importJobId, fileItem.id);

          setFileState(fileItem.id, (current) => ({
            ...current,
            status: "completed",
            progress: 100,
          }));
        } catch (error) {
          const message = error instanceof Error ? error.message : "导入失败";
          setFileState(fileItem.id, (current) => ({
            ...current,
            status: "failed",
            error: message,
          }));
          throw error;
        }
      }

      await onImportComplete?.();
      toast.success(`已将 ${files.length} 篇论文导入「${knowledgeBaseName}」`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "导入失败");
    } finally {
      setIsImporting(false);
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setFiles([]);
      setIsImporting(false);
    }
    onOpenChange(open);
  };

  const completedCount = files.filter((f) => f.status === "completed").length;
  const totalCount = files.length;

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

        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.2 }}>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-2">
          <TabsList className="grid w-full grid-cols-1 bg-paper-2">
            <TabsTrigger value="local" className="data-[state=active]:bg-paper-1">
              <FileText className="h-3.5 w-3.5 mr-1.5" />
              本地 PDF
            </TabsTrigger>
          </TabsList>

          {/* 本地 PDF */}
          <TabsContent value="local" className="mt-4">
            <div
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
                "border-border/50 hover:border-primary/50 hover:bg-primary/5"
              )}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
            >
              <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm font-medium text-foreground">
                拖拽 PDF 文件到此处
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                或{" "}
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
                      {file.status === "uploading" && (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      )}
                      {file.status === "completed" && (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      )}
                      {file.status === "failed" && (
                        <AlertCircle className="h-4 w-4 text-destructive" />
                      )}
                      {!isImporting && file.status === "pending" && (
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
          </TabsContent>

        </Tabs>

        {/* Import progress */}
        {isImporting && files.length > 0 && (
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
                <div
                  key={file.id}
                  className="flex items-center gap-3 text-sm"
                >
                  {file.status === "completed" && (
                    <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                  )}
                  {file.status === "uploading" && (
                    <Loader2 className="h-4 w-4 animate-spin text-primary flex-shrink-0" />
                  )}
                  {file.status === "pending" && (
                    <Clock className="h-4 w-4 text-muted-foreground/50 flex-shrink-0" />
                  )}
                  {file.status === "failed" && (
                    <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />
                  )}
                  <span className="flex-1 truncate">{file.name}</span>
                  {file.status === "completed" && (
                    <span className="text-xs text-muted-foreground">
                      导入完成
                    </span>
                  )}
                  {file.status === "uploading" && (
                    <span className="text-xs text-muted-foreground">
                      处理中... {Math.round(file.progress)}%
                    </span>
                  )}
                  {file.status === "pending" && (
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
          <Button
            onClick={handleImport}
            disabled={isImporting || files.length === 0}
          >
            {isImporting ? "导入中..." : `开始导入 (${files.length})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
