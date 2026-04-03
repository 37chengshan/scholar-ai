import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Search, Loader2, BookOpen, FileText, CheckCircle2, Star } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const steps = [
  "Typing query...",
  "Searching papers...",
  "Parsing IMRaD...",
  "Generating insights...",
  "Done",
];

export function DemoAnimation() {
  const [stage, setStage] = useState(0);
  const [typedText, setTypedText] = useState("");
  const fullQuery = "Agentic RAG 与多模态文献解析最新进展";

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    
    // Stage 0: Typing
    if (stage === 0) {
      if (typedText.length < fullQuery.length) {
        timeout = setTimeout(() => {
          setTypedText(fullQuery.slice(0, typedText.length + 1));
        }, 100);
      } else {
        timeout = setTimeout(() => setStage(1), 800);
      }
    } 
    // Stage 1: Searching/Loading
    else if (stage === 1) {
      timeout = setTimeout(() => setStage(2), 2000);
    } 
    // Stage 2: Result
    else if (stage === 2) {
      // Stay on result for a while, then loop
      timeout = setTimeout(() => {
        setStage(0);
        setTypedText("");
      }, 6000);
    }

    return () => clearTimeout(timeout);
  }, [stage, typedText, fullQuery]);

  return (
    <div className="relative w-full max-w-4xl mx-auto rounded-2xl shadow-2xl overflow-hidden border border-border/50 bg-[#Fdfaf6] aspect-[16/10] md:aspect-[16/9]">
      {/* Top Bar simulating browser/app header */}
      <div className="h-12 border-b border-border bg-[#F4ECE1] flex items-center px-4 gap-2">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-400/80" />
          <div className="w-3 h-3 rounded-full bg-amber-400/80" />
          <div className="w-3 h-3 rounded-full bg-green-400/80" />
        </div>
        <div className="flex-1 mx-4 h-6 bg-[#fdfaf6] rounded flex items-center justify-center opacity-60">
          <span className="text-[10px] uppercase tracking-widest text-foreground/50 font-serif">ScholarAI Workspace</span>
        </div>
      </div>

      <div className="p-6 h-[calc(100%-3rem)] flex flex-col">
        {/* Search Bar Area */}
        <motion.div 
          layout
          className={cn(
            "relative w-full max-w-xl mx-auto flex items-center bg-white border-2 border-primary/20 rounded-full px-4 h-14 shadow-sm",
            stage === 0 ? "mt-24" : "mt-2 mb-6"
          )}
        >
          <Search className="w-5 h-5 text-primary/50 mr-3" />
          <div className="flex-1 font-serif text-lg text-foreground relative">
            {typedText}
            {stage === 0 && (
              <motion.span
                animate={{ opacity: [1, 0] }}
                transition={{ repeat: Infinity, duration: 0.8 }}
                className="inline-block w-0.5 h-5 bg-primary ml-1 align-middle"
              />
            )}
          </div>
          {stage === 1 && (
            <Loader2 className="w-5 h-5 text-primary animate-spin" />
          )}
        </motion.div>

        {/* Results Area */}
        <AnimatePresence mode="wait">
          {stage === 1 && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="flex-1 flex flex-col items-center justify-center space-y-4"
            >
              <div className="flex items-center gap-3 text-primary">
                <Loader2 className="w-8 h-8 animate-spin" />
                <span className="font-serif italic text-lg tracking-wider">AI 正在深度检索与解析中...</span>
              </div>
              <div className="flex gap-4 opacity-60">
                {steps.slice(1, 4).map((step, idx) => (
                  <div key={idx} className="flex items-center gap-1.5 text-sm font-serif">
                    <CheckCircle2 className="w-4 h-4" /> {step}
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {stage === 2 && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex-1 grid grid-cols-12 gap-6 overflow-hidden"
            >
              {/* Left Column: Parsed Document Preview */}
              <div className="col-span-5 bg-white border border-border/50 rounded-xl p-4 shadow-inner flex flex-col gap-4">
                <div className="flex items-center gap-2 pb-2 border-b border-border/30">
                  <FileText className="w-4 h-4 text-primary" />
                  <span className="text-xs font-bold tracking-wide text-foreground/70 uppercase">Original Document Source</span>
                </div>
                <div className="flex-1 space-y-3 opacity-60">
                  <div className="w-3/4 h-5 bg-border rounded-sm" />
                  <div className="w-full h-3 bg-border rounded-sm" />
                  <div className="w-full h-3 bg-border rounded-sm" />
                  <div className="w-5/6 h-3 bg-border rounded-sm" />
                  <div className="w-full h-24 bg-border/40 rounded flex items-center justify-center mt-4">
                    <span className="text-[10px] tracking-wider text-foreground/40 font-serif">Figure 1. Architecture</span>
                  </div>
                  <div className="w-full h-3 bg-border rounded-sm" />
                  <div className="w-4/5 h-3 bg-border rounded-sm" />
                </div>
              </div>

              {/* Right Column: AI Response */}
              <div className="col-span-7 bg-primary/5 border border-primary/20 rounded-xl p-5 overflow-hidden flex flex-col relative">
                <div className="flex items-center gap-2 mb-4">
                  <Star className="w-5 h-5 text-primary fill-primary" />
                  <h3 className="font-serif font-bold text-lg text-foreground">Synthesis Report</h3>
                </div>
                
                <div className="space-y-4">
                  <motion.div 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    <p className="font-serif text-sm leading-relaxed text-foreground/80">
                      Based on the recent literature analyzed (12 documents), <span className="text-primary font-bold">Agentic RAG</span> significantly outperforms traditional pipelines by breaking down complex queries and dynamically assigning tasks to specialized sub-agents.
                    </p>
                  </motion.div>
                  
                  <motion.div 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 }}
                    className="p-3 bg-white/60 border-l-4 border-primary rounded-r-md text-sm font-serif italic"
                  >
                    "Integrating multimodal parsers like Docling with Graph-based retrieval yields a 45% increase in citation accuracy for visually-rich academic papers."
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 1 }}
                    className="flex gap-2 flex-wrap"
                  >
                    <span className="px-2 py-1 bg-white border border-border/50 rounded-full text-[10px] text-foreground/60 shadow-sm flex items-center gap-1"><BookOpen className="w-3 h-3"/> Hybrid Retrieval</span>
                    <span className="px-2 py-1 bg-white border border-border/50 rounded-full text-[10px] text-foreground/60 shadow-sm flex items-center gap-1"><BookOpen className="w-3 h-3"/> IMRaD Parsing</span>
                    <span className="px-2 py-1 bg-white border border-border/50 rounded-full text-[10px] text-foreground/60 shadow-sm flex items-center gap-1"><BookOpen className="w-3 h-3"/> Multimodal</span>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}