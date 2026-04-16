/**
 * ReferenceListCard Component
 *
 * Displays extract_references tool result as numbered academic-style references.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useLanguage } from '../../contexts/LanguageContext';
import { Quote, ExternalLink } from 'lucide-react';

interface Reference {
  title: string;
  authors?: string[];
  year?: number;
  doi?: string;
}

interface ReferenceListCardProps {
  result: {
    references: Reference[];
  };
}

function formatAuthors(authors?: string[], isZh?: boolean): string {
  if (!authors || authors.length === 0) return isZh ? '未知作者' : 'Unknown authors';
  if (authors.length === 1) return authors[0];
  if (authors.length === 2) return authors.join(' & ');
  return `${authors[0]} ${isZh ? '等' : 'et al.'}`;
}

export function ReferenceListCard({ result }: ReferenceListCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const references = result.references ?? [];

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      <div className="flex items-center gap-2 p-3 border-b border-border/50">
        <Quote className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold">
          {isZh ? `提取的引用文献 (${references.length})` : `Extracted references (${references.length})`}
        </span>
      </div>
      <div className="divide-y divide-border/20">
        {references.map((ref, idx) => (
          <div key={idx} className="px-3 py-2.5 hover:bg-muted/30 transition-colors">
            <div className="flex items-start gap-2">
              <span className="text-xs font-mono text-muted-foreground mt-0.5 flex-shrink-0">
                [{idx + 1}]
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-foreground">
                  {formatAuthors(ref.authors, isZh)}.{' '}
                  <span className="font-medium">{ref.title}.</span>{' '}
                  {ref.year && <span>{ref.year}. </span>}
                </div>
                {ref.doi && (
                  <a
                    href={`https://doi.org/${ref.doi}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary mt-1 hover:underline"
                  >
                    <ExternalLink className="w-3 h-3" />
                    DOI: {ref.doi}
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
      {references.length === 0 && (
        <div className="px-3 py-4 text-center text-xs text-muted-foreground">
          {isZh ? '未找到引用文献' : 'No references found'}
        </div>
      )}
    </div>
  );
}
