import { Monitor } from 'lucide-react';
import { FontSizeSelector } from '@/app/components/FontSizeSelector';

interface DisplaySectionProps {
  fontSize: 'small' | 'medium' | 'large' | 'extra-large';
  setFontSize: (value: 'small' | 'medium' | 'large' | 'extra-large') => void;
  isZh: boolean;
}

export function DisplaySection({ fontSize, setFontSize, isZh }: DisplaySectionProps) {
  const t = {
    title: isZh ? '显示设置' : 'Display Settings',
    description: isZh ? '自定义阅读与界面尺寸' : 'Customize your viewing experience',
  };

  return (
    <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col max-w-2xl">
      <div className="p-5 border-b border-border/50 flex items-center gap-3 bg-muted/20">
        <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
          <Monitor className="w-3.5 h-3.5 text-primary" />
        </div>
        <div>
          <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em] font-serif tracking-tight">{t.title}</h3>
          <p className="text-[9px] font-mono text-muted-foreground mt-0.5">{t.description}</p>
        </div>
      </div>

      <div className="p-6">
        <FontSizeSelector value={fontSize} onChange={setFontSize} />
      </div>
    </div>
  );
}
