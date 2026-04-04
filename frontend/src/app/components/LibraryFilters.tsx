import { useLanguage } from '../contexts/LanguageContext';
import { Label } from './ui/label';
import { Checkbox } from './ui/checkbox';
import { Input } from './ui/input';

interface LibraryFiltersProps {
  filters: {
    starred?: boolean;
    author?: string;
    projectId?: string;
  };
  onFilterChange: (filters: LibraryFiltersProps['filters']) => void;
}

/**
 * LibraryFilters Component
 *
 * Filter panel for Library page (D-11):
 * - Starred filter (checkbox)
 * - Author filter (text input)
 * - Project filter (select dropdown - if available)
 *
 * Follows UI-SPEC.md design constraints.
 */
export function LibraryFilters({ filters, onFilterChange }: LibraryFiltersProps) {
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    filters: isZh ? "筛选" : "Filters",
    starred: isZh ? "仅显示已星标" : "Starred Only",
    author: isZh ? "作者" : "Author",
    authorPlaceholder: isZh ? "输入作者名称" : "Enter author name",
    project: isZh ? "项目" : "Project",
    clearFilters: isZh ? "清空筛选" : "Clear Filters",
  };

  const handleStarredChange = (checked: boolean) => {
    onFilterChange({ ...filters, starred: checked || undefined });
  };

  const handleAuthorChange = (value: string) => {
    onFilterChange({ ...filters, author: value || undefined });
  };

  const handleClearFilters = () => {
    onFilterChange({});
  };

  const hasActiveFilters = filters.starred || filters.author || filters.projectId;

  return (
    <div className="space-y-4 p-4 bg-white border border-[#f4ece1] rounded-sm">
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

      <div className="space-y-4">
        {/* Starred Filter */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="starred"
            checked={filters.starred || false}
            onCheckedChange={handleStarredChange}
          />
          <Label htmlFor="starred" className="text-sm cursor-pointer">
            {t.starred}
          </Label>
        </div>

        {/* Author Filter */}
        <div className="space-y-2">
          <Label htmlFor="author" className="text-sm font-semibold">
            {t.author}
          </Label>
          <Input
            id="author"
            value={filters.author || ''}
            onChange={(e) => handleAuthorChange(e.target.value)}
            placeholder={t.authorPlaceholder}
            className="bg-[#fdfaf6]"
          />
        </div>

        {/* Project Filter - placeholder for future implementation */}
        {/* TODO: Add project dropdown when projects are implemented */}
      </div>
    </div>
  );
}