/**
 * TokenUsageCard Component
 *
 * Displays user's total token usage and cost for current month.
 * Shows input/output breakdown and daily usage chart.
 */

import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Activity, TrendingUp, Zap, DollarSign } from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import * as usersApi from '@/services/usersApi';

interface TokenUsageData {
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  totalCostCny: number;
  requestCount: number;
  daily_breakdown: Array<{
    date: string;
    tokens: number;
    cost: number;
  }>;
}

interface TokenUsageCardProps {
  className?: string;
}

export function TokenUsageCard({ className }: TokenUsageCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const [usage, setUsage] = useState<TokenUsageData | null>(null);
  const [loading, setLoading] = useState(true);

  const t = {
    title: isZh ? 'Token 使用统计' : 'Token Usage',
    totalTokens: isZh ? '总 Token' : 'Total Tokens',
    inputTokens: isZh ? '输入 Token' : 'Input Tokens',
    outputTokens: isZh ? '输出 Token' : 'Output Tokens',
    totalCost: isZh ? '总花费' : 'Total Cost',
    requests: isZh ? '请求数' : 'Requests',
    thisMonth: isZh ? '本月' : 'This Month',
    dailyUsage: isZh ? '每日使用' : 'Daily Usage',
  };

  useEffect(() => {
    fetchTokenUsage();
  }, []);

  const fetchTokenUsage = async () => {
    try {
      const monthlyUsage = await usersApi.getMonthlyTokenUsage();

      setUsage({
        ...monthlyUsage,
        daily_breakdown: monthlyUsage.dailyBreakdown,
      });
    } catch (error) {
      console.error('Failed to fetch token usage:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  const formatCurrency = (num: number) => {
    return `¥${num.toFixed(2)}`;
  };

  if (loading) {
    return (
      <div className={clsx('bg-card border border-border rounded-lg p-4', className)}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-muted rounded w-1/3"></div>
          <div className="h-8 bg-muted rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (!usage) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx('bg-card border border-border rounded-lg p-4', className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold tracking-wide uppercase text-muted-foreground flex items-center gap-2">
          <Activity className="w-4 h-4" />
          {t.title}
        </h3>
        <span className="text-xs text-muted-foreground">{t.thisMonth}</span>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {/* Total Tokens */}
        <div className="bg-primary/5 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Zap className="w-3.5 h-3.5 text-primary" />
            <span className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
              {t.totalTokens}
            </span>
          </div>
          <div className="text-2xl font-bold text-foreground">
            {formatNumber(usage.totalTokens)}
          </div>
        </div>

        {/* Total Cost */}
        <div className="bg-green-50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <DollarSign className="w-3.5 h-3.5 text-green-600" />
            <span className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
              {t.totalCost}
            </span>
          </div>
          <div className="text-2xl font-bold text-green-600">
            {formatCurrency(usage.totalCostCny)}
          </div>
        </div>
      </div>

      {/* Breakdown */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">{t.inputTokens}</span>
          <span className="font-mono font-bold">{formatNumber(usage.inputTokens)}</span>
        </div>
        <div className="w-full bg-muted rounded-full h-1.5">
          <div
            className="bg-primary h-1.5 rounded-full"
            style={{
              width: `${
                usage.totalTokens > 0
                  ? (usage.inputTokens / usage.totalTokens) * 100
                  : 0
              }%`,
            }}
          />
        </div>

        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">{t.outputTokens}</span>
          <span className="font-mono font-bold">{formatNumber(usage.outputTokens)}</span>
        </div>
        <div className="w-full bg-muted rounded-full h-1.5">
          <div
            className="bg-green-500 h-1.5 rounded-full"
            style={{
              width: `${
                usage.totalTokens > 0
                  ? (usage.outputTokens / usage.totalTokens) * 100
                  : 0
              }%`,
            }}
          />
        </div>

        <div className="flex items-center justify-between text-xs pt-2 border-t border-border/50">
          <span className="text-muted-foreground">{t.requests}</span>
          <span className="font-mono font-bold">{usage.requestCount}</span>
        </div>
      </div>

      {/* Daily Usage Chart */}
      {usage.daily_breakdown && usage.daily_breakdown.length > 0 && (
        <div className="pt-4 border-t border-border/50">
          <div className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground mb-2">
            {t.dailyUsage}
          </div>
          <div className="flex items-end gap-1 h-16">
            {usage.daily_breakdown.slice(-7).map((day, idx) => {
              const maxTokens = Math.max(
                ...usage.daily_breakdown.map((d) => d.tokens)
              );
              const height =
                maxTokens > 0 ? (day.tokens / maxTokens) * 100 : 0;

              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: `${height}%` }}
                    transition={{ delay: idx * 0.05 }}
                    className="w-full bg-primary/60 rounded-t"
                    style={{ minHeight: '4px' }}
                  />
                  <span className="text-[8px] text-muted-foreground">
                    {new Date(day.date).getDate()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </motion.div>
  );
}