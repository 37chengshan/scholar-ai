import { Search as SearchIcon, Globe, Plus, RefreshCw, BarChart2, Hash, ExternalLink, Calendar, Users, TrendingUp, Layers } from "lucide-react";
import { clsx } from "clsx";
import { useState } from "react";
import { motion } from "motion/react";
import { useLanguage } from "../contexts/LanguageContext";
import { papersApi } from "@/services";

export function Search() {
  const [activeSource, setActiveSource] = useState("all");
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    sources: isZh ? "检索来源" : "Sources",
    global: isZh ? "全局搜索" : "Global",
    aggregators: isZh ? "聚合引擎" : "Aggregators",
    allSources: isZh ? "全部来源" : "All Sources",
    connectors: isZh ? "连接器" : "Connectors",
    statusConn: isZh ? "已连接" : "Connected",
    statusLimit: isZh ? "频率限制" : "Rate Limited",
    statusDisconn: isZh ? "未连接" : "Disconnected",
    refresh: isZh ? "刷新令牌" : "Refresh Tokens",
    matches: isZh ? "209 条结果 / 1.4秒" : "209 matches / 1.4s",
    query: isZh ? "查询" : "Query",
    placeholder: isZh ? "输入检索词，例如自主智能体、大模型..." : "Search for autonomous agents, LLMs...",
    loadMore: isZh ? "加载更多结果" : "Load More Results",
    import: isZh ? "导入" : "Import",
    analyze: isZh ? "分析" : "Analyze",
    source: isZh ? "原文" : "Source",
    analysis: isZh ? "检索分析" : "Analysis",
    velocity: isZh ? "发表趋势" : "Velocity",
    topAuthors: isZh ? "热门作者" : "Top Authors",
    topics: isZh ? "提取主题" : "Topics",
    report: isZh ? "生成报告" : "Report",
    tagNames: isZh ? ["大语言模型", "智能体", "推理", "思维链", "工具调用", "模拟"] : ["LLMs", "Agentic", "Reasoning", "Chain-of-Thought", "Tool Use", "Simulation"]
  };

  const SOURCES = [
    { id: "arxiv", name: "arXiv.org", status: t.statusConn, statusType: "Connected", results: 124 },
    { id: "semanticscholar", name: "Semantic Scholar", status: t.statusConn, statusType: "Connected", results: 85 },
    { id: "crossref", name: "Crossref API", status: t.statusLimit, statusType: "Rate Limited", results: 0 },
    { id: "pubmed", name: "PubMed Central", status: t.statusDisconn, statusType: "Disconnected", results: 0 },
  ];

  const SEARCH_RESULTS = [
    { id: 1, title: isZh ? "生成式智能体：人类行为的交互式模拟" : "Generative Agents: Interactive Simulacra of Human Behavior", authors: "Joon Sung Park, Joseph C. O'Brien, Carrie J. Cai, Meredith Ringel Morris, Percy Liang, Michael S. Bernstein", year: 2023, source: "arXiv", citations: 432, abstract: isZh ? "可信的人类行为代理可以赋能交互式应用程序，从沉浸式环境到人际交流的演练空间。在本文中，我们引入了生成式智能体——计算软件智能体，它们可以模拟可信的人类行为..." : "Believable proxies of human behavior can empower interactive applications ranging from immersive environments to rehearsal spaces for interpersonal communication. In this paper, we introduce generative agents—computational software agents that simulate believable human behavior..." },
    { id: 2, title: isZh ? "ReAct：在语言模型中协同推理与行动" : "ReAct: Synergizing Reasoning and Acting in Language Models", authors: "Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao", year: 2022, source: "arXiv", citations: 891, abstract: isZh ? "虽然大型语言模型（LLM）在语言理解和交互式决策任务中展现出了令人印象深刻的能力，但它们的推理能力（例如思维链提示）和行动能力（例如生成行动计划）主要被作为独立的主题进行研究..." : "While large language models (LLMs) have demonstrated impressive capabilities across tasks in language understanding and interactive decision making, their abilities for reasoning (e.g. chain-of-thought prompting) and acting (e.g. action plan generation) have primarily been studied as separate topics..." },
    { id: 3, title: isZh ? "Toolformer：语言模型可以教自己使用工具" : "Toolformer: Language Models Can Teach Themselves to Use Tools", authors: "Timo Schick, Jane Dwivedi-Yu, Roberto Dessì, Roberta Raileanu, Maria Lomeli, Luke Zettlemoyer, Nicola Cancedda, Thomas Scialom", year: 2023, source: "Semantic Scholar", citations: 567, abstract: isZh ? "语言模型表现出了惊人的能力，只需少量示例或文本指令即可解决新任务，尤其是在规模化的情况下。然而，它们在基本功能方面仍然很困难，例如算术或事实查找，而这些方面更简单、更小的模型却表现出色..." : "Language models (LMs) exhibit remarkable abilities to solve new tasks from just a few examples or textual instructions, especially at scale. They also, however, struggle with basic functionality, such as arithmetic or factual lookup, where much simpler and smaller models excel..." },
    { id: 4, title: isZh ? "AutoGPT：具有长期记忆的自主 AI 智能体" : "AutoGPT: Autonomous AI Agent with Long-term Memory", authors: "Toran Bruce Richards, et al.", year: 2023, source: "arXiv", citations: 215, abstract: isZh ? "AutoGPT 是一个实验性的开源应用程序，展示了 GPT-4 语言模型的能力。这个由 GPT-4 驱动的程序将 LLM 的'思维'链接在一起，以自主实现您设定的任何目标..." : "AutoGPT is an experimental open-source application showcasing the capabilities of the GPT-4 language model. This program, driven by GPT-4, chains together LLM \"thoughts\", to autonomously achieve whatever goal you set..." },
    { id: 5, title: isZh ? "HuggingGPT：通过人类反馈训练语言模型遵循指令" : "HuggingGPT: Training Language Models to Follow Instructions with Human Feedback", authors: "Long Ouyang, et al.", year: 2022, source: "Semantic Scholar", citations: 1243, abstract: isZh ? "使语言模型变得更大并不能从本质上使它们更好地遵循用户的意图。例如，大型语言模型可能会生成不真实、有害或根本对用户无益的输出..." : "Making language models bigger does not inherently make them better at following a user's intent. For example, large language models can generate outputs that are untruthful, toxic, or simply not helpful to the user..." },
    { id: 6, title: isZh ? "思维链提示激发了大型语言模型的推理能力" : "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models", authors: "Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bos, Ed Chi, Quoc Le", year: 2022, source: "arXiv", citations: 3412, abstract: isZh ? "我们探讨了生成思维链——一系列中间推理步骤——如何显著提高大型语言模型执行复杂推理的能力。特别是，我们展示了这种推理能力如何在足够大的语言模型中自然地涌现..." : "We explore how generating a chain of thought—a series of intermediate reasoning steps—significantly improves the ability of large language models to perform complex reasoning. In particular, we show how such reasoning abilities emerge naturally in sufficiently large language models..." }
  ];

  return (
    <div className="h-full flex font-sans bg-background text-foreground relative selection:bg-primary selection:text-primary-foreground">
      {/* Column 1: Sources (Left) */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[220px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center">
          <h2 className="font-serif text-xl font-black tracking-tight leading-none mb-1">{t.sources}</h2>
          <p className="text-[8px] font-bold tracking-[0.2em] uppercase text-primary">{t.global}</p>
        </div>
        
        <div className="flex-1 overflow-y-auto py-5 flex flex-col gap-6 px-4">
          <div>
            <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{t.aggregators}</div>
            <button 
              onClick={() => setActiveSource("all")}
              className={clsx(
                "flex items-center gap-2.5 px-2 py-2 rounded-sm transition-colors group w-full",
                activeSource === "all" ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" : "hover:bg-muted text-foreground/80 hover:text-primary"
              )}
            >
              <Globe className={clsx("w-3.5 h-3.5", activeSource === "all" ? "text-primary-foreground" : "text-primary")} />
              <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left">{t.allSources}</span>
              <span className={clsx("text-[9px] font-mono", activeSource === "all" ? "text-primary-foreground/70" : "text-muted-foreground")}>209</span>
            </button>
          </div>

          <div>
            <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{t.connectors}</div>
            <div className="flex flex-col gap-0.5">
              {SOURCES.map((source) => (
                <button 
                  key={source.id}
                  onClick={() => setActiveSource(source.id)}
                  className={clsx(
                    "flex items-center gap-2.5 px-2 py-2 rounded-sm transition-colors group w-full",
                    activeSource === source.id ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" : "hover:bg-muted text-foreground/80 hover:text-primary"
                  )}
                >
                  <div className={clsx(
                    "w-1.5 h-1.5 rounded-full flex-shrink-0",
                    source.statusType === "Connected" ? "bg-green-500" : source.statusType === "Rate Limited" ? "bg-yellow-500" : "bg-red-500"
                  )} />
                  <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left truncate">{source.name}</span>
                  {source.results > 0 && <span className={clsx("text-[9px] font-mono", activeSource === source.id ? "text-primary-foreground/70" : "text-muted-foreground")}>{source.results}</span>}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-border/50 bg-background/80 backdrop-blur-md">
          <button className="w-full border border-foreground/20 text-foreground py-2.5 rounded-sm text-[9px] font-bold uppercase tracking-[0.2em] hover:bg-muted transition-colors flex items-center justify-center gap-2 group shadow-sm bg-card">
            <RefreshCw className="w-3 h-3 group-hover:rotate-180 transition-transform duration-500" />
            {t.refresh}
          </button>
        </div>
      </motion.div>

      {/* Column 2: Search Interface & Results (Middle) */}
      <div className="flex-1 flex flex-col h-full bg-background min-w-[500px]">
        <div className="px-5 py-4 border-b border-border/50 bg-background/90 backdrop-blur-md sticky top-0 z-10 flex flex-col gap-3 shadow-sm">
          <div className="flex justify-between items-center gap-4">
            <div className="flex-1 max-w-2xl flex items-center gap-3 bg-card border border-primary/30 p-1 rounded-full focus-within:border-primary transition-colors shadow-sm group">
              <SearchIcon className="w-4 h-4 text-primary ml-3" />
              <input 
                type="text" 
                defaultValue={isZh ? "自主智能体 大语言模型" : "Autonomous Agents LLM"}
                className="flex-1 bg-transparent border-none text-sm font-serif font-bold tracking-wide focus:outline-none focus:ring-0 placeholder:font-sans placeholder:font-normal placeholder:tracking-normal placeholder:text-muted-foreground"
                placeholder={t.placeholder}
              />
              <button className="bg-primary text-primary-foreground px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-secondary transition-colors h-full shadow-sm shadow-primary/20">
                {t.query}
              </button>
            </div>
            <div className="text-[9px] font-mono tracking-[0.2em] text-muted-foreground flex-shrink-0">
              {t.matches}
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-muted/5 p-5">
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="grid grid-cols-1 xl:grid-cols-2 gap-5"
          >
            {SEARCH_RESULTS.map((paper) => (
              <div 
                key={paper.id} 
                className="p-5 border border-border/50 bg-card rounded-sm flex flex-col gap-3 group hover:border-primary/50 hover:shadow-md transition-all duration-300 relative overflow-hidden"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary/0 via-primary/0 to-primary/0 group-hover:via-primary/50 transition-colors duration-500" />
                
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2 text-[8px] font-bold uppercase tracking-widest text-primary">
                    <span className="bg-primary/10 px-1.5 py-0.5 rounded-sm">{paper.source}</span>
                    <span className="text-muted-foreground font-mono">{paper.year}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest text-muted-foreground">
                    <div className="w-1.5 h-1.5 rounded-full bg-secondary" />
                    {paper.citations}
                  </div>
                </div>
                
                <div className="flex flex-col gap-1.5">
                  <h3 className="font-serif font-black text-xl leading-tight group-hover:text-primary transition-colors tracking-tight line-clamp-2">
                    {paper.title}
                  </h3>
                  <p className="font-sans text-[11px] font-medium text-foreground/80 line-clamp-1 truncate">{paper.authors}</p>
                </div>
                
                <div className="flex flex-col flex-1">
                  <p className="font-serif text-xs text-foreground/70 leading-[1.6] line-clamp-3 italic border-l-2 border-primary/20 pl-3 mt-1 flex-1">
                    {paper.abstract}
                  </p>
                </div>
                
                <div className="flex items-center justify-between gap-3 mt-3 pt-3 border-t border-border/30 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest bg-primary text-primary-foreground px-3 py-1.5 rounded-sm hover:bg-secondary transition-colors shadow-sm">
                    <Plus className="w-3 h-3" /> {t.import}
                  </button>
                  <div className="flex items-center gap-2">
                    <button className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest text-foreground/60 hover:text-primary transition-colors px-2 py-1">
                      <BarChart2 className="w-3 h-3" /> {t.analyze}
                    </button>
                    <button className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest text-foreground/60 hover:text-primary transition-colors px-2 py-1">
                      <ExternalLink className="w-3 h-3" /> {t.source}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </motion.div>
          
          <div className="p-8 flex justify-center bg-transparent">
            <button className="text-[10px] font-bold uppercase tracking-[0.3em] text-muted-foreground hover:text-primary transition-colors border-b border-muted-foreground hover:border-primary pb-1 group flex items-center gap-2">
              <RefreshCw className="w-3 h-3 group-hover:rotate-180 transition-transform duration-500" /> {t.loadMore}
            </button>
          </div>
        </div>
      </div>

      {/* Column 3: Analysis & Filters (Right) */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[240px] border-l border-border/50 flex flex-col h-full bg-muted/10 flex-shrink-0 relative"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-3.5 h-3.5 text-primary" />
            <h2 className="font-serif text-lg font-bold tracking-tight">{t.analysis}</h2>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6 flex flex-col gap-8">
          
          {/* Publication Year Histogram */}
          <div className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Calendar className="w-3 h-3" /> {t.velocity}
            </h3>
            <div className="flex items-end gap-1 h-20 mt-2">
              <div className="w-full bg-muted/50 rounded-sm hover:bg-primary/80 transition-colors h-[20%] relative group"></div>
              <div className="w-full bg-muted/50 rounded-sm hover:bg-primary/80 transition-colors h-[30%] relative group"></div>
              <div className="w-full bg-muted/50 rounded-sm hover:bg-primary/80 transition-colors h-[50%] relative group"></div>
              <div className="w-full bg-primary rounded-sm transition-colors h-[90%] relative group shadow-sm shadow-primary/20">
                <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[8px] font-mono text-primary font-bold">85</span>
              </div>
              <div className="w-full bg-muted/50 rounded-sm hover:bg-primary/80 transition-colors h-[60%] relative group"></div>
            </div>
            <div className="flex justify-between text-[8px] font-mono text-muted-foreground mt-1">
              <span>2019</span>
              <span className="text-primary font-bold">2022</span>
              <span>2024</span>
            </div>
          </div>

          {/* Top Authors */}
          <div className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Users className="w-3 h-3" /> {t.topAuthors}
            </h3>
            <div className="flex flex-col gap-2 mt-1">
              {[
                { name: "Joon Sung Park", score: 85 },
                { name: "Michael S. Bernstein", score: 72 },
                { name: "Shunyu Yao", score: 68 },
                { name: "Timo Schick", score: 45 }
              ].map((author) => (
                <div key={author.name} className="flex flex-col gap-1 group cursor-pointer">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-medium text-foreground/80 group-hover:text-primary transition-colors">{author.name}</span>
                    <span className="text-[9px] font-mono text-muted-foreground">{(author.score / 10).toFixed(1)}k</span>
                  </div>
                  <div className="w-full h-1 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-primary/40 group-hover:bg-primary transition-all" style={{ width: `${author.score}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Extracted Topics */}
          <div className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Hash className="w-3 h-3" /> {t.topics}
            </h3>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {t.tagNames.map((tag) => (
                <span key={tag} className="font-sans text-[9px] font-bold uppercase tracking-[0.1em] bg-card border border-border/50 text-foreground/70 px-2 py-1 rounded-sm hover:bg-primary hover:text-primary-foreground hover:border-primary transition-colors cursor-pointer shadow-sm">
                  {tag}
                </span>
              ))}
            </div>
          </div>

        </div>
        
        <div className="px-5 py-4 border-t border-border/50 bg-background/80 backdrop-blur-md">
          <button className="w-full bg-transparent border border-foreground/20 text-foreground py-2 rounded-sm text-[9px] font-bold uppercase tracking-[0.2em] hover:bg-muted transition-colors flex justify-center items-center gap-2">
            <TrendingUp className="w-3.5 h-3.5 text-foreground/50" />
            {t.report}
          </button>
        </div>
      </motion.div>
    </div>
  );
}