import { useState } from 'react';
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react';
import { ToolCallCard } from '@/app/components/ToolCallCard';
import type { ToolTimelineItem } from '@/features/chat/components/workspaceTypes';

interface ToolTimelinePanelProps {
  visible: boolean;
  timeline: ToolTimelineItem[];
}

export function ToolTimelinePanel({ visible, timeline }: ToolTimelinePanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (!visible || timeline.length === 0) {
    return null;
  }

  const completedCount = timeline.filter(t => t.status === 'success' || t.status === 'error').length;

  return (
    <div className="w-full">
      {/* Collapsed summary row */}
      <button
        type="button"
        onClick={() => setExpanded(v => !v)}
        className="flex items-center gap-1.5 text-[11px] text-zinc-500 hover:text-zinc-700 transition-colors py-1 group"
      >
        {expanded
          ? <ChevronDown className="w-3 h-3" />
          : <ChevronRight className="w-3 h-3" />
        }
        <Wrench className="w-3 h-3 text-zinc-400" />
        <span>
          {completedCount > 0
            ? `已调用 ${timeline.length} 个工具`
            : `调用 ${timeline.length} 个工具中…`
          }
        </span>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-1 space-y-1.5 border-l border-zinc-200 pl-3">
          {timeline.map((item) => (
            <ToolCallCard
              key={item.id}
              toolCall={{
                id: item.id,
                tool: item.tool,
                parameters: {},
                status: item.status,
                startedAt: item.startedAt,
                completedAt: item.completedAt,
                duration: item.duration,
                result: item.summary,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
