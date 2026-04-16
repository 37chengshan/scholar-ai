/**
 * TokenMonitor Component
 *
 * Session-level token usage display with progress bar and cost.
 * Per D-06: shows formatted token count, percentage, and cost.
 *
 * Features:
 * - Color-coded progress bar (green/yellow/orange/red)
 * - Formatted numbers with Intl.NumberFormat
 * - Bilingual labels via useLanguage()
 * - Mono font for numeric values (--font-mono)
 */

import { Progress } from '../components/ui/progress';
import { useLanguage } from '../contexts/LanguageContext';

interface TokenMonitorProps {
  tokens: number;
  limit?: number;
  cost: number;
  className?: string;
}

const DEFAULT_LIMIT = 128000;

export function TokenMonitor({
  tokens,
  limit = DEFAULT_LIMIT,
  cost,
  className,
}: TokenMonitorProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const percentage = Math.min((tokens / limit) * 100, 100);
  const formattedTokens = new Intl.NumberFormat().format(tokens);
  const formattedLimit = new Intl.NumberFormat().format(limit);
  const formattedPercentage = percentage.toFixed(1);

  // Color coding per plan spec
  const getProgressColor = () => {
    if (percentage > 95) return 'bg-destructive';
    if (percentage > 80) return 'bg-primary';
    if (percentage >= 50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className={`rounded-lg border border-border/50 bg-card p-4 space-y-3 ${className || ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">
          {isZh ? 'Token 使用量' : 'Token Usage'}
        </span>
        <span className="font-mono text-xs">
          {formattedTokens} / {formattedLimit} ({formattedPercentage}%)
        </span>
      </div>

      {/* Progress bar */}
      <Progress value={percentage} className={`h-2 ${getProgressColor()}`} />

      {/* Cost display */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {isZh ? '花费' : 'Cost'}
        </span>
        <span className="font-mono text-xs text-green-600">
          ¥{cost.toFixed(4)}
        </span>
      </div>
    </div>
  );
}
