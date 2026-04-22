import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  Activity, Zap, BookOpen, MessageSquare, Eye, TrendingUp, 
  RefreshCw, Download, Database, Clock, ArrowUpRight, ArrowDownRight,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';

// Mock data
const tokenUsageData = [
  { name: '周一', tokens: 4200, cost: 0.84 },
  { name: '周二', tokens: 3800, cost: 0.76 },
  { name: '周三', tokens: 5200, cost: 1.04 },
  { name: '周四', tokens: 4800, cost: 0.96 },
  { name: '周五', tokens: 6100, cost: 1.22 },
  { name: '周六', tokens: 3200, cost: 0.64 },
  { name: '周日', tokens: 2800, cost: 0.56 },
];

const usageDistribution = [
  { name: '对话', value: 45, tokens: 45000 },
  { name: '检索', value: 30, tokens: 30000 },
  { name: '分析', value: 15, tokens: 15000 },
  { name: '其他', value: 10, tokens: 10000 },
];

const COLORS = ['#d35400', '#e67e22', '#f39c12', '#16a34a'];

interface KPI {
  label: string;
  value: string;
  trend: number;
  trendLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'orange' | 'blue' | 'green' | 'purple';
}

export function Analytics() {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const t = {
    title: isZh ? '数据看板' : 'Analytics',
    subtitle: isZh ? '项目概览与使用统计' : 'Project Overview & Usage Statistics',
    systemStatus: isZh ? '系统状态' : 'System Status',
    active: isZh ? '活跃' : 'Active',
    lastUpdate: isZh ? '最后更新' : 'Last Update',
    refresh: isZh ? '刷新' : 'Refresh',
    export: isZh ? '导出' : 'Export',
    tokenUsage: isZh ? 'Token 消耗' : 'Token Usage',
    weeklyTrend: isZh ? '周趋势' : 'Weekly Trend',
    usageBreakdown: isZh ? '使用分布' : 'Usage Breakdown',
    totalTokens: isZh ? '本周总计' : 'Weekly Total',
    avgCost: isZh ? '平均成本' : 'Avg Cost',
    documents: isZh ? '文献总数' : 'Total Documents',
    papers: isZh ? '论文数量' : 'Papers',
    chunks: isZh ? '知识切片' : 'Knowledge Chunks',
    entities: isZh ? '提取实体' : 'Entities Extracted',
    interactions: isZh ? '用户交互' : 'User Interactions',
    conversations: isZh ? '对话数' : 'Conversations',
    searches: isZh ? '检索数' : 'Searches',
    reads: isZh ? '阅读数' : 'Deep Reads',
    recentActivity: isZh ? '最近活动' : 'Recent Activity',
    noData: isZh ? '暂无数据' : 'No Data',
  };

  const kpis: KPI[] = [
    {
      label: t.totalTokens,
      value: '30.1K',
      trend: 12.5,
      trendLabel: isZh ? '+周比增长' : 'vs last week',
      icon: Zap,
      color: 'orange',
    },
    {
      label: t.documents,
      value: '1,248',
      trend: 3.2,
      trendLabel: isZh ? '+新增文献' : 'new papers',
      icon: BookOpen,
      color: 'blue',
    },
    {
      label: t.interactions,
      value: '2,401',
      trend: 8.1,
      trendLabel: isZh ? '+用户交互' : 'interactions',
      icon: MessageSquare,
      color: 'green',
    },
    {
      label: t.entities,
      value: '89.3K',
      trend: 4.2,
      trendLabel: isZh ? '+实体' : 'extracted',
      icon: Database,
      color: 'purple',
    },
  ];

  const recentActivities = [
    {
      type: 'chat',
      title: isZh ? '新对话：LLM 在医疗中的应用' : 'New chat: LLM in Healthcare',
      time: isZh ? '2 小时前' : '2h ago',
      icon: MessageSquare,
    },
    {
      type: 'search',
      title: isZh ? '检索：深度学习优化' : 'Searched: Deep Learning Optimization',
      time: isZh ? '4 小时前' : '4h ago',
      icon: Activity,
    },
    {
      type: 'read',
      title: isZh ? '深度阅读：论文 ID 12847' : 'Deep read: Paper 12847',
      time: isZh ? '6 小时前' : '6h ago',
      icon: Eye,
    },
    {
      type: 'upload',
      title: isZh ? '上传知识库：量子计算研究' : 'Uploaded KB: Quantum Computing',
      time: isZh ? '1 天前' : '1d ago',
      icon: Clock,
    },
  ];

  return (
    <div className="min-h-full bg-background text-foreground">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b border-border/60 bg-background/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            <div>
              <h1 className="text-3xl font-serif font-black tracking-tight">{t.title}</h1>
              <p className="text-sm text-muted-foreground mt-1">{t.subtitle}</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                {t.refresh}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs"
              >
                <Download className="h-3.5 w-3.5" />
                {t.export}
              </Button>
            </div>
          </div>

          {/* System Status */}
          <div className="mt-4 flex items-center gap-4 text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/80">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              {t.systemStatus}: {t.active}
            </span>
            <span className="text-border">·</span>
            <span>{t.lastUpdate}: {new Date().toLocaleString(isZh ? 'zh-CN' : 'en-US')}</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* KPI Cards */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
        >
          {kpis.map((kpi, i) => (
            <div
              key={i}
              className="group flex flex-col gap-3 bg-card border border-border/60 p-5 shadow-sm hover:border-primary/50 transition-all duration-200 relative overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent group-hover:via-primary/60 transition-all duration-300" />
              
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  <div className={clsx(
                    'rounded-xl p-2.5 transition-colors duration-200',
                    kpi.color === 'orange' ? 'bg-orange-500/10' :
                    kpi.color === 'blue' ? 'bg-blue-500/10' :
                    kpi.color === 'green' ? 'bg-green-500/10' :
                    'bg-purple-500/10'
                  )}>
                    <kpi.icon className={clsx(
                      'h-4 w-4',
                      kpi.color === 'orange' ? 'text-orange-600' :
                      kpi.color === 'blue' ? 'text-blue-600' :
                      kpi.color === 'green' ? 'text-green-600' :
                      'text-purple-600'
                    )} />
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground/70">
                    {kpi.label}
                  </span>
                </div>
                <div className={clsx(
                  'text-[10px] font-bold flex items-center gap-0.5 px-2 py-1 rounded-sm bg-green-500/10 text-green-700',
                  kpi.trend < 0 && 'bg-red-500/10 text-red-700'
                )}>
                  {kpi.trend > 0 ? <ArrowUpRight className="h-2.5 w-2.5" /> : <ArrowDownRight className="h-2.5 w-2.5" />}
                  {Math.abs(kpi.trend)}%
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <h3 className="font-serif text-2xl font-black tracking-tight">{kpi.value}</h3>
                <p className="text-[8px] text-foreground/50 uppercase tracking-widest">{kpi.trendLabel}</p>
              </div>
            </div>
          ))}
        </motion.div>

        {/* Charts Section */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8"
        >
          {/* Main Chart */}
          <div className="lg:col-span-2 bg-card border border-border/60 p-6 shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="font-serif text-base font-bold tracking-tight">{t.tokenUsage}</h3>
                <p className="text-[9px] text-muted-foreground uppercase tracking-widest mt-1">{t.weeklyTrend}</p>
              </div>
              <span className="text-[10px] font-bold uppercase px-2 py-1 bg-primary/10 text-primary border border-primary/20 rounded-sm">
                +12.5%
              </span>
            </div>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={tokenUsageData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#d35400" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#d35400" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 2" vertical={false} stroke="rgba(45, 36, 30, 0.08)" />
                  <XAxis
                    dataKey="name"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 9, fontFamily: 'Outfit, sans-serif', fill: '#7a6b5d', fontWeight: 600 }}
                    dy={10}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace', fill: '#7a6b5d' }}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: '2px',
                      border: '1px solid rgba(45, 36, 30, 0.2)',
                      fontFamily: 'Outfit, sans-serif',
                      fontSize: '10px',
                      backgroundColor: '#ffffff',
                    }}
                    formatter={(value) => `${value.toLocaleString()} tokens`}
                  />
                  <Area type="monotone" dataKey="tokens" stroke="#d35400" strokeWidth={2} fillOpacity={1} fill="url(#colorTokens)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Distribution Pie */}
          <div className="bg-card border border-border/60 p-6 shadow-sm flex flex-col">
            <h3 className="font-serif text-base font-bold tracking-tight mb-6">{t.usageBreakdown}</h3>
            <div className="flex-1 flex justify-center items-center min-h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={usageDistribution}
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  >
                    {usageDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      borderRadius: '2px',
                      border: '1px solid rgba(45, 36, 30, 0.2)',
                      fontFamily: 'Outfit, sans-serif',
                      fontSize: '10px',
                      backgroundColor: '#ffffff',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2 mt-4 pt-4 border-t border-border/50">
              {usageDistribution.map((item, i) => (
                <div key={i} className="flex items-center justify-between text-[9px]">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i] }} />
                    <span className="text-foreground/70">{item.name}</span>
                  </div>
                  <span className="font-mono font-bold text-foreground">{item.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Recent Activity */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="bg-card border border-border/60 p-6 shadow-sm"
        >
          <h3 className="font-serif text-base font-bold tracking-tight mb-4">{t.recentActivity}</h3>
          <div className="space-y-3">
            {recentActivities.map((activity, i) => (
              <div key={i} className="flex items-center gap-4 pb-3 border-b border-border/50 last:border-0 last:pb-0">
                <div className="p-2.5 rounded-xl bg-muted/30">
                  <activity.icon className="h-3.5 w-3.5 text-foreground/60" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">{activity.title}</p>
                  <p className="text-[9px] text-muted-foreground uppercase tracking-widest">{activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
