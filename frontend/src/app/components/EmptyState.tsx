import { Plus } from "lucide-react";

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  variant?: "default" | "papers" | "graph" | "compare";
}

// Paper stack SVG illustration
function PapersIllustration() {
  return (
    <svg viewBox="0 0 160 160" fill="none" className="w-full h-full">
      {/* Back paper */}
      <rect x="30" y="40" width="80" height="100" rx="4"
            fill="var(--color-paper-3, #f4ece1)" stroke="var(--color-rule, rgba(45,36,30,0.08))" strokeWidth="1" />
      {/* Middle paper */}
      <rect x="40" y="30" width="80" height="100" rx="4"
            fill="var(--color-paper-2, #fdfaf6)" stroke="var(--color-rule, rgba(45,36,30,0.08))" strokeWidth="1" />
      {/* Front paper */}
      <rect x="50" y="20" width="80" height="100" rx="4"
            fill="var(--color-paper-1, #ffffff)" stroke="var(--color-rule-strong, rgba(45,36,30,0.15))" strokeWidth="1.5" />
      {/* Text lines on front paper */}
      <line x1="65" y1="45" x2="115" y2="45" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="65" y1="55" x2="105" y2="55" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="65" y1="65" x2="110" y2="65" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="65" y1="75" x2="95" y2="75" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      {/* Plus button */}
      <circle cx="120" cy="100" r="16" fill="var(--color-primary, #d35400)" />
      <line x1="114" y1="100" x2="126" y2="100" stroke="white" strokeWidth="2" strokeLinecap="round" />
      <line x1="120" y1="94" x2="120" y2="106" stroke="white" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

// Network/graph SVG illustration (for "under construction")
function GraphIllustration() {
  return (
    <svg viewBox="0 0 160 160" fill="none" className="w-full h-full">
      {/* Network nodes */}
      <circle cx="50" cy="60" r="8" fill="var(--color-muted, #f4ece1)" stroke="var(--color-rule-strong, rgba(45,36,30,0.15))" strokeWidth="1" />
      <circle cx="110" cy="50" r="8" fill="var(--color-muted, #f4ece1)" stroke="var(--color-rule-strong, rgba(45,36,30,0.15))" strokeWidth="1" />
      <circle cx="80" cy="100" r="8" fill="var(--color-muted, #f4ece1)" stroke="var(--color-rule-strong, rgba(45,36,30,0.15))" strokeWidth="1" />
      <circle cx="120" cy="110" r="8" fill="var(--color-muted, #f4ece1)" stroke="var(--color-rule-strong, rgba(45,36,30,0.15))" strokeWidth="1" />
      {/* Dashed connections */}
      <line x1="50" y1="60" x2="110" y2="50" stroke="var(--color-rule, rgba(45,36,30,0.08))" strokeWidth="1.5" strokeDasharray="4 4" />
      <line x1="50" y1="60" x2="80" y2="100" stroke="var(--color-rule, rgba(45,36,30,0.08))" strokeWidth="1.5" strokeDasharray="4 4" />
      <line x1="110" y1="50" x2="80" y2="100" stroke="var(--color-rule, rgba(45,36,30,0.08))" strokeWidth="1.5" strokeDasharray="4 4" />
      <line x1="80" y1="100" x2="120" y2="110" stroke="var(--color-rule, rgba(45,36,30,0.08))" strokeWidth="1.5" strokeDasharray="4 4" />
      {/* Construction badge */}
      <circle cx="80" cy="80" r="24" fill="var(--color-paper-2, #fdfaf6)" stroke="var(--color-rule-strong, rgba(45,36,30,0.15))" strokeWidth="1" />
      {/* Wrench icon (simplified) */}
      <path d="M74 76 L86 84 M86 76 L74 84" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="2" strokeLinecap="round" opacity="0.5" />
    </svg>
  );
}

// Compare SVG illustration
function CompareIllustration() {
  return (
    <svg viewBox="0 0 160 160" fill="none" className="w-full h-full">
      {/* Left document */}
      <rect x="25" y="30" width="50" height="70" rx="4"
            fill="var(--color-paper-2, #fdfaf6)" stroke="var(--color-rule-strong, rgba(45,36,30,0.15))" strokeWidth="1" />
      <line x1="35" y1="45" x2="65" y2="45" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="1.5" strokeLinecap="round" opacity="0.3" />
      <line x1="35" y1="55" x2="60" y2="55" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="1.5" strokeLinecap="round" opacity="0.3" />
      <line x1="35" y1="65" x2="62" y2="65" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="1.5" strokeLinecap="round" opacity="0.3" />
      {/* Right document */}
      <rect x="85" y="30" width="50" height="70" rx="4"
            fill="var(--color-paper-2, #fdfaf6)" stroke="var(--color-rule-strong, rgba(45,36,30,0.15))" strokeWidth="1" />
      <line x1="95" y1="45" x2="125" y2="45" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="1.5" strokeLinecap="round" opacity="0.3" />
      <line x1="95" y1="55" x2="120" y2="55" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="1.5" strokeLinecap="round" opacity="0.3" />
      <line x1="95" y1="65" x2="122" y2="65" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="1.5" strokeLinecap="round" opacity="0.3" />
      {/* VS badge */}
      <circle cx="80" cy="65" r="12" fill="var(--color-primary, #d35400)" />
      <text x="80" y="70" textAnchor="middle" fontSize="12" fontWeight="600" fill="white">vs</text>
      {/* Construction badge */}
      <circle cx="80" cy="120" r="16" fill="var(--color-paper-3, #f4ece1)" stroke="var(--color-rule, rgba(45,36,30,0.08))" strokeWidth="1" />
      <path d="M74 116 L86 124 M86 116 L74 124" stroke="var(--color-muted-foreground, #7a6b5d)" strokeWidth="2" strokeLinecap="round" opacity="0.5" />
    </svg>
  );
}

export function EmptyState({ icon: _icon, title, description, action, variant = "default" }: EmptyStateProps) {
  const illustration = variant === "graph" ? <GraphIllustration /> :
                       variant === "compare" ? <CompareIllustration /> :
                       <PapersIllustration />;

  return (
    <div className="empty-state">
      {/* SVG illustration */}
      <div className="empty-state__illustration">
        {illustration}
      </div>

      <h3 className="empty-state__title">{title}</h3>
      {description && (
        <p className="empty-state__description">{description}</p>
      )}
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-primary text-primary-foreground rounded-full hover:bg-primary/90 transition-colors font-sans text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          {action.label}
        </button>
      )}
    </div>
  );
}

// Preset empty states
export function NoPapersState({ onUpload, isZh = false }: { onUpload: () => void; isZh?: boolean }) {
  return (
    <EmptyState
      title={isZh ? "暂无论文" : "No papers yet"}
      description={isZh ? "上传您的第一篇论文，开始使用 AI 驱动的阅读和分析功能。" : "Upload your first paper to get started with AI-powered reading and analysis."}
      action={{ label: isZh ? '上传第一篇论文' : 'Upload Paper', onClick: onUpload }}
    />
  );
}

export function NoSearchResultsState({ query }: { query: string }) {
  return (
    <EmptyState
      title="No results found"
      description={`No papers matching "${query}". Try different keywords or search external sources.`}
    />
  );
}
