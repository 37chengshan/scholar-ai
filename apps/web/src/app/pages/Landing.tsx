import { useNavigate } from "react-router";
import { motion, useReducedMotion } from "motion/react";
import {
  ArrowRight,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  FileSearch,
  Layers,
  MessageSquareText,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Waypoints,
  Zap,
} from "lucide-react";
import { Logo } from "../components/landing/Logo";
import { useAuth } from "@/contexts/AuthContext";

const features = [
  {
    icon: BrainCircuit,
    title: "Agent 驱动研究",
    description: "AI Agent 自动规划检索、阅读、对比与产出步骤，你只需描述研究目标。",
    gradient: "from-[var(--color-paper-2)] to-[var(--color-paper-1)]",
  },
  {
    icon: Waypoints,
    title: "过程与证据可视化",
    description: "每一步都有状态、下一动作与证据产物，研究过程完全透明可追溯。",
    gradient: "from-[var(--color-paper-2)] to-[var(--color-paper-1)]",
  },
  {
    icon: RefreshCw,
    title: "可恢复与可确认",
    description: "失败任务可重试，高风险操作需确认，结果审核后再接受。",
    gradient: "from-[var(--color-paper-2)] to-[var(--color-paper-1)]",
  },
  {
    icon: ShieldCheck,
    title: "结构化最终回答",
    description: "答案自动附带引用来源、一致性评分与低置信度说明。",
    gradient: "from-[var(--color-paper-2)] to-[var(--color-paper-1)]",
  },
];

const workflow = [
  { icon: Search, label: "描述研究目标", desc: "输入问题，Agent 自动判断最佳执行路径" },
  { icon: FileSearch, label: "检索与分析", desc: "多源检索、精读论文、对比关键信息" },
  { icon: MessageSquareText, label: "交互式执行", desc: "实时查看进度、确认关键操作、查阅证据" },
  { icon: BookOpen, label: "结构化产出", desc: "带引用的最终答案、工件、低置信度提示" },
];

const stats = [
  { value: "10+", label: "内置研究工具" },
  { value: "< 1s", label: "首次响应延迟" },
  { value: "100%", label: "过程可追溯" },
  { value: "∞", label: "可恢复的工作流" },
];

