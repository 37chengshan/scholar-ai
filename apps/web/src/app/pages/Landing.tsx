import React from "react";
import { useNavigate } from "react-router";
import { Search, ArrowRight, BookMarked, Cpu, LayoutTemplate, Network, CheckCircle2, Star } from "lucide-react";
import { motion } from "motion/react";
import { Logo } from "../components/landing/Logo";
import { DemoAnimation } from "../components/landing/DemoAnimation";
import { GlobalDragonBackground } from "../components/landing/GlobalDragonBackground";
import { InteractiveText } from "../components/landing/InteractiveText";
import { Testimonials } from "../components/landing/Testimonials";
import { useAuth } from "@/contexts/AuthContext";
import { PaperTexture } from "../components/PaperTexture";

const features = [
  {
    icon: <Search className="w-6 h-6 text-primary" />,
    title: "智能文献检索",
    description: "基于全文和多模态数据的精准检索，快速定位核心论文和段落。",
  },
  {
    icon: <LayoutTemplate className="w-6 h-6 text-primary" />,
    title: "IMRaD结构化解析",
    description: "自动识别引言、方法、结果和讨论模块，提升阅读效率。",
  },
  {
    icon: <BookMarked className="w-6 h-6 text-primary" />,
    title: "全文多模态问答",
    description: "不仅读取文本，更解析图表内容，支持跨模态复杂提问。",
  },
  {
    icon: <Network className="w-6 h-6 text-primary" />,
    title: "知识图谱生成",
    description: "自动提取实体和关系，构建可视化引文和知识网络，洞悉前沿脉络。",
  },
];

const techStack = [
  { name: "Agentic RAG", desc: "智能任务分解与多步推理" },
  { name: "Hybrid Search", desc: "向量+图谱混合检索架构" },
  { name: "Docling Engine", desc: "多模态PDF高保真解析" },
  { name: "Knowledge Graph", desc: "基于Neo4j的知识体系构建" }
];

