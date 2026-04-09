import { useState, useCallback } from "react";
import { motion } from "motion/react";
import { Upload, Link, BookOpen, FolderOpen, X, FileText, CheckCircle, Loader2, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Checkbox } from "../components/ui/checkbox";
import { Label } from "../components/ui/label";
import { Progress } from "../components/ui/progress";
import { cn } from "../components/ui/utils";

interface ImportKnowledgeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  knowledgeBaseId: string;
  knowledgeBaseName: string;
}

interface FileItem {
  id: string;
  name: string;
  size: number;
  status: "pending" | "uploading" | "completed" | "failed";
  progress: number;
  chunkCount?: number;
  entityCount?: number;
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
  knowledgeBaseId: _knowledgeBaseId,
  knowledgeBaseName,
}: ImportKnowledgeDialogProps) {
  const [activeTab, setActiveTab] = useState("local");
  const [files, setFiles] = useState<FileItem[]>([]);
  const [urlInput, setUrlInput] = useState("");
  const [arxivInput, setArxivInput] = useState("");
  const [isImporting, setIsImporting] = useState(false);

  // Parse settings
  const [parseEngine, setParseEngine] = useState("docling");
  const [embeddingModel, setEmbeddingModel] = useState("bge-m3");
  const [enableImrad, setEnableImrad] = useState(true);
  const [enableChunks, setEnableChunks] = useState(true);
  const [enableGraph, setEnableGraph] = useState(true);

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

  const handleImport = () => {
    if (files.length === 0 && activeTab === "local") return;

    setIsImporting(true);

    // Simulate import progress for mock
    setFiles((prev) =>
      prev.map((f) => ({
        ...f,
        status: "uploading" as const,
        progress: 0,
      }))
    );

    // Simulate per-file progress
    files.forEach((file) => {
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 20 + 5;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          setFiles((prev) =>
            prev.map((f) =>
              f.id === file.id
                ? {
                    ...f,
                    status: "completed" as const,
                    progress: 100,
                    chunkCount: Math.floor(Math.random() * 100 + 50),
                    entityCount: Math.floor(Math.random() * 30 + 10),
                  }
                : f
            )
          );
          // Check if all complete
          setFiles((prev) => {
            const allDone = prev.every(
              (f) => f.status === "completed" || f.status === "failed"
            );
            if (allDone) {
              setIsImporting(false);
            }
            return prev;
          });
        } else {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === file.id ? { ...f, progress: Math.min(progress, 99) } : f
            )
          );
        }
      }, 300);
    });
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setFiles([]);
      setUrlInput("");
      setArxivInput("");
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
            选择论文来源，配置解析参数后开始导入
          </DialogDescription>
        </DialogHeader>

        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.2 }}>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-2">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="local">📄 本地 PDF</TabsTrigger>
            <TabsTrigger value="url">🔗 URL/DOI</TabsTrigger>
            <TabsTrigger value="arxiv">📚 arXiv</TabsTrigger>
            <TabsTrigger value="batch">📁 批量导入</TabsTrigger>
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

          {/* URL/DOI */}
          <TabsContent value="url" className="mt-4">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label>论文 URL 或 DOI</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Link className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="https://doi.org/10.48550/arXiv.2301.12345"
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  支持 DOI 链接、论文 URL、Semantic Scholar 链接
                </p>
              </div>
            </div>
          </TabsContent>

          {/* arXiv */}
          <TabsContent value="arxiv" className="mt-4">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label>arXiv ID</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <BookOpen className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="2301.12345 或 arXiv:2301.12345"
                      value={arxivInput}
                      onChange={(e) => setArxivInput(e.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  输入 arXiv 论文 ID，系统将自动下载并解析
                </p>
              </div>
            </div>
          </TabsContent>

          {/* 批量导入 */}
          <TabsContent value="batch" className="mt-4">
            <div
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
                "border-border/50 hover:border-primary/50 hover:bg-primary/5"
              )}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
            >
              <FolderOpen className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm font-medium text-foreground">
                拖拽文件夹或多个 PDF 文件
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                或{" "}
                <label className="text-primary cursor-pointer hover:underline">
                  点击选择
                  <input
                    type="file"
                    accept=".pdf"
                    multiple
                    className="hidden"
                    onChange={handleFileSelect}
                  />
                </label>
              </p>
            </div>
          </TabsContent>
        </Tabs>

        {/* 解析设置 */}
        <div className="mt-4 rounded-lg border border-border/50 p-4 bg-card">
          <h4 className="font-serif text-sm font-semibold text-foreground mb-3">解析设置</h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Label>解析引擎</Label>
              <Select value={parseEngine} onValueChange={setParseEngine}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="docling">Docling</SelectItem>
                  <SelectItem value="mineru">MinerU</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label>向量化模型</Label>
              <Select value={embeddingModel} onValueChange={setEmbeddingModel}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bge-m3">BGE-M3</SelectItem>
                  <SelectItem value="text-embedding-3">
                    text-embedding-3
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex flex-wrap gap-4 mt-4">
            <div className="flex items-center gap-2">
              <Checkbox
                id="import-imrad"
                checked={enableImrad}
                onCheckedChange={(c) => setEnableImrad(c as boolean)}
              />
              <Label htmlFor="import-imrad" className="text-sm cursor-pointer">
                提取 IMRaD 结构
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="import-chunks"
                checked={enableChunks}
                onCheckedChange={(c) => setEnableChunks(c as boolean)}
              />
              <Label htmlFor="import-chunks" className="text-sm cursor-pointer">
                生成向量化切片
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="import-graph"
                checked={enableGraph}
                onCheckedChange={(c) => setEnableGraph(c as boolean)}
              />
              <Label htmlFor="import-graph" className="text-sm cursor-pointer">
                构建知识图谱实体
              </Label>
            </div>
          </div>
        </div>

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
                    <span className="h-4 w-4 flex-shrink-0 text-muted-foreground">
                      ⏳
                    </span>
                  )}
                  {file.status === "failed" && (
                    <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />
                  )}
                  <span className="flex-1 truncate">{file.name}</span>
                  {file.status === "completed" && (
                    <span className="text-xs text-muted-foreground">
                      解析完成 · {file.chunkCount} 切片 · {file.entityCount} 实体
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
            disabled={
              isImporting ||
              (activeTab === "local" && files.length === 0) ||
              (activeTab === "url" && !urlInput.trim()) ||
              (activeTab === "arxiv" && !arxivInput.trim())
            }
          >
            {isImporting
              ? "导入中..."
              : activeTab === "local"
              ? `开始导入 (${files.length})`
              : "开始导入"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
