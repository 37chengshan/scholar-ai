/**
 * Intent Selector Component
 * 
 * Per D-24: Fuzzy instruction recognition with user confirmation
 * Displays multiple intent options as cards for user selection
 * when the system detects ambiguous user queries.
 * 
 * Usage:
 * <IntentSelector
 *   options={[
 *     { intent: 'question', label: 'Search Library', description: 'Search your uploaded papers' },
 *     { intent: 'external_search', label: 'External Search', description: 'Search arXiv and Semantic Scholar' }
 *   ]}
 *   onSelect={(intent) => console.log('Selected:', intent)}
 * />
 */

import React from 'react';

export interface IntentOption {
  intent: string;
  label: string;
  description: string;
}

interface IntentSelectorProps {
  options: IntentOption[];
  onSelect: (intent: string) => void;
}

export function IntentSelector({ options, onSelect }: IntentSelectorProps) {
  return (
    <div className="flex gap-2 p-3 bg-muted rounded-lg">
      {options.map((option) => (
        <button
          key={option.intent}
          onClick={() => onSelect(option.intent)}
          className="flex-1 p-3 bg-card border border-border rounded hover:border-primary transition-colors text-left"
        >
          <div className="font-medium text-sm">{option.label}</div>
          <div className="text-xs text-muted-foreground mt-1">{option.description}</div>
        </button>
      ))}
    </div>
  );
}

export default IntentSelector;