import { ThinkingProcess, type ThinkingStep } from '@/app/components/ThinkingProcess';

interface ReasoningPanelProps {
  visible: boolean;
  steps: ThinkingStep[];
  durationSeconds: number;
}

export function ReasoningPanel({ visible, steps, durationSeconds }: ReasoningPanelProps) {
  if (!visible || steps.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <ThinkingProcess
        steps={steps}
        duration={durationSeconds}
        onComplete={() => {}}
        autoCollapse={true}
      />
    </div>
  );
}
