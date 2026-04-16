import { useLanguage } from '../contexts/LanguageContext';
import { Label } from './ui/label';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';

interface SearchFiltersProps {
  filters: {
    sortBy?: 'relevance' | 'date';
  };
  onFilterChange: (filters: SearchFiltersProps['filters']) => void;
}

/**
 * SearchFilters Component
 *
 * Sort panel for Search page:
 * - Sort by (Relevance, Date)
 */
export function SearchFilters({ filters, onFilterChange }: SearchFiltersProps) {
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    sortBy: isZh ? "排序方式" : "Sort By",
    relevance: isZh ? "相关性" : "Relevance",
    date: isZh ? "时间" : "Date",
  };

  const handleSortChange = (value: string) => {
    onFilterChange({ sortBy: value as 'relevance' | 'date' });
  };

  return (
    <div className="space-y-3">
      <Label className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5">
        {t.sortBy}
      </Label>
      <RadioGroup
        value={filters.sortBy || 'relevance'}
        onValueChange={handleSortChange}
        className="space-y-2"
      >
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="relevance" id="sort-relevance" />
          <Label htmlFor="sort-relevance" className="text-xs cursor-pointer">
            {t.relevance}
          </Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="date" id="sort-date" />
          <Label htmlFor="sort-date" className="text-xs cursor-pointer">
            {t.date}
          </Label>
        </div>
      </RadioGroup>
    </div>
  );
}