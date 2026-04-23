import type { ReactNode } from 'react';
import { motion } from 'motion/react';

interface SettingsSectionLayoutProps {
  title: string;
  versionLabel: string;
  children: ReactNode;
}

export function SettingsSectionLayout({ title, versionLabel, children }: SettingsSectionLayoutProps) {
  return (
    <div className="flex-1 flex flex-col h-full bg-background min-w-[500px] border-r border-border/50 relative">
      <div className="px-6 py-4 border-b border-border/50 bg-background/90 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center shadow-sm">
        <div className="flex items-baseline gap-3">
          <h2 className="font-serif text-2xl font-black tracking-tight capitalize">{title}</h2>
          <span className="text-[9px] font-mono tracking-[0.2em] text-muted-foreground uppercase">{versionLabel}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8 lg:p-12 flex flex-col gap-10 bg-muted/5">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="flex flex-col gap-8"
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}
