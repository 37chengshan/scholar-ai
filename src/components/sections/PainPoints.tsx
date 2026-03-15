import React from 'react';
import { motion } from 'framer-motion';
import { Search, Clock, Puzzle, Database } from 'lucide-react';

const painPoints = [
  {
    icon: Search,
    title: '搜索分散低效',
    description: 'Google Scholar、arXiv、IEEE等平台割裂，查找一篇关键论文平均耗时30分钟',
    stat: '30min',
    statLabel: '平均查找时间',
  },
  {
    icon: Clock,
    title: '精读效率低',
    description: '读一篇论文需数小时，难以快速提取核心方法与实验数据',
    stat: '60%',
    statLabel: '时间花在阅读上',
  },
  {
    icon: Puzzle,
    title: '知识体系化难',
    description: '论文越读越多，但知识零散，难以形成系统认知',
    stat: '碎片化',
    statLabel: '知识孤岛严重',
  },
  {
    icon: Database,
    title: '文献库检索难',
    description: '文献库中数百篇论文，模型上下文有限，无法快速准确查找资料',
    stat: '2天',
    statLabel: '人工整理耗时',
    highlight: true,
  },
];

export const PainPoints: React.FC = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 40 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] },
    },
  };

  return (
    <section className="relative py-24 lg:py-32 overflow-hidden">
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-neon-cyan/30 to-transparent" />
      <div className="absolute top-1/2 right-0 w-[300px] h-[300px] bg-neon-purple/5 rounded-full blur-[100px]" />

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
            核心痛点
          </span>
          <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4">
            科研人员的<span className="text-gradient">四大困扰</span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            每天花费大量时间在低效的信息检索与阅读上
          </p>
        </motion.div>

        {/* Pain Points Grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8"
        >
          {painPoints.map((point, index) => (
            <motion.div
              key={index}
              variants={itemVariants}
              className={`
                relative p-8 rounded-2xl overflow-hidden group
                ${point.highlight
                  ? 'bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border border-neon-cyan/30'
                  : 'bg-bg-tertiary border border-white/10 hover:border-white/20'
                }
                transition-all duration-500 hover:-translate-y-2
              `}
            >
              {/* Highlight Effect */}
              {point.highlight && (
                <div className="absolute inset-0 bg-gradient-to-br from-neon-cyan/5 to-neon-purple/5" />
              )}

              {/* Glow Effect on Hover */}
              <div className={`
                absolute -top-20 -right-20 w-40 h-40 rounded-full blur-3xl
                transition-all duration-500 group-hover:opacity-100 opacity-0
                ${point.highlight ? 'bg-neon-cyan/30' : 'bg-neon-cyan/20'}
              `} />

              <div className="relative z-10">
                {/* Icon & Title Row */}
                <div className="flex items-start gap-4 mb-4">
                  <div className={`
                    flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center
                    ${point.highlight
                      ? 'bg-neon-cyan/20 text-neon-cyan'
                      : 'bg-white/5 text-gray-400 group-hover:text-neon-cyan group-hover:bg-neon-cyan/10'
                    }
                    transition-colors duration-300
                  `}>
                    <point.icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-display text-xl font-semibold text-white mb-2">
                      {point.title}
                    </h3>
                    <p className="text-gray-400 text-sm leading-relaxed">
                      {point.description}
                    </p>
                  </div>
                </div>

                {/* Stat */}
                <div className="mt-6 pt-6 border-t border-white/5">
                  <div className="flex items-baseline gap-2">
                    <span className={`
                      font-display text-3xl font-bold
                      ${point.highlight ? 'text-neon-cyan' : 'text-white'}
                    `}>
                      {point.stat}
                    </span>
                    <span className="text-gray-500 text-sm">{point.statLabel}</span>
                  </div>
                </div>
              </div>

              {/* Corner Decoration */}
              {point.highlight && (
                <div className="absolute top-4 right-4">
                  <span className="px-2 py-1 text-xs font-display uppercase text-neon-cyan bg-neon-cyan/10 border border-neon-cyan/30 rounded">
                    最大痛点
                  </span>
                </div>
              )}
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};
