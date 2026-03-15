import React from 'react';
import { motion } from 'framer-motion';
import { Search, Brain, Network, FileSearch } from 'lucide-react';

const features = [
  {
    icon: Search,
    title: '智能论文搜索',
    subtitle: 'Intelligent Search',
    description: '跨平台聚合搜索（arXiv、Semantic Scholar），基于引用网络 PageRank 算法识别领域关键论文，语义搜索实现精准匹配。',
    highlights: ['跨平台聚合', 'PageRank排序', '语义匹配'],
  },
  {
    icon: Brain,
    title: 'AI 论文精读',
    subtitle: 'AI Paper Reading',
    description: '基于 Docling 自动解析论文 IMRaD 结构，生成结构化精读笔记。交互式问答基于原文回答，带引用溯源。',
    highlights: ['IMRaD解析', '结构化笔记', '引用溯源'],
  },
  {
    icon: Network,
    title: '知识图谱构建',
    subtitle: 'Knowledge Graph',
    description: '自动提取论文实体（作者、方法、数据集），构建领域知识图谱，可视化展示研究演进脉络和热点。',
    highlights: ['实体抽取', '关系构建', '可视化展示'],
  },
  {
    icon: FileSearch,
    title: '文献库智能检索',
    subtitle: 'Smart Library Search',
    description: '核心创新功能！Agentic RAG + 混合搜索 + IMRaD感知分块，在数百篇论文中秒级精准检索，跨文档信息整合。',
    highlights: ['Agentic RAG', '混合搜索', '秒级检索'],
    highlight: true,
  },
];

export const Features: React.FC = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 50 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] },
    },
  };

  return (
    <section className="relative py-24 lg:py-32 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-neon-cyan/5 rounded-full blur-[150px]" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-neon-purple/5 rounded-full blur-[120px]" />
      </div>

      <div className="container px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16 lg:mb-20"
        >
          <span className="inline-block px-4 py-1 mb-4 text-xs font-display uppercase tracking-wider text-neon-cyan border border-neon-cyan/30 rounded-full bg-neon-cyan/10">
            核心功能
          </span>
          <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4">
            四大<span className="text-gradient">创新功能</span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            从搜索到精读，从知识管理到智能检索，全方位提升科研效率
          </p>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8"
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              variants={itemVariants}
              className={`
                relative p-8 rounded-2xl overflow-hidden group
                ${feature.highlight
                  ? 'bg-gradient-to-br from-cyan-500/10 via-bg-tertiary to-purple-500/10 border border-neon-cyan/30'
                  : 'bg-bg-tertiary border border-white/10 hover:border-white/20'
                }
                transition-all duration-500
              `}
            >
              {/* Background Glow */}
              <div className={`
                absolute -top-32 -right-32 w-64 h-64 rounded-full blur-[80px]
                transition-all duration-700 group-hover:opacity-100 opacity-0
                ${feature.highlight ? 'bg-neon-cyan/20' : 'bg-neon-cyan/10'}
              `} />

              {/* Content */}
              <div className="relative z-10">
                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                  <div className={`
                    w-14 h-14 rounded-xl flex items-center justify-center
                    ${feature.highlight
                      ? 'bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 text-neon-cyan'
                      : 'bg-white/5 text-gray-400 group-hover:text-neon-cyan group-hover:bg-neon-cyan/10'
                    }
                    transition-colors duration-300
                  `}>
                    <feature.icon className="w-7 h-7" />
                  </div>
                  {feature.highlight && (
                    <span className="px-3 py-1 text-xs font-display uppercase text-neon-cyan bg-neon-cyan/10 border border-neon-cyan/30 rounded-full">
                      核心创新
                    </span>
                  )}
                </div>

                {/* Title */}
                <div className="mb-4">
                  <span className="text-xs font-display uppercase tracking-wider text-gray-500 mb-1 block">
                    {feature.subtitle}
                  </span>
                  <h3 className="font-display text-2xl font-bold text-white">
                    {feature.title}
                  </h3>
                </div>

                {/* Description */}
                <p className="text-gray-400 leading-relaxed mb-6">
                  {feature.description}
                </p>

                {/* Highlights */}
                <div className="flex flex-wrap gap-2">
                  {feature.highlights.map((highlight, i) => (
                    <span
                      key={i}
                      className={`
                        px-3 py-1 text-xs font-medium rounded-full
                        ${feature.highlight
                          ? 'bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30'
                          : 'bg-white/5 text-gray-400 border border-white/10'
                        }
                      `}
                    >
                      {highlight}
                    </span>
                  ))}
                </div>
              </div>

              {/* Hover Gradient Border Effect */}
              <div className={`
                absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none
                ${feature.highlight ? '' : 'bg-gradient-to-br from-neon-cyan/5 to-transparent'}
              `} />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};
