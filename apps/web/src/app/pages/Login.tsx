import { ArrowRight, Fingerprint, Database, Cpu, Activity, ShieldCheck, TerminalSquare, Command } from "lucide-react";
import { motion } from "motion/react";
import { useLocation, useNavigate } from "react-router";
import { useState, useEffect } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import { Badge } from "../components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import * as authApi from "@/services/authApi";
import { navigateToSafeTarget } from "@/lib/navigation";
import {
  ACTIVE_EMBEDDING_MODEL,
  ACTIVE_GENERATION_MODEL,
  ACTIVE_RERANK_MODEL,
  formatEmbeddingModelLabel,
  formatGenerationModelLabel,
} from "@/config/modelRuntime";

const SYSTEM_LOGS_EN = [
  "[SYS] Initializing system environment...",
  "[SYS] Initializing vector database...",
  "[OK] Graph DB connected. Latency: 12ms",
  "[SYS] Binding online embedding and rerank runtime...",
  `[OK] ${formatEmbeddingModelLabel(ACTIVE_EMBEDDING_MODEL)} and ${ACTIVE_RERANK_MODEL} ready`,
  "[SYS] Awaiting user authentication...",
];

const SYSTEM_LOGS_ZH = [
  "[SYS] 正在初始化系统环境...",
  "[SYS] 正在初始化向量数据库...",
  "[OK] 图数据库已连接。延迟: 12ms",
  "[SYS] 正在绑定在线 embedding / rerank 运行时...",
  `[OK] ${formatEmbeddingModelLabel(ACTIVE_EMBEDDING_MODEL)} 与 ${ACTIVE_RERANK_MODEL} 已就绪`,
  "[SYS] 等待用户身份验证...",
];

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { language } = useLanguage();
  const { login, isAuthenticated, loading: authLoading } = useAuth();
  const [logs, setLogs] = useState<string[]>([]);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const isZh = language === "zh";
  const SYSTEM_LOGS = isZh ? SYSTEM_LOGS_ZH : SYSTEM_LOGS_EN;
  const returnTo = typeof location.state?.from === "string" ? location.state.from : null;

  const normalizeAuthError = (rawMessage: string): string => {
    const trimmed = rawMessage.trim();
    if (!isZh) {
      return trimmed;
    }

    const invalidCredentialMessages = new Set([
      "Email or password is incorrect",
      "Invalid credentials",
      "Incorrect email or password",
    ]);

    if (invalidCredentialMessages.has(trimmed)) {
      return "邮箱或密码错误";
    }

    return trimmed;
  };

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      if (navigateToSafeTarget(returnTo, (to) => navigate(to, { replace: true }))) {
        return;
      }
      navigate("/dashboard", { replace: true });
    }
  }, [authLoading, isAuthenticated, navigate, returnTo]);

  const t = {
    os: isZh ? "个人研究工作台" : "AI-Powered Research Workspace",
    vol: "v4.0",
    title1: isZh ? "知识" : "Knowledge",
    title2: isZh ? "引擎." : "Engine.",
    auth: isZh ? "身份验证" : "Authentication",
    authDesc: isZh ? "为研究人员提供可检索、可追溯的论文阅读与分析体验。您的问题、笔记和阅读进度都会保存在个人空间中。" : "ScholarAI Reading System currently runs on Zhipu GLM-4.6V-FlashX with DashScope online embedding and rerank on the main path, providing traceable paper reading and analysis for researchers. All queries are kept strictly confidential, creating your private literature library.",
    index: isZh ? "全局索引" : "Global Index",
    indexDesc: isZh ? "覆盖 ArXiv、Semantic Scholar 和 PubMed 的大规模论文索引，支持检索、导入、阅读和后续问答在同一工作流里衔接。" : "Currently indexing 14.2M papers across ArXiv, Semantic Scholar, and PubMed. System runs on distributed Node architecture with real-time vector synchronization.",
    activeNodes: isZh ? "向量维度" : "Vector Dimensions",
    graphSize: isZh ? "Embedding模型" : "Embedding Model",
    inference: isZh ? "推理引擎" : "Inference",
    vectorDB: isZh ? "向量数据库" : "Vector DB",
    synced: isZh ? "已同步" : "Synced",
    terminal: isZh ? "终端输出" : "Terminal Output",
    idReq: isZh ? (mode === "login" ? "需要身份识别" : "创建新账户") : (mode === "login" ? "Identification Required" : "Create Account"),
    plsAuth: isZh ? (mode === "login" ? "请登录后继续您的研究工作流" : "注册后即可开始整理、阅读和追问论文") : (mode === "login" ? "Please authenticate to continue" : "Register to use ScholarAI Reading System"),
    userId: isZh ? "邮箱地址" : "Researcher ID / Email",
    passkey: isZh ? "登录密码" : "Passkey",
    reset: isZh ? "重置" : "Reset",
    enterCreds: isZh ? "输入您的凭证" : "Enter your credentials",
    enterKey: isZh ? "输入密钥" : "Enter passkey",
    connect: isZh ? (mode === "login" ? "登录并继续" : "创建账户") : (mode === "login" ? "Establish Connection" : "Create Account"),
    sso: isZh ? "单点登录 (SSO)" : "SSO Login",
    requestAccess: isZh ? "申请访问权限" : "Request Access",
    statusText: isZh ? "系统状态：" : "Node: 04 • Status: ",
    active: isZh ? "活跃" : "Active",
    ip: isZh ? " • 连接已加密" : " • IP: Encrypted",
    name: isZh ? "姓名" : "Name",
    enterName: isZh ? "输入您的姓名" : "Enter your name",
    switchToRegister: isZh ? "没有账户？立即注册" : "Don't have an account? Register",
    switchToLogin: isZh ? "已有账户？返回登录" : "Already have an account? Login",
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

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(email, password);
      if (navigateToSafeTarget(returnTo, (to) => navigate(to, { replace: true }))) {
        return;
      }
      navigate("/dashboard");
    } catch (err: any) {
      const errorData = err.response?.data;
      const errorMessage = normalizeAuthError(errorData?.detail?.detail
        || errorData?.error?.detail
        || err.message
        || (isZh ? "登录失败" : "Login failed"));
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await authApi.register(email, password, name);
      await login(email, password);
      if (navigateToSafeTarget(returnTo, (to) => navigate(to, { replace: true }))) {
        return;
      }
      navigate("/dashboard");
    } catch (err: any) {
      const errorData = err.response?.data;
      const errorMessage = errorData?.detail?.detail
        || errorData?.error?.detail
        || err.message
        || (isZh ? "注册失败" : "Registration failed");
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
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
            <h2 className={`font-serif font-black leading-[0.85] tracking-tighter text-foreground ${isZh ? "text-[60px] md:text-[80px] xl:text-[100px] mb-2" : "text-[60px] md:text-[90px] xl:text-[120px]"}`}>
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
              { label: t.activeNodes, value: "1024", icon: Activity },
              { label: t.graphSize, value: formatEmbeddingModelLabel(ACTIVE_EMBEDDING_MODEL), icon: Database },
              { label: t.inference, value: formatGenerationModelLabel(ACTIVE_GENERATION_MODEL), icon: Cpu },
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
          key={`${language}-${mode}`}
          className="w-full max-w-sm flex flex-col gap-12"
        >
          <div className="flex flex-col gap-2">
            <div className="w-12 h-12 bg-primary/10 border border-primary/20 flex items-center justify-center rounded-sm mb-4">
              <Fingerprint className="w-6 h-6 text-primary" />
            </div>
            <h2 className="font-serif text-3xl font-black tracking-tight">{t.idReq}</h2>
            <p className="text-[11px] font-bold tracking-[0.2em] uppercase text-muted-foreground">{t.plsAuth}</p>
          </div>

          <form onSubmit={mode === "login" ? handleLogin : handleRegister} className="flex flex-col gap-8">
            <div className="flex flex-col gap-8 relative group">
              <div className="absolute -left-4 top-0 w-0.5 h-full bg-primary/0 group-focus-within:bg-primary transition-colors duration-500" />
              
              {mode === "register" && (
                <div className="flex flex-col gap-2 group/input">
                  <label htmlFor="register-name" className="text-[9px] font-bold tracking-[0.3em] uppercase text-foreground/70 group-focus-within/input:text-primary transition-colors">
                    {t.name}
                  </label>
                  <input
                    id="register-name"
                    name="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-transparent border-b-2 border-foreground/20 pb-3 pt-1 text-lg font-serif focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground/30 rounded-none"
                    placeholder={t.enterName}
                    required
                  />
                </div>
              )}

              <div className="flex flex-col gap-2 group/input">
                <label htmlFor="auth-email" className="text-[9px] font-bold tracking-[0.3em] uppercase text-foreground/70 group-focus-within/input:text-primary transition-colors">
                  {t.userId}
                </label>
                <input
                  id="auth-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-transparent border-b-2 border-foreground/20 pb-3 pt-1 text-lg font-serif focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground/30 rounded-none"
                  placeholder={t.enterCreds}
                  required
                />
              </div>

              <div className="flex flex-col gap-2 group/input">
                <div className="flex justify-between items-end">
                  <label htmlFor="auth-password" className="text-[9px] font-bold tracking-[0.3em] uppercase text-foreground/70 group-focus-within/input:text-primary transition-colors">
                    {t.passkey}
                  </label>
                  {mode === "login" && (
                    <button
                      type="button"
                      onClick={() => navigate('/forgot-password')}
                      className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-primary transition-colors"
                    >
                      {isZh ? "忘记密码?" : "Forgot Password?"}
                    </button>
                  )}
                </div>
                <input
                  id="auth-password"
                  name="password"
                  type="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-transparent border-b-2 border-foreground/20 pb-3 pt-1 text-lg font-mono tracking-[0.3em] focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground/30 rounded-none"
                  placeholder={t.enterKey}
                  required
                />
              </div>
            </div>

            {error && (
              <div className="text-sm text-red-500 font-medium">
                {error}
              </div>
            )}

            <div className="flex flex-col gap-4 mt-4">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-foreground text-background py-4 flex items-center justify-center gap-3 rounded-sm group hover:bg-primary transition-colors shadow-lg hover:shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span className="text-[10px] font-bold tracking-[0.3em] uppercase">
                  {isLoading ? (isZh ? "连接中..." : "Connecting...") : t.connect}
                </span>
                {!isLoading && <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />}
              </button>
            </div>
          </form>

          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
              setName("");
              setEmail("");
              setPassword("");
            }}
            className="text-[10px] font-bold tracking-[0.2em] uppercase text-primary hover:text-primary/80 transition-colors text-center w-full"
          >
            {mode === "login" ? t.switchToRegister : t.switchToLogin}
          </button>

          <div className="text-[9px] font-mono text-muted-foreground text-center mt-4">
            {t.statusText}<span className="text-green-500">{t.active}</span>{t.ip}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
