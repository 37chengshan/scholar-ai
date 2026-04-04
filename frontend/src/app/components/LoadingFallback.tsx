import { motion } from "motion/react";

export function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col items-center gap-4"
      >
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-muted-foreground text-sm font-medium"
        >
          加载中...
        </motion.span>
      </motion.div>
    </div>
  );
}