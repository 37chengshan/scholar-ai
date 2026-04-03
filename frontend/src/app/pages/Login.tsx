import { ArrowRight, Fingerprint, Database, Cpu, Activity, ShieldCheck, TerminalSquare, Command } from "lucide-react";
import { motion } from "motion/react";
import { useNavigate } from "react-router";
import { clsx } from "clsx";
import { useState, useEffect } from "react";
import { useLanguage } from "../contexts/LanguageContext";

const SYSTEM_LOGS_EN = [
  "[SYS] Initializing Node 04 environment...",
  "[SYS] Connecting to decentralized knowledge graph...",
  "[OK] Graph DB connected. Latency: 12ms",
  "[SYS] Loading local embedding models...",
  "[OK] text-embedding-3-small loaded into VRAM",
  "[SYS] Awaiting user authentication...",
];

const SYSTEM_LOGS_ZH = [
  "[SYS] 正在初始化 Node 04 环境...",
  "[SYS] 正在连接至去中心化知识图谱...",
  "[OK] 图数据库已连接。延迟: 12ms",
  "[SYS] 正在加载本地嵌入模型...",
  "[OK] text-embedding-3-small 已载入显存",
  "[SYS] 等待用户身份验证...",
];

export function Login() {
  const navigate = useNavigate();
  const { language } = useLanguage();
  const [logs, setLogs] = useState<string[]>([]);
  
  const isZh = language === "zh";
  const SYSTEM_LOGS = isZh ? SYSTEM_LOGS_ZH : SYSTEM_LOGS_EN;

  const t = {
    os: isZh ? "研究操作系统" : "Research Operating System",
    vol: isZh ? "第四卷" : "Vol. 4",
    title1: isZh ? "知识" : "Knowledge",
    title2: isZh ? "引擎." : "Engine.",
    auth: isZh ? "身份验证" : "Authentication",
    authDesc: isZh ? "去中心化知识图谱与语言模型推理引擎的访问权限严格限制为经授权的学术人员。所有查询及嵌入生成将被记录。" : "Access to the decentralized knowledge graph and language model inference engine is strictly restricted to authorized academic personnel. All queries and embedding generations are logged.",
    index: isZh ? "全局索引" : "Global Index",
    indexDesc: isZh ? "目前已为 ArXiv、Semantic Scholar 和 PubMed 中的 1420 万篇论文建立索引。系统运行于具备实时向量同步功能的分布式节点架构之上。" : "Currently indexing 14.2M papers across ArXiv, Semantic Scholar, and PubMed. System runs on distributed Node architecture with real-time vector synchronization.",
    activeNodes: isZh ? "活跃节点" : "Active Nodes",
    graphSize: isZh ? "图谱大小" : "Graph Size",
    inference: isZh ? "推理引擎" : "Inference",
    vectorDB: isZh ? "向量数据库" : "Vector DB",
    synced: isZh ? "已同步" : "Synced",
    terminal: isZh ? "终端输出" : "Terminal Output",
    idReq: isZh ? "需要身份识别" : "Identification Required",
    plsAuth: isZh ? "请进行身份验证以继续" : "Please authenticate to continue",
    userId: isZh ? "研究员 ID / 邮箱" : "Researcher ID / Email",
    passkey: isZh ? "访问密钥" : "Passkey",
    reset: isZh ? "重置" : "Reset",
    enterCreds: isZh ? "输入您的凭证" : "Enter your credentials",
    enterKey: isZh ? "输入密钥" : "Enter passkey",
    connect: isZh ? "建立连接" : "Establish Connection",
    sso: isZh ? "单点登录 (SSO)" : "SSO Login",
    requestAccess: isZh ? "申请访问权限" : "Request Access",
    statusText: isZh ? "节点: 04 • 状态: " : "Node: 04 • Status: ",
    active: isZh ? "活跃" : "Active",
    ip: isZh ? " • IP: 已加密" : " • IP: Encrypted"
  };

  // Simulate streaming logs for high-density tech feel
  useEffect(() => {
    let currentIndex = 0;
    setLogs([]);
    const interval = setInterval(() => {
      if (currentIndex < SYSTEM_LOGS.length) {
        setLogs(prev => [...prev, SYSTEM_LOGS[currentIndex]]);
        currentIndex++;
      } else {
        clearInterval(interval);
      }
    }, 400);
    return () => clearInterval(interval);
  }, [language]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    navigate("/");
  };

  return (
    <div className="h-screen w-full bg-background text-foreground flex flex-col md:flex-row font-sans selection:bg-primary selection:text-primary-foreground relative overflow-hidden">
      {/* Global Noise Overlay */}
      <svg className="absolute inset-0 w-full h-full opacity-[0.03] pointer-events-none z-50 mix-blend-multiply">
        <filter id="noiseFilter">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" />
        </filter>
        <rect width="100%" height="100%" filter="url(#noiseFilter)" />
      </svg>

      {/* Left Column: Editorial / System Status (High Density) */}
      <div className="flex-1 flex flex-col justify-between p-8 lg:p-16 border-r border-border/50 relative bg-muted/5 z-10">
        
        {/* Top: Logo & Volume */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex justify-between items-start"
        >
          <div className="flex flex-col gap-1">
            <h1 className="font-serif text-3xl font-black tracking-tighter leading-none">ScholarAI</h1>
            <p className="text-[10px] font-bold tracking-[0.3em] uppercase text-muted-foreground">{t.os}</p>
          </div>
          <div className="text-[9px] font-bold tracking-[0.3em] uppercase bg-primary text-primary-foreground px-3 py-1.5 rounded-sm shadow-sm">
            {t.vol}
          </div>
        </motion.div>

        {/* Middle: Editorial Abstract Typography */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          key={language}
          className="flex flex-col gap-8 max-w-xl my-12 md:my-0"
        >
          <div className="flex flex-col">
            <h2 className={clsx(
              "font-serif font-black leading-[0.85] tracking-tighter text-foreground",
              isZh ? "text-[60px] md:text-[80px] xl:text-[100px] mb-2" : "text-[60px] md:text-[90px] xl:text-[120px]"
            )}>
              {t.title1}<br />
              <span className="text-primary/90 italic font-medium tracking-tight">{t.title2}</span>
            </h2>
          </div>
          
          <div className="grid grid-cols-2 gap-8 pt-8 border-t border-border/50">
            <div className="flex flex-col gap-2">
              <span className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground flex items-center gap-1.5">
                <ShieldCheck className="w-3 h-3 text-primary" /> {t.auth}
              </span>
              <p className="font-serif text-[11px] leading-[1.6] text-foreground/80 text-justify">
                {t.authDesc}
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground flex items-center gap-1.5">
                <Database className="w-3 h-3 text-primary" /> {t.index}
              </span>
              <p className="font-serif text-[11px] leading-[1.6] text-foreground/80 text-justify">
                {t.indexDesc}
              </p>
            </div>
          </div>
        </motion.div>

        {/* Bottom: Technical Diagnostics Panel */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex flex-col gap-6"
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 border-b border-border/50 pb-6">
            {[
              { label: t.activeNodes, value: "1,024", icon: Activity },
              { label: t.graphSize, value: "4.2 TB", icon: Database },
              { label: t.inference, value: "GPT-4 Turbo", icon: Cpu },
              { label: t.vectorDB, value: t.synced, icon: Command }
            ].map((stat, i) => (
              <div key={i} className="flex flex-col gap-1.5">
                <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground flex items-center gap-1 whitespace-nowrap">
                  <stat.icon className="w-2.5 h-2.5" /> {stat.label}
                </span>
                <span className="font-mono text-xs font-bold">{stat.value}</span>
              </div>
            ))}
          </div>

          <div className="bg-[#1e1e1e] p-4 rounded-sm border border-[#3c3f41] h-32 overflow-hidden flex flex-col font-mono text-[9px] leading-[1.6] tracking-wide shadow-inner">
            <div className="text-[#6a8759] uppercase tracking-widest border-b border-[#3c3f41] pb-1.5 mb-2 flex justify-between items-center">
              <span>{t.terminal}</span>
              <TerminalSquare className="w-3 h-3" />
            </div>
            <div className="flex flex-col gap-1 flex-1 overflow-y-auto">
              {logs.map((log, i) => (
                <div key={i} className="text-[#a9b7c6] flex gap-2">
                  <span className="text-[#5c6370] shrink-0">[{new Date().toISOString().split('T')[1].slice(0,8)}]</span>
                  <span>{log}</span>
                </div>
              ))}
              <div className="flex gap-2 items-center mt-1">
                <span className="text-[#5c6370]">[{new Date().toISOString().split('T')[1].slice(0,8)}]</span>
                <span className="w-1.5 h-2.5 bg-[#cc7832] animate-pulse" />
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Right Column: Login Form */}
      <div className="w-full md:w-[480px] lg:w-[540px] flex flex-col justify-center items-center p-8 lg:p-16 bg-background relative z-10 shadow-2xl">
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          key={language}
          className="w-full max-w-sm flex flex-col gap-12"
        >
          <div className="flex flex-col gap-2">
            <div className="w-12 h-12 bg-primary/10 border border-primary/20 flex items-center justify-center rounded-sm mb-4">
              <Fingerprint className="w-6 h-6 text-primary" />
            </div>
            <h2 className="font-serif text-3xl font-black tracking-tight">{t.idReq}</h2>
            <p className="text-[11px] font-bold tracking-[0.2em] uppercase text-muted-foreground">{t.plsAuth}</p>
          </div>

          <form onSubmit={handleLogin} className="flex flex-col gap-8">
            <div className="flex flex-col gap-8 relative group">
              <div className="absolute -left-4 top-0 w-0.5 h-full bg-primary/0 group-focus-within:bg-primary transition-colors duration-500" />
              
              <div className="flex flex-col gap-2 group/input">
                <label className="text-[9px] font-bold tracking-[0.3em] uppercase text-foreground/70 group-focus-within/input:text-primary transition-colors">
                  {t.userId}
                </label>
                <input 
                  type="text" 
                  defaultValue="vance.e@institute.edu"
                  className="w-full bg-transparent border-b-2 border-foreground/20 pb-3 pt-1 text-lg font-serif focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground/30 rounded-none"
                  placeholder={t.enterCreds}
                />
              </div>

              <div className="flex flex-col gap-2 group/input">
                <div className="flex justify-between items-end">
                  <label className="text-[9px] font-bold tracking-[0.3em] uppercase text-foreground/70 group-focus-within/input:text-primary transition-colors">
                    {t.passkey}
                  </label>
                  <a href="#" className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-primary transition-colors">
                    {t.reset}
                  </a>
                </div>
                <input 
                  type="password" 
                  defaultValue="**********"
                  className="w-full bg-transparent border-b-2 border-foreground/20 pb-3 pt-1 text-lg font-mono tracking-[0.3em] focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground/30 rounded-none"
                  placeholder={t.enterKey}
                />
              </div>
            </div>

            <div className="flex flex-col gap-4 mt-4">
              <button 
                type="submit" 
                className="w-full bg-foreground text-background py-4 flex items-center justify-center gap-3 rounded-sm group hover:bg-primary transition-colors shadow-lg hover:shadow-primary/20"
              >
                <span className="text-[10px] font-bold tracking-[0.3em] uppercase">{t.connect}</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </button>
              
              <div className="grid grid-cols-2 gap-4">
                <button type="button" className="w-full bg-muted/50 border border-border/50 text-foreground py-3 flex items-center justify-center gap-2 rounded-sm hover:bg-muted transition-colors">
                  <span className="text-[9px] font-bold tracking-[0.2em] uppercase">{t.sso}</span>
                </button>
                <button type="button" className="w-full bg-muted/50 border border-border/50 text-foreground py-3 flex items-center justify-center gap-2 rounded-sm hover:bg-muted transition-colors">
                  <span className="text-[9px] font-bold tracking-[0.2em] uppercase">{t.requestAccess}</span>
                </button>
              </div>
            </div>
          </form>

          <div className="text-[9px] font-mono text-muted-foreground text-center mt-4">
            {t.statusText}<span className="text-green-500">{t.active}</span>{t.ip}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
