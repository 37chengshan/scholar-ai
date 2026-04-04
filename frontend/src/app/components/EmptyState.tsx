interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon = '📭', title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="text-6xl mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      {description && (
        <p className="text-gray-600 text-center max-w-md mb-4">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// Preset empty states
export function NoPapersState({ onUpload }: { onUpload: () => void }) {
  return (
    <EmptyState
      icon="📄"
      title="No papers yet"
      description="Upload your first paper to get started with AI-powered reading and analysis."
      action={{ label: 'Upload Paper', onClick: onUpload }}
    />
  );
}

export function NoSearchResultsState({ query }: { query: string }) {
  return (
    <EmptyState
      icon="🔍"
      title="No results found"
      description={`No papers matching \"${query}\". Try different keywords or search external sources.`}
    />
  );
}