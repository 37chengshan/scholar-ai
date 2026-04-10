/**
 * SessionTokenBadge Component
 *
 * Displays token usage for a single chat session.
 * Shows compact badge with token count and cost.
 */

import { motion } from 'motion/react';
import { Zap } from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';

interface SessionTokenBadgeProps {
  tokens: number;
  cost?: number;
  className?: string;
  variant?: 'default' | 'compact';
}

export function SessionTokenBadge({
  tokens,
  cost,
  className,
  variant = 'default',
}: SessionTokenBadgeProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const formatNumber = (num: number) => {
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  const formatCost = (num: number) => {
    if (num < 0.01) {
      return `¥${(num * 100).toFixed(1)}分`;
    }
    return `¥${num.toFixed(2)}`;
  };

  if (variant === 'compact') {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className={clsx(
          'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono',
          'bg-primary/10 text-primary',
          className
        )}
      >
        <Zap className="w-3 h-3" />
        <span>{formatNumber(tokens)}</span>
        {cost !== undefined && cost > 0 && (
          <span className="opacity-60">·{formatCost(cost)}</span>
        )}
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={clsx(
        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs',
        'bg-muted/50 border border-border/50',
        className
      )}
    >
      <Zap className="w-3.5 h-3.5 text-primary" />
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">
          {isZh ? 'Token:' : 'Tokens:'}
        </span>
        <span className="font-mono font-bold">{formatNumber(tokens)}</span>
        {cost !== undefined && cost > 0 && (
          <>
            <span className="text-border">·</span>
            <span className="text-green-600 font-medium">{formatCost(cost)}</span>
          </>
        )}
      </div>
    </motion.div>
  );
}