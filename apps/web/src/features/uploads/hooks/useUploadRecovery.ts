import { uploadSessionApi, UploadSessionState } from '@/services/uploadSessionApi';
import type { UploadQueueItem } from '@/features/uploads/state/uploadWorkspaceStore';

export interface UploadRecoveryResult {
  session: UploadSessionState;
  nextStatus: UploadQueueItem['status'];
  progress: number;
  error?: string;
}

export function useUploadRecovery() {
  const recoverSession = async (sessionId: string): Promise<UploadSessionState> => {
    return uploadSessionApi.getSession(sessionId);
  };

  const recoverUploadItem = async (
    item: Pick<UploadQueueItem, 'file' | 'uploadSessionId'>
  ): Promise<UploadRecoveryResult> => {
    if (!item.uploadSessionId) {
      throw new Error('缺少上传会话 ID，无法恢复');
    }

    const session = await recoverSession(item.uploadSessionId);

    if (session.status === 'aborted') {
      return {
        session,
        nextStatus: 'cancelled',
        progress: session.progress,
        error: '该上传任务已取消，请重新添加文件以创建新的导入任务',
      };
    }

    if (session.status === 'completed') {
      return {
        session,
        nextStatus: 'queued',
        progress: session.progress,
      };
    }

    if (!item.file) {
      return {
        session,
        nextStatus: 'needs_file_reselect',
        progress: session.progress,
        error: '请重新选择原始文件后继续上传',
      };
    }

    if (session.missingParts.length === 0) {
      const completedSession = await uploadSessionApi.completeSession(session.uploadSessionId);
      return {
        session: completedSession,
        nextStatus: 'queued',
        progress: completedSession.progress,
      };
    }

    return {
      session,
      nextStatus: 'pending',
      progress: session.progress,
    };
  };

  return {
    recoverSession,
    recoverUploadItem,
  };
}