const scrollToSection = (id: string) => {
  const element = document.getElementById(id);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

export function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  // Handle "开始探索" button click
  const handleExplore = () => {
    if (isAuthenticated) {
      navigate('/dashboard');
    } else {
      navigate('/login');
    }
  };

  return (
    <div className="min-h-screen text-foreground font-serif relative overflow-hidden selection:bg-primary/20">
      <GlobalDragonBackground />
      <PaperTexture />

      {/* Navigation */}
      <nav className="fixed top-0 inset-x-0 h-24 flex items-center justify-between px-8 lg:px-16 z-40 bg-background/80 backdrop-blur-md border-b border-border/30">
        <Logo />
        <div className="hidden md:flex items-center gap-8 text-sm uppercase tracking-[0.2em]">
          <button
            onClick={() => scrollToSection('features')}
            className="hover:text-primary transition-colors relative z-50 cursor-pointer"
          >
            功能探索
          </button>
          <button
            onClick={() => scrollToSection('tech')}
            className="hover:text-primary transition-colors relative z-50 cursor-pointer"
          >
            技术架构
          </button>
          <button
            onClick={() => scrollToSection('testimonials')}
            className="hover:text-primary transition-colors relative z-50 cursor-pointer"
          >
            用户评价
          </button>
          <button
            onClick={() => scrollToSection('footer')}
            className="hover:text-primary transition-colors relative z-50 cursor-pointer"
          >
            支持
          </button>
        </div>
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/login')}
            className="text-sm uppercase tracking-widest font-bold hidden md:block relative z-50"
          >
            登录
          </button>
          <button
            onClick={handleExplore}
            className="bg-foreground text-background px-6 py-2.5 rounded-full text-xs uppercase tracking-widest font-bold hover:bg-primary hover:text-white transition-all relative z-50"
          >
            开始探索
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="pt-32 relative z-10">
        {/* Hero Section */}
        <section className="px-8 lg:px-16 py-12 lg:py-24 max-w-7xl mx-auto relative">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-end">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="lg:col-span-8 relative z-10"
            >
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/30 bg-primary/5 text-primary text-xs font-bold tracking-widest uppercase mb-8 ml-12">
                <Star className="w-3 h-3 fill-primary" />
                <span><InteractiveText text="新一代学术研究引擎" /></span>
              </div>
              
              <h1 className="text-6xl md:text-[5rem] lg:text-[7rem] font-black tracking-tighter leading-[0.9] flex flex-col">
                <span className="ml-0">
                  <InteractiveText text="颠覆" />
                </span>
                <span className="ml-16 md:ml-32 text-primary italic font-serif relative z-10 text-[1.2em]">
                  <InteractiveText text="文献阅读" />
                  <svg className="absolute w-[120%] h-4 -bottom-1 -left-2 text-primary/20 -z-10" viewBox="0 0 100 10" preserveAspectRatio="none">
                    <path d="M0 5 Q 50 10 100 5" stroke="currentColor" strokeWidth="8" fill="none" />
                  </svg>
                </span>
                <span className="ml-8 md:ml-16 mt-2">
                  <InteractiveText text="的未来范式" />
                </span>
              </h1>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="lg:col-span-4 pb-4 mt-12 lg:mt-0"
            >
              <div className="pl-6 md:pl-8 border-l-2 border-primary/30">
                <p className="text-lg md:text-xl text-foreground/80 leading-relaxed font-serif">
                  <InteractiveText text="AI驱动的论文精读助手。将文献阅读时间从小时级缩短至分钟级，支持结构化解析、多模态问答与知识图谱构建。" />
                </p>
                <div className="flex flex-col gap-4 mt-8 w-full max-w-sm">
                  <button 
                    onClick={handleExplore}
                    className="bg-primary text-white px-8 py-4 rounded-full text-sm font-bold tracking-widest uppercase hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 flex items-center justify-between group relative z-50"
                  >
                    <span>开始探索</span> 
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </button>
                  <button className="bg-transparent text-foreground border border-foreground/20 px-8 py-3.5 rounded-full text-sm font-bold tracking-widest uppercase hover:border-foreground transition-all text-center relative z-50 bg-background/50 backdrop-blur-sm">
                    技术白皮书
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
          
          <div className="absolute top-10 right-10 w-64 h-64 border border-primary/10 rounded-full mix-blend-multiply opacity-50 -z-10"></div>
          <div className="absolute top-32 right-32 w-48 h-48 bg-primary/5 rounded-full mix-blend-multiply opacity-50 -z-10 blur-2xl"></div>
        </section>

        {/* Demo Animation Section */}
        <motion.section
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8 }}
          className="py-16 px-4 md:px-8 w-full max-w-6xl mx-auto relative"
        >
          <div className="absolute inset-0 bg-primary/5 -skew-y-3 transform origin-left -z-10 rounded-3xl"></div>
          <div className="text-center mb-12 relative z-10 pointer-events-none">
            <h2 className="text-sm font-bold tracking-[0.3em] uppercase text-primary mb-3">System Demonstration</h2>
            <p className="text-3xl font-bold font-serif"><InteractiveText text="体验 Agentic RAG 的强大检索" /></p>
          </div>
          <DemoAnimation />
        </motion.section>

        {/* Magazine Style Features Grid */}
        <motion.section
          id="features"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="py-24 px-8 lg:px-16 max-w-7xl mx-auto"
        >
          <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-8 border-b-2 border-foreground pb-8">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="max-w-xl relative z-10 pointer-events-none"
            >
              <h2 className="text-4xl md:text-5xl font-bold mb-4"><InteractiveText text="核心功能与优势" /></h2>
              <p className="text-foreground/70 text-lg"><InteractiveText text="专为科研人员打造的第三代 AI 学术阅读平台，深度理解每一篇文献的灵魂。" /></p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="text-right flex-shrink-0 text-sm font-bold tracking-[0.2em] uppercase opacity-50"
            >
              <p>Vol. 1 — The Future of Reading</p>
            </motion.div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                className="group flex flex-col gap-4"
              >
                <div className="w-14 h-14 rounded-full bg-secondary flex items-center justify-center transform group-hover:scale-110 transition-transform duration-300">
                  {feature.icon}
                </div>
                <div className="relative z-10 pointer-events-none mt-2 flex flex-col gap-2">
                  <h3 className="text-xl font-bold"><InteractiveText text={feature.title} /></h3>
                  <p className="text-foreground/70 text-sm leading-relaxed"><InteractiveText text={feature.description} /></p>
                </div>
                <div className="h-px w-12 bg-primary/30 mt-auto pt-4 group-hover:w-full transition-all duration-500"></div>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* Tech Stack & Image Section (Editorial layout) */}
        <motion.section
          id="tech"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="py-24 px-8 lg:px-16 bg-[#F4ECE1]/50 border-y border-border/50"
        >
          <div className="max-w-7xl mx-auto">
            <motion.div
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.2 }}
              className="relative z-10 pointer-events-none mb-12"
            >
              <h2 className="text-sm font-bold tracking-[0.3em] uppercase text-primary mb-3">Architecture</h2>
              <h3 className="text-4xl md:text-5xl font-bold mb-6"><InteractiveText text="强大的核心技术栈" /></h3>
              <p className="text-lg text-foreground/70 leading-relaxed max-w-3xl">
                <InteractiveText text="基于先进的多智能体协作平台与混合检索架构，实现从文献检索到结构化拆解的全流程自动化。将结构化知识与大模型完美结合。" />
              </p>
            </motion.div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-6 max-w-4xl">
              {techStack.map((tech, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: 0.4 + idx * 0.1 }}
                  className="flex gap-4 items-start"
                >
                  <div className="mt-1">
                    <Cpu className="w-5 h-5 text-primary opacity-80" />
                  </div>
                  <div>
                    <h4 className="font-bold text-lg relative z-10 pointer-events-none"><InteractiveText text={tech.name} /></h4>
                    <p className="text-sm text-foreground/60 mt-1 relative z-10 pointer-events-none"><InteractiveText text={tech.desc} /></p>
                  </div>
                </motion.div>
              ))}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.8 }}
              className="mt-12 pt-8 border-t border-border/50"
            >
              <button className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest hover:text-primary transition-colors group">
                查看完整技术白皮书
                <ArrowRight className="w-4 h-4 group-hover:translate-x-2 transition-transform" />
              </button>
            </motion.div>
          </div>
        </motion.section>

        {/* Testimonials Section */}
        <motion.section
          id="testimonials"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="py-24 px-8 lg:px-16 max-w-7xl mx-auto"
        >
          <Testimonials />
        </motion.section>

      </main>

      {/* Footer */}
      <footer id="footer" className="bg-foreground text-background py-16 px-8 lg:px-16 mt-20 relative z-10">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-12">
          <div className="col-span-1 md:col-span-2">
            <div className="invert grayscale brightness-200 contrast-200">
               <Logo />
            </div>
            <p className="mt-6 text-background/60 max-w-sm text-sm leading-relaxed">
              ScholarAI - 下一代 AI 驱动的学术研究平台，致力于打破知识壁垒，让科研探索变得前所未有的高效。
            </p>
          </div>
          <div>
            <h4 className="font-bold uppercase tracking-widest mb-6 text-xs text-background/50">产品</h4>
            <ul className="space-y-3 text-sm">
              <li><a href="#" className="hover:text-primary transition-colors">文献检索</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">智能解析</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">知识图谱</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">API 文档</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold uppercase tracking-widest mb-6 text-xs text-background/50">关于</h4>
            <ul className="space-y-3 text-sm">
              <li><a href="#" className="hover:text-primary transition-colors">团队</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">博客</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">联系我们</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">隐私政策</a></li>
            </ul>
          </div>
        </div>
        <div className="max-w-7xl mx-auto mt-16 pt-8 border-t border-background/20 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-background/40">
          <p>© 2026 ScholarAI. All rights reserved.</p>
          <div className="flex gap-4">
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Cookies</a>
          </div>
        </div>
      </footer>
    </div>
  );
}