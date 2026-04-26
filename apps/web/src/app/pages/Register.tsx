import { ArrowRight, Fingerprint, ShieldCheck, CheckCircle } from "lucide-react";
import { motion } from "motion/react";
import { useNavigate } from "react-router";
import { useState } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import { Badge } from "../components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import * as authApi from "@/services/authApi";

export function Register() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { language } = useLanguage();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const isZh = language === "zh";

  const t = {
    os: isZh ? "研究操作系统" : "Research Operating System",
    vol: isZh ? "第四卷" : "Vol. 4",
    title: isZh ? "创建账户" : "Create Account",
    titleDesc: isZh ? "加入去中心化知识图谱网络" : "Join the Decentralized Knowledge Graph Network",
    auth: isZh ? "身份验证" : "Authentication",
    authDesc: isZh ? "访问权限严格限制为经授权的学术人员" : "Access restricted to authorized academic personnel",
    name: isZh ? "研究员姓名" : "Researcher Name",
    enterName: isZh ? "输入您的姓名" : "Enter your name",
    email: isZh ? "机构邮箱" : "Institutional Email",
    enterEmail: isZh ? "输入您的邮箱" : "Enter your email",
    passkey: isZh ? "访问密钥" : "Access Passkey",
    enterPasskey: isZh ? "创建访问密钥" : "Create your passkey",
    confirmPasskey: isZh ? "确认密钥" : "Confirm Passkey",
    enterConfirm: isZh ? "再次输入密钥" : "Enter passkey again",
    createAccount: isZh ? "创建账户" : "Create Account",
    hasAccount: isZh ? "已有账户？" : "Already have an account?",
    login: isZh ? "登录" : "Login",
    passwordRequirements: isZh ? "密码要求" : "Password Requirements",
    reqLength: isZh ? "至少 8 个字符" : "At least 8 characters",
    reqUpper: isZh ? "至少一个大写字母" : "At least one uppercase letter",
    reqLower: isZh ? "至少一个小写字母" : "At least one lowercase letter",
    reqNumber: isZh ? "至少一个数字" : "At least one number",
    statusText: isZh ? "节点：04 • 状态：" : "Node: 04 • Status: ",
    active: isZh ? "活跃" : "Active",
    ip: isZh ? " • IP: 已加密" : " • IP: Encrypted",
    welcome: isZh ? "欢迎加入" : "Welcome aboard",
    benefits: isZh ? "账户权益" : "Account Benefits",
    benefit1: isZh ? "管理个人论文库" : "Manage personal paper library",
    benefit2: isZh ? "AI 智能问答" : "AI-powered Q&A",
    benefit3: isZh ? "知识图谱可视化" : "Knowledge graph visualization",
    benefit4: isZh ? "多论文对比分析" : "Multi-paper comparison",
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validate passwords match
    if (password !== confirmPassword) {
      setError(isZh ? "两次输入的密码不一致" : "Passwords do not match");
      return;
    }

    // Validate password requirements
    const passwordRegex = /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$/;
    if (!passwordRegex.test(password)) {
      setError(isZh ? "密码不符合要求" : "Password does not meet requirements");
      return;
    }

    setIsLoading(true);

    try {
      // Call register API
      await authApi.register(email, password, name);

      // Auto-login after successful registration
      await login(email, password);
      navigate("/dashboard");
    } catch (err: any) {
      const errorMessage = err.message || (isZh ? "注册失败" : "Registration failed");
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const passwordRequirements = [
    { label: t.reqLength, met: password.length >= 8 },
    { label: t.reqUpper, met: /[A-Z]/.test(password) },
    { label: t.reqLower, met: /[a-z]/.test(password) },
    { label: t.reqNumber, met: /[0-9]/.test(password) },
  ];

  return (
    <div className="h-screen w-full bg-background text-foreground flex flex-col md:flex-row font-sans selection:bg-primary selection:text-primary-foreground relative overflow-hidden">
      {/* Global Noise Overlay */}
      <svg className="absolute inset-0 w-full h-full opacity-[0.03] pointer-events-none z-50 mix-blend-multiply">
        <filter id="noiseFilter">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" />
        </filter>
        <rect width="100%" height="100%" filter="url(#noiseFilter)" />
      </svg>

      {/* Left Column: Benefits */}
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

        {/* Middle: Title & Benefits */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          key={language}
          className="flex flex-col gap-8 max-w-xl my-12 md:my-0"
        >
          <div className="flex flex-col">
            <h2 className="font-serif text-[50px] md:text-[60px] xl:text-[70px] font-black leading-[0.9] tracking-tighter text-foreground mb-4">
              {t.title}
            </h2>
            <p className="text-[11px] font-bold tracking-[0.2em] uppercase text-muted-foreground">
              {t.titleDesc}
            </p>
          </div>
          
          <div className="flex flex-col gap-4 pt-8 border-t border-border/50">
            <span className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground flex items-center gap-1.5">
              <ShieldCheck className="w-3 h-3 text-primary" /> {t.benefits}
            </span>
            {[
              { icon: "📚", text: t.benefit1 },
              { icon: "🤖", text: t.benefit2 },
              { icon: "🕸️", text: t.benefit3 },
              { icon: "📊", text: t.benefit4 },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 text-[11px] font-serif leading-[1.6] text-foreground/80">
                <span className="text-lg">{item.icon}</span>
                <span>{item.text}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Bottom: Status */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex flex-col gap-6"
        >
          <div className="text-[9px] font-mono text-muted-foreground">
            {t.statusText}<span className="text-green-500">{t.active}</span>{t.ip}
          </div>
        </motion.div>
      </div>

      {/* Right Column: Register Form */}
      <div className="w-full md:w-[480px] lg:w-[540px] flex flex-col justify-center items-center p-8 lg:p-16 bg-background relative z-10 shadow-2xl">
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          key={language}
          className="w-full max-w-sm flex flex-col gap-8"
        >
          <div className="flex flex-col gap-2">
            <div className="w-12 h-12 bg-primary/10 border border-primary/20 flex items-center justify-center rounded-sm mb-4">
              <Fingerprint className="w-6 h-6 text-primary" />
            </div>
            <h2 className="font-serif text-2xl font-black tracking-tight">{t.welcome}</h2>
          </div>

          <form onSubmit={handleRegister} className="flex flex-col gap-6">
            <div className="flex flex-col gap-6 relative group">
              <div className="absolute -left-4 top-0 w-0.5 h-full bg-primary/0 group-focus-within:bg-primary transition-colors duration-500" />
              
              {/* Name Field */}
              <div className="flex flex-col gap-2 group/input">
                <label className="text-[9px] font-bold tracking-[0.3em] uppercase text-foreground/70 group-focus-within/input:text-primary transition-colors">
                  {t.name}
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-transparent border-b-2 border-foreground/20 pb-3 pt-1 text-lg font-serif focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground/30 rounded-none"
                  placeholder={t.enterName}
                  required
                  autoComplete="name"
                />
              </div>

              {/* Email Field */}
              <div className="flex flex-col gap-2 group/input">
                <label className="text-[9px] font-bold tracking-[0.3em] uppercase text-foreground/70 group-focus-within/input:text-primary transition-colors">
                  {t.email}
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-transparent border-b-2 border-foreground/20 pb-3 pt-1 text-lg font-serif focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground/30 rounded-none"
                  placeholder={t.enterEmail}
                  required
                  autoComplete="email"
                />
              </div>

              {/* Password Field */}
              <div className="flex flex-col gap-2 group/input">
                <label className="text-[9px] font-bold tracking-[0.3em] uppercase text-foreground/70 group-focus-within/input:text-primary transition-colors">
                  {t.passkey}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-transparent border-b-2 border-foreground/20 pb-3 pt-1 text-lg font-mono tracking-[0.3em] focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground/30 rounded-none"
                  placeholder={t.enterPasskey}
                  required
                  autoComplete="new-password"
                />
              </div>

              {/* Password Requirements */}
              {password && (
                <div className="flex flex-col gap-1.5 mt-2">
                  <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground">
                    {t.passwordRequirements}
                  </span>
                  {passwordRequirements.map((req, i) => (
                    <div key={i} className="flex items-center gap-2 text-[8px] font-mono">
                      <CheckCircle className={`w-2.5 h-2.5 ${req.met ? "text-green-500" : "text-muted-foreground/30"}`} />
                      <span className={req.met ? "text-green-500" : "text-muted-foreground/50"}>{req.label}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Confirm Password Field */}
              <div className="flex flex-col gap-2 group/input">
                <label className="text-[9px] font-bold tracking-[0.3em] uppercase text-foreground/70 group-focus-within/input:text-primary transition-colors">
                  {t.confirmPasskey}
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full bg-transparent border-b-2 border-foreground/20 pb-3 pt-1 text-lg font-mono tracking-[0.3em] focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground/30 rounded-none"
                  placeholder={t.enterConfirm}
                  required
                  autoComplete="new-password"
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
                  {isLoading ? (isZh ? "创建中..." : "Creating...") : t.createAccount}
                </span>
                {!isLoading && <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />}
              </button>
              
              <div className="text-center text-[9px] font-mono text-muted-foreground mt-2">
                {t.hasAccount}
                <button
                  type="button"
                  onClick={() => navigate("/login")}
                  className="ml-2 text-primary hover:underline"
                >
                  {t.login}
                </button>
              </div>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
