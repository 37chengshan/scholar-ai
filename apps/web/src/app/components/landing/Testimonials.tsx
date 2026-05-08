import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Quote, ChevronLeft, ChevronRight, Star } from "lucide-react";
import { InteractiveText } from "./InteractiveText";

const testimonials = [
  {
    id: 1,
    name: "张明远教授",
    title: "斯坦福大学 计算机科学系",
    avatar: "Z",
    content: "ScholarAI 颠覆了我们实验室的文献 Review 惯例。从前要花几周摸索的脉络，现在一两天就能全景展现。对结构化信息的精准把握更是出乎意料的好。",
    rating: 5,
    metric: "文献梳理时间节省",
    metricValue: "70%",
  },
  {
    id: 2,
    name: "Sophia Li",
    title: "麻省理工学院 计算生物学博士后",
    avatar: "L",
    content: "作为一个深陷在跨学科前沿海量数据中的研究者，ScholarAI 是我的救生圈。基于图的关联能一下子打通思维死路，跨模态解读能力也让我能无缝吞吐大量生僻图表。",
    rating: 5,
    metric: "日均文献消化量",
    metricValue: "3x 提升",
  },
  {
    id: 3,
    name: "Alex Wang",
    title: "Top 3 AI Lab 算法研究员",
    avatar: "W",
    content: "令人惊叹的 Agentic RAG 底层调优。它的检索不仅仅是找字面相似，它更像是个带了脑子的高级学术助理，抓取出的隐性逻辑极其精准，已经成了我们团队日常科研的基础设施。",
    rating: 5,
    metric: "隐语境洞察准确率",
    metricValue: "95%+",
  },
  {
    id: 4,
    name: "陈思琪",
    title: "知名医学研究中心 资深PI",
    avatar: "C",
    content: "医学临床论文极其繁复，ScholarAI 在保证零幻觉的同时大大压缩了我们的查证成本。不用自己人工对比一堆长表和附录数据，效率提升是肉眼可见的巨大跃迁。",
    rating: 5,
    metric: "核心论点提取耗时",
    metricValue: "断崖式降低",
  },
];

export function Testimonials() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [direction, setDirection] = useState(0);

  const slideVariants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 300 : -300,
      opacity: 0,
    }),
    center: {
      zIndex: 1,
      x: 0,
      opacity: 1,
    },
    exit: (direction: number) => ({
      zIndex: 0,
      x: direction < 0 ? 300 : -300,
      opacity: 0,
    }),
  };

  const paginate = (newDirection: number) => {
    setDirection(newDirection);
    setCurrentIndex((prevIndex) => {
      let nextIndex = prevIndex + newDirection;
      if (nextIndex < 0) nextIndex = testimonials.length - 1;
      if (nextIndex >= testimonials.length) nextIndex = 0;
      return nextIndex;
    });
  };

  const current = testimonials[currentIndex];

  return (
    <div className="relative">
      {/* Section Header */}
      <div className="text-center mb-16 relative z-10">
        <h2 className="text-sm font-bold tracking-[0.3em] uppercase text-primary mb-3 font-serif tracking-tight">
          <InteractiveText text="Testimonials" />
        </h2>
        <h3 className="text-4xl md:text-5xl font-bold font-serif tracking-tight">
          <InteractiveText text="来自科研工作者的真实反馈" />
        </h3>
      </div>

      {/* Main Testimonial Card */}
      <div className="max-w-4xl mx-auto relative">
        {/* Quote Icon */}
        <div className="absolute -top-8 left-8 w-16 h-16 bg-primary rounded-full flex items-center justify-center z-20">
          <Quote className="w-8 h-8 text-white" />
        </div>

        {/* Card */}
        <div className="bg-white border border-border/50 rounded-2xl p-8 md:p-12 shadow-xl relative overflow-hidden min-h-[400px]">
          {/* Decorative Elements */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-secondary/5 rounded-full translate-y-1/2 -translate-x-1/2" />

          {/* Content */}
          <div className="relative z-10">
            <AnimatePresence initial={false} custom={direction} mode="wait">
              <motion.div
                key={currentIndex}
                custom={direction}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{
                  x: { type: "spring", stiffness: 300, damping: 30 },
                  opacity: { duration: 0.2 },
                }}
                className="space-y-8"
              >
                {/* Rating */}
                <div className="flex gap-1">
                  {Array.from({ length: current.rating }).map((_, i) => (
                    <Star key={i} className="w-5 h-5 text-primary fill-primary" />
                  ))}
                </div>

                {/* Quote */}
                <blockquote className="text-xl md:text-2xl leading-relaxed text-foreground/90 font-serif relative z-10 pointer-events-none">
                  "<InteractiveText text={current.content} />"
                </blockquote>

                {/* Author Info */}
                <div className="flex items-center justify-between flex-wrap gap-4 pt-6 border-t border-border/30">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-full bg-primary flex items-center justify-center text-white text-xl font-bold">
                      {current.avatar}
                    </div>
                    <div className="relative z-10 pointer-events-none">
                      <h4 className="font-bold text-lg">
                        <InteractiveText text={current.name} />
                      </h4>
                      <p className="text-sm text-foreground/60">
                        <InteractiveText text={current.title} />
                      </p>
                    </div>
                  </div>

                  {/* Metric */}
                  <div className="text-right">
                    <div className="text-3xl font-bold text-primary font-serif tracking-tight">
                      <InteractiveText text={current.metricValue} />
                    </div>
                    <div className="text-sm text-foreground/60">
                      <InteractiveText text={current.metric} />
                    </div>
                  </div>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Navigation Arrows */}
          <div className="absolute bottom-8 right-8 flex gap-2 z-20">
            <button
              type="button"
              onClick={() => paginate(-1)}
              className="w-12 h-12 rounded-full border border-border/50 flex items-center justify-center hover:bg-primary hover:text-white hover:border-primary transition-colors relative z-50"
              aria-label="查看上一条用户评价"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              type="button"
              onClick={() => paginate(1)}
              className="w-12 h-12 rounded-full border border-border/50 flex items-center justify-center hover:bg-primary hover:text-white hover:border-primary transition-colors relative z-50"
              aria-label="查看下一条用户评价"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Dots Indicator */}
        <div className="flex justify-center gap-2 mt-8">
          {testimonials.map((_, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setDirection(idx > currentIndex ? 1 : -1);
                setCurrentIndex(idx);
              }}
              className={`w-2 h-2 rounded-full transition-[width,background-color] relative z-50 ${
                idx === currentIndex
                  ? "w-8 bg-primary"
                  : "bg-border hover:bg-primary/50"
              }`}
              aria-label={`查看第 ${idx + 1} 条用户评价`}
              aria-pressed={idx === currentIndex}
            />
          ))}
        </div>
      </div>

      {/* Trust Badges */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.3 }}
        className="mt-20 pt-12 border-t border-border/30"
      >
        <p className="text-center text-sm text-foreground/50 mb-8 tracking-widest uppercase">
          <InteractiveText text="受到众多顶尖高校与研究机构信赖" />
        </p>
        <div className="flex flex-wrap justify-center items-center gap-8 md:gap-16 opacity-40">
          {["清华大学", "北京大学", "中科院", "上海交通大学", "浙江大学"].map((uni) => (
            <span key={uni} className="text-lg font-bold tracking-wider relative z-10 pointer-events-none">
              <InteractiveText text={uni} />
            </span>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
