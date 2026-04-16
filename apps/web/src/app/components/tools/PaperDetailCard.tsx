/**
 * PaperDetailCard Component
 *
 * Displays read_paper tool result with title, abstract, and IMRaD sections.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { FileText, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';

interface PaperDetailCardProps {
  result: {
    paper_id: string;
    title: string;
    abstract?: string;
    imrad_sections?: Record<string, string>;
  };
}

const IMRAD_ORDER = ['introduction', 'methods', 'results', 'discussion'];

const IMRAD_LABELS: Record<string, { zh: string; en: string }> = {
  introduction: { zh: '引言', en: 'Introduction' },
  methods: { zh: '方法', en: 'Methods' },
  results: { zh: '结果', en: 'Results' },
  discussion: { zh: '讨论', en: 'Discussion' },
};

export function PaperDetailCard({ result }: PaperDetailCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const sections = result.imrad_sections ?? {};
  const availableSections = IMRAD_ORDER.filter((key) => sections[key]);
  const abstract = result.abstract ?? '';
  const showAbstractExpand = abstract.length > 200;
  const abstractPreview = showAbstractExpand && !expanded ? abstract.slice(0, 200) + '...' : abstract;

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      <div className="p-3">
        <div className="flex items-start gap-2">
          <FileText className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-serif font-semibold leading-snug">{result.title}</h4>
          </div>
        </div>

        {/* Abstract */}
        {abstract && (
          <div className="mt-3">
            <p className="text-xs text-muted-foreground leading-relaxed">{abstractPreview}</p>
            {showAbstractExpand && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs text-primary mt-1 hover:underline flex items-center gap-1"
              >
                {expanded ? (
                  <>
                    <ChevronUp className="w-3 h-3" />
                    {isZh ? '收起' : 'Show less'}
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3 h-3" />
                    {isZh ? '阅读更多' : 'Read more'}
                  </>
                )}
              </button>
            )}
          </div>
        )}

        {/* IMRaD Sections */}
        {availableSections.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {availableSections.map((key) => {
              const label = IMRAD_LABELS[key] ?? { zh: key, en: key };
              return (
                <div key={key} className="flex items-start gap-2 text-xs">
                  <span className="text-muted-foreground font-medium min-w-[3em]">
                    {isZh ? label.zh : label.en}
                  </span>
                  <span className="text-muted-foreground/60 truncate">{sections[key]}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Link to Read page */}
        <a
          href={`/read?paperId=${result.paper_id}`}
          className="flex items-center gap-1 text-xs text-primary mt-3 hover:underline"
        >
          <ExternalLink className="w-3 h-3" />
          {isZh ? '打开阅读页面' : 'Open in Read'}
        </a>
      </div>
    </div>
  );
}
