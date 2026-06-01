import { useTheme } from 'next-themes';
import { Moon, Sun, Monitor } from 'lucide-react';
import { clsx } from 'clsx';

const OPTIONS = [
  { value: 'light', icon: Sun, labelZh: '浅色', labelEn: 'Light' },
  { value: 'dark', icon: Moon, labelZh: '深色', labelEn: 'Dark' },
  { value: 'system', icon: Monitor, labelZh: '跟随系统', labelEn: 'System' },
] as const;

interface ThemeSelectorProps {
  isZh: boolean;
}

export function ThemeSelector({ isZh }: ThemeSelectorProps) {
  const { theme, setTheme } = useTheme();
  const currentTheme = theme ?? 'light';

  return (
    <div className="flex flex-col gap-2">
      <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
        {isZh ? '主题' : 'Theme'}
      </label>
      <div className="flex gap-2">
        {OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const isActive = currentTheme === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => setTheme(opt.value)}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 rounded-sm border text-xs font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                  : 'bg-card border-border/50 text-foreground/70 hover:border-border hover:text-foreground',
              )}
              aria-pressed={isActive}
              aria-label={isZh ? opt.labelZh : opt.labelEn}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{isZh ? opt.labelZh : opt.labelEn}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
