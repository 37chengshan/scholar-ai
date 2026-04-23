import { Activity, HardDrive, TerminalSquare } from 'lucide-react';
import { motion } from 'motion/react';

interface SettingsStatusRailProps {
  diagnosticsLabel: string;
  storageUsageLabel: string;
  storageHint: string;
  streamLabel: string;
}

export function SettingsStatusRail({
  diagnosticsLabel,
  storageUsageLabel,
  storageHint,
  streamLabel,
}: SettingsStatusRailProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4 }}
      className="w-[260px] flex flex-col h-full bg-card flex-shrink-0 relative border-l border-border/50"
    >
      <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex items-center gap-2">
        <TerminalSquare className="w-4 h-4 text-primary" />
        <h2 className="font-serif text-lg font-bold tracking-tight">{diagnosticsLabel}</h2>
      </div>

      <div className="flex-1 flex flex-col min-h-0 bg-muted/10">
        <div className="p-5 border-b border-border/50">
          <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground mb-3 flex items-center gap-1.5">
            <HardDrive className="w-3 h-3" /> {storageUsageLabel}
          </h3>
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
              {storageHint}
            </div>
          </div>
        </div>

        <div className="flex-1 flex flex-col p-4 bg-[#1e1e1e] text-[#a9b7c6] overflow-hidden">
          <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-[#6a8759] mb-3 pb-2 border-b border-[#3c3f41]">{streamLabel}</h3>
          <div className="flex-1 overflow-y-auto flex flex-col gap-2 font-mono text-[9px] leading-[1.4] tracking-wide">
            <div className="flex gap-2 items-start mt-1">
              <span className="text-[#5c6370]">[{new Date().toLocaleTimeString('en-US', { hour12: false })}]</span>
              <span className="text-[#cc7832] w-2 h-3 bg-[#cc7832] animate-pulse shrink-0" />
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-border/50">
          <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5" /> Passive Monitor
          </div>
        </div>
      </div>
    </motion.div>
  );
}
