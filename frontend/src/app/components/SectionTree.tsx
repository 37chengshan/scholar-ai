/**
 * Section Tree Component
 *
 * IMRaD structure navigation for PDF papers:
 * - Introduction, Methods, Results, Discussion sections
 * - Shows page range for each section
 * - Highlights current section based on active page
 * - Click to jump to section start page
 *
 * Requirements: PAGE-06 (Read page section navigation)
 */

interface IMRaDSection {
  start: number;
  end: number;
}

interface IMRaDStructure {
  introduction?: IMRaDSection;
  methods?: IMRaDSection;
  results?: IMRaDSection;
  discussion?: IMRaDSection;
}

interface SectionTreeProps {
  imrad: IMRaDStructure | null;
  onPageSelect: (page: number) => void;
  currentPage: number;
}

export function SectionTree({ imrad, onPageSelect, currentPage }: SectionTreeProps) {
  if (!imrad) {
    return <div className="p-4 text-gray-500">No sections available</div>;
  }

  const sections = [
    { name: 'Introduction', data: imrad.introduction, icon: '📖' },
    { name: 'Methods', data: imrad.methods, icon: '🔧' },
    { name: 'Results', data: imrad.results, icon: '📊' },
    { name: 'Discussion', data: imrad.discussion, icon: '💬' },
  ].filter(s => s.data);

  return (
    <div className="p-4">
      <h3 className="font-semibold mb-3">Sections</h3>
      <div className="space-y-1">
        {sections.map(section => {
          const isActive = currentPage >= section.data!.start && currentPage <= section.data!.end;
          return (
            <button
              key={section.name}
              onClick={() => onPageSelect(section.data!.start)}
              className={`w-full text-left px-3 py-2 rounded flex items-center gap-2 ${
                isActive ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100'
              }`}
            >
              <span>{section.icon}</span>
              <span>{section.name}</span>
              <span className="text-xs text-gray-500 ml-auto">
                p.{section.data!.start}-{section.data!.end}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}