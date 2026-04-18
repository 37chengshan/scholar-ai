import { ToolCallCard } from '@/app/components/ToolCallCard';
import type { ToolTimelineItem } from '@/features/chat/components/workspaceTypes';

interface ToolTimelinePanelProps {
  visible: boolean;
  timeline: ToolTimelineItem[];
}

export function ToolTimelinePanel({ visible, timeline }: ToolTimelinePanelProps) {
  if (!visible || timeline.length === 0) {
    return null;
  }

  return (
    <div className="space-y-1.5">
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
  );
}
