import React from 'react';
import { motion } from 'framer-motion';
import { Search, Database, Zap } from 'lucide-react';

interface StepAnimationProps {
  activeStep: number;
}

export const StepAnimation: React.FC<StepAnimationProps> = ({ activeStep }) => {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center p-6 relative min-h-[360px]">
      {/* Step 0: User Query Animation */}
      {activeStep === 0 && (
        <motion.div
          className="flex flex-col items-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Typing Animation */}
          <div className="relative bg-bg-tertiary border border-white/10 rounded-xl p-4 mb-6 w-72">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-green-400" />
              <span className="text-xs text-gray-500">用户输入</span>
            </div>
            <div className="font-mono text-sm text-gray-300 text-left">
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
              >"</motion.span>
              {['Y', 'O', 'L', 'O', '系', '列', '方', '法', '的', '演', '进', '路', '线', '是', '什', '么', '？'].map((char, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 + i * 0.08 }}
                  className="text-neon-cyan"
                >
                  {char}
                </motion.span>
              ))}
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.8 }}
              >"</motion.span>
              <motion.span
                animate={{ opacity: [1, 0, 1] }}
                transition={{ duration: 0.8, repeat: Infinity }}
                className="text-neon-cyan"
              >
                |
              </motion.span>
            </div>
          </div>

          {/* Search Pulse */}
          <motion.div
            className="relative w-20 h-20"
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <motion.div
              className="absolute inset-0 rounded-full border-2 border-neon-cyan/30"
              animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
            <div className="absolute inset-0 rounded-full bg-neon-cyan/10 flex items-center justify-center">
              <Search className="w-8 h-8 text-neon-cyan" />
            </div>
          </motion.div>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="text-gray-400 mt-4 font-display"
          >
            接收用户提问...
          </motion.p>
        </motion.div>
      )}

      {/* Step 1: Analysis Animation */}
      {activeStep === 1 && (
        <motion.div
          className="flex flex-col items-center w-full max-w-xs"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Query Decomposition */}
          <div className="relative w-full">
            {/* Main Query */}
            <motion.div
              className="bg-bg-tertiary border border-neon-cyan/30 rounded-lg px-4 py-3 text-sm text-white text-center mb-4"
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="flex items-center justify-center gap-2">
                <Search className="w-4 h-4 text-neon-cyan" />
                <span>跨文档复杂查询</span>
              </div>
            </motion.div>

            {/* Down Arrow */}
            <motion.div
              className="flex justify-center mb-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <motion.div
                animate={{ y: [0, 5, 0] }}
                transition={{ duration: 1, repeat: Infinity }}
                className="text-neon-cyan"
              >
                ↓
              </motion.div>
            </motion.div>

            {/* Sub-questions - Stacked Vertically */}
            <div className="space-y-3">
              <motion.div
                className="bg-bg-tertiary border border-white/10 rounded-lg px-4 py-3 text-sm text-gray-300"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 rounded-full bg-blue-400" />
                  <span className="text-blue-400 text-xs">子问题 1</span>
                </div>
                <div className="text-white">YOLO 是什么？</div>
              </motion.div>

              <motion.div
                className="bg-bg-tertiary border border-white/10 rounded-lg px-4 py-3 text-sm text-gray-300"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.7 }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 rounded-full bg-purple-400" />
                  <span className="text-purple-400 text-xs">子问题 2</span>
                </div>
                <div className="text-white">有哪些版本？</div>
              </motion.div>

              <motion.div
                className="bg-bg-tertiary border border-white/10 rounded-lg px-4 py-3 text-sm text-gray-300"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.9 }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 rounded-full bg-pink-400" />
                  <span className="text-pink-400 text-xs">子问题 3</span>
                </div>
                <div className="text-white">演进关系是什么？</div>
              </motion.div>
            </div>
          </div>

          <motion.div
            className="flex items-center gap-2 mt-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2 }}
          >
            <Zap className="w-5 h-5 text-neon-cyan" />
            <span className="text-gray-400 font-display">智能分析中...</span>
          </motion.div>
        </motion.div>
      )}

      {/* Step 2: Agentic Retrieval Animation */}
      {activeStep === 2 && (
        <motion.div
          className="flex flex-col items-center w-full"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Parallel Search Visualization */}
          <div className="relative w-64 h-56">
            {/* Center Hub */}
            <motion.div
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-14 h-14 rounded-full bg-gradient-to-br from-neon-cyan to-neon-blue flex items-center justify-center z-10"
              animate={{
                boxShadow: [
                  '0 0 20px rgba(0, 245, 255, 0.3)',
                  '0 0 40px rgba(0, 245, 255, 0.5)',
                  '0 0 20px rgba(0, 245, 255, 0.3)',
                ],
              }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <Database className="w-6 h-6 text-white" />
            </motion.div>

            {/* Database Nodes - positioned within bounds */}
            {[
              { x: 15, y: 15, delay: 0 },
              { x: 105, y: 5, delay: 0.1 },
              { x: 195, y: 15, delay: 0.2 },
              { x: 10, y: 95, delay: 0.3 },
              { x: 200, y: 95, delay: 0.4 },
              { x: 30, y: 170, delay: 0.5 },
              { x: 105, y: 180, delay: 0.6 },
              { x: 180, y: 170, delay: 0.7 },
            ].map((node, i) => (
              <motion.div
                key={i}
                className="absolute w-9 h-9"
                style={{ left: node.x, top: node.y }}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: node.delay }}
              >
                {/* Node */}
                <motion.div
                  className="w-9 h-9 rounded-lg bg-bg-tertiary border border-white/10 flex items-center justify-center text-[9px] text-gray-400 relative z-10"
                  animate={{
                    borderColor: ['rgba(255,255,255,0.1)', 'rgba(0,245,255,0.5)', 'rgba(255,255,255,0.1)'],
                  }}
                  transition={{ duration: 1, repeat: Infinity, delay: node.delay }}
                >
                  <span className="font-mono">{(i + 1) * 30}</span>
                </motion.div>

                {/* Data flow particles */}
                <motion.div
                  className="absolute top-1/2 left-1/2 w-1.5 h-1.5 rounded-full bg-neon-cyan z-20"
                  style={{ marginLeft: -3, marginTop: -3 }}
                  animate={{
                    x: node.x < 105 ? [0, 45] : [0, -45],
                    y: node.y < 95 ? [0, 35] : [0, -35],
                    opacity: [1, 0],
                  }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: node.delay + 0.5 }}
                />
              </motion.div>
            ))}

            {/* Connection Lines - SVG overlay */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
              {[
                { x1: 52, y1: 52, x2: 33, y2: 33 },
                { x1: 52, y1: 52, x2: 114, y2: 23 },
                { x1: 52, y1: 52, x2: 193, y2: 33 },
                { x1: 52, y1: 52, x2: 28, y2: 103 },
                { x1: 52, y1: 52, x2: 198, y2: 103 },
                { x1: 52, y1: 52, x2: 48, y2: 178 },
                { x1: 52, y1: 52, x2: 114, y2: 188 },
                { x1: 52, y1: 52, x2: 178, y2: 178 },
              ].map((line, i) => (
                <motion.line
                  key={i}
                  x1={line.x1}
                  y1={line.y1}
                  x2={line.x2}
                  y2={line.y2}
                  stroke="rgba(0, 245, 255, 0.2)"
                  strokeWidth="1"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ delay: i * 0.1 + 0.3, duration: 0.5 }}
                />
              ))}
            </svg>
          </div>

          <motion.div
            className="flex items-center gap-3 mt-6"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1 }}
          >
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-gray-500">8</span>
            </div>
            <span className="text-gray-400 font-display text-sm">Agentic 并行检索中...</span>
          </motion.div>

          {/* Progress dots */}
          <div className="flex items-center gap-2 mt-3">
            {[...Array(5)].map((_, i) => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-neon-cyan"
                animate={{
                  scale: [1, 1.5, 1],
                  opacity: [0.3, 1, 0.3],
                }}
                transition={{
                  duration: 0.8,
                  repeat: Infinity,
                  delay: i * 0.1,
                }}
              />
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
};
