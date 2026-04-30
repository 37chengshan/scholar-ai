import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion } from 'motion/react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  Activity, RefreshCw, CheckCircle2, XCircle, AlertTriangle, Clock,
  TrendingUp, TrendingDown, Minus, Database, Zap, ArrowUpRight, ArrowDownRight,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from '../components/ui/button';
import { evalApi } from '@/services/evalApi';
import type {
  EvaluationOverview,
  BenchmarkRunDetail,
  BenchmarkDiff,
  EvalRunVerdict,
  MetricDeltaStatus,
  NormalizedMetrics,
} from '@scholar-ai/types';

function pct(v: number) { return `${(v * 100).toFixed(1)}%`; }
function sec(v: number) { return `${v.toFixed(2)}s`; }
function usd(v: number) { return `$${v.toFixed(4)}`; }

const METRIC_CFG: Record<string, { label: string; fmt: (v: number) => string; higherIsBetter: boolean }> = {
  retrieval_hit_rate:       { label: 'Retrieval Hit Rate',       fmt: pct, higherIsBetter: true },
  recall_at_5:              { label: 'Recall@5',                 fmt: pct, higherIsBetter: true },
  recall_at_10:             { label: 'Recall@10',                fmt: pct, higherIsBetter: true },
  rerank_gain:              { label: 'Rerank Gain',              fmt: pct, higherIsBetter: true },
  citation_jump_valid_rate: { label: 'Citation Jump Valid Rate',  fmt: pct, higherIsBetter: true },
  answer_supported_rate:    { label: 'Answer Supported Rate',    fmt: pct, higherIsBetter: true },
  groundedness:             { label: 'Groundedness',             fmt: pct, higherIsBetter: true },
  abstain_precision:        { label: 'Abstain Precision',        fmt: pct, higherIsBetter: true },
  latency_p50:              { label: 'Latency P50',              fmt: sec, higherIsBetter: false },
  latency_p95:              { label: 'Latency P95',              fmt: sec, higherIsBetter: false },
  cost_per_answer:          { label: 'Cost / Answer',            fmt: usd, higherIsBetter: false },
};

function RunBadge({ mode }: { mode: 'offline' | 'online' }) {
  return (
    <span className={clsx(
      'inline-flex items-center px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-sm',
      mode === 'offline' ? 'bg-blue-500/10 text-blue-500' : 'bg-purple-500/10 text-purple-500',
    )}>{mode}</span>
  );
}

function VerdictBadge({ verdict }: { verdict: EvalRunVerdict }) {
  const cls = verdict === 'PASS' ? 'bg-green-500/10 text-green-600'
            : verdict === 'FAIL' ? 'bg-red-500/10 text-red-600'
            : 'bg-yellow-500/10 text-yellow-600';
  const Icon = verdict === 'PASS' ? CheckCircle2 : verdict === 'FAIL' ? XCircle : AlertTriangle;
  return (
    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 text-xs font-bold rounded-sm', cls)}>
      <Icon className="h-3.5 w-3.5" />{verdict}
    </span>
  );
}

function DeltaIcon({ status }: { status: MetricDeltaStatus }) {
  if (status === 'improved') return <ArrowUpRight className="h-3.5 w-3.5 text-green-500" />;
  if (status === 'regressed') return <ArrowDownRight className="h-3.5 w-3.5 text-red-500" />;
  return <Minus className="h-3.5 w-3.5 text-muted-foreground" />;
}