export function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const shouldReduceMotion = useReducedMotion();

  const handleEnter = () => {
    navigate(isAuthenticated ? "/chat" : "/login");
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* ── Header ── */}
      <header className="sticky top-0 z-30 border-b border-border/70 bg-paper-2/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
          <Logo />
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/login")}
              className="rounded-sm border border-border/70 px-3.5 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-muted transition-colors"
            >
              登录
            </button>
            <button
              onClick={handleEnter}
              className="rounded-sm bg-primary px-4 py-1.5 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
            >
              进入工作台
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-24">
        {/* ── Hero ── */}
        <section className="pt-16 pb-20 lg:pt-24 lg:pb-28">
          <motion.div
            initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 20 }}
            animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
            transition={{ duration: shouldReduceMotion ? 0 : 0.5 }}
            className="text-center max-w-3xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 rounded-sm border border-border bg-paper-1 px-4 py-1.5 editorial-kicker mb-8">
              <Sparkles className="h-3.5 w-3.5" />
              Agent-Native Academic Workspace
            </div>
            <h1 className="editorial-title-xl">
              研究过程不该是
              <span className="text-primary">
                黑盒猜测
              </span>
            </h1>
            <p className="mt-6 text-base md:text-lg text-muted-foreground leading-relaxed max-w-2xl mx-auto">
              ScholarAI 将学术研究组织为可执行、可追溯、可恢复的 Agent 工作流。
              你始终知道当前阶段、下一步动作和产出证据。
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <button
                onClick={handleEnter}
                className="group inline-flex items-center gap-2 rounded-sm bg-primary px-7 py-3.5 text-sm font-bold text-primary-foreground shadow-md hover:bg-primary/90 transition-all"
              >
                开始研究任务
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </button>
              <button
                onClick={() => navigate("/search")}
                className="rounded-sm border border-border bg-paper-1 px-7 py-3.5 text-sm font-bold text-foreground/80 hover:bg-muted transition-colors"
              >
                浏览检索入口
              </button>
            </div>
          </motion.div>

          {/* Stats bar */}
          <motion.div
            initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 16 }}
            animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
            transition={{ duration: shouldReduceMotion ? 0 : 0.5, delay: shouldReduceMotion ? 0 : 0.2 }}
            className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-3 max-w-3xl mx-auto"
          >
            {stats.map((s) => (
              <div key={s.label} className="editorial-panel text-center px-3 py-3">
                <div className="text-2xl font-black text-primary">{s.value}</div>
                <div className="editorial-meta mt-1">{s.label}</div>
              </div>
            ))}
          </motion.div>
        </section>

        {/* ── Workflow ── */}
        <section className="py-16">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: "-80px" }}
            className="text-center mb-12"
          >
            <div className="editorial-kicker mb-3">
              How It Works
            </div>
            <h2 className="editorial-title-lg">
              四步完成一次深度研究
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-1">
            {workflow.map((step, i) => (
              <motion.div
                key={step.label}
                initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 16 }}
                whileInView={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: shouldReduceMotion ? 0 : 0.35, delay: shouldReduceMotion ? 0 : i * 0.08 }}
                className="relative flex flex-col items-center text-center p-6 editorial-card"
              >
                {i < workflow.length - 1 && (
                  <div className="hidden md:block absolute right-0 top-1/2 -translate-y-1/2 w-px h-12 bg-gradient-to-b from-transparent via-border to-transparent" />
                )}
                <div className="flex items-center justify-center w-12 h-12 rounded-sm bg-paper-2 border border-border mb-4">
                  <step.icon className="h-5 w-5 text-primary" />
                </div>
                <div className="editorial-meta mb-1">Step {i + 1}</div>
                <h3 className="text-sm font-bold mb-2">{step.label}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── Features ── */}
        <section className="py-16">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: "-80px" }}
            className="text-center mb-12"
          >
            <div className="editorial-kicker mb-3">
              Core Capabilities
            </div>
            <h2 className="editorial-title-lg">
              为学术研究场景而生
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-5">
            {features.map((f, i) => (
              <motion.article
                key={f.title}
                initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 16 }}
                whileInView={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: shouldReduceMotion ? 0 : 0.35, delay: shouldReduceMotion ? 0 : i * 0.06 }}
                className={`group editorial-card bg-gradient-to-br ${f.gradient} p-6`}
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-sm bg-paper-1 border border-border shadow-sm">
                    <f.icon className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold mb-1">{f.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{f.description}</p>
                  </div>
                </div>
              </motion.article>
            ))}
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="py-16">
          <motion.div
            initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0.98 }}
            whileInView={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: shouldReduceMotion ? 0 : 0.4 }}
            className="editorial-panel px-8 py-12 md:px-12 text-foreground text-center relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-paper-2 via-transparent to-paper-3 pointer-events-none" />

            <div className="relative">
              <Zap className="h-8 w-8 text-primary mx-auto mb-4" />
              <h2 className="editorial-title-lg">
                在一个工作台里完成
                <br className="hidden md:block" />
                计划、执行、确认与恢复
              </h2>
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3 max-w-xl mx-auto">
                {[
                  "统一 Scope 与 Active Run 语义",
                  "统一 Pending / Recoverable 动作处理",
                  "统一 Artifacts / Evidence 结果追踪",
                  "统一跨页面状态与动作文案",
                ].map((text) => (
                  <div key={text} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <CheckCircle2 className="h-4 w-4 text-secondary flex-shrink-0" />
                    {text}
                  </div>
                ))}
              </div>
              <button
                onClick={handleEnter}
                className="mt-8 inline-flex items-center gap-2 rounded-sm bg-primary px-7 py-3.5 text-sm font-bold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
              >
                立即体验
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-border/70 py-8 bg-paper-2/60">
        <div className="mx-auto max-w-6xl px-6 flex items-center justify-between text-xs text-muted-foreground">
          <span>© {new Date().getFullYear()} ScholarAI</span>
          <span>Agent-Native Academic Workspace</span>
        </div>
      </footer>
    </div>
  );
}
