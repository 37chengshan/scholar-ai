import { useTheme } from 'next-themes';
import { Moon, Sun, Monitor } from 'lucide-react';
import { Button } from './button';

const THEMES = ['light', 'dark', 'system'] as const;
type ThemeValue = (typeof THEMES)[number];

const ICONS: Record<ThemeValue, React.ComponentType<{ className?: string }>> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
};

const LABELS: Record<ThemeValue, string> = {
  light: 'Light mode',
  dark: 'Dark mode',
  system: 'System theme',
};

function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  const currentTheme: ThemeValue =
    theme === 'dark' ? 'dark' : theme === 'system' ? 'system' : 'light';
  const nextTheme: ThemeValue =
    THEMES[(THEMES.indexOf(currentTheme) + 1) % THEMES.length];
  const Icon = ICONS[currentTheme];

  return (
    <Button
      variant="ghost"
      size="icon"
      className={className}
      onClick={() => setTheme(nextTheme)}
      aria-label={`Switch to ${LABELS[nextTheme]}`}
      title={LABELS[currentTheme]}
    >
      <Icon className="size-4" />
    </Button>
  );
}

export { ThemeToggle };
