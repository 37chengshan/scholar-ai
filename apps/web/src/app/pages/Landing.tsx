import { useNavigate } from "react-router";
import { motion } from "motion/react";
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
    gradient: "from-teal-500/10 to-emerald-500/10",
  },
  {
    icon: Waypoints,
    title: "过程与证据可视化",
    description: "每一步都有状态、下一动作与证据产物，研究过程完全透明可追溯。",
    gradient: "from-blue-500/10 to-indigo-500/10",
  },
  {
    icon: RefreshCw,
    title: "可恢复与可确认",
    description: "失败任务可重试，高风险操作需确认，结果审核后再接受。",
    gradient: "from-amber-500/10 to-orange-500/10",
  },
  {
    icon: ShieldCheck,
    title: "结构化最终回答",
    description: "答案自动附带引用来源、一致性评分与低置信度说明。",
    gradient: "from-violet-500/10 to-purple-500/10",
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

  const handleEnter = () => {
    navigate(isAuthenticated ? "/chat" : "/login");
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 text-gray-900 dark:text-gray-100">
      {/* ── Header ── */}
      <header className="sticky top-0 z-30 border-b border-gray-200/60 dark:border-gray-800/60 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
          <Logo />
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/login")}
              className="rounded-lg border border-gray-200 dark:border-gray-700 px-3.5 py-1.5 text-xs font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              登录
            </button>
            <button
              onClick={handleEnter}
              className="rounded-lg bg-teal-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm shadow-teal-600/20 hover:bg-teal-500 transition-colors"
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
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center max-w-3xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-900/30 px-4 py-1.5 text-xs font-semibold text-teal-700 dark:text-teal-300 mb-8">
              <Sparkles className="h-3.5 w-3.5" />
              Agent-Native Academic Workspace
            </div>
            <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-[1.05]">
              研究过程不该是
              <span className="bg-gradient-to-r from-teal-600 to-emerald-600 bg-clip-text text-transparent">
                黑盒猜测
              </span>
            </h1>
            <p className="mt-6 text-lg md:text-xl text-gray-600 dark:text-gray-400 leading-relaxed max-w-2xl mx-auto">
              ScholarAI 将学术研究组织为可执行、可追溯、可恢复的 Agent 工作流。
              你始终知道当前阶段、下一步动作和产出证据。
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <button
                onClick={handleEnter}
                className="group inline-flex items-center gap-2 rounded-xl bg-teal-600 px-7 py-3.5 text-sm font-bold text-white shadow-lg shadow-teal-600/25 hover:bg-teal-500 hover:shadow-teal-500/30 transition-all"
              >
                开始研究任务
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </button>
              <button
                onClick={() => navigate("/search")}
                className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-7 py-3.5 text-sm font-bold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                浏览检索入口
              </button>
            </div>
          </motion.div>

          {/* Stats bar */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto"
          >
            {stats.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-black text-teal-600 dark:text-teal-400">{s.value}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{s.label}</div>
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
            <div className="text-xs font-bold uppercase tracking-[0.2em] text-teal-600 dark:text-teal-400 mb-3">
              How It Works
            </div>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
              四步完成一次深度研究
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-1">
            {workflow.map((step, i) => (
              <motion.div
                key={step.label}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.35, delay: i * 0.08 }}
                className="relative flex flex-col items-center text-center p-6"
              >
                {i < workflow.length - 1 && (
                  <div className="hidden md:block absolute right-0 top-1/2 -translate-y-1/2 w-px h-12 bg-gradient-to-b from-transparent via-gray-200 dark:via-gray-700 to-transparent" />
                )}
                <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-teal-50 dark:bg-teal-900/30 border border-teal-100 dark:border-teal-800 mb-4">
                  <step.icon className="h-5 w-5 text-teal-600 dark:text-teal-400" />
                </div>
                <div className="text-xs font-bold text-teal-600 dark:text-teal-400 mb-1">Step {i + 1}</div>
                <h3 className="text-sm font-bold mb-2">{step.label}</h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{step.desc}</p>
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
            <div className="text-xs font-bold uppercase tracking-[0.2em] text-teal-600 dark:text-teal-400 mb-3">
              Core Capabilities
            </div>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
              为学术研究场景而生
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-5">
            {features.map((f, i) => (
              <motion.article
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.35, delay: i * 0.06 }}
                className={`group rounded-2xl border border-gray-200/80 dark:border-gray-800/80 bg-gradient-to-br ${f.gradient} p-6 hover:border-teal-200 dark:hover:border-teal-800 transition-colors`}
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm">
                    <f.icon className="h-5 w-5 text-teal-600 dark:text-teal-400" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold mb-1">{f.title}</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{f.description}</p>
                  </div>
                </div>
              </motion.article>
            ))}
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="py-16">
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.4 }}
            className="rounded-3xl bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 dark:from-gray-800 dark:via-gray-750 dark:to-gray-800 px-8 py-12 md:px-12 text-white text-center relative overflow-hidden"
          >
            {/* Decorative glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-teal-600/10 via-transparent to-emerald-600/10 pointer-events-none" />

            <div className="relative">
              <Zap className="h-8 w-8 text-teal-400 mx-auto mb-4" />
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight">
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
                  <div key={text} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                    {text}
                  </div>
                ))}
              </div>
              <button
                onClick={handleEnter}
                className="mt-8 inline-flex items-center gap-2 rounded-xl bg-teal-500 px-7 py-3.5 text-sm font-bold text-white shadow-lg shadow-teal-500/20 hover:bg-teal-400 transition-colors"
              >
                立即体验
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-gray-200/60 dark:border-gray-800/60 py-8">
        <div className="mx-auto max-w-6xl px-6 flex items-center justify-between text-xs text-gray-400">
          <span>© {new Date().getFullYear()} ScholarAI</span>
          <span>Agent-Native Academic Workspace</span>
        </div>
      </footer>
    </div>
  );
}
