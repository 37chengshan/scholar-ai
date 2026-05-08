import { useEffect, useMemo, useRef, useState } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { Progress } from './ui/progress';
import { Label } from './ui/label';
import { Info, AlertTriangle, AlertCircle, Activity } from 'lucide-react';
import * as systemApi from '@/services/systemApi';

type StorageMetric = systemApi.StorageMetric;
type SystemLog = systemApi.SystemLog;

/**
 * SystemDiagnostics Component
 *
 * System monitoring panel for Settings page (D-14):
 * - Storage usage meters (Vector DB + File Storage)
 * - Real-time system logs stream (SSE)
 *
 * Follows UI-SPEC.md design constraints.
 */
export function SystemDiagnostics() {
  const { language } = useLanguage();
  const isZh = language === "zh";
  const [vectorDB, setVectorDB] = useState<StorageMetric>({ used: '0', total: '0', percentage: 0 });
  const [fileStorage, setFileStorage] = useState<StorageMetric>({ used: '0', total: '0', percentage: 0 });
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [storageError, setStorageError] = useState<string | null>(null);
  const [logsError, setLogsError] = useState<string | null>(null);
  const unmountedRef = useRef(false);

  const t = useMemo(() => ({
    title: isZh ? "系统诊断" : "System Diagnostics",
    vectorDB: isZh ? "向量数据库" : "Vector DB",
    fileStorage: isZh ? "文件存储" : "File Storage",
    logs: isZh ? "系统日志流" : "System Logs",
    storageTitle: isZh ? '存储使用情况' : 'Storage Usage',
    storageError: isZh ? '暂时无法获取存储指标。' : 'Unable to fetch storage metrics right now.',
    logsError: isZh ? '日志流暂时不可用。' : 'Live logs are temporarily unavailable.',
    logsEmpty: isZh ? '还没有新的系统日志。' : 'No system logs yet.',
    live: isZh ? '实时' : 'Live',
  }), [isZh]);

  // Fetch storage usage
  useEffect(() => {
    const fetchStorage = async () => {
      try {
        setStorageError(null);
        const storageInfo = await systemApi.getStorageInfo();
        setVectorDB(storageInfo.vectorDB);
        setFileStorage(storageInfo.fileStorage);
      } catch {
        setStorageError(t.storageError);
      }
    };

    void fetchStorage();
    const interval = setInterval(fetchStorage, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [t.storageError]);

  // Connect to logs stream (SSE)
  useEffect(() => {
    unmountedRef.current = false;
    setLogsError(null);
    const eventSource = systemApi.createSystemLogsEventSource();

    eventSource.onmessage = (event) => {
      const log: SystemLog = JSON.parse(event.data);
      setLogsError(null);
      setLogs(prev => [...prev.slice(-99), log]); // Keep last 100 logs
    };

    eventSource.onerror = () => {
      if (unmountedRef.current) {
        return;
      }

      setLogsError(t.logsError);
      eventSource.close();
    };

    return () => {
      unmountedRef.current = true;
      eventSource.close();
    };
  }, [t.logsError]);

  const getProgressColor = (percentage: number): string => {
    if (percentage < 50) return 'bg-green-500';
    if (percentage < 80) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'INFO':
        return <Info className="w-4 h-4 text-blue-500" />;
      case 'WARN':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'ERROR':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      {/* Storage Usage Panel */}
      <div className="space-y-6 p-6 bg-card border border-border/50 rounded-sm shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <h3 className="text-xl font-semibold font-serif tracking-tight">{t.storageTitle}</h3>
          <span className="inline-flex items-center gap-1 rounded-sm border border-border/50 bg-muted/20 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
            <Activity className="h-3 w-3 text-primary" />
            {t.live}
          </span>
        </div>

        {storageError ? (
          <div className="rounded-sm border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">
            {storageError}
          </div>
        ) : null}

        {/* Vector DB */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <Label className="text-sm font-semibold">{t.vectorDB}</Label>
            <span className="text-sm text-muted-foreground">
              {vectorDB.used}GB / {vectorDB.total}GB
            </span>
          </div>
          <Progress value={vectorDB.percentage} className="h-2" />
          <div className={`text-[10px] font-mono ${getProgressColor(vectorDB.percentage).replace('bg-', 'text-')}`}>
            {vectorDB.percentage.toFixed(0)}%
          </div>
        </div>

        {/* File Storage */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <Label className="text-sm font-semibold">{t.fileStorage}</Label>
            <span className="text-sm text-muted-foreground">
              {fileStorage.used}GB / {fileStorage.total}GB
            </span>
          </div>
          <Progress value={fileStorage.percentage} className="h-2" />
          <div className={`text-[10px] font-mono ${getProgressColor(fileStorage.percentage).replace('bg-', 'text-')}`}>
            {fileStorage.percentage.toFixed(0)}%
          </div>
        </div>
      </div>

      {/* System Logs Stream */}
      <div className="space-y-3 p-6 bg-card border border-border/50 rounded-sm shadow-sm">
        <h3 className="text-xl font-semibold font-serif tracking-tight">{t.logs}</h3>

        {logsError ? (
          <div className="rounded-sm border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">
            {logsError}
          </div>
        ) : null}

        <div className="h-[400px] overflow-y-auto space-y-2 bg-muted/20 border border-border/50 p-4 rounded-sm font-mono text-sm">
          {logs.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              {t.logsEmpty}
            </div>
          ) : logs.map((log, index) => (
            <div key={index} className="flex items-start gap-2 rounded-sm border border-border/40 bg-background/80 p-2">
              {getLogIcon(log.level)}
              <span className="text-xs text-muted-foreground">
                [{new Date(log.timestamp).toLocaleTimeString(isZh ? 'zh-CN' : 'en-US')}]
              </span>
              <span className="flex-1">{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}