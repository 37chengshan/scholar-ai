import React from 'react';
import { motion } from 'framer-motion';
import { Github, ExternalLink, Heart } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="relative py-16 overflow-hidden">
      {/* Top Border */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      {/* Background Elements */}
      <div className="absolute bottom-0 left-1/4 w-[300px] h-[300px] bg-neon-cyan/5 rounded-full blur-[100px]" />

      <div className="container px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="max-w-6xl mx-auto">
          {/* Main Content */}
          <div className="flex flex-col lg:flex-row items-center justify-between gap-8 mb-12">
            {/* Brand */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="text-center lg:text-left"
            >
              <h3 className="font-display text-2xl font-bold text-white mb-2">
                AI论文<span className="text-neon-cyan">精读助手</span>
              </h3>
              <p className="text-gray-500 text-sm">
                基于 Agentic RAG 的智能学术阅读平台
              </p>
            </motion.div>

            {/* Links */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="flex items-center gap-6"
            >
              <a
                href="#"
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                <Github className="w-5 h-5" />
                <span className="text-sm">GitHub</span>
              </a>
              <a
                href="#"
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/20 transition-colors"
              >
                <ExternalLink className="w-5 h-5" />
                <span className="text-sm">在线演示</span>
              </a>
            </motion.div>
          </div>

          {/* Tech Stack */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="py-8 border-t border-white/5"
          >
            <div className="text-center">
              <p className="text-gray-500 text-sm mb-4">技术栈</p>
              <div className="flex flex-wrap items-center justify-center gap-3">
                {['React', 'Tailwind CSS', 'PaperQA2', 'Docling', 'PGVector', 'Neo4j'].map((tech) => (
                  <span
                    key={tech}
                    className="px-3 py-1 text-xs font-medium text-gray-400 bg-white/5 border border-white/10 rounded-full"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Copyright */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="pt-8 border-t border-white/5 text-center"
          >
            <p className="text-gray-500 text-sm flex items-center justify-center gap-1">
              Made with <Heart className="w-4 h-4 text-neon-pink fill-neon-pink" /> by AI论文精读助手团队
            </p>
            <p className="text-gray-600 text-xs mt-2">
              © 2026 AI Paper Assistant. Open source under Apache 2.0 License.
            </p>
          </motion.div>
        </div>
      </div>
    </footer>
  );
};
