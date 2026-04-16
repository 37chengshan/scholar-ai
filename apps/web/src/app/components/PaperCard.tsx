/**
 * PaperCard Component
 *
 * Structured academic paper display with IMRaD structure.
 * Shows title, authors, year, abstract, sections, figures, tables.
 *
 * Part of Agent-Native architecture (D-16)
 */

import { useState } from 'react';
import { useNavigate } from 'react-router';
import { motion, AnimatePresence } from 'motion/react';
import {
  ChevronDown,
  ChevronUp,
  FileText,
  Image,
  Table,
  User,
  Calendar,
  Building,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Figure data
 */
export interface Figure {
  id: string;
  caption: string;
  page?: number;
  imageUrl?: string;
}

/**
 * Table data
 */
export interface TableData {
  id: string;
  caption: string;
  headers?: string[];
  rows?: string[][];
  page?: number;
}

/**
 * IMRaD section
 */
export interface IMRaDSection {
  type: 'introduction' | 'method' | 'results' | 'discussion';
  title: string;
  content: string;
  page?: number;
}

/**
 * PaperCard props
 */
export interface PaperCardProps {
  id: string;
  title: string;
  authors?: string[];
  year?: number;
  venue?: string;
  abstract?: string;
  imradSections?: IMRaDSection[];
  figures?: Figure[];
  tables?: TableData[];
  className?: string;
}

/**
 * Get section icon
 */
function getSectionIcon(type: string) {
  switch (type) {
    case 'introduction':
      return '📖';
    case 'method':
      return '🔬';
    case 'results':
      return '📊';
    case 'discussion':
      return '💬';
    default:
      return '📄';
  }
}

/**
 * Get section label
 */
function getSectionLabel(type: string, isZh: boolean): string {
  const labels: Record<string, { en: string; zh: string }> = {
    introduction: { en: 'Introduction', zh: '引言' },
    method: { en: 'Method', zh: '方法' },
    results: { en: 'Results', zh: '结果' },
    discussion: { en: 'Discussion', zh: '讨论' },
  };
  return isZh ? labels[type]?.zh : labels[type]?.en;
}

/**
 * CollapsibleSection Component
 */
function CollapsibleSection({
  title,
  icon,
  children,
  defaultExpanded = false,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="border border-border/50 rounded-sm overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 bg-muted/30 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium">{title}</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="p-3 text-sm text-muted-foreground">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * PaperCard Component
 *
 * Displays structured academic paper information with collapsible sections.
 */
export function PaperCard({
  id,
  title,
  authors = [],
  year,
  venue,
  abstract,
  imradSections = [],
  figures = [],
  tables = [],
  className,
}: PaperCardProps) {
  const navigate = useNavigate();
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const t = {
    abstract: isZh ? '摘要' : 'Abstract',
    sections: isZh ? '章节' : 'Sections',
    figures: isZh ? '图表' : 'Figures',
    tables: isZh ? '表格' : 'Tables',
    page: isZh ? '页' : 'p.',
    readPaper: isZh ? '阅读论文' : 'Read Paper',
  };

  const handleTitleClick = () => {
    navigate(`/read/${id}`);
  };

  return (
    <div
      className={clsx(
        'bg-card border border-border rounded-lg shadow-sm hover:shadow-md transition-shadow',
        className
      )}
    >
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        {/* Title */}
        <button
          onClick={handleTitleClick}
          className="w-full text-left font-serif text-lg font-semibold text-foreground hover:text-primary transition-colors"
        >
          {title}
        </button>

        {/* Meta: Authors • Year • Venue */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-muted-foreground">
          {authors.length > 0 && (
            <div className="flex items-center gap-1">
              <User className="w-3 h-3" />
              <span className="truncate max-w-[200px]">
                {authors.slice(0, 3).join(', ')}
                {authors.length > 3 && ' et al.'}
              </span>
            </div>
          )}
          {year && (
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              <span>{year}</span>
            </div>
          )}
          {venue && (
            <div className="flex items-center gap-1">
              <Building className="w-3 h-3" />
              <span className="truncate max-w-[150px]">{venue}</span>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Abstract */}
        {abstract && (
          <CollapsibleSection
            title={t.abstract}
            icon={<FileText className="w-4 h-4 text-muted-foreground" />}
            defaultExpanded={true}
          >
            <div className="whitespace-pre-wrap line-clamp-6">{abstract}</div>
          </CollapsibleSection>
        )}

        {/* IMRaD Sections */}
        {imradSections.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
              {t.sections}
            </div>
            {imradSections.map((section, idx) => (
              <CollapsibleSection
                key={idx}
                title={`${getSectionIcon(section.type)} ${section.title || getSectionLabel(section.type, isZh)}`}
                icon={null}
              >
                <div className="whitespace-pre-wrap">{section.content}</div>
                {section.page && (
                  <div className="text-xs text-muted-foreground mt-2">
                    {t.page} {section.page}
                  </div>
                )}
              </CollapsibleSection>
            ))}
          </div>
        )}

        {/* Figures */}
        {figures.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
              <Image className="w-3.5 h-3.5" />
              {t.figures}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {figures.slice(0, 4).map((fig, idx) => (
                <div
                  key={fig.id || idx}
                  className="border border-border/50 rounded-sm p-2 bg-muted/20"
                >
                  <div className="aspect-video bg-muted/50 rounded-sm flex items-center justify-center mb-2">
                    {fig.imageUrl ? (
                      <img
                        src={fig.imageUrl}
                        alt={fig.caption}
                        className="max-w-full max-h-full object-contain"
                      />
                    ) : (
                      <Image className="w-8 h-8 text-muted-foreground/30" />
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground line-clamp-2">
                    {fig.caption}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tables */}
        {tables.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
              <Table className="w-3.5 h-3.5" />
              {t.tables}
            </div>
            {tables.slice(0, 2).map((table, idx) => (
              <div
                key={table.id || idx}
                className="border border-border/50 rounded-sm overflow-hidden"
              >
                <div className="px-3 py-2 bg-muted/30 text-xs font-medium">
                  {table.caption}
                </div>
                {table.headers && table.rows && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-muted/20">
                        <tr>
                          {table.headers.map((header, hIdx) => (
                            <th
                              key={hIdx}
                              className="px-2 py-1.5 text-left font-medium"
                            >
                              {header}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {table.rows.slice(0, 3).map((row, rIdx) => (
                          <tr key={rIdx} className="border-t border-border/30">
                            {row.map((cell, cIdx) => (
                              <td key={cIdx} className="px-2 py-1">
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export type { PaperCardProps as PaperCardPropsType };