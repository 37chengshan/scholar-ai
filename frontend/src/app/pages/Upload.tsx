import { UploadCloud, FolderUp, Link, History, Settings2, FileText, CheckCircle2, Clock, Play, Server, Tags, AlertCircle, RefreshCw } from "lucide-react";
import { clsx } from "clsx";
import { motion } from "motion/react";
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useLanguage } from "../contexts/LanguageContext";
import { useUpload } from "../hooks/useUpload";
import { Progress } from "../components/ui/progress";

export function Upload() {
  const [activeTab, setActiveTab] = useState("local");
  const { language } = useLanguage();
  const isZh = language === "zh";
  
  // Real upload hook
  const { files, addFiles, uploadAll, removeFile, clearFiles, isUploading } = useUpload();

  const t = {
    sources: isZh ? "数据来源" : "Sources",
    inputMethods: isZh ? "输入方式" : "Input Methods",
    localFiles: isZh ? "本地文件" : "Local Files",
    urlDoi: isZh ? "URL / DOI" : "URL / DOI",
    syncZotero: isZh ? "同步 Zotero" : "Sync Zotero",
    recentBatches: isZh ? "最近批次" : "Recent Batches",
    filesCount: isZh ? "个文件" : "Files",
    ingestionQueue: isZh ? "处理队列" : "Ingestion Queue",
    itemsPending: isZh ? `${files.length} 个项目待处理` : `${files.length} items pending`,
    clearAll: isZh ? "清空全部" : "Clear All",
    startProc: isZh ? "开始处理" : "Start Processing",
    dropHere: isZh ? "将 PDF 文件拖拽至此" : "Drop PDF files here",
    clickBrowse: isZh ? "或点击浏览本地文件" : "or click to browse local filesystem",
    pdfsOnly: isZh ? "PDF 文件" : "PDFs",
    maxSize: isZh ? "最大 50MB/文件" : "Max 50MB/file",
    colFilename: isZh ? "文件名与元数据" : "Filename & Metadata",
    colStatus: isZh ? "状态" : "Status",
    colSize: isZh ? "大小" : "Size",
    colProgress: isZh ? "进度" : "Progress",
    colActions: isZh ? "操作" : "Actions",
    btnEdit: isZh ? "编辑" : "Edit",
    btnDrop: isZh ? "移除" : "Drop",
    pipeline: isZh ? "处理管道" : "Pipeline",
    extraction: isZh ? "提取配置" : "Extraction",
    parseMeta: isZh ? "解析元数据" : "Parse Metadata",
    parseMetaDesc: isZh ? "通过 Crossref API 提取标题、作者、年份、期刊等信息。" : "Extract Title, Authors, Year, Venue via Crossref API.",
    genEmbed: isZh ? "生成嵌入向量" : "Generate Embeddings",
    genEmbedDesc: isZh ? "将内容向量化以支持语义搜索 (OpenAI text-embedding-3)。" : "Vectorize content for semantic search (OpenAI text-embedding-3).",
    autoSumm: isZh ? "自动摘要" : "Auto-Summarize",
    autoSummDesc: isZh ? "使用当前 LLM 生成三句话的简短总结 (TLDR)。" : "Generate a 3-sentence TLDR using the active LLM.",
    forceOcr: isZh ? "强制 OCR" : "Force OCR",
    forceOcrDesc: isZh ? "处理扫描版 PDF (速度较慢，消耗更多算力)。" : "Process scanned PDFs (slower, uses more compute).",
    targetOrg: isZh ? "目标分类" : "Target Organization",
    collection: isZh ? "收藏夹" : "Collection",
    optInbox: isZh ? "收件箱 (默认)" : "Inbox (Default)",
    optLLM: isZh ? "LLM 架构" : "LLM Architectures",
    optAgent: isZh ? "智能体框架" : "Agentic Frameworks",
    optVision: isZh ? "视觉模型" : "Vision Models",
    optNew: isZh ? "+ 创建新分类..." : "+ Create New...",
    autoTag: isZh ? "自动打标签" : "Auto-Tagging",
    tagPlaceholder: isZh ? "输入标签，以逗号分隔..." : "Comma separated tags...",
    estProc: isZh ? "预计处理时间" : "Est. Processing",
    mins: isZh ? `~${Math.ceil(files.length * 0.4)} 分钟` : `~${Math.ceil(files.length * 0.4)} mins`,
    uploading: isZh ? "上传中..." : "Uploading...",
    noFiles: isZh ? "暂无文件" : "No files",
  };

  const BATCHES = [
    { id: "B-842", time: isZh ? "10分钟前" : "10 mins ago", count: 12, status: "completed" },
    { id: "B-841", time: isZh ? "2小时前" : "2 hours ago", count: 4, status: "completed" },
    { id: "B-840", time: isZh ? "昨天" : "Yesterday", count: 28, status: "completed" },
  ];

  // Dropzone configuration
  const onDrop = useCallback((acceptedFiles: File[]) => {
    addFiles(acceptedFiles);
  }, [addFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    maxFiles: 50,
  });

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Map status to display
  const getStatusDisplay = (status: string) => {
    const statusMap: Record<string, { text: string; type: string }> = {
      pending: { text: isZh ? "等待中" : "Pending", type: "Pending" },
      uploading: { text: isZh ? "上传中" : "Uploading", type: "Processing" },
      processing: { text: isZh ? "处理中" : "Processing", type: "Processing" },
      completed: { text: isZh ? "完成" : "Completed", type: "Ready" },
      failed: { text: isZh ? "失败" : "Failed", type: "Failed" },
    };
    return statusMap[status] || { text: status, type: "Pending" };
  };

  return (
    <div className="h-full flex font-sans bg-background text-foreground relative selection:bg-primary selection:text-primary-foreground">
      {/* Left Column: Import Sources & History */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[220px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center">
          <h2 className="font-serif text-xl font-black tracking-tight leading-none mb-1">{t.sources}</h2>
          <UploadCloud className="w-4 h-4 text-primary" />
        </div>
        
        <div className="flex-1 overflow-y-auto py-5 flex flex-col gap-6 px-4">
          <div>
            <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{t.inputMethods}</div>
            <div className="flex flex-col gap-1">
              <button 
                onClick={() => setActiveTab("local")}
                className={clsx(
                  "flex items-center gap-2.5 px-3 py-2 rounded-sm transition-colors group w-full text-left",
                  activeTab === "local" ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" : "hover:bg-card border border-transparent hover:border-border/50 text-foreground/80 hover:text-primary"
                )}
              >
                <FolderUp className="w-3.5 h-3.5" />
                <span className="text-[10px] font-bold uppercase tracking-widest flex-1">{t.localFiles}</span>
              </button>
              <button 
                onClick={() => setActiveTab("url")}
                className={clsx(
                  "flex items-center gap-2.5 px-3 py-2 rounded-sm transition-colors group w-full text-left",
                  activeTab === "url" ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" : "hover:bg-card border border-transparent hover:border-border/50 text-foreground/80 hover:text-primary"
                )}
              >
                <Link className="w-3.5 h-3.5" />
                <span className="text-[10px] font-bold uppercase tracking-widest flex-1">{t.urlDoi}</span>
              </button>
              <button 
                onClick={() => setActiveTab("zotero")}
                className={clsx(
                  "flex items-center gap-2.5 px-3 py-2 rounded-sm transition-colors group w-full text-left",
                  activeTab === "zotero" ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" : "hover:bg-card border border-transparent hover:border-border/50 text-foreground/80 hover:text-primary"
                )}
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span className="text-[10px] font-bold uppercase tracking-widest flex-1">{t.syncZotero}</span>
              </button>
            </div>
          </div>

          <div>
            <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <History className="w-3 h-3" /> {t.recentBatches}
            </div>
            <div className="flex flex-col gap-2">
              {BATCHES.map((batch) => (
                <div key={batch.id} className="flex flex-col gap-1 p-2 rounded-sm hover:bg-card border border-transparent hover:border-border/50 transition-colors cursor-pointer group">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-mono font-bold group-hover:text-primary transition-colors">{batch.id}</span>
                    <span className="text-[9px] font-mono text-muted-foreground">{batch.time}</span>
                  </div>
                  <div className="flex justify-between items-center mt-1">
                    <span className="text-[9px] font-bold uppercase tracking-widest text-foreground/60">{batch.count} {t.filesCount}</span>
                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Middle Column: Dropzone & File List */}
      <div className="flex-1 flex flex-col h-full bg-background min-w-[500px] border-r border-border/50">
        <div className="px-6 py-4 border-b border-border/50 bg-background/90 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center shadow-sm">
          <div className="flex items-baseline gap-3">
            <h2 className="font-serif text-2xl font-black tracking-tight">{t.ingestionQueue}</h2>
            <span className="text-[9px] font-mono tracking-[0.2em] text-muted-foreground">{t.itemsPending}</span>
          </div>
          <div className="flex gap-2">
            <button 
              onClick={clearFiles}
              disabled={files.length === 0}
              className="text-[9px] font-bold uppercase tracking-[0.2em] bg-background border border-foreground/20 text-foreground px-3 py-1.5 rounded-sm hover:bg-muted transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t.clearAll}
            </button>
            <button 
              onClick={uploadAll}
              disabled={isUploading || files.length === 0 || files.every(f => f.status !== 'pending')}
              className="text-[9px] font-bold uppercase tracking-[0.2em] bg-primary text-primary-foreground px-4 py-1.5 rounded-sm hover:bg-secondary transition-colors shadow-sm flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-3 h-3" /> {isUploading ? t.uploading : t.startProc}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 bg-muted/5">
          {/* Dropzone */}
          <div 
            {...getRootProps()} 
            className={clsx(
              "w-full border-2 border-dashed transition-colors rounded-sm flex flex-col items-center justify-center py-12 px-6 cursor-pointer group",
              isDragActive 
                ? "border-primary bg-primary/10" 
                : "border-primary/20 hover:border-primary/50 bg-primary/5 hover:bg-primary/10"
            )}
          >
            <input {...getInputProps()} />
            <div className="w-12 h-12 bg-background border border-primary/20 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-sm">
              <UploadCloud className="w-5 h-5 text-primary" />
            </div>
            <h3 className="font-serif text-xl font-bold tracking-tight mb-2">{t.dropHere}</h3>
            <p className="text-[11px] font-sans text-muted-foreground">{t.clickBrowse}</p>
            <div className="mt-6 flex gap-4 text-[9px] font-bold uppercase tracking-[0.2em] text-foreground/50">
              <span className="flex items-center gap-1"><FileText className="w-3 h-3" /> {t.pdfsOnly}</span>
              <span className="flex items-center gap-1"><Server className="w-3 h-3" /> {t.maxSize}</span>
            </div>
          </div>

          {/* Table / List */}
          {files.length > 0 ? (
            <div className="flex flex-col border border-border/50 bg-card rounded-sm shadow-sm overflow-hidden">
              <div className="grid grid-cols-12 gap-4 p-3 border-b border-border/50 bg-muted/30 text-[9px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
                <div className="col-span-5">{t.colFilename}</div>
                <div className="col-span-2">{t.colStatus}</div>
                <div className="col-span-2">{t.colProgress}</div>
                <div className="col-span-1 text-right">{t.colSize}</div>
                <div className="col-span-2 text-right">{t.colActions}</div>
              </div>
              <div className="flex flex-col divide-y divide-border/30">
                {files.map((file, index) => {
                  const statusDisplay = getStatusDisplay(file.status);
                  return (
                    <div key={index} className="grid grid-cols-12 gap-4 p-3 items-center hover:bg-muted/20 transition-colors group">
                      <div className="col-span-5 flex flex-col gap-1 min-w-0">
                        <span className="text-[11px] font-mono font-bold text-foreground truncate group-hover:text-primary transition-colors">
                          {file.file.name}
                        </span>
                        {file.error && (
                          <span className="text-[9px] text-red-500 truncate">{file.error}</span>
                        )}
                      </div>
                      <div className="col-span-2 flex items-center">
                        <span className={clsx(
                          "text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-sm flex items-center gap-1.5",
                          statusDisplay.type === "Ready" ? "bg-green-500/10 text-green-600 border border-green-500/20" :
                          statusDisplay.type === "Processing" ? "bg-primary/10 text-primary border border-primary/20" :
                          statusDisplay.type === "Failed" ? "bg-red-500/10 text-red-600 border border-red-500/20" :
                          "bg-muted text-muted-foreground border border-border/50"
                        )}>
                          {statusDisplay.type === "Processing" && <RefreshCw className="w-2.5 h-2.5 animate-spin" />}
                          {statusDisplay.type === "Failed" && <AlertCircle className="w-2.5 h-2.5" />}
                          {statusDisplay.type === "Ready" && <CheckCircle2 className="w-2.5 h-2.5" />}
                          {statusDisplay.type === "Pending" && <Clock className="w-2.5 h-2.5" />}
                          {statusDisplay.text}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <Progress value={file.progress} className="h-1" />
                      </div>
                      <div className="col-span-1 text-right text-[10px] font-mono text-muted-foreground">
                        {formatSize(file.file.size)}
                      </div>
                      <div className="col-span-2 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => removeFile(index)}
                          disabled={file.status === 'uploading' || file.status === 'processing'}
                          className="text-[9px] font-bold uppercase tracking-widest text-destructive hover:text-destructive/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {t.btnDrop}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <FileText className="w-12 h-12 mb-4 opacity-30" />
              <p className="text-[11px] font-bold uppercase tracking-widest">{t.noFiles}</p>
            </div>
          )}
        </div>
      </div>

      {/* Right Column: Pipeline Configuration */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[240px] flex flex-col h-full bg-muted/10 flex-shrink-0 relative"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings2 className="w-4 h-4 text-primary" />
            <h2 className="font-serif text-lg font-bold tracking-tight">{t.pipeline}</h2>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6 flex flex-col gap-8">
          
          <div className="flex flex-col gap-4">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5">{t.extraction}</h3>
            <div className="flex flex-col gap-3">
              <label className="flex items-start gap-3 cursor-pointer group">
                <input type="checkbox" defaultChecked className="mt-0.5 accent-primary w-3.5 h-3.5 rounded-sm border-border/50" />
                <div className="flex flex-col">
                  <span className="text-[11px] font-bold uppercase tracking-widest text-foreground/80 group-hover:text-primary transition-colors">{t.parseMeta}</span>
                  <span className="text-[9px] text-muted-foreground leading-tight mt-0.5">{t.parseMetaDesc}</span>
                </div>
              </label>
              
              <label className="flex items-start gap-3 cursor-pointer group">
                <input type="checkbox" defaultChecked className="mt-0.5 accent-primary w-3.5 h-3.5 rounded-sm border-border/50" />
                <div className="flex flex-col">
                  <span className="text-[11px] font-bold uppercase tracking-widest text-foreground/80 group-hover:text-primary transition-colors">{t.genEmbed}</span>
                  <span className="text-[9px] text-muted-foreground leading-tight mt-0.5">{t.genEmbedDesc}</span>
                </div>
              </label>

              <label className="flex items-start gap-3 cursor-pointer group">
                <input type="checkbox" defaultChecked className="mt-0.5 accent-primary w-3.5 h-3.5 rounded-sm border-border/50" />
                <div className="flex flex-col">
                  <span className="text-[11px] font-bold uppercase tracking-widest text-foreground/80 group-hover:text-primary transition-colors">{t.autoSumm}</span>
                  <span className="text-[9px] text-muted-foreground leading-tight mt-0.5">{t.autoSummDesc}</span>
                </div>
              </label>

              <label className="flex items-start gap-3 cursor-pointer group">
                <input type="checkbox" className="mt-0.5 accent-primary w-3.5 h-3.5 rounded-sm border-border/50" />
                <div className="flex flex-col">
                  <span className="text-[11px] font-bold uppercase tracking-widest text-foreground/80 group-hover:text-primary transition-colors">{t.forceOcr}</span>
                  <span className="text-[9px] text-muted-foreground leading-tight mt-0.5">{t.forceOcrDesc}</span>
                </div>
              </label>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Tags className="w-3 h-3" /> {t.targetOrg}
            </h3>
            
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] font-bold uppercase tracking-widest text-foreground/70">{t.collection}</label>
                <select className="w-full bg-card border border-border/50 rounded-sm px-3 py-2 text-[10px] font-bold uppercase tracking-widest focus:outline-none focus:border-primary transition-colors appearance-none shadow-sm cursor-pointer">
                  <option>{t.optInbox}</option>
                  <option>{t.optLLM}</option>
                  <option>{t.optAgent}</option>
                  <option>{t.optVision}</option>
                  <option>{t.optNew}</option>
                </select>
              </div>

              <div className="flex flex-col gap-1.5 mt-2">
                <label className="text-[9px] font-bold uppercase tracking-widest text-foreground/70">{t.autoTag}</label>
                <input 
                  type="text" 
                  placeholder={t.tagPlaceholder}
                  className="w-full bg-card border border-border/50 rounded-sm px-3 py-2 text-[10px] font-sans placeholder:text-muted-foreground placeholder:uppercase placeholder:tracking-widest focus:outline-none focus:border-primary transition-colors shadow-sm"
                />
              </div>
            </div>
          </div>

        </div>
        
        <div className="p-4 border-t border-border/50 bg-background/80 backdrop-blur-md">
          <div className="flex justify-between items-center text-[9px] font-mono tracking-[0.2em] text-muted-foreground">
            <span>{t.estProc}</span>
            <span className="font-bold text-primary">{t.mins}</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}