function FamilyChart({ byFamily }: { byFamily: BenchmarkRunDetail['by_family'] }) {
  const families = Object.keys(byFamily.retrieval);
  const data = families.map((f) => ({
    name: f.replace(/_/g, ' '),
    recall5: Math.round((byFamily.retrieval[f]?.recall_at_5 ?? 0) * 100),
    supported: Math.round((byFamily.answer_quality[f]?.answer_supported_rate ?? 0) * 100),
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
        <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }} tickFormatter={(v) => `${v}%`} />
        <Tooltip
          contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 4, fontSize: 11 }}
          formatter={(v: number, name: string) => [`${v}%`, name === 'recall5' ? 'Recall@5' : 'Ans Supported']}
        />
        <Bar dataKey="recall5" fill="hsl(var(--primary))" opacity={0.85} radius={[2, 2, 0, 0]} />
        <Bar dataKey="supported" fill="#22c55e" opacity={0.85} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function Analytics() {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const [overview, setOverview] = useState<EvaluationOverview | null>(null);
  const [selected, setSelected] = useState<BenchmarkRunDetail | null>(null);
  const [diff, setDiff] = useState<BenchmarkDiff | null>(null);
  const [modeFilter, setModeFilter] = useState<'all' | 'offline' | 'online'>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function metricVal(m: NormalizedMetrics, key: string): number {
    if (key === 'recall_at_5') return m.top_k_recall.recall_at_5;
    if (key === 'recall_at_10') return m.top_k_recall.recall_at_10;
    return ((m as unknown) as Record<string, number>)[key] ?? 0;
  }

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const ov = await evalApi.getOverview();
      setOverview(ov);
      const latestId = ov.latest_offline_gate?.run_id;
      if (latestId) {
        const detail = await evalApi.getRunDetail(latestId);
        setSelected(detail);
      }
    } catch {
      setError(isZh ? '加载失败，请重试' : 'Load failed. Please retry.');
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { void loadData(); }, [loadData]);

  const pickRun = async (runId: string) => {
    try {
      const detail = await evalApi.getRunDetail(runId);
      setSelected(detail);
      setDiff(null);
    } catch { /* ignore */ }
  };

  const compare = async (baseId: string, candidateId: string) => {
    try { setDiff(await evalApi.getDiff(baseId, candidateId)); } catch { /* ignore */ }
  };

  const filteredRuns = (overview?.recent_runs ?? []).filter(
    (r) => modeFilter === 'all' || r.mode === modeFilter,
  );
  const summaryCards = useMemo(() => {
    if (!overview?.latest_offline_gate) {
      return [];
    }

    const gate = overview.latest_offline_gate;
    const hasFailures = gate.gate_failures.length > 0;
    const conclusion = hasFailures
      ? (isZh ? '当前离线门禁未通过' : 'Current offline gate is not passing')
      : (isZh ? '当前离线门禁已通过' : 'Current offline gate is passing');
    const status = hasFailures
      ? (isZh ? `${gate.gate_failures.length} 个门槛未达标` : `${gate.gate_failures.length} gate checks are failing`)
      : (isZh ? '关键门槛当前全部达标' : 'Key quality thresholds are currently satisfied');
    const reason = selected
      ? (isZh
          ? `当前查看运行 ${selected.run_id.slice(-8)}，有据率 ${pct(selected.metrics.answer_supported_rate)}，Recall@5 ${pct(selected.metrics.top_k_recall.recall_at_5)}。`
          : `Run ${selected.run_id.slice(-8)} is in focus with ${pct(selected.metrics.answer_supported_rate)} answer support and ${pct(selected.metrics.top_k_recall.recall_at_5)} Recall@5.`)
      : (isZh
          ? '最新离线门禁定义了当前系统质量是否可继续对外展示。'
          : 'The latest offline gate determines whether the system is safe to present externally.');
    const nextAction = hasFailures
      ? (isZh ? '先看失败门槛与最近运行差异，再决定是否继续上线或复测。' : 'Inspect failing gates and recent run deltas before promoting or rerunning.')
      : (isZh ? '继续检查最近运行趋势，确认改进不是一次性波动。' : 'Review recent run trends to confirm this pass is stable, not a one-off spike.');

    return [
      { title: isZh ? '结论' : 'Conclusion', value: conclusion, body: reason },
      { title: isZh ? '当前状态' : 'Current Status', value: hasFailures ? (isZh ? '未过门槛' : 'Below Gate') : (isZh ? '达标' : 'On Target'), body: status },
      { title: isZh ? '为什么重要' : 'Why It Matters', value: isZh ? '质量门槛' : 'Quality Gate', body: isZh ? '这里决定当前 RAG 质量是否可信、是否值得继续对外演示。' : 'This is the read-only quality bar that tells you whether the current RAG system is trustworthy enough to show.' },
      { title: isZh ? '下一步' : 'Next Action', value: hasFailures ? (isZh ? '看失败项' : 'Inspect Failures') : (isZh ? '看趋势' : 'Review Trend'), body: nextAction },
    ];
  }, [isZh, overview, selected]);

  return (
    <div className="min-h-full bg-background text-foreground">
      <div className="sticky top-0 z-10 border-b border-border/60 bg-background/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div>
            <h1 className="text-3xl font-serif font-black tracking-tight">{isZh ? '评测看板' : 'Evaluation Dashboard'}</h1>
            <p className="text-sm text-muted-foreground mt-1">{isZh ? 'Phase 6 · RAG 质量门禁与基准测试' : 'Phase 6 · RAG Quality Gate & Benchmarks'}</p>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={() => void loadData()} disabled={loading}>
            <RefreshCw className={clsx('h-3.5 w-3.5', loading && 'animate-spin')} />
            {isZh ? '刷新' : 'Refresh'}
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {loading && (
          <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
            <Activity className="h-4 w-4 animate-spin mr-2" />{isZh ? '加载中...' : 'Loading...'}
          </div>
        )}
        {!loading && error && (
          <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/20 rounded-md text-red-600 text-sm">
            <XCircle className="h-4 w-4 flex-shrink-0" />{error}
          </div>
        )}
        {!loading && !error && !overview?.latest_offline_gate && (
          <div className="flex items-center gap-2 p-6 border border-border/60 rounded-md text-muted-foreground text-sm">
            <Database className="h-4 w-4 flex-shrink-0" />
            {isZh ? '暂无评测数据，请先运行 Phase 6 benchmark' : 'No eval data yet. Run Phase 6 benchmark first.'}
          </div>
        )}

        {!loading && !error && overview && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="space-y-8">

            {summaryCards.length > 0 && (
              <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                {summaryCards.map((card) => (
                  <div key={card.title} className="rounded-2xl border border-border/60 bg-card p-5 shadow-sm">
                    <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">{card.title}</div>
                    <div className="mt-3 text-lg font-semibold tracking-tight text-foreground">{card.value}</div>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{card.body}</p>
                  </div>
                ))}
              </section>
            )}

            {overview.latest_offline_gate && (() => {
              const gate = overview.latest_offline_gate!;
              const m = gate.metrics;
              return (
                <section>
                  <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
                    {isZh ? '最新离线门禁' : 'Latest Offline Gate'} · <span className="font-mono">{gate.run_id.slice(-16)}</span>
                  </h2>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { label: isZh ? '门禁状态' : 'Gate Status', value: gate.verdict, sub: `${gate.gate_failures.length} failure(s)`, Icon: gate.verdict === 'PASS' ? CheckCircle2 : XCircle },
                      { label: isZh ? '检索命中率' : 'Hit Rate', value: pct(m.retrieval_hit_rate), sub: `Recall@5: ${pct(m.top_k_recall.recall_at_5)}`, Icon: TrendingUp },
                      { label: isZh ? '回答有据率' : 'Ans Supported', value: pct(m.answer_supported_rate), sub: `Groundedness: ${pct(m.groundedness)}`, Icon: CheckCircle2 },
                      { label: 'Latency P95', value: sec(m.latency_p95), sub: `P50: ${sec(m.latency_p50)} · Fallback: ${m.fallback_used_count}`, Icon: Clock },
                    ].map(({ label, value, sub, Icon }) => (
                      <div key={label} className="group flex flex-col gap-3 bg-card border border-border/60 p-5 shadow-sm hover:border-primary/40 transition-all relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-primary/20 to-transparent group-hover:via-primary/50 transition-all" />
                        <div className="flex items-center gap-2">
                          <div className="p-2 bg-primary/10 rounded-lg"><Icon className="h-4 w-4 text-primary" /></div>
                          <span className="text-xs font-medium text-muted-foreground">{label}</span>
                        </div>
                        <div className="text-2xl font-black tracking-tight font-mono">{value}</div>
                        <div className="text-xs text-muted-foreground">{sub}</div>
                      </div>
                    ))}
                  </div>
                  {gate.gate_failures.length > 0 && (
                    <div className="mt-3 p-3 bg-red-500/5 border border-red-500/20 rounded-md">
                      <div className="flex items-center gap-1.5 mb-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                        <span className="text-xs font-bold text-red-600">{isZh ? '门禁失败项' : 'Gate Failures'}</span>
                      </div>
                      <ul className="space-y-0.5">{gate.gate_failures.map((f, i) => (
                        <li key={i} className="text-xs text-red-600 font-mono">{f}</li>
                      ))}</ul>
                    </div>
                  )}
                </section>
              );
            })()}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    {isZh ? '最近运行' : 'Recent Runs'} ({overview.run_count})
                  </h2>
                  <div className="flex gap-1">
                    {(['all', 'offline', 'online'] as const).map((m) => (
                      <button key={m} onClick={() => setModeFilter(m)}
                        className={clsx('px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-sm transition-colors',
                          modeFilter === m ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-muted/80')}>
                        {m === 'all' ? (isZh ? '全部' : 'All') : m}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="border border-border/60 rounded-md overflow-hidden">
                  {filteredRuns.length === 0
                    ? <div className="p-4 text-xs text-muted-foreground text-center">{isZh ? '暂无数据' : 'No data'}</div>
                    : (
                      <table className="w-full text-xs">
                        <thead className="bg-muted/50 border-b border-border/40">
                          <tr>
                            <th className="text-left py-2 px-3 font-medium text-muted-foreground">Run</th>
                            <th className="py-2 px-3 font-medium text-muted-foreground">Mode</th>
                            <th className="py-2 px-3 font-medium text-muted-foreground">Verdict</th>
                            <th className="py-2 px-3 font-medium text-muted-foreground">{isZh ? '日期' : 'Date'}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredRuns.map((run) => (
                            <tr key={run.run_id}
                              className={clsx('border-b border-border/30 cursor-pointer hover:bg-muted/30 transition-colors', selected?.run_id === run.run_id && 'bg-primary/5')}
                              onClick={() => void pickRun(run.run_id)}>
                              <td className="py-2 px-3 font-mono truncate max-w-[120px]" title={run.run_id}>{run.run_id.slice(-12)}</td>
                              <td className="py-2 px-3 text-center"><RunBadge mode={run.mode} /></td>
                              <td className="py-2 px-3 text-center"><VerdictBadge verdict={run.overall_verdict} /></td>
                              <td className="py-2 px-3 text-muted-foreground whitespace-nowrap">{new Date(run.created_at).toLocaleDateString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                </div>
              </section>

              <section>
                <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">{isZh ? '运行详情' : 'Run Detail'}</h2>
                {!selected
                  ? <div className="flex items-center justify-center h-40 border border-border/60 rounded-md text-muted-foreground text-xs">{isZh ? '点击运行行查看详情' : 'Click a run row to view details'}</div>
                  : (
                    <div className="border border-border/60 rounded-md overflow-hidden">
                      <div className="px-3 py-2 bg-muted/40 border-b border-border/40 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <RunBadge mode={selected.meta.mode} />
                          <span className="text-xs font-mono text-muted-foreground">{selected.run_id.slice(-16)}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <VerdictBadge verdict={selected.meta.overall_verdict} />
                          {filteredRuns.length > 1 && filteredRuns[filteredRuns.length - 1]?.run_id !== selected.run_id && (
                            <button className="text-[10px] text-primary underline underline-offset-2"
                              onClick={() => { const base = filteredRuns[filteredRuns.length - 1]; if (base) void compare(base.run_id, selected.run_id); }}>
                              {isZh ? '与基线对比' : 'Compare to baseline'}
                            </button>
                          )}
                        </div>
                      </div>
                      <table className="w-full text-xs">
                        <thead className="bg-muted/30 border-b border-border/40">
                          <tr>
                            <th className="text-left py-1.5 px-3 font-medium text-muted-foreground">{isZh ? '指标' : 'Metric'}</th>
                            <th className="text-right py-1.5 px-3 font-medium text-muted-foreground">{isZh ? '值' : 'Value'}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(METRIC_CFG).map(([key, cfg]) => (
                            <tr key={key} className="border-b border-border/30 hover:bg-muted/20">
                              <td className="py-1.5 px-3">{cfg.label}</td>
                              <td className="py-1.5 px-3 text-right font-mono">{cfg.fmt(metricVal(selected.metrics, key))}</td>
                            </tr>
                          ))}
                          <tr className="border-b border-border/30">
                            <td className="py-1.5 px-3">{isZh ? 'Fallback 次数' : 'Fallback Count'}</td>
                            <td className="py-1.5 px-3 text-right font-mono">{selected.metrics.fallback_used_count}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  )}
              </section>
            </div>

            {selected && Object.keys(selected.by_family.retrieval).length > 0 && (
              <section>
                <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">{isZh ? '查询族分布' : 'Query Family Breakdown'}</h2>
                <div className="border border-border/60 rounded-md p-4">
                  <FamilyChart byFamily={selected.by_family} />
                  <div className="flex gap-4 mt-2 justify-center text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-primary opacity-80 inline-block" />Recall@5</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-green-500 opacity-80 inline-block" />Answer Supported</span>
                  </div>
                </div>
              </section>
            )}

            {diff && (
              <section>
                <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
                  {isZh ? '对比报告' : 'Diff Report'} · <span className="font-mono">{diff.base_run_id.slice(-12)}</span>{' \u2192 '}<span className="font-mono">{diff.candidate_run_id.slice(-12)}</span>
                </h2>
                <div className="flex items-center gap-4 mb-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1 text-green-600 font-medium"><TrendingUp className="h-3.5 w-3.5" />{diff.summary.improved} {isZh ? '改进' : 'improved'}</span>
                  <span className="flex items-center gap-1 text-red-600 font-medium"><TrendingDown className="h-3.5 w-3.5" />{diff.summary.regressed} {isZh ? '退化' : 'regressed'}</span>
                  <span className="flex items-center gap-1"><Minus className="h-3.5 w-3.5" />{diff.summary.unchanged} {isZh ? '未变' : 'unchanged'}</span>
                </div>
                <div className="border border-border/60 rounded-md overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50 border-b border-border/40">
                      <tr>
                        <th className="text-left py-2 px-3 font-medium text-muted-foreground">{isZh ? '指标' : 'Metric'}</th>
                        <th className="text-right py-2 px-3 font-medium text-muted-foreground">{isZh ? '基线' : 'Baseline'}</th>
                        <th className="text-right py-2 px-3 font-medium text-muted-foreground">{isZh ? '候选' : 'Candidate'}</th>
                        <th className="text-right py-2 px-3 font-medium text-muted-foreground">\u0394</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(diff.deltas).map(([key, d]) => {
                        const cfg = METRIC_CFG[key];
                        if (!cfg) return null;
                        return (
                          <tr key={key} className="border-b border-border/40 hover:bg-muted/30 transition-colors">
                            <td className="py-2 px-3 font-medium">{cfg.label}</td>
                            <td className="py-2 px-3 text-right font-mono text-muted-foreground">{cfg.fmt(d.base)}</td>
                            <td className="py-2 px-3 text-right font-mono">{cfg.fmt(d.candidate)}</td>
                            <td className="py-2 px-3">
                              <div className="flex items-center justify-end gap-1">
                                <DeltaIcon status={d.status} />
                                <span className={clsx('text-xs font-mono', d.status === 'improved' ? 'text-green-500' : d.status === 'regressed' ? 'text-red-500' : 'text-muted-foreground')}>
                                  {d.delta >= 0 ? '+' : ''}{cfg.fmt(Math.abs(d.delta))}
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {selected && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground p-3 bg-muted/30 rounded-md border border-border/40">
                <Zap className="h-3.5 w-3.5 flex-shrink-0" />
                <span>
                  Reranker: <strong>{selected.meta.reranker === 'on' ? 'ON' : 'OFF'}</strong>
                  {selected.metrics.rerank_gain > 0 && <> \xb7 Gain: <strong className="text-green-600">{pct(selected.metrics.rerank_gain)}</strong></>}
                  {' \xb7 '}Abstain precision: <strong>{pct(selected.metrics.abstain_precision)}</strong>
                  {' \xb7 '}Citation jump valid: <strong>{pct(selected.metrics.citation_jump_valid_rate)}</strong>
                  {' \xb7 '}Cost/answer: <strong>{usd(selected.metrics.cost_per_answer)}</strong>
                </span>
              </div>
            )}

          </motion.div>
        )}
      </div>
    </div>
  );
}
