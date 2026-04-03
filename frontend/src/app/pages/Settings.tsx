import { Camera, Key, Lock, Save, User, RefreshCw, TerminalSquare, Cpu, Box, HardDrive, Wifi, Activity, Shield, Globe } from "lucide-react";
import { motion } from "motion/react";
import { clsx } from "clsx";
import { useState } from "react";
import { useLanguage } from "../contexts/LanguageContext";

const LOGS = [
  { time: "10:42:01", level: "INFO", message: "User session authenticated." },
  { time: "10:42:03", level: "WARN", message: "OpenAI API rate limit approaching (85%)." },
  { time: "10:45:12", level: "INFO", message: "Ingestion batch B-842 completed." },
  { time: "10:46:00", level: "ERROR", message: "Failed to parse 1706.03762.pdf (Timeout)." },
  { time: "10:50:33", level: "INFO", message: "Settings configuration saved." },
];

export function Settings() {
  const [activeSection, setActiveSection] = useState("profile");
  const { language, setLanguage } = useLanguage();

  const isZh = language === "zh";

  const t = {
    system: isZh ? "系统" : "System",
    preferences: isZh ? "偏好设置" : "Preferences",
    profileData: isZh ? "个人资料" : "Profile Data",
    security: isZh ? "安全设置" : "Security",
    apiIntegration: isZh ? "API 集成" : "API Integrations",
    computeNodes: isZh ? "计算节点" : "Compute Nodes",
    dataStorage: isZh ? "数据存储" : "Data Storage",
    localization: isZh ? "语言设置" : "Localization",
    configVer: isZh ? "配置 v2.4.1" : "Configuration v2.4.1",
    commit: isZh ? "提交更改" : "Commit",
    langModels: isZh ? "语言模型" : "Language Models",
    primaryEngine: isZh ? "主推理引擎" : "Primary Inference Engine",
    connected: isZh ? "已连接" : "Connected",
    provider: isZh ? "供应商" : "Provider",
    modelArch: isZh ? "模型架构" : "Model Architecture",
    apiSecret: isZh ? "API 密钥" : "API Secret Key",
    rotateKey: isZh ? "轮换密钥" : "Rotate Key",
    test: isZh ? "测试" : "Test",
    advParams: isZh ? "高级参数" : "Advanced Parameters",
    genConstraints: isZh ? "生成约束" : "Generation Constraints",
    temp: isZh ? "随机性 (Temperature)" : "Temperature",
    maxTokens: isZh ? "最大 Token" : "Max Tokens",
    sysPrompt: isZh ? "系统提示词" : "System Prompt / Instructions",
    auth: isZh ? "身份验证" : "Authentication",
    level4: isZh ? "需要 Level 4 权限" : "Level 4 Clearance required",
    curPasskey: isZh ? "当前密钥" : "Current Passkey",
    newPasskey: isZh ? "新密钥" : "New Passkey",
    enterNewKey: isZh ? "输入新密钥" : "ENTER NEW KEY",
    diagnostics: isZh ? "系统诊断" : "Diagnostics",
    storageUsage: isZh ? "存储使用量" : "Storage Usage",
    vectorDB: isZh ? "向量数据库" : "Vector DB",
    blobStorage: isZh ? "文件存储 (PDFs)" : "Blob Storage (PDFs)",
    sysStream: isZh ? "系统流" : "System Stream",
    selectToView: isZh ? "选择 API 集成、安全或语言\n以查看配置详情。" : "Select API Integrations, Security or Localization\nto view configurations."
  };

  return (
    <div className="h-full flex font-sans bg-background text-foreground relative selection:bg-primary selection:text-primary-foreground">
      {/* Left Column: Navigation & Profile Summary */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[220px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center">
          <h2 className="font-serif text-xl font-black tracking-tight leading-none mb-1">{t.system}</h2>
          <Box className="w-4 h-4 text-primary" />
        </div>
        
        <div className="flex-1 overflow-y-auto py-5 flex flex-col gap-6 px-4">
          
          <div className="flex flex-col items-center gap-3 pb-6 border-b border-border/50">
            <div className="w-20 h-20 rounded-full border-2 border-background overflow-hidden relative cursor-pointer shadow-md group">
              <img 
                src="https://images.unsplash.com/photo-1631885628966-a14af9faaa9b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx3b21hbiUyMHByb2ZpbGUlMjBwb3J0cmFpdHxlbnwxfHx8fDE3NzUxMDc0OTl8MA&ixlib=rb-4.1.0&q=80&w=1080" 
                alt="Avatar" 
                className="w-full h-full object-cover filter grayscale group-hover:grayscale-0 transition-all duration-700"
              />
              <div className="absolute inset-0 bg-primary/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-sm">
                <Camera className="w-4 h-4 text-primary-foreground" />
              </div>
            </div>
            <div className="text-center">
              <div className="font-serif text-lg font-black leading-tight">Dr. E. Vance</div>
              <div className="text-[9px] font-mono tracking-[0.2em] text-muted-foreground mt-1">ID: 994-XQ-12</div>
            </div>
          </div>

          <div>
            <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{t.preferences}</div>
            <div className="flex flex-col gap-1">
              {[
                { id: "profile", icon: User, label: t.profileData },
                { id: "localization", icon: Globe, label: t.localization },
                { id: "security", icon: Lock, label: t.security },
                { id: "api", icon: Key, label: t.apiIntegration },
                { id: "compute", icon: Cpu, label: t.computeNodes },
                { id: "storage", icon: HardDrive, label: t.dataStorage },
              ].map((item) => (
                <button 
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={clsx(
                    "flex items-center gap-2.5 px-3 py-2 rounded-sm transition-colors group w-full text-left",
                    activeSection === item.id ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" : "hover:bg-card border border-transparent hover:border-border/50 text-foreground/80 hover:text-primary"
                  )}
                >
                  <item.icon className="w-3.5 h-3.5" />
                  <span className="text-[10px] font-bold uppercase tracking-widest flex-1">{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Middle Column: Configuration Forms (Dense) */}
      <div className="flex-1 flex flex-col h-full bg-background min-w-[500px] border-r border-border/50 relative">
        <div className="px-6 py-4 border-b border-border/50 bg-background/90 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center shadow-sm">
          <div className="flex items-baseline gap-3">
            <h2 className="font-serif text-2xl font-black tracking-tight capitalize">
              {activeSection === "api" ? t.apiIntegration : 
               activeSection === "security" ? t.security : 
               activeSection === "localization" ? t.localization :
               activeSection.replace("-", " ")}
            </h2>
            <span className="text-[9px] font-mono tracking-[0.2em] text-muted-foreground uppercase">{t.configVer}</span>
          </div>
          <button className="text-[9px] font-bold uppercase tracking-[0.2em] bg-primary text-primary-foreground px-4 py-1.5 rounded-sm hover:bg-secondary transition-colors shadow-sm flex items-center gap-1.5">
            <Save className="w-3 h-3" /> {t.commit}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-8 lg:p-12 flex flex-col gap-10 bg-muted/5">
          
          {/* Localization Section */}
          {activeSection === "localization" && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col gap-8 max-w-2xl"
            >
              <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col">
                <div className="p-5 border-b border-border/50 flex justify-between items-center bg-muted/20">
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
                      <Globe className="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em]">Language Settings</h3>
                      <p className="text-[9px] font-mono text-muted-foreground mt-0.5">Interface Translation</p>
                    </div>
                  </div>
                </div>
                
                <div className="p-6 flex flex-col gap-5">
                  <div className="flex flex-col gap-4">
                    <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">Display Language</label>
                    <div className="flex gap-4">
                      <button
                        onClick={() => setLanguage("en")}
                        className={clsx(
                          "flex-1 border p-4 rounded-sm transition-colors text-center font-bold tracking-widest text-[11px] uppercase",
                          language === "en" ? "border-primary bg-primary/10 text-primary shadow-sm" : "border-border/50 hover:border-primary/50 text-foreground/70"
                        )}
                      >
                        English
                      </button>
                      <button
                        onClick={() => setLanguage("zh")}
                        className={clsx(
                          "flex-1 border p-4 rounded-sm transition-colors text-center font-bold tracking-widest text-[11px] uppercase",
                          language === "zh" ? "border-primary bg-primary/10 text-primary shadow-sm" : "border-border/50 hover:border-primary/50 text-foreground/70"
                        )}
                      >
                        中文 (Chinese)
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeSection === "api" && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col gap-8 max-w-3xl"
            >
              {/* Primary AI Provider */}
              <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col relative overflow-hidden group">
                <div className="absolute top-0 left-0 w-1 h-full bg-primary/20 group-hover:bg-primary transition-colors duration-500" />
                <div className="p-5 border-b border-border/50 flex justify-between items-center bg-muted/20">
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
                      <Key className="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em]">{t.langModels}</h3>
                      <p className="text-[9px] font-mono text-muted-foreground mt-0.5">{t.primaryEngine}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 bg-green-500/10 text-green-600 px-2 py-0.5 rounded-sm border border-green-500/20">
                    <Wifi className="w-2.5 h-2.5" />
                    <span className="text-[8px] font-bold uppercase tracking-widest">{t.connected}</span>
                  </div>
                </div>

                <div className="p-6 flex flex-col gap-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="flex flex-col gap-2">
                      <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">{t.provider}</label>
                      <select className="w-full bg-background border border-border/50 rounded-sm px-3 py-2 text-[11px] font-bold uppercase tracking-widest focus:outline-none focus:border-primary transition-colors appearance-none shadow-sm cursor-pointer">
                        <option>OpenAI (Default)</option>
                        <option>Anthropic</option>
                        <option>Google DeepMind</option>
                        <option>Local / Ollama</option>
                      </select>
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">{t.modelArch}</label>
                      <select className="w-full bg-background border border-border/50 rounded-sm px-3 py-2 text-[11px] font-bold uppercase tracking-widest focus:outline-none focus:border-primary transition-colors appearance-none shadow-sm cursor-pointer">
                        <option>GPT-4 Turbo</option>
                        <option>GPT-4o</option>
                        <option>GPT-3.5 Turbo</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70 flex justify-between">
                      <span>{t.apiSecret}</span>
                      <button className="text-primary hover:text-secondary transition-colors underline underline-offset-2">{t.rotateKey}</button>
                    </label>
                    <div className="flex gap-3">
                      <input 
                        type="password" 
                        defaultValue="sk-proj-98f7a6sd5f87asdf87"
                        className="flex-1 bg-background border border-border/50 rounded-sm px-4 py-2.5 text-[12px] font-mono tracking-[0.2em] focus:outline-none focus:border-primary transition-colors shadow-sm placeholder:text-muted-foreground/50"
                      />
                      <button className="bg-muted border border-border/50 text-foreground px-4 py-2.5 rounded-sm text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-background transition-colors flex items-center gap-1.5 shadow-sm">
                        <RefreshCw className="w-3 h-3" /> {t.test}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Advanced Parameters */}
              <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col">
                <div className="p-5 border-b border-border/50 flex justify-between items-center bg-muted/20">
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
                      <Cpu className="w-3.5 h-3.5 text-foreground/70" />
                    </div>
                    <div>
                      <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em]">{t.advParams}</h3>
                      <p className="text-[9px] font-mono text-muted-foreground mt-0.5">{t.genConstraints}</p>
                    </div>
                  </div>
                </div>

                <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
                  <div className="flex flex-col gap-4">
                    <div className="flex justify-between items-end">
                      <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">{t.temp}</label>
                      <span className="text-[10px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded-sm border border-primary/20">0.7</span>
                    </div>
                    <input type="range" min="0" max="100" defaultValue="70" className="w-full accent-primary h-1.5 bg-muted rounded-full appearance-none [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary cursor-pointer" />
                  </div>
                  
                  <div className="flex flex-col gap-4">
                    <div className="flex justify-between items-end">
                      <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">{t.maxTokens}</label>
                      <span className="text-[10px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded-sm border border-primary/20">4096</span>
                    </div>
                    <input type="range" min="0" max="100" defaultValue="50" className="w-full accent-primary h-1.5 bg-muted rounded-full appearance-none [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary cursor-pointer" />
                  </div>
                  
                  <div className="flex flex-col gap-4 md:col-span-2">
                    <div className="flex justify-between items-end">
                      <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">{t.sysPrompt}</label>
                    </div>
                    <textarea 
                      defaultValue={isZh ? "你是一名专业的学术研究员。请严格根据论文内容进行分析，提取实证结果和理论框架，不要产生幻觉。重点关注因果推理。" : "You are an expert academic researcher. Analyze papers strictly based on their content, extracting empirical results and theoretical frameworks without hallucinating details. Emphasize causal reasoning."}
                      className="w-full bg-background border border-border/50 rounded-sm p-4 text-[11px] font-mono leading-[1.6] focus:outline-none focus:border-primary transition-colors shadow-sm min-h-[100px] resize-y"
                    />
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          
          {/* Mock Security Section */}
          {activeSection === "security" && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col gap-8 max-w-2xl"
            >
              <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col">
                <div className="p-5 border-b border-border/50 flex justify-between items-center bg-muted/20">
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
                      <Shield className="w-3.5 h-3.5 text-destructive" />
                    </div>
                    <div>
                      <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em]">{t.auth}</h3>
                      <p className="text-[9px] font-mono text-muted-foreground mt-0.5">{t.level4}</p>
                    </div>
                  </div>
                </div>
                
                <div className="p-6 flex flex-col gap-5">
                  <div className="flex flex-col gap-2">
                    <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">{t.curPasskey}</label>
                    <input 
                      type="password" 
                      defaultValue="********"
                      className="w-full bg-background border-b-2 border-border/50 rounded-t-sm px-3 py-3 text-[14px] font-mono tracking-[0.3em] focus:outline-none focus:border-primary transition-colors bg-transparent"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">{t.newPasskey}</label>
                    <input 
                      type="password" 
                      placeholder={t.enterNewKey}
                      className="w-full bg-background border-b-2 border-border/50 rounded-t-sm px-3 py-3 text-[14px] font-mono tracking-[0.3em] focus:outline-none focus:border-primary transition-colors bg-transparent placeholder:text-muted-foreground/30"
                    />
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeSection !== "api" && activeSection !== "security" && activeSection !== "localization" && (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest text-center whitespace-pre-line">
                <Activity className="w-4 h-4 mx-auto mb-2 text-primary/50" />
                {t.selectToView}
              </p>
            </div>
          )}

        </div>
      </div>

      {/* Right Column: Console / Environment Details */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[260px] flex flex-col h-full bg-card flex-shrink-0 relative border-l border-border/50"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TerminalSquare className="w-4 h-4 text-primary" />
            <h2 className="font-serif text-lg font-bold tracking-tight">{t.diagnostics}</h2>
          </div>
        </div>

        <div className="flex-1 flex flex-col min-h-0 bg-muted/10">
          
          <div className="p-5 border-b border-border/50">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground mb-3 flex items-center gap-1.5">
              <HardDrive className="w-3 h-3" /> {t.storageUsage}
            </h3>
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-end">
                <span className="text-[9px] font-bold uppercase tracking-widest text-foreground">{t.vectorDB}</span>
                <span className="text-[9px] font-mono text-primary">1.2 GB / 5 GB</span>
              </div>
              <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-primary" style={{ width: "24%" }} />
              </div>
              
              <div className="flex justify-between items-end mt-3">
                <span className="text-[9px] font-bold uppercase tracking-widest text-foreground">{t.blobStorage}</span>
                <span className="text-[9px] font-mono text-primary">14.5 GB / 50 GB</span>
              </div>
              <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-primary" style={{ width: "29%" }} />
              </div>
            </div>
          </div>

          <div className="flex-1 flex flex-col p-4 bg-[#1e1e1e] text-[#a9b7c6] overflow-hidden">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-[#6a8759] mb-3 pb-2 border-b border-[#3c3f41]">{t.sysStream}</h3>
            
            <div className="flex-1 overflow-y-auto flex flex-col gap-2 font-mono text-[9px] leading-[1.4] tracking-wide">
              {LOGS.map((log, i) => (
                <div key={i} className="flex gap-2 items-start">
                  <span className="text-[#5c6370] shrink-0">[{log.time}]</span>
                  <span className={clsx(
                    "shrink-0",
                    log.level === "INFO" ? "text-[#629755]" :
                    log.level === "WARN" ? "text-[#cc7832]" :
                    log.level === "ERROR" ? "text-[#cc2828]" : ""
                  )}>{log.level}</span>
                  <span className="break-all">{log.message}</span>
                </div>
              ))}
              <div className="flex gap-2 items-start mt-1">
                <span className="text-[#5c6370]">[{new Date().toLocaleTimeString('en-US', { hour12: false })}]</span>
                <span className="text-[#cc7832] w-2 h-3 bg-[#cc7832] animate-pulse shrink-0" />
              </div>
            </div>
          </div>

        </div>
      </motion.div>
    </div>
  );
}
