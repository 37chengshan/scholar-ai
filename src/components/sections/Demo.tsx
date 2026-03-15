import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Database, Zap, CheckCircle, Clock, Sparkles } from 'lucide-react';
import { StepAnimation } from '../effects/StepAnimation';

const demoSteps = [
  {
    title: '用户提问',
    content: '"YOLO系列方法的演进路线是什么？"',
    icon: Search,
    delay: 0,
  },
  {
    title: '智能分析',
    content: '系统识别为跨文档复杂查询，分解为子问题',
    icon: Zap,
    delay: 800,
  },
  {
    title: 'Agentic检索',
    content: '在300篇论文中并行检索相关段落',
    icon: Database,
    delay: 1600,
  },
  {
    title: '生成答案',
    content: '按时间线组织信息，生成结构化答案',
    icon: CheckCircle,
    delay: 2400,
  },
];

const comparisonData = {
  traditional: {
    time: '2天',
    steps: ['手动翻阅数十篇论文', '关键词搜索筛选', '人工整理时间线', '核对信息准确性'],
    painPoints: ['耗时费力', '容易遗漏', '难以验证'],
  },
  aiAssistant: {
    time: '10秒',
    steps: ['自然语言提问', 'Agentic智能检索', '自动整合生成', '带引用溯源'],
    advantages: ['秒级响应', '全面准确', '可验证'],
  },
};

