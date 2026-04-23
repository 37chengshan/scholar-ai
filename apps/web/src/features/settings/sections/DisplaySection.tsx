import { Monitor } from 'lucide-react';
import { FontSizeSelector } from '@/app/components/FontSizeSelector';

interface DisplaySectionProps {
  fontSize: 'small' | 'medium' | 'large' | 'extra-large';
  setFontSize: (value: 'small' | 'medium' | 'large' | 'extra-large') => void;
}

export function DisplaySection({ fontSize, setFontSize }: DisplaySectionProps) {
  return (
    <div className="bg-card border border-border/50 rounded-sm shadow-sm flex flex-col max-w-2xl">
      <div className="p-5 border-b border-border/50 flex items-center gap-3 bg-muted/20">
        <div className="w-6 h-6 bg-background border border-border/50 flex items-center justify-center rounded-sm">
          <Monitor className="w-3.5 h-3.5 text-primary" />
        </div>
        <div>
          <h3 className="font-sans text-[11px] font-bold uppercase tracking-[0.2em]">Display Settings</h3>
          <p className="text-[9px] font-mono text-muted-foreground mt-0.5">Customize your viewing experience</p>
        </div>
      </div>

      <div className="p-6">
        <FontSizeSelector value={fontSize} onChange={setFontSize} />
      </div>
    </div>
  );
}
