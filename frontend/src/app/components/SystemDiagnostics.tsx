import { useState, useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { Progress } from './ui/progress';
import { Label } from './ui/label';
import { Info, AlertTriangle, AlertCircle } from 'lucide-react';
import apiClient from '@/utils/apiClient';
import { API_BASE_URL } from '@/config/api';

interface StorageMetric {
  used: string;
  total: string;
  percentage: number;
}

interface SystemLog {
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
  timestamp: string;
}

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

  const t = {
    title: isZh ? "系统诊断" : "System Diagnostics",
    vectorDB: isZh ? "向量数据库" : "Vector DB",
    fileStorage: isZh ? "文件存储" : "File Storage",
    logs: isZh ? "系统日志流" : "System Logs",
  };

  // Fetch storage usage
  useEffect(() => {
    const fetchStorage = async () => {
      try {
        const response = await apiClient.get<{
          success: boolean;
          data: {
            vectorDB: StorageMetric;
            fileStorage: StorageMetric;
          };
        }>('/api/system/storage');

        if (response.data.success) {
          setVectorDB(response.data.data.vectorDB);
          setFileStorage(response.data.data.fileStorage);
        }
      } catch (error) {
        console.error('Failed to fetch storage:', error);
      }
    };

    fetchStorage();
    const interval = setInterval(fetchStorage, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  // Connect to logs stream (SSE)
  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE_URL}/api/system/logs/stream`, {
      withCredentials: true,
    });

    eventSource.onmessage = (event) => {
      const log: SystemLog = JSON.parse(event.data);
      setLogs(prev => [...prev.slice(-99), log]); // Keep last 100 logs
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

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
    <div className="grid grid-cols-2 gap-6">
      {/* Storage Usage Panel */}
      <div className="space-y-6 p-6 bg-white border border-[#f4ece1] rounded-sm">
        <h3 className="text-xl font-semibold">{t.title}</h3>

        {/* Vector DB */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <Label className="text-sm font-semibold">{t.vectorDB}</Label>
            <span className="text-sm text-muted-foreground">
              {vectorDB.used}GB / {vectorDB.total}GB
            </span>
          </div>
          <Progress value={vectorDB.percentage} className="h-2" />
          <div className={`h-2 rounded ${getProgressColor(vectorDB.percentage)}`} style={{ width: `${vectorDB.percentage}%` }} />
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
          <div className={`h-2 rounded ${getProgressColor(fileStorage.percentage)}`} style={{ width: `${fileStorage.percentage}%` }} />
        </div>
      </div>

      {/* System Logs Stream */}
      <div className="space-y-3 p-6 bg-white border border-[#f4ece1] rounded-sm">
        <h3 className="text-xl font-semibold">{t.logs}</h3>

        <div className="h-[400px] overflow-y-auto space-y-2 bg-[#fdfaf6] p-4 rounded-sm font-mono text-sm">
          {logs.map((log, index) => (
            <div key={index} className="flex items-start gap-2">
              {getLogIcon(log.level)}
              <span className="text-xs text-muted-foreground">
                [{new Date(log.timestamp).toLocaleTimeString()}]
              </span>
              <span className="flex-1">{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}