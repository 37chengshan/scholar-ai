import { Globe } from 'lucide-react';
import { clsx } from 'clsx';

interface LocalizationSectionProps {
  language: 'en' | 'zh';
  setLanguage: (language: 'en' | 'zh') => void;
}

export function LocalizationSection({ language, setLanguage }: LocalizationSectionProps) {
  return (
    <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col max-w-2xl">
      <div className="p-5 border-b border-border/50 flex items-center gap-3 bg-muted/20">
        <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
          <Globe className="w-3.5 h-3.5 text-primary" />
        </div>
        <div>
          <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em]">Language Settings</h3>
          <p className="text-[9px] font-mono text-muted-foreground mt-0.5">Interface Translation</p>
        </div>
      </div>

      <div className="p-6 flex flex-col gap-4">
        <label className="text-[9px] font-bold tracking-[0.2em] uppercase text-foreground/70">Display Language</label>
        <div className="flex gap-4">
          <button
            onClick={() => setLanguage('en')}
            className={clsx(
              'flex-1 border p-4 rounded-sm transition-colors text-center font-bold tracking-widest text-[11px] uppercase',
              language === 'en' ? 'border-primary bg-primary/10 text-primary shadow-sm' : 'border-border/50 hover:border-primary/50 text-foreground/70',
            )}
          >
            English
          </button>
          <button
            onClick={() => setLanguage('zh')}
            className={clsx(
              'flex-1 border p-4 rounded-sm transition-colors text-center font-bold tracking-widest text-[11px] uppercase',
              language === 'zh' ? 'border-primary bg-primary/10 text-primary shadow-sm' : 'border-border/50 hover:border-primary/50 text-foreground/70',
            )}
          >
            中文 (Chinese)
          </button>
        </div>
      </div>
    </div>
  );
}
