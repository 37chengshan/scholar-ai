import { useNavigate } from "react-router";
import { motion } from "motion/react";
import { ArrowRight, CheckCircle2, Layers, RefreshCw, Sparkles, Waypoints } from "lucide-react";
import { Logo } from "../components/landing/Logo";
import { useAuth } from "@/contexts/AuthContext";

const promises = [
  {
    icon: Layers,
    title: "任务驱动研究",
    description: "从检索、导入、阅读到问答与产出，所有步骤在同一工作流中推进。",
  },
  {
    icon: Waypoints,
    title: "过程与证据可视化",
    description: "每一步都有状态、下一动作与证据产物，不再依赖记忆跨页面追踪。",
  },
  {
    icon: RefreshCw,
    title: "可恢复与可确认",
    description: "失败任务可恢复，待确认动作可继续，结果可审核后再接受。",
  },
];

const stages = [
  "Plan Research Task",
  "Execute With Agent Workflow",
  "Review Evidence & Citations",
  "Confirm Deliverables",
];

export function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const handleEnter = () => {
    if (isAuthenticated) {
      navigate("/chat");
      return;
    }
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[#f7f5ef] text-zinc-900">
      <header className="sticky top-0 z-30 border-b border-zinc-200 bg-[#f7f5ef]/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Logo />
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/login")}
              className="rounded border border-zinc-300 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-zinc-700 hover:bg-zinc-100"
            >
              登录
            </button>
            <button
              onClick={handleEnter}
              className="rounded bg-zinc-900 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-white hover:bg-zinc-800"
            >
              进入工作台
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-20 pt-12">
        <section className="grid gap-10 lg:grid-cols-[1.2fr_1fr]">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
            <div className="inline-flex items-center gap-2 rounded-full border border-zinc-300 bg-white px-3 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-600">
              <Sparkles className="h-3 w-3 text-amber-600" />
              Agent-Native Academic Workspace
            </div>
            <h1 className="mt-5 text-5xl font-black leading-[1.02] tracking-tight md:text-6xl">
              学术研究不该是
              <span className="block text-[#0f766e]">反复跳页的流程</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-zinc-700">
              ScholarAI 把研究过程组织为可执行工作流：你始终知道当前阶段、下一步动作、产出证据与可恢复任务。
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button
                onClick={handleEnter}
                className="inline-flex items-center gap-2 rounded bg-[#0f766e] px-5 py-3 text-sm font-bold uppercase tracking-[0.14em] text-white hover:bg-[#115e59]"
              >
                开始研究任务
                <ArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => navigate("/search")}
                className="rounded border border-zinc-300 bg-white px-5 py-3 text-sm font-bold uppercase tracking-[0.14em] text-zinc-700 hover:bg-zinc-100"
              >
                浏览检索入口
              </button>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45, delay: 0.1 }}
            className="rounded-lg border border-zinc-200 bg-white p-5"
          >
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">Workflow Timeline</div>
            <div className="mt-4 space-y-3">
              {stages.map((stage, index) => (
                <div key={stage} className="flex items-start gap-3 rounded border border-zinc-200 p-3">
                  <div className="mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full border border-zinc-300 text-[10px] font-bold text-zinc-600">
                    {index + 1}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-zinc-900">{stage}</div>
                    <div className="mt-1 text-xs text-zinc-600">状态、动作与产物在同一面板持续可见。</div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </section>

        <section className="mt-16 grid gap-4 md:grid-cols-3">
          {promises.map((item) => (
            <motion.article
              key={item.title}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-120px" }}
              transition={{ duration: 0.35 }}
              className="rounded-lg border border-zinc-200 bg-white p-5"
            >
              <item.icon className="h-5 w-5 text-[#0f766e]" />
              <h2 className="mt-4 text-lg font-bold text-zinc-900">{item.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-zinc-700">{item.description}</p>
            </motion.article>
          ))}
        </section>

        <section className="mt-16 rounded-lg border border-zinc-200 bg-zinc-900 px-6 py-7 text-white">
          <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-400">Core Promise</div>
          <h2 className="mt-3 text-2xl font-bold">在一个工作台里完成计划、执行、确认与恢复</h2>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {[
              "统一 Scope 与 Active Run 语义",
              "统一 Pending / Recoverable 动作处理",
              "统一 Artifacts / Evidence 结果追踪",
              "统一跨页面状态与动作文案",
            ].map((text) => (
              <div key={text} className="flex items-center gap-2 text-sm text-zinc-200">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                {text}
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
