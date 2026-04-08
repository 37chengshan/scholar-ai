import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { motion } from 'motion/react';
import { ArrowUpRight, Activity, Database, GitCommit, Search, RefreshCw, Eye, BookOpen, MessageSquare, Clock, ChevronRight } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { Badge } from '../components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboard } from '@/app/hooks/useDashboard';
import { DashboardSkeleton } from '../components/Skeleton';
import { useState, useEffect } from 'react';
import apiClient from '@/utils/apiClient';

export function Dashboard() {
  const { language } = useLanguage();
  const { user } = useAuth();
  const isZh = language === "zh";
  
  // Use dashboard hook for stats
  const { stats, loading, error, weeklyTrendData, subjectDistData, refresh } = useDashboard(user?.id);

  // Recent papers state
  const [recentPapers, setRecentPapers] = useState<Array<{
    id: string;
    title: string;
    authors: string[];
    year?: number;
    currentPage: number;
    lastReadAt: string;
    progress: number;
  }>>([]);
  const [recentPapersLoading, setRecentPapersLoading] = useState(false);

  // Recent sessions state
  const [recentSessions, setRecentSessions] = useState<Array<{
    id: string;
    title?: string;
    createdAt: string;
    lastActivityAt: string;
    messageCount: number;
  }>>([]);
  const [recentSessionsLoading, setRecentSessionsLoading] = useState(false);

  // Fetch recent papers
  useEffect(() => {
    if (!user?.id) return;
    
    async function fetchRecentPapers() {
      try {
        setRecentPapersLoading(true);
        const response = await apiClient.get<{
          success: boolean;
          data: Array<{
            id: string;
            title: string;
            authors: string[];
            year?: number;
            currentPage: number;
            lastReadAt: string;
            progress: number;
          }>;
        }>('/api/dashboard/recent-papers?limit=3');
        
        if (response.data.success) {
          setRecentPapers(response.data.data);
        }
      } catch (err) {
        console.error('Failed to fetch recent papers:', err);
      } finally {
        setRecentPapersLoading(false);
      }
    }
    
    fetchRecentPapers();
  }, [user?.id]);

  // Fetch recent sessions
  useEffect(() => {
    if (!user?.id) return;
    
    async function fetchRecentSessions() {
      try {
        setRecentSessionsLoading(true);
        const response = await apiClient.get<{
          success: boolean;
          data: Array<{
            id: string;
            title?: string;
            createdAt: string;
            lastActivityAt: string;
            messageCount: number;
          }>;
        }>('/api/sessions');
        
        if (response.data.success) {
          // Sort by lastActivityAt and take top 3
          const sorted = response.data.data
            .sort((a, b) => new Date(b.lastActivityAt).getTime() - new Date(a.lastActivityAt).getTime())
            .slice(0, 3);
          setRecentSessions(sorted);
        }
      } catch (err) {
        console.error('Failed to fetch recent sessions:', err);
      } finally {
        setRecentSessionsLoading(false);
      }
    }
    
    fetchRecentSessions();
  }, [user?.id]);

  // Chart colors
  const PIE_COLORS = ['#d35400', '#e67e22', '#f39c12', '#f1c40f'];

  // Helper function to format time ago
  function getTimeAgo(dateString: string, isZh: boolean): string {
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return isZh ? "刚刚" : "Just now";
    if (diffMins < 60) return isZh ? `${diffMins}分钟前` : `${diffMins}m ago`;
    if (diffHours < 24) return isZh ? `${diffHours}小时前` : `${diffHours}h ago`;
    return isZh ? `${diffDays}天前` : `${diffDays}d ago`;
  }

  const t = {
    sysStatus: isZh ? "系统状态" : "System Status",
    node: isZh ? "节点 04" : "Node 04",
    apiActive: isZh ? "API: 活跃" : "API: Active",
    dbSynced: isZh ? "DB: 已同步" : "DB: Synced",
    updateAgo: isZh ? "更新: 2分钟前" : "Update: 2m ago",
    totalPapers: isZh ? "总文献量" : "Total Papers",
    localIndex: isZh ? "本地索引" : "Local index",
    entitiesExt: isZh ? "提取实体" : "Entities Extracted",
    kg: isZh ? "知识图谱" : "Knowledge graph",
    llmGens: isZh ? "LLM 生成" : "LLM Generations",
    tokensProc: isZh ? "处理的 Token" : "Tokens processed",
    deepReads: isZh ? "深度阅读" : "Deep Reads",
    analyzedDocs: isZh ? "已分析文档" : "Analyzed documents",
    globalQueries: isZh ? "全局查询" : "Global Queries",
    extSearches: isZh ? "外部搜索" : "External searches",
    ingestVel: isZh ? "数据摄入速度" : "Ingestion Velocity",
    weeklyTrend: isZh ? "每周趋势" : "Weekly Trend",
    export: isZh ? "导出" : "Export",
    subjDist: isZh ? "主题分布" : "Subject Distribution",
    recentReads: isZh ? "最近阅读" : "Recent Readings",
    library: isZh ? "文献库" : "Library",
    activeSessions: isZh ? "活跃会话" : "Active Sessions",
    terminal: isZh ? "终端" : "Terminal",
    monthlyUsage: isZh ? "本月用量" : "Monthly Usage",
    totalTokens: isZh ? "总 Token" : "Total Tokens",
    totalCost: isZh ? "总费用" : "Total Cost",
    requestCount: isZh ? "请求次数" : "Request Count",
    costUnit: isZh ? "元" : "CNY",
  };

  return (
    <div className="min-h-full font-sans bg-background text-foreground selection:bg-primary selection:text-primary-foreground relative p-6 lg:p-8 flex flex-col gap-6">

      {loading ? (
        <DashboardSkeleton />
      ) : (
        <>
          {/* Status Indicator */}
          <div className="flex justify-end gap-2">
            {error && (
              <Badge variant="destructive" className="text-xs">
                {isZh ? "加载失败" : "Load Failed"}
              </Badge>
            )}
            <button 
              onClick={refresh}
              disabled={loading}
              className="text-xs"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Header Info - High Density */}
          <div className="flex justify-between items-end border-b border-border/50 pb-4">
            <div className="flex gap-6 items-center">
              <div className="flex flex-col">
                <span className="text-[9px] font-bold tracking-[0.3em] uppercase text-primary">{t.sysStatus}</span>
                <span className="font-serif text-2xl font-black tracking-tight leading-none mt-1">{t.node}</span>
              </div>
              <div className="h-8 w-px bg-border/50" />
              <div className="flex gap-5 text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  {t.apiActive}
                </div>
                <div className="flex items-center gap-1.5">
                  <Database className="w-3 h-3" />
                  {t.dbSynced}
                </div>
                <div className="flex items-center gap-1.5">
                  <RefreshCw className="w-3 h-3" />
                  {t.updateAgo}
                </div>
              </div>
            </div>
            <div className="text-right text-[9px] font-mono tracking-[0.2em] text-muted-foreground uppercase bg-muted/50 px-2.5 py-1.5 rounded-sm border border-border/50">
              {new Date().toISOString().split('T')[0]}
            </div>
          </div>

          {/* KPI Cards Grid */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4"
          >
            {[
              { label: t.totalPapers, value: stats?.paperCount || "—", desc: t.localIndex, icon: Database, trend: stats?.weeklyTrend ? `+${stats.weeklyTrend}%` : "—" },
              { label: t.entitiesExt, value: stats?.entityCount || "—", desc: t.kg, icon: GitCommit, trend: "+4.2%" },
              { label: t.llmGens, value: stats?.tokenCount ? `${(stats.tokenCount / 1000).toFixed(1)}M` : "—", desc: t.tokensProc, icon: Activity, trend: "+24%" },
              { label: t.deepReads, value: stats?.queryCount || "—", desc: t.analyzedDocs, icon: Eye, trend: "+8%" },
              { label: t.globalQueries, value: stats?.queryCount || "—", desc: t.extSearches, icon: Search, trend: "+1.5%" },
            ].map((kpi, i) => (
              <div key={i} className="group flex flex-col gap-2.5 bg-card border border-border/50 p-4 shadow-sm hover:border-primary/50 transition-colors relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary/0 via-primary/0 to-primary/0 group-hover:from-primary/20 group-hover:via-primary group-hover:to-primary/20 transition-all duration-500" />
                <div className="flex justify-between items-start">
                  <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground flex items-center gap-1.5">
                    <kpi.icon className="w-3 h-3 text-primary/70" />
                    {kpi.label}
                  </span>
                  <span className="text-[8px] font-mono text-green-600 flex items-center bg-green-500/10 px-1 rounded-sm">
                    <ArrowUpRight className="w-2.5 h-2.5" />
                    {kpi.trend}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <h3 className="font-serif text-xl font-black tracking-tight">{kpi.value}</h3>
                  <p className="text-[9px] text-foreground/50 tracking-widest uppercase">{kpi.desc}</p>
                </div>
              </div>
            ))}
          </motion.div>

          {/* Monthly Token Usage Card */}
          {stats?.monthlyTokenUsage && stats.monthlyTokenUsage.totalTokens > 0 && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="bg-gradient-to-br from-primary/5 to-primary/10 border border-primary/20 p-5 shadow-sm"
            >
              <div className="flex justify-between items-end border-b border-border/50 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-primary" />
                  <h3 className="font-serif text-base font-bold tracking-tight">{t.monthlyUsage}</h3>
                </div>
                <div className="text-[8px] font-bold tracking-[0.2em] uppercase px-1.5 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-sm">
                  {new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })}
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-6">
                <div className="flex flex-col gap-1.5">
                  <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground">{t.totalTokens}</span>
                  <div className="flex items-baseline gap-1">
                    <h3 className="font-serif text-2xl font-black text-primary">
                      {(stats.monthlyTokenUsage.totalTokens / 1000).toFixed(1)}K
                    </h3>
                    <span className="text-[10px] font-mono text-muted-foreground">tokens</span>
                  </div>
                </div>
                
                <div className="flex flex-col gap-1.5">
                  <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground">{t.totalCost}</span>
                  <div className="flex items-baseline gap-1">
                    <h3 className="font-serif text-2xl font-black text-primary">
                      {stats.monthlyTokenUsage.totalCostCny.toFixed(2)}
                    </h3>
                    <span className="text-[10px] font-mono text-muted-foreground">{t.costUnit}</span>
                  </div>
                </div>
                
                <div className="flex flex-col gap-1.5">
                  <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground">{t.requestCount}</span>
                  <div className="flex items-baseline gap-1">
                    <h3 className="font-serif text-2xl font-black text-primary">
                      {stats.monthlyTokenUsage.requestCount}
                    </h3>
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {isZh ? "次" : "reqs"}
                    </span>
                  </div>
                </div>
              </div>
              
              {stats.monthlyTokenUsage.dailyBreakdown.length > 0 && (
                <div className="mt-4 pt-3 border-t border-border/50">
                  <div className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-2">
                    {isZh ? "每日分布" : "Daily Breakdown"}
                  </div>
                  <div className="flex gap-2 overflow-x-auto">
                    {stats.monthlyTokenUsage.dailyBreakdown.slice(-7).map((day, i) => (
                      <div key={i} className="flex flex-col gap-0.5 bg-background/50 px-2 py-1.5 rounded-sm border border-border/30 min-w-[60px]">
                        <span className="text-[8px] font-mono text-muted-foreground">
                          {new Date(day.date).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}
                        </span>
                        <span className="text-[9px] font-bold text-primary">
                          {(day.tokens / 1000).toFixed(1)}K
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* Charts Layout */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[300px]"
          >
            {/* Main Chart */}
            <div className="lg:col-span-8 bg-card border border-border/50 p-5 shadow-sm flex flex-col">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-3">
                  <h3 className="font-serif text-base font-bold tracking-tight">{t.ingestVel}</h3>
                  <div className="text-[8px] font-bold tracking-[0.2em] uppercase px-1.5 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-sm">
                    {t.weeklyTrend}
                  </div>
                </div>
                <button className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
                  {t.export} <ArrowUpRight className="w-3 h-3" />
                </button>
              </div>
              <div className="flex-1 w-full min-h-[200px]">
                {weeklyTrendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={weeklyTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#d35400" stopOpacity={0.15}/>
                          <stop offset="95%" stopColor="#d35400" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="2 2" vertical={false} stroke="rgba(45, 36, 30, 0.08)" />
                      <XAxis
                        dataKey="name"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontSize: 9, fontFamily: 'Outfit, sans-serif', fill: '#7a6b5d', fontWeight: 600, letterSpacing: '0.1em' }}
                        dy={10}
                      />
                      <YAxis 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace', fill: '#7a6b5d' }} 
                      />
                      <Tooltip 
                        contentStyle={{ borderRadius: '2px', border: '1px solid rgba(45, 36, 30, 0.2)', fontFamily: 'Outfit, sans-serif', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 'bold', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', backgroundColor: '#ffffff' }}
                        itemStyle={{ fontFamily: 'JetBrains Mono, monospace', color: '#d35400' }}
                      />
                      <Area type="monotone" dataKey="uv" stroke="#d35400" strokeWidth={2} fillOpacity={1} fill="url(#colorUv)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground text-[10px] font-bold uppercase tracking-widest">
                    {isZh ? "暂无数据" : "No data yet"}
                  </div>
                )}
              </div>
            </div>

            {/* Secondary Stats / Pie Chart */}
            <div className="lg:col-span-4 bg-card border border-border/50 p-5 shadow-sm flex flex-col">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-serif text-base font-bold tracking-tight">{t.subjDist}</h3>
              </div>
              <div className="flex-1 flex justify-center items-center min-h-[160px]">
                {subjectDistData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={subjectDistData}
                        innerRadius={50}
                        outerRadius={70}
                        paddingAngle={2}
                        dataKey="value"
                        stroke="none"
                      >
                        {subjectDistData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ borderRadius: '2px', border: '1px solid rgba(45, 36, 30, 0.2)', fontFamily: 'Outfit, sans-serif', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 'bold', backgroundColor: '#ffffff' }} 
                        itemStyle={{ fontFamily: 'JetBrains Mono, monospace' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-muted-foreground text-[10px] font-bold uppercase tracking-widest">
                    {isZh ? "暂无数据" : "No data yet"}
                  </div>
                )}
              </div>
              {subjectDistData.length > 0 && (
                <div className="grid grid-cols-2 gap-y-2.5 gap-x-2 mt-2 pt-3 border-t border-border/50">
                  {subjectDistData.map((item, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-[8px] font-bold tracking-[0.1em] uppercase text-foreground/80 group cursor-default">
                      <div className="w-1.5 h-1.5 rounded-sm transition-transform group-hover:scale-150" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                      <span className="truncate group-hover:text-primary transition-colors">{item.name}</span>
                      <span className="ml-auto font-mono text-muted-foreground">{item.value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>

          {/* Recent Activity Sections */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            {/* Recent Readings */}
            <div className="bg-card border border-border/50 p-5 shadow-sm flex flex-col">
              <div className="flex justify-between items-end border-b border-border/50 pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-primary" />
                  <h3 className="font-serif text-base font-bold tracking-tight">{t.recentReads}</h3>
                </div>
                <button className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
                  {t.library} <ArrowUpRight className="w-2.5 h-2.5" />
                </button>
              </div>
              <div className="flex flex-col gap-0 divide-y divide-border/30">
                {recentPapersLoading ? (
                  <div className="py-8 text-center text-muted-foreground text-[10px]">
                    {isZh ? "加载中..." : "Loading..."}
                  </div>
                ) : recentPapers.length === 0 ? (
                  <div className="py-8 text-center text-muted-foreground text-[10px]">
                    {isZh ? "暂无阅读记录" : "No reading history"}
                  </div>
                ) : (
                  recentPapers.map((paper, i) => {
                    const timeAgo = getTimeAgo(paper.lastReadAt, isZh);
                    return (
                      <div key={paper.id} className="py-2.5 flex items-center justify-between group cursor-pointer hover:bg-muted/30 -mx-2 px-2 rounded-sm transition-colors">
                        <div className="flex flex-col gap-1 w-full max-w-[75%]">
                          <span className="font-serif text-sm font-bold truncate group-hover:text-primary transition-colors">{paper.title}</span>
                          <div className="flex items-center gap-3 text-[9px] font-mono text-muted-foreground">
                            <span className="uppercase tracking-widest font-sans font-bold text-[8px]">{paper.authors?.slice(0, 3).join(', ') || '—'}</span>
                            <span className="flex items-center gap-1"><Clock className="w-2.5 h-2.5" /> {timeAgo}</span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1.5">
                          <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-foreground/70">{paper.progress}%</span>
                          <div className="w-12 h-1 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-primary" style={{ width: `${paper.progress}%` }} />
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Recent Conversations */}
            <div className="bg-card border border-border/50 p-5 shadow-sm flex flex-col">
              <div className="flex justify-between items-end border-b border-border/50 pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-primary" />
                  <h3 className="font-serif text-base font-bold tracking-tight">{t.activeSessions}</h3>
                </div>
                <button className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
                  {t.terminal} <ArrowUpRight className="w-2.5 h-2.5" />
                </button>
              </div>
              <div className="flex flex-col gap-0 divide-y divide-border/30">
                {recentSessionsLoading ? (
                  <div className="py-8 text-center text-muted-foreground text-[10px]">
                    {isZh ? "加载中..." : "Loading..."}
                  </div>
                ) : recentSessions.length === 0 ? (
                  <div className="py-8 text-center text-muted-foreground text-[10px]">
                    {isZh ? "暂无会话记录" : "No sessions yet"}
                  </div>
                ) : (
                  recentSessions.map((session, i) => {
                    const timeAgo = getTimeAgo(session.lastActivityAt, isZh);
                    return (
                      <div key={session.id} className="py-2.5 flex items-center justify-between group cursor-pointer hover:bg-muted/30 -mx-2 px-2 rounded-sm transition-colors">
                        <div className="flex flex-col gap-1 w-full max-w-[75%]">
                          <span className="font-serif text-sm font-bold truncate group-hover:text-primary transition-colors">
                            {session.title || (isZh ? "未命名会话" : "Untitled Session")}
                          </span>
                          <div className="flex items-center gap-3 text-[8px] uppercase tracking-widest text-muted-foreground font-bold">
                            <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded-sm">
                              {isZh ? `${session.messageCount} 条消息` : `${session.messageCount} msgs`}
                            </span>
                            <span className="font-mono flex items-center gap-1 text-[9px]">
                              <Clock className="w-2.5 h-2.5" /> {timeAgo}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-[9px] font-mono text-muted-foreground">
                          <ChevronRight className="w-3 h-3 text-foreground/30 group-hover:text-primary transition-colors" />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </div>
  );
}