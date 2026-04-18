/**
 * AI Summary Panel Component
 *
 * Displays AI-generated summary in left sidebar:
 * - Five-paragraph format (Background, Methods, Results, Discussion, Key Contributions)
 * - Loading state while summary is generated
 * - Static display after summary available
 *
 * Requirements: D-06 (AI summary tab in left navigation)
 */

import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';
import { useLanguage } from '../contexts/LanguageContext';

interface AISummaryPanelProps {
  paperId: string;
  summary?: string;
}

export function AISummaryPanel({ paperId, summary }: AISummaryPanelProps) {
  const [displaySummary, setDisplaySummary] = useState<string | null>(null);
  const { language } = useLanguage();
  const isZh = language === 'zh';

  useEffect(() => {
    if (summary) {
      setDisplaySummary(summary);
    } else {
      // Show placeholder per UI-SPEC
      setDisplaySummary(null);
    }
  }, [summary]);

  return (
    <ScrollArea className="h-full" data-testid="ai-summary-panel">
      <div className="p-4">
        <h3 className="text-lg font-bold mb-3">
          {isZh ? 'AI 总结' : 'AI Summary'}
        </h3>

        {displaySummary === null ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">
              {isZh ? '正在生成 AI 总结...' : 'Generating AI summary...'}
            </span>
          </div>
        ) : (
          <div className="text-[15px] leading-loose whitespace-pre-wrap prose max-w-prose mx-auto magazine-body">
            {displaySummary}
          </div>
        )}
      </div>
    </ScrollArea>
  );
}