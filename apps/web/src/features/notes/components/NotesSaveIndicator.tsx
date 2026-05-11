import { AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react';

interface NotesSaveIndicatorProps {
  selectedNoteId: string | null;
  hasUnsavedChanges: boolean;
  retryingSave: boolean;
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  lastSaved: Date | null;
  onRetrySave: () => void;
}

export function NotesSaveIndicator({
  selectedNoteId,
  hasUnsavedChanges,
  retryingSave,
  saveStatus,
  lastSaved,
  onRetrySave,
}: NotesSaveIndicatorProps) {
  if (!selectedNoteId) return null;

  if (!window.navigator.onLine) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-700">
        <AlertCircle className="h-3 w-3" />
        <span>离线模式，修改将在联网后保存</span>
      </div>
    );
  }

  if (saveStatus === 'idle' && hasUnsavedChanges) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-700">
        <Clock className="h-3 w-3" />
        <span>有未保存修改</span>
      </div>
    );
  }

  if (saveStatus === 'saving') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-yellow-600">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>保存中...</span>
      </div>
    );
  }

  if (saveStatus === 'error') {
    return (
      <button
        type="button"
        onClick={onRetrySave}
        className="flex items-center gap-1.5 text-xs text-destructive hover:underline"
      >
        <AlertCircle className="h-3 w-3" />
        <span>{retryingSave ? '重试中...' : '保存失败，点击重试'}</span>
      </button>
    );
  }

  if (saveStatus === 'saved' && lastSaved) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-600">
        <CheckCircle2 className="h-3 w-3" />
        <span>已保存 {lastSaved.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
    );
  }

  return null;
}
