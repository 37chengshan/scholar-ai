/**
 * MessageAlertCard Component
 *
 * Displays show_message tool result using shadcn Alert component.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useLanguage } from '../../contexts/LanguageContext';
import { Alert, AlertDescription } from '../ui/alert';
import { Info, AlertTriangle, AlertCircle, CheckCircle2 } from 'lucide-react';

interface MessageAlertCardProps {
  result: {
    message: string;
    type?: 'info' | 'warning' | 'error' | 'success';
  };
}

const ICON_MAP = {
  info: Info,
  warning: AlertTriangle,
  error: AlertCircle,
  success: CheckCircle2,
};

const COLOR_MAP: Record<string, string> = {
  info: 'text-blue-500',
  warning: 'text-yellow-500',
  error: 'text-destructive',
  success: 'text-green-600',
};

export function MessageAlertCard({ result }: MessageAlertCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const type = result.type ?? 'info';
  const Icon = ICON_MAP[type] ?? Info;
  const iconColor = COLOR_MAP[type] ?? COLOR_MAP.info;

  return (
    <Alert className="border-border/50">
      <Icon className={iconColor} />
      <AlertDescription className="text-sm">{result.message}</AlertDescription>
    </Alert>
  );
}
