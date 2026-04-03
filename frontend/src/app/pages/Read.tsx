import { Download, Save, Maximize2, Zap, Bold, Italic, Underline, List, Link } from "lucide-react";
import { motion } from "motion/react";
import { clsx } from "clsx";
import { useLanguage } from "../contexts/LanguageContext";

export function Read() {
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    analysis: isZh ? "AI 分析" : "Analysis",
    coreInsight: isZh ? "核心洞察" : "Core Insight",
    insightText: isZh ? "本论文介绍了 Transformer 架构，它完全摒弃了循环和卷积机制，仅依靠注意力机制便实现了最先进的结果。" : "This paper introduces the Transformer architecture, which dispenses with recurrence and convolutions entirely, relying solely on attention mechanisms to achieve state-of-the-art results.",
    entityExt: isZh ? "实体提取" : "Entity Extraction",
    tags: isZh ? ["Transformer", "自注意力", "机器翻译", "WMT 2014", "BLEU"] : ["Transformer", "Self-Attention", "Machine Translation", "WMT 2014", "BLEU"],
    titleLabel: isZh ? "标题" : "Title",
    titleVal: isZh ? "注意力机制就是你需要的一切" : "Attention Is All You Need",
    published: isZh ? "出版年份" : "Published",
    citations: isZh ? "引用量" : "Citations",
    doi: isZh ? "DOI / 标识" : "DOI",
    page: isZh ? "1 / 15 页" : "1 / 15",
    abstractTitle: isZh ? "摘要" : "Abstract",
    abstractText: isZh ? "主要的序列转换模型基于复杂的循环或卷积神经网络，包括编码器和解码器。表现最好的模型还通过注意力机制连接编码器和解码器。我们提出了一种新的简单网络架构：Transformer，仅基于注意力机制，完全摒弃了循环和卷积。在两个机器翻译任务上的实验表明，这些模型具有优越性..." : "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior...",
    notes: isZh ? "阅读笔记" : "Notes",
    sync: isZh ? "同步" : "Sync",
    noteTitle: isZh ? "注意力机制就是你需要的一切" : "Attention Is All You Need",
    noteP1Part1: isZh ? "这篇论文是现代大语言模型 (LLMs) 的基础。其核心创新在于使用 " : "This paper is foundational for modern LLMs. The core innovation is replacing RNNs/LSTMs with the ",
    noteP1Part2: isZh ? " 架构取代了 RNN/LSTM。" : " architecture.",
    keyHighlights: isZh ? "关键亮点：" : "Key Highlights:",
    li1: isZh ? "完全依赖自注意力机制来计算表示。" : "Relies entirely on self-attention to compute representations.",
    li2: isZh ? "高度可并行化，训练速度远快于序列模型。" : "Highly parallelizable, training much faster than sequential models.",
    li3: isZh ? "在英德翻译任务中达到 28.4 BLEU。" : "Achieved 28.4 BLEU on English-to-German.",
    quote: isZh ? "“我们提出了一种新的简单网络架构，Transformer，它完全基于注意力机制，完全摒弃了循环和卷积。”" : '"We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely."',
    noteP2: isZh ? "需要进一步深入研究缩放点积注意力的具体方程式。" : "Need to look deeper into the specific equations for scaled dot-product attention.",
    lastEdited: isZh ? "最后编辑于 2 分钟前" : "Last edited 2 mins ago"
  };

  return (
    <div className="h-full flex font-sans bg-background text-foreground overflow-hidden selection:bg-primary selection:text-primary-foreground relative">
      {/* Column 1: AI Intro + Metadata (Left) */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[240px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center">
          <h2 className="font-serif text-xl font-black tracking-tight leading-none mb-1">{t.analysis}</h2>
          <Zap className="w-4 h-4 text-primary" />
        </div>
        
        <div className="flex-1 overflow-y-auto px-4 py-6 flex flex-col gap-6">
          <div className="relative group">
            <div className="absolute inset-0 bg-primary/5 rounded-sm transform translate-x-1.5 translate-y-1.5 transition-transform group-hover:translate-x-2 group-hover:translate-y-2" />
            <div className="bg-card border border-primary/20 p-4 relative shadow-sm backdrop-blur-sm z-10 rounded-sm">
              <div className="absolute -top-2.5 left-4 bg-primary text-primary-foreground px-2.5 py-0.5 font-sans text-[8px] uppercase font-bold tracking-[0.2em] rounded-sm shadow-sm shadow-primary/20">
                {t.coreInsight}
              </div>
              <p className="font-serif text-[11px] leading-[1.8] mt-1 text-foreground italic text-justify">
                {t.insightText}
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <h3 className="font-sans text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5">
              {t.entityExt}
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {t.tags.map((tag) => (
                <span key={tag} className="font-sans text-[9px] font-bold uppercase tracking-[0.1em] bg-primary/5 border border-primary/10 text-primary px-2 py-1 rounded-sm hover:bg-primary hover:text-primary-foreground transition-colors cursor-pointer shadow-sm">
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-4 mt-auto border-t border-border/50 pt-5">
            <div className="flex flex-col gap-3">
              <div>
                <div className="font-sans text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-0.5">{t.titleLabel}</div>
                <div className="font-serif text-sm font-bold leading-tight">{t.titleVal}</div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="font-sans text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-0.5">{t.published}</div>
                  <div className="font-serif text-xs font-bold">2017</div>
                </div>
                <div>
                  <div className="font-sans text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-0.5">{t.citations}</div>
                  <div className="font-serif text-xs font-bold text-primary">105,432</div>
                </div>
              </div>
              <div>
                <div className="font-sans text-[8px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-0.5">{t.doi}</div>
                <div className="font-mono text-[9px] text-foreground/70 underline decoration-1 underline-offset-4 hover:text-primary cursor-pointer">10.48550/arXiv.1706.03762</div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Column 2: PDF Reader (Middle) */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.2 }}
        className="flex-1 border-r border-border/50 flex flex-col h-full bg-muted/10 min-w-[400px]"
      >
        <div className="px-5 py-3.5 border-b border-border/50 flex justify-between items-center bg-background/90 backdrop-blur-md sticky top-0 z-10 shadow-sm">
          <div className="flex items-center gap-4">
            <h2 className="font-serif text-base font-bold tracking-tight truncate max-w-[200px] xl:max-w-[400px]">Attention Is All You Need.pdf</h2>
            <div className="font-sans text-[9px] font-bold uppercase tracking-[0.2em] bg-primary/10 text-primary px-2 py-0.5 rounded-sm border border-primary/20 whitespace-nowrap">
              {t.page}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-2 rounded-sm border border-foreground/20 hover:bg-muted transition-colors text-foreground/70 group shadow-sm bg-card">
              <Download className="w-3.5 h-3.5 group-hover:text-primary transition-colors" />
            </button>
            <button className="p-2 rounded-sm border border-foreground/20 hover:bg-muted transition-colors text-foreground/70 group shadow-sm bg-card">
              <Maximize2 className="w-3.5 h-3.5 group-hover:text-primary transition-colors" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 lg:p-10 flex justify-center items-start bg-muted/30">
          <div className="w-full max-w-[700px] aspect-[1/1.414] bg-card shadow-xl flex flex-col relative overflow-hidden group border border-border/50">
            <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1707256786130-6d028236813f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxhY2FkZW1pYyUyMHBhcGVyJTIwY292ZXJ8ZW58MXx8fHwxNzc1MTk4MzcxfDA&ixlib=rb-4.1.0&q=80&w=1080')] bg-cover opacity-[0.03] filter grayscale mix-blend-multiply" />
            <div className="relative z-10 p-10 flex flex-col gap-6">
              <h1 className="font-serif text-3xl md:text-4xl font-black text-center leading-[1.1] tracking-tight">Attention Is All You Need</h1>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-4 text-center font-sans mt-2 border-y border-border/50 py-6">
                <div><span className="font-bold text-xs">Ashish Vaswani*</span><br/><span className="text-[9px] text-muted-foreground">Google Brain</span></div>
                <div><span className="font-bold text-xs">Noam Shazeer*</span><br/><span className="text-[9px] text-muted-foreground">Google Brain</span></div>
                <div><span className="font-bold text-xs">Niki Parmar*</span><br/><span className="text-[9px] text-muted-foreground">Google Research</span></div>
                <div><span className="font-bold text-xs">Jakob Uszkoreit*</span><br/><span className="text-[9px] text-muted-foreground">Google Research</span></div>
              </div>
              
              <div className="mt-4 max-w-xl mx-auto">
                <h2 className="font-sans text-[10px] font-bold uppercase tracking-[0.3em] text-center mb-4">{t.abstractTitle}</h2>
                <p className="font-serif text-sm leading-[1.8] text-justify hyphens-auto text-foreground/90">
                  {t.abstractText}
                </p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Column 3: Note taking (Right) */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="w-[300px] flex flex-col h-full bg-card flex-shrink-0"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center shadow-sm">
          <h2 className="font-serif text-xl font-black tracking-tight leading-none mb-1">{t.notes}</h2>
          <button className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-[0.2em] bg-primary text-primary-foreground px-3 py-1.5 rounded-sm hover:bg-secondary transition-colors shadow-sm">
            <Save className="w-3 h-3" /> {t.sync}
          </button>
        </div>

        <div className="flex border-b border-border/50 bg-muted/20 sticky top-[61px] z-10 px-3 py-1.5 gap-1.5 shadow-sm">
          <button className="p-1.5 hover:bg-muted rounded-sm transition-colors text-foreground/70 hover:text-primary"><Bold className="w-3.5 h-3.5" /></button>
          <button className="p-1.5 hover:bg-muted rounded-sm transition-colors text-foreground/70 hover:text-primary"><Italic className="w-3.5 h-3.5" /></button>
          <button className="p-1.5 hover:bg-muted rounded-sm transition-colors text-foreground/70 hover:text-primary"><Underline className="w-3.5 h-3.5" /></button>
          <button className="p-1.5 hover:bg-muted rounded-sm transition-colors text-foreground/70 hover:text-primary"><List className="w-3.5 h-3.5" /></button>
          <button className="p-1.5 hover:bg-muted rounded-sm transition-colors text-foreground/70 hover:text-primary"><Link className="w-3.5 h-3.5" /></button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6 outline-none bg-background">
          <div 
            className="w-full h-full font-serif text-[13px] leading-[1.8] text-foreground/90 focus:outline-none cursor-text min-h-full"
            contentEditable
            suppressContentEditableWarning
          >
            <h1 className="font-serif text-xl font-black tracking-tight mb-4 leading-tight">{t.noteTitle}</h1>
            <p className="mb-4">{t.noteP1Part1}<span className="bg-primary/10 border border-primary/20 px-1 py-0.5 rounded-sm font-mono text-[10px] text-primary">Transformer</span>{t.noteP1Part2}</p>
            <h2 className="font-sans text-[9px] font-bold uppercase tracking-[0.2em] text-muted-foreground mt-6 mb-3 border-b border-border/50 pb-1">{t.keyHighlights}</h2>
            <ul className="list-disc pl-4 mb-4 space-y-2">
              <li><strong>{t.li1.includes('self-attention') ? 'self-attention' : (isZh ? '自注意力机制' : '')}</strong>{t.li1.replace('self-attention', '').replace('自注意力机制', '')}</li>
              <li>{t.li2}</li>
              <li>{t.li3}</li>
            </ul>
            <div className="my-6 text-foreground/70 italic font-serif text-[12px] border-l-2 border-primary/30 pl-3 py-1.5 bg-muted/10">
              {t.quote}
            </div>
            <p className="mb-4">{t.noteP2}</p>
          </div>
        </div>
        
        <div className="p-3 border-t border-border/50 bg-background/80 backdrop-blur-md font-sans text-[8px] uppercase tracking-[0.3em] text-muted-foreground text-center">
          {t.lastEdited}
        </div>
      </motion.div>
    </div>
  );
}
