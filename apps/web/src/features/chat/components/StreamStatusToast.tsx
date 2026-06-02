/**
 * StreamStatusToast - Error/cancelled status toast with retry
 *
 * Displays user-friendly error messages without leaking backend internals.
 * Includes retry button for recoverable errors.
 */

import { useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { AlertCircle, RefreshCw, XCircle } from 'lucide-react';
import type { StreamStatus } from '@/types/chat';

interface StreamStatusToastOptions {
  streamStatus: StreamStatus;
  errorCode?: string;
  errorMessage?: string;
  isZh?: boolean;
  onRetry?: () => void;
}

/**
 * Maps error codes to user-friendly messages.
 * Never exposes internal backend error details.
 */
function getUserFriendlyMessage(
  errorCode: string | undefined,
  isZh: boolean,
): string {
  switch (errorCode) {
    case 'NETWORK_ERROR':
    case 'CONNECTION_LOST':
      return isZh ? '连接中断，正在重试...' : 'Connection lost. Retrying...';
    case 'TIMEOUT':
      return isZh ? '请求超时，请重试' : 'Request timed out. Please try again.';
    case 'RATE_LIMITED':
      return isZh ? '请求过于频繁，请稍后再试' : 'Too many requests. Please wait a moment.';
    case 'UNAUTHORIZED':
      return isZh ? '认证已过期，请重新登录' : 'Session expired. Please sign in again.';
    case 'SERVER_ERROR':
      return isZh ? '服务暂时不可用，请稍后重试' : 'Service unavailable. Please try again later.';
    case 'CANCELLED':
      return isZh ? '已取消生成' : 'Generation cancelled.';
    default:
      return isZh ? '请求失败，请重试' : 'Request failed. Please try again.';
  }
}

export function useStreamStatusToast({
  streamStatus,
  errorCode,
  errorMessage,
  isZh = true,
  onRetry,
}: StreamStatusToastOptions): void {
  const showErrorToast = useCallback(() => {
    const message = getUserFriendlyMessage(errorCode, isZh);

    if (streamStatus === 'error') {
      toast.error(message, {
        icon: <AlertCircle className="w-4 h-4 text-red-500" />,
        action: onRetry
          ? {
              label: isZh ? '重试' : 'Retry',
              onClick: onRetry,
            }
          : undefined,
        duration: errorCode === 'RATE_LIMITED' ? 5000 : 4000,
      });
    }

    if (streamStatus === 'cancelled') {
      toast(message, {
        icon: <XCircle className="w-4 h-4 text-muted-foreground" />,
        duration: 2000,
      });
    }
  }, [streamStatus, errorCode, isZh, onRetry]);

  useEffect(() => {
    if (streamStatus === 'error' || streamStatus === 'cancelled') {
      showErrorToast();
    }
  }, [streamStatus, showErrorToast]);
}
