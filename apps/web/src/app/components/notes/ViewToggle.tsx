/**
 * View Toggle Component
 *
 * Toggle between different note organization views:
 * - By Time: Chronological list
 * - By Paper: Grouped by linked papers
 * - By Tag: Grouped by tags
 *
 * Uses Button component with variant switching.
 */

import { Button } from '../ui/button';
import { Clock, FileText, Hash } from 'lucide-react';

interface ViewToggleProps {
  value: 'time' | 'paper' | 'tag';
  onChange: (mode: 'time' | 'paper' | 'tag') => void;
}

export function ViewToggle({ value, onChange }: ViewToggleProps) {
  return (
    <div className="flex gap-2">
      <Button
        variant={value === 'time' ? 'default' : 'outline'}
        size="sm"
        onClick={() => onChange('time')}
        className="flex items-center gap-1"
      >
        <Clock className="w-4 h-4" />
        By Time
      </Button>
      <Button
        variant={value === 'paper' ? 'default' : 'outline'}
        size="sm"
        onClick={() => onChange('paper')}
        className="flex items-center gap-1"
      >
        <FileText className="w-4 h-4" />
        By Paper
      </Button>
      <Button
        variant={value === 'tag' ? 'default' : 'outline'}
        size="sm"
        onClick={() => onChange('tag')}
        className="flex items-center gap-1"
      >
        <Hash className="w-4 h-4" />
        By Tag
      </Button>
    </div>
  );
}