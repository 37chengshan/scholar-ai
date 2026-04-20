/**
 * Section Tree Component
 *
 * Supports heterogeneous section payloads from parser output:
 * - IMRaD keys: introduction/methods/results/discussion/conclusion
 * - Section arrays: sections/section_ranges
 * - Page keys: start/end, page_start/page_end, page/pageNumber
 */

type UnknownRecord = Record<string, unknown>;

interface SectionItem {
  key: string;
  title: string;
  start: number;
  end: number;
}

interface SectionTreeProps {
  imrad: unknown;
  onPageSelect: (page: number) => void;
  currentPage: number;
  isZh?: boolean;
}

const SECTION_LABELS: Record<string, { zh: string; en: string }> = {
  introduction: { zh: '引言', en: 'Introduction' },
  methods: { zh: '方法', en: 'Methods' },
  methodology: { zh: '方法', en: 'Methodology' },
  approach: { zh: '方法', en: 'Approach' },
  materials: { zh: '材料', en: 'Materials' },
  results: { zh: '结果', en: 'Results' },
  evaluation: { zh: '评估', en: 'Evaluation' },
  discussion: { zh: '讨论', en: 'Discussion' },
  conclusion: { zh: '结论', en: 'Conclusion' },
  related_work: { zh: '相关工作', en: 'Related Work' },
  abstract: { zh: '摘要', en: 'Abstract' },
};

function toSectionTitle(rawKey: string, isZh: boolean): string {
  const normalized = rawKey.trim().toLowerCase().replace(/[\s-]+/g, '_');
  const known = SECTION_LABELS[normalized];
  if (known) {
    return isZh ? known.zh : known.en;
  }

  if (isZh) {
    return rawKey;
  }

  return rawKey
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.max(1, Math.floor(value));
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.max(1, Math.floor(parsed)) : null;
  }
  return null;
}

function parseRange(data: unknown): { start: number; end: number } | null {
  if (!data || typeof data !== 'object') {
    return null;
  }
  const range = data as UnknownRecord;

  const start =
    toNumber(range.start) ??
    toNumber(range.page_start) ??
    toNumber(range.pageStart) ??
    toNumber(range.page) ??
    toNumber(range.pageNumber);
  const end =
    toNumber(range.end) ??
    toNumber(range.page_end) ??
    toNumber(range.pageEnd) ??
    start;

  if (!start) {
    return null;
  }

  return {
    start,
    end: end && end >= start ? end : start,
  };
}

function parseFromArray(items: unknown[], isZh: boolean): SectionItem[] {
  return items
    .map((item, index) => {
      if (!item || typeof item !== 'object') {
        return null;
      }
      const raw = item as UnknownRecord;
      const titleCandidate =
        (typeof raw.title === 'string' && raw.title) ||
        (typeof raw.name === 'string' && raw.name) ||
        (typeof raw.section === 'string' && raw.section) ||
        `Section ${index + 1}`;
      const range = parseRange(raw);
      if (!range) {
        return null;
      }
      return {
        key: `${titleCandidate}-${range.start}-${range.end}-${index}`,
        title: toSectionTitle(titleCandidate, isZh),
        start: range.start,
        end: range.end,
      };
    })
    .filter((section): section is SectionItem => section !== null)
    .sort((a, b) => a.start - b.start);
}

function parseSections(imrad: unknown, isZh: boolean): SectionItem[] {
  if (!imrad) {
    return [];
  }

  if (Array.isArray(imrad)) {
    return parseFromArray(imrad, isZh);
  }

  if (typeof imrad !== 'object') {
    return [];
  }

  const record = imrad as UnknownRecord;
  if (Array.isArray(record.sections)) {
    const fromSections = parseFromArray(record.sections, isZh);
    if (fromSections.length > 0) {
      return fromSections;
    }
  }
  if (Array.isArray(record.section_ranges)) {
    const fromRanges = parseFromArray(record.section_ranges, isZh);
    if (fromRanges.length > 0) {
      return fromRanges;
    }
  }

  return Object.entries(record)
    .map(([key, value]) => {
      const range = parseRange(value);
      if (!range) {
        return null;
      }
      return {
        key,
        title: toSectionTitle(key, isZh),
        start: range.start,
        end: range.end,
      };
    })
    .filter((section): section is SectionItem => section !== null)
    .sort((a, b) => a.start - b.start);
}

export function SectionTree({ imrad, onPageSelect, currentPage, isZh = true }: SectionTreeProps) {
  const sections = parseSections(imrad, isZh);

  if (sections.length === 0) {
    return (
      <div className="p-4" data-testid="section-tree">
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          {isZh ? '暂无可导航章节，稍后可在完成解析后查看。' : 'No navigable sections yet. Try again after parsing completes.'}
        </div>
      </div>
    );
  }

  return (
    <div className="p-3" data-testid="section-tree">
      <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {isZh ? '章节导航' : 'Sections'}
      </h3>
      <div className="space-y-1.5">
        {sections.map((section) => {
          const isActive = currentPage >= section.start && currentPage <= section.end;
          return (
            <button
              key={section.key}
              onClick={() => onPageSelect(section.start)}
              data-testid={`section-${section.key.toLowerCase()}`}
              className={[
                'w-full rounded-md border px-3 py-2 text-left transition-all',
                isActive
                  ? 'border-primary/40 bg-primary/10 text-primary shadow-sm'
                  : 'border-transparent bg-white/70 hover:border-border hover:bg-accent/40',
              ].join(' ')}
            >
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium">{section.title}</span>
                <span className="ml-auto text-[10px] text-muted-foreground">
                  p.{section.start}-{section.end}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}