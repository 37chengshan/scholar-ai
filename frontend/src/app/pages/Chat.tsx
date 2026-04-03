import { Plus, Search, ArrowUp, ImageIcon, Code, Mic, Cpu, AlignLeft, RefreshCw, Send, Bot, Check, AlertCircle, Copy, ThumbsUp, ThumbsDown } from "lucide-react";
import { clsx } from "clsx";
import { motion } from "motion/react";
import { useState } from "react";
import { useLanguage } from "../contexts/LanguageContext";

export function Chat() {
  const [input, setInput] = useState("");
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    terminal: isZh ? "终端对话" : "Terminal",
    sessions: isZh ? "会话列表" : "Sessions",
    search: isZh ? "搜索..." : "Search...",
    history: isZh ? "历史记录" : "History",
    chatTitles: isZh ? [
      "模拟时钟 React 应用",
      "极简设计系统",
      "Figma 变量规划",
      "OKLCH 颜色算法",
      "组件命名建议"
    ] : [
      "Analog Clock React app",
      "Simple Design System",
      "Figma variable planning",
      "OKCLH token algorithm",
      "Component naming advice"
    ],
    dates: isZh ? ["2分钟前", "1小时前", "5小时前", "昨天", "5月12日"] : ["2m ago", "1h ago", "5h ago", "Yesterday", "May 12"],
    context: isZh ? "上下文" : "Context",
    userMessage: isZh ? "嗨 Flippy！帮我写一个用来构建模拟时钟的脚本。" : "Hey Flippy! Write me a script for building an Analog Clock.",
    botResponse: isZh ? "没问题。这是你的模拟时钟项目的 TypeScript 代码块。它使用 React 构建，并以英国伦敦的本地时间为标准。如果您想对代码进行任何完善，请告诉我。" : "Sure. Here is a TypeScript code block for your Analog Clock project. It is built using React, and uses the local time for London, England as standard. Let me know if you would like to make any refinements to the code.",
    copy: isZh ? "复制" : "Copy",
    good: isZh ? "很好" : "Good",
    bad: isZh ? "不好" : "Bad",
    retry: isZh ? "重试" : "Retry",
    addContext: isZh ? "添加上下文" : "Add Context",
    placeholder: isZh ? "给 Flippy 发送消息..." : "Message Flippy...",
    verify: isZh ? "请验证输出结果。" : "Verify outputs.",
    shortcuts: isZh ? "Return 发送 · Shift+Return 换行" : "Return to send · Shift+Return for new line",
    inspector: isZh ? "检查器" : "Inspector",
    activeContext: isZh ? "活动上下文" : "Active Context",
    linesInfo: isZh ? "42 行 • 2分钟前" : "42 lines • 2m ago",
    memoryBank: isZh ? "记忆库" : "Memory Bank",
    tags: ["React", "TypeScript", "Date API", "Timezone"]
  };

  const CHATS = t.chatTitles.map((title, i) => ({
    title,
    date: t.dates[i],
    model: ["GPT-4 Turbo", "Claude 3 Opus", "GPT-4 Turbo", "Gemini Pro", "Claude 3 Opus"][i]
  }));

  return (
    <div className="h-full flex font-sans bg-background text-foreground relative selection:bg-primary selection:text-primary-foreground">
      {/* Left Sidebar: Sessions (Dense & Compact) */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[200px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
      >
        <div className="px-4 py-3.5 border-b border-border/50 flex items-center justify-between bg-background/80 backdrop-blur-md sticky top-0 z-10">
          <div className="flex flex-col">
            <h2 className="font-serif text-lg font-black tracking-tight leading-none mb-1">{t.terminal}</h2>
            <p className="text-[8px] font-bold tracking-[0.2em] uppercase text-primary">{t.sessions}</p>
          </div>
          <button className="w-6 h-6 rounded-sm border border-foreground/20 flex items-center justify-center hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all duration-300 shadow-sm bg-card">
            <Plus className="w-3 h-3" />
          </button>
        </div>
        
        <div className="px-3 py-3 border-b border-border/50">
          <div className="relative">
            <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input 
              type="text" 
              placeholder={t.search}
              className="w-full bg-card border border-border/50 rounded-sm pl-7 pr-2 py-1.5 text-[10px] font-sans placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all shadow-sm"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-3 px-2 flex flex-col gap-1">
          <div className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-1.5 px-1.5 pb-1 border-b border-border/50">{t.history}</div>
          {CHATS.map((chat, i) => (
            <button 
              key={i} 
              className={clsx(
                "text-left flex flex-col gap-1 px-2.5 py-2 rounded-sm transition-all duration-300 border border-transparent group",
                i === 0 ? "bg-primary/10 border-primary/20" : "hover:bg-card hover:border-border/50"
              )}
            >
              <div className="flex justify-between items-center w-full">
                <span className={clsx("text-[10px] font-bold uppercase tracking-widest truncate", i === 0 ? "text-primary" : "text-foreground/80 group-hover:text-primary")}>
                  {chat.title}
                </span>
              </div>
              <div className="flex justify-between items-center w-full">
                <span className="text-[8px] font-mono text-muted-foreground">{chat.date}</span>
                <span className="text-[7px] uppercase tracking-[0.1em] bg-muted px-1 py-0.5 rounded-sm text-foreground/60 truncate max-w-[60px]">{chat.model}</span>
              </div>
            </button>
          ))}
        </div>
      </motion.div>

      {/* Main Chat Area (High Density) */}
      <div className="flex-1 flex flex-col h-full bg-background min-w-[500px] relative border-r border-border/50">
        
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-border/50 flex items-center justify-between bg-background/90 backdrop-blur-md sticky top-0 z-10 shadow-sm">
          <div className="flex items-center gap-3">
            <Bot className="w-4 h-4 text-primary" />
            <h2 className="font-serif text-base font-bold tracking-tight leading-none truncate max-w-[200px]">{CHATS[0].title}</h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[8px] font-bold tracking-[0.2em] uppercase border border-primary text-primary px-1.5 py-0.5 rounded-sm bg-primary/5 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              GPT-4 Turbo
            </span>
            <button className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-foreground transition-colors border border-border/50 px-1.5 py-0.5 rounded-sm flex items-center gap-1 hover:bg-muted shadow-sm bg-card hidden sm:flex">
              <AlignLeft className="w-3 h-3" /> {t.context}
            </button>
          </div>
        </div>

        {/* Conversation Stream */}
        <div className="flex-1 overflow-y-auto px-5 lg:px-8 py-6 flex flex-col gap-6 max-w-4xl mx-auto w-full">
          
          {/* User Message */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-end w-full group"
          >
            <div className="flex items-center gap-2 mb-1 mr-1">
              <span className="text-[8px] font-mono text-muted-foreground">10:42 AM</span>
              <span className="text-[8px] font-bold uppercase tracking-[0.2em] text-foreground">User</span>
            </div>
            <div className="max-w-[85%] bg-card border border-border/50 px-4 py-3 shadow-sm rounded-l-md rounded-tr-md">
              <p className="font-serif text-sm leading-[1.6] text-foreground/90">
                {t.userMessage}
              </p>
            </div>
            <div className="flex gap-2 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity mr-1">
              <button className="text-muted-foreground hover:text-primary transition-colors"><Copy className="w-3 h-3" /></button>
            </div>
          </motion.div>

          {/* AI Response */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="flex flex-col items-start w-full group"
          >
            <div className="flex items-center gap-2 mb-1 ml-1">
              <span className="text-[8px] font-bold uppercase tracking-[0.2em] text-primary">Flippy AI</span>
              <span className="text-[8px] font-mono text-muted-foreground">10:42 AM</span>
            </div>
            
            <div className="max-w-[95%] bg-muted/20 border border-primary/20 px-5 py-4 shadow-sm rounded-r-md rounded-tl-md w-full relative">
              <p className="font-serif text-sm leading-[1.6] text-foreground/90 mb-4">
                {t.botResponse}
              </p>
              
              {/* Code Block (Compact) */}
              <div className="bg-card border border-border/50 rounded-sm overflow-hidden flex flex-col shadow-sm my-3">
                <div className="bg-muted/50 px-3 py-1.5 flex justify-between items-center border-b border-border/50">
                  <div className="flex items-center gap-1.5">
                    <Code className="w-3 h-3 text-primary" />
                    <span className="font-mono text-[9px] text-foreground font-bold tracking-[0.1em]">AnalogClock.tsx</span>
                  </div>
                  <button className="flex items-center gap-1 font-sans text-[8px] uppercase tracking-[0.2em] font-bold text-muted-foreground hover:text-primary transition-colors bg-background border border-border/50 px-1.5 py-0.5 rounded-sm shadow-sm">
                    <Copy className="w-2.5 h-2.5" /> {t.copy}
                  </button>
                </div>
                <div className="flex bg-background">
                  <div className="w-8 border-r border-border/50 bg-muted/20 flex flex-col items-end py-3 px-2 font-mono text-[9px] text-muted-foreground/60 select-none leading-[1.5]">
                    {Array.from({length: 12}).map((_, i) => <div key={i}>{i+1}</div>)}
                  </div>
                  <div className="p-3 font-mono text-[10px] leading-[1.5] text-foreground/90 overflow-x-auto whitespace-pre">
                    <span className="text-primary font-bold">import</span> React, {'{'} useState, useEffect {'}'} <span className="text-primary font-bold">from</span> <span className="text-[#3b82f6]">"react"</span>;{'\n'}
                    <span className="text-primary font-bold">export default function</span> <span className="text-[#8b5cf6] font-bold">AnalogClock</span>() {'{\n'}
                    {'  '}<span className="text-primary font-bold">const</span> [time, setTime] = <span className="text-[#8b5cf6]">useState</span>({'{'} hours: <span className="text-[#ef4444]">0</span>, mins: <span className="text-[#ef4444]">0</span>, secs: <span className="text-[#ef4444]">0</span> {'}'});{'\n'}
                    {'  '}<span className="text-primary font-bold">useEffect</span>(() {`=>`} {'{\n'}
                    {'    '}<span className="text-primary font-bold">const</span> updateClock = () {`=>`} {'{\n'}
                    {'      '}<span className="text-muted-foreground italic">// Get London's local time</span>{'\n'}
                    {'      '}<span className="text-primary font-bold">const</span> londonTime = <span className="text-primary font-bold">new</span> <span className="text-[#8b5cf6]">Date</span>().toLocaleTimeString(<span className="text-[#3b82f6]">"en-GB"</span>, {'{\n'}
                    {'        '}timeZone: <span className="text-[#3b82f6]">"Europe/London"</span>, hour12: <span className="text-[#ef4444]">false</span>{'\n'}
                    {'      }'});{'\n'}
                    {'      '}<span className="text-muted-foreground italic">// Implementation omitted for brevity</span>{'\n'}
                    {'    }'};{'\n'}
                    {'  }'}, []);{'\n'}
                    {'}'}
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex gap-3 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity ml-1">
              <button className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 text-[8px] uppercase tracking-[0.2em] font-bold"><ThumbsUp className="w-2.5 h-2.5" /> {t.good}</button>
              <button className="text-muted-foreground hover:text-destructive transition-colors flex items-center gap-1 text-[8px] uppercase tracking-[0.2em] font-bold"><ThumbsDown className="w-2.5 h-2.5" /> {t.bad}</button>
              <button className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 text-[8px] uppercase tracking-[0.2em] font-bold"><RefreshCw className="w-2.5 h-2.5" /> {t.retry}</button>
            </div>
          </motion.div>
        </div>

        {/* Dense Input Area */}
        <div className="px-5 py-3 border-t border-border/50 bg-background/80 backdrop-blur-md flex-shrink-0 z-20 shadow-[0_-4px_12px_rgba(0,0,0,0.05)]">
          <div className="max-w-4xl mx-auto w-full flex flex-col gap-1.5 relative">
            <div className="flex items-center gap-2 mb-0.5 px-1">
              <span className="text-[8px] font-bold tracking-[0.2em] uppercase text-primary flex items-center gap-1">
                <Bot className="w-2.5 h-2.5" /> GPT-4 Turbo
              </span>
              <div className="w-px h-2 bg-border/50" />
              <button className="text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
                <Plus className="w-2.5 h-2.5" /> {t.addContext}
              </button>
            </div>
            
            <div className="relative flex items-end bg-card rounded-sm border border-primary/20 shadow-sm focus-within:shadow-md focus-within:border-primary/50 transition-all duration-300">
              <div className="flex gap-1 p-1.5 pl-2">
                <button className="w-6 h-6 rounded-sm hover:bg-muted transition-colors flex items-center justify-center text-foreground/70 hover:text-primary group">
                  <ImageIcon className="w-3.5 h-3.5 group-hover:scale-110 transition-transform" />
                </button>
                <button className="w-6 h-6 rounded-sm hover:bg-muted transition-colors flex items-center justify-center text-foreground/70 hover:text-primary group">
                  <Code className="w-3.5 h-3.5 group-hover:scale-110 transition-transform" />
                </button>
              </div>
              
              <textarea 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={t.placeholder} 
                className="flex-1 p-2 pt-2.5 font-sans text-[11px] md:text-[13px] font-medium placeholder:text-muted-foreground focus:outline-none resize-none min-h-[36px] max-h-[120px] bg-transparent leading-relaxed"
                rows={1}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = `\${Math.min(target.scrollHeight, 120)}px`;
                }}
              />
              
              <div className="p-1.5 pr-2">
                <button 
                  className={clsx(
                    "w-6 h-6 rounded-sm flex items-center justify-center transition-all duration-300 shadow-sm",
                    input.trim() 
                      ? "bg-primary text-primary-foreground hover:bg-secondary" 
                      : "bg-muted text-muted-foreground border border-border/50"
                  )}
                >
                  <Send className="w-3 h-3" />
                </button>
              </div>
            </div>
            <div className="flex justify-between items-center px-1 mt-0.5">
              <div className="text-[7px] uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-1">
                <AlertCircle className="w-2 h-2" /> {t.verify}
              </div>
              <div className="text-[7px] font-mono text-muted-foreground">
                {t.shortcuts}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Optional Right Panel (Context/Inspector) */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="w-[220px] hidden xl:flex flex-col h-full bg-muted/10 flex-shrink-0"
      >
        <div className="px-5 py-3.5 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex items-center gap-2">
          <AlignLeft className="w-3.5 h-3.5 text-primary" />
          <h2 className="font-serif text-sm font-bold tracking-tight">{t.inspector}</h2>
        </div>
        
        <div className="flex-1 overflow-y-auto px-4 py-5 flex flex-col gap-5">
          <div className="flex flex-col gap-2.5">
            <h3 className="text-[8px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5">{t.activeContext}</h3>
            <div className="bg-card border border-border/50 p-2.5 rounded-sm shadow-sm flex items-start gap-2.5 group cursor-pointer hover:border-primary/50 transition-colors">
              <div className="w-5 h-7 bg-muted border border-border/50 flex items-center justify-center rounded-sm">
                <span className="text-[5px] font-bold uppercase tracking-widest text-primary">TSX</span>
              </div>
              <div className="flex flex-col flex-1 min-w-0 gap-0.5">
                <span className="text-[9px] font-bold font-mono truncate">AnalogClock.tsx</span>
                <span className="text-[8px] text-muted-foreground">{t.linesInfo}</span>
              </div>
              <Check className="w-2.5 h-2.5 text-green-500" />
            </div>
          </div>
          
          <div className="flex flex-col gap-2.5">
            <h3 className="text-[8px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5">{t.memoryBank}</h3>
            <div className="flex flex-wrap gap-1">
              {t.tags.map(tag => (
                <span key={tag} className="text-[8px] font-bold uppercase tracking-[0.1em] border border-border/50 bg-background px-1.5 py-0.5 rounded-sm text-foreground/70 shadow-sm">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
