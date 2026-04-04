import { useLanguage } from '../contexts/LanguageContext';
import { Label } from './ui/label';
import { Checkbox } from './ui/checkbox';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';

interface SearchFiltersProps {
  filters: {
    sources?: string[];
    yearFrom?: number;
    yearTo?: number;
    author?: string;
    sortBy?: 'relevance' | 'date';
  };
  onFilterChange: (filters: SearchFiltersProps['filters']) => void;
}

/**
 * SearchFilters Component
 *
 * Filter panel for Search page (D-13):
 * - Source filters (Semantic Scholar, arXiv, CrossRef, Internal)
 * - Year range
 * - Author
 * - Sort by (Relevance, Date)
 *
 * Follows UI-SPEC.md design constraints.
 */
export function SearchFilters({ filters, onFilterChange }: SearchFiltersProps) {
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    filters: isZh ? "筛选" : "Filters",
    sources: isZh ? "来源" : "Sources",
    semanticScholar: "Semantic Scholar",
    arxiv: "arXiv",
    crossRef: "CrossRef",
    internal: isZh ? "内部库" : "Internal Library",
    sortBy: isZh ? "排序方式" : "Sort By",
    relevance: isZh ? "相关性" : "Relevance",
    date: isZh ? "时间" : "Date",
    clearFilters: isZh ? "清空筛选" : "Clear Filters",
  };

  const sources = [
    { id: 'semantic-scholar', label: t.semanticScholar },
    { id: 'arxiv', label: t.arxiv },
    { id: 'crossref', label: t.crossRef },
    { id: 'internal', label: t.internal },
  ];

  const handleSourceChange = (sourceId: string, checked: boolean) => {
    const currentSources = filters.sources || [];
    const newSources = checked
      ? [...currentSources, sourceId]
      : currentSources.filter(s => s !== sourceId);

    onFilterChange({ ...filters, sources: newSources.length > 0 ? newSources : undefined });
  };

  const handleSortChange = (value: string) => {
    onFilterChange({ ...filters, sortBy: value as 'relevance' | 'date' });
  };

  const handleClearFilters = () => {
    onFilterChange({});
  };

  const hasActiveFilters = (filters.sources && filters.sources.length > 0) || filters.author || filters.yearFrom;

  return (
    <div className="space-y-6 p-4 bg-white border border-[#f4ece1] rounded-sm">
      <div className="flex justify-between items-center">
        <Label className="text-sm font-semibold">{t.filters}</Label>
        {hasActiveFilters && (
          <button
            onClick={handleClearFilters}
            className="text-xs text-muted-foreground hover:text-[#d35400] transition-colors"
          >
            {t.clearFilters}
          </button>
        )}
      </div>

      {/* Source Filters */}
      <div className="space-y-3">
        <Label className="text-sm font-semibold">{t.sources}</Label>
        <div className="space-y-2">
          {sources.map((source) => (
            <div key={source.id} className="flex items-center space-x-2">
              <Checkbox
                id={source.id}
                checked={filters.sources?.includes(source.id) || false}
                onCheckedChange={(checked) => handleSourceChange(source.id, checked as boolean)}
              />
              <Label htmlFor={source.id} className="text-sm cursor-pointer">
                {source.label}
              </Label>
            </div>
          ))}
        </div>
      </div>

      {/* Sort By */}
      <div className="space-y-3">
        <Label className="text-sm font-semibold">{t.sortBy}</Label>
        <RadioGroup
          value={filters.sortBy || 'relevance'}
          onValueChange={handleSortChange}
          className="space-y-2"
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="relevance" id="sort-relevance" />
            <Label htmlFor="sort-relevance" className="text-sm cursor-pointer">
              {t.relevance}
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="date" id="sort-date" />
            <Label htmlFor="sort-date" className="text-sm cursor-pointer">
              {t.date}
            </Label>
          </div>
        </RadioGroup>
      </div>
    </div>
  );
}