export const Demo: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    if (!isPlaying) return;

    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % demoSteps.length);
    }, 2000);

    return () => clearInterval(timer);
  }, [isPlaying]);

  return (
    <section className="relative py-24 lg:py-32 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0">
        {/* Gradient Orbs */}
        <div className="absolute top-1/4 left-0 w-[400px] h-[400px] bg-neon-cyan/10 rounded-full blur-[150px]" />
        <div className="absolute bottom-1/4 right-0 w-[500px] h-[500px] bg-neon-purple/10 rounded-full blur-[150px]" />

        {/* Grid Pattern */}
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(0, 245, 255, 0.5) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0, 245, 255, 0.5) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />
      </div>

      {/* Top Border */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-neon-cyan/50 to-transparent" />

      <div className="container px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="inline-block px-4 py-1 mb-4 text-xs font-display uppercase tracking-wider text-neon-cyan border border-neon-cyan/30 rounded-full bg-neon-cyan/10">
            核心亮点演示
          </span>
          <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4">
            文献库<span className="text-gradient">智能检索引擎</span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Agentic RAG + 混合搜索 + IMRaD感知分块，突破上下文限制，实现秒级精准检索
          </p>
        </motion.div>

        {/* Demo Area */}
        <div className="max-w-6xl mx-auto">
          {/* Main Demo Card */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.7 }}
            className="relative mb-12"
          >
            <div className="absolute -inset-px bg-gradient-to-r from-neon-cyan/50 via-neon-blue/50 to-neon-purple/50 rounded-3xl blur-sm opacity-50" />
            <div className="relative bg-bg-tertiary border border-white/10 rounded-3xl overflow-hidden">
              {/* Demo Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-white/5">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-neon-cyan animate-pulse" />
                  <span className="font-display text-sm text-gray-300">Agentic RAG Pipeline</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">实时演示</span>
                  <button
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
                  >
                    {isPlaying ? (
                      <span className="text-xs">⏸</span>
                    ) : (
                      <span className="text-xs">▶</span>
                    )}
                  </button>
                </div>
              </div>

              {/* Demo Content */}
              <div className="p-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Left: Steps */}
                  <div className="space-y-4">
                    {demoSteps.map((step, index) => (
                      <motion.div
                        key={index}
                        className={`
                          relative flex items-start gap-4 p-4 rounded-xl transition-all duration-300
                          ${activeStep === index
                            ? 'bg-neon-cyan/10 border border-neon-cyan/30'
                            : 'bg-white/5 border border-white/5'
                          }
                        `}
                        animate={{
                          opacity: activeStep === index ? 1 : 0.5,
                          x: activeStep === index ? 0 : -10,
                        }}
                      >
                        <div className={`
                          flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center
                          ${activeStep === index
                            ? 'bg-neon-cyan/20 text-neon-cyan'
                            : 'bg-white/5 text-gray-500'
                          }
                        `}>
                          <step.icon className="w-5 h-5" />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-display font-semibold text-white mb-1">
                            {step.title}
                          </h4>
                          <p className={`
                            text-sm
                            ${activeStep === index ? 'text-neon-cyan' : 'text-gray-400'}
                          `}>
                            {step.content}
                          </p>
                        </div>
                        {activeStep === index && (
                          <motion.div
                            layoutId="activeIndicator"
                            className="absolute right-4 top-1/2 -translate-y-1/2"
                          >
                            <div className="w-2 h-2 rounded-full bg-neon-cyan animate-ping" />
                          </motion.div>
                        )}
                      </motion.div>
                    ))}
                  </div>

                  {/* Right: Result Preview with Enhanced Animation */}
                  <div className="relative min-h-[400px]">
                    <AnimatePresence mode="wait">
                      {activeStep === 3 ? (
                        <motion.div
                          key="result"
                          initial={{ opacity: 0, scale: 0.95, y: 20 }}
                          animate={{ opacity: 1, scale: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.95, y: -20 }}
                          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                          className="bg-bg-secondary border border-white/10 rounded-xl p-6 relative overflow-hidden"
                        >
                          {/* Background glow effect */}
                          <motion.div
                            className="absolute -top-20 -right-20 w-40 h-40 bg-neon-cyan/20 rounded-full blur-[60px]"
                            animate={{
                              scale: [1, 1.3, 1],
                              opacity: [0.3, 0.6, 0.3],
                            }}
                            transition={{ duration: 3, repeat: Infinity }}
                          />

                          <div className="relative z-10">
                            <h4 className="font-display text-lg font-semibold text-white mb-4 flex items-center gap-2">
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: "spring", stiffness: 200, damping: 10 }}
                              >
                                <CheckCircle className="w-5 h-5 text-green-400" />
                              </motion.div>
                              检索结果
                              <motion.span
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.3 }}
                                className="text-xs text-neon-cyan ml-auto bg-neon-cyan/10 px-2 py-1 rounded-full"
                              >
                                5篇相关论文
                              </motion.span>
                            </h4>

                            <div className="space-y-3">
                              {[
                                { version: 'YOLO v1', year: '2016', improvement: '首次提出单阶段检测', source: 'You Only Look Once (CVPR 2016)', color: 'from-cyan-500 to-blue-500' },
                                { version: 'YOLO v2', year: '2017', improvement: '引入BatchNorm和Anchor', source: 'YOLO9000 (CVPR 2017)', color: 'from-blue-500 to-indigo-500' },
                                { version: 'YOLO v3', year: '2018', improvement: '多尺度预测', source: 'YOLOv3 (arXiv 2018)', color: 'from-indigo-500 to-purple-500' },
                                { version: 'YOLO v4', year: '2020', improvement: 'Bag of Freebies', source: 'YOLOv4 (arXiv 2020)', color: 'from-purple-500 to-pink-500' },
                                { version: 'YOLO v5', year: '2020', improvement: 'PyTorch实现，工程优化', source: 'Ultralytics (GitHub)', color: 'from-pink-500 to-rose-500' },
                              ].map((item, i) => (
                                <motion.div
                                  key={i}
                                  initial={{ opacity: 0, x: 20 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: 0.1 + i * 0.08 }}
                                  className="flex items-center gap-3 text-sm group cursor-pointer"
                                >
                                  <motion.div
                                    whileHover={{ scale: 1.1 }}
                                    className={`w-2 h-2 rounded-full bg-gradient-to-r ${item.color}`}
                                  />
                                  <span className="font-display font-semibold text-neon-cyan w-16">{item.version}</span>
                                  <span className="text-gray-500 w-10 text-xs">{item.year}</span>
                                  <span className="text-gray-300 flex-1 group-hover:text-white transition-colors">{item.improvement}</span>
                                </motion.div>
                              ))}
                            </div>

                            <motion.div
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              transition={{ delay: 0.6 }}
                              className="mt-4 pt-4 border-t border-white/10"
                            >
                              <div className="flex items-center gap-2 text-xs text-gray-500">
                                <Sparkles className="w-4 h-4 text-neon-cyan" />
                                <span>信息来源于5篇相关论文，点击可查看原文引用</span>
                              </div>
                            </motion.div>
                          </div>
                        </motion.div>
                      ) : (
                        <StepAnimation activeStep={activeStep} />
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Comparison Cards */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-6"
          >
            {/* Traditional Way */}
            <div className="p-6 rounded-2xl bg-bg-tertiary border border-white/10">
              <div className="flex items-center gap-3 mb-4">
                <Clock className="w-5 h-5 text-gray-500" />
                <h3 className="font-display font-semibold text-gray-400">传统方式</h3>
                <span className="ml-auto font-display text-2xl font-bold text-gray-500">2天</span>
              </div>
              <ul className="space-y-2">
                {comparisonData.traditional.steps.map((step, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-gray-500">
                    <span className="w-1.5 h-1.5 rounded-full bg-gray-600" />
                    {step}
                  </li>
                ))}
              </ul>
            </div>

            {/* AI Assistant */}
            <div className="relative p-6 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border border-neon-cyan/30">
              <div className="absolute -top-px -left-px -right-px h-px bg-gradient-to-r from-neon-cyan via-neon-blue to-neon-purple" />
              <div className="flex items-center gap-3 mb-4">
                <Zap className="w-5 h-5 text-neon-cyan" />
                <h3 className="font-display font-semibold text-white">AI论文精读助手</h3>
                <span className="ml-auto font-display text-2xl font-bold text-neon-cyan">10秒</span>
              </div>
              <ul className="space-y-2">
                {comparisonData.aiAssistant.steps.map((step, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle className="w-4 h-4 text-neon-cyan" />
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
