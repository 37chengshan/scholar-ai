/**
 * ProgressIndicator Component
 *
 * Stage-level progress display with:
 * - Human-readable stage names (上传中, 解析中, etc.)
 * - Overall percentage calculation with stage weights
 * - Visual progress bar with accent color
 *
 * Per D-02:
 * - Stage labels: 上传中 → 解析中 → IMRaD 提取中 → 向量生成中 → 存储中
 * - Stage weights: 上传 10% → 解析 30% → IMRaD 提取 20% → 向量生成 30% → 存储 10%
 * - Polling interval: 2s (handled by parent component)
 */

import { clsx } from 'clsx';
import { Progress } from '@/app/components/ui/progress';
import { useLanguage } from '@/app/contexts/LanguageContext';

/**
 * Stage labels mapping (per UI-SPEC)
 */
const STAGE_LABELS: Record<string, { zh: string; en: string }> = {
  uploading: { zh: '上传中', en: 'Uploading' },
  parsing: { zh: '解析中', en: 'Parsing' },
  imrad: { zh: 'IMRaD 提取中', en: 'IMRaD Extraction' },
  vectorizing: { zh: '向量生成中', en: 'Vectorizing' },
  storing: { zh: '存储中', en: 'Storing' },
  completed: { zh: '已完成', en: 'Completed' },
  failed: { zh: '失败', en: 'Failed' },
};

/**
 * Stage weights for overall percentage calculation (per D-02)
 */
const STAGE_WEIGHTS: Record<string, number> = {
  uploading: 10,
  parsing: 30,
  imrad: 20,
  vectorizing: 30,
  storing: 10,
};

/**
 * Stage order for calculating cumulative progress
 */
const STAGE_ORDER = ['uploading', 'parsing', 'imrad', 'vectorizing', 'storing'];

/**
 * Map backend status to stage name
 */
function mapStatusToStage(status: string): string {
  const statusMap: Record<string, string> = {
    pending: 'uploading',
    uploading: 'uploading',
    processing_ocr: 'parsing',
    parsing: 'parsing',
    extracting_imrad: 'imrad',
    imrad: 'imrad',
    generating_notes: 'vectorizing',
    vectorizing: 'vectorizing',
    storing: 'storing',
    completed: 'completed',
    failed: 'failed',
  };
  return statusMap[status] || 'parsing';
}

/**
 * Calculate overall progress percentage
 * 
 * Formula: sum of completed stage weights + (current stage weight * stageProgress / 100)
 */
function calculateOverallProgress(stage: string, stageProgress: number): number {
  if (stage === 'completed') return 100;
  if (stage === 'failed') return 0;

  const stageIndex = STAGE_ORDER.indexOf(stage);
  if (stageIndex === -1) return 0;

  // Calculate cumulative weight from completed stages
  let cumulativeWeight = 0;
  for (let i = 0; i < stageIndex; i++) {
    cumulativeWeight += STAGE_WEIGHTS[STAGE_ORDER[i]] || 0;
  }

  // Add current stage progress
  const currentWeight = STAGE_WEIGHTS[stage] || 0;
  const currentProgress = (currentWeight * stageProgress) / 100;

  return Math.min(100, Math.round(cumulativeWeight + currentProgress));
}

/**
 * Component props
 */
interface ProgressIndicatorProps {
  status: string;
  stage?: string;
  progress?: number;
  errorMessage?: string | null;
  className?: string;
}

/**
 * ProgressIndicator Component
 *
 * Displays stage-level progress with:
 * - Progress bar (h-2, accent color #d35400 per UI-SPEC)
 * - Stage name text (text-sm, font-bold)
 * - Percentage text (text-lg, font-bold, accent color)
 *
 * @param props - Component props
 * @returns JSX element
 */
export function ProgressIndicator({
  status,
  stage,
  progress,
  errorMessage,
  className,
}: ProgressIndicatorProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  // Map status to stage
  const currentStage = stage || mapStatusToStage(status);
  const stageProgress = progress ?? 0;

  // Calculate overall progress
  const overallProgress = calculateOverallProgress(currentStage, stageProgress);

  // Get stage label
  const stageLabel = STAGE_LABELS[currentStage] || STAGE_LABELS.parsing;
  const displayLabel = isZh ? stageLabel.zh : stageLabel.en;

  // Determine if failed
  const isFailed = status === 'failed' || currentStage === 'failed';

  return (
    <div className={clsx('flex flex-col gap-2', className)}>
      {/* Progress bar */}
      <Progress 
        value={overallProgress} 
        className={clsx(
          'h-2',
          isFailed && '[&>div]:bg-red-500'
        )}
      />

      {/* Stage name and percentage */}
      <div className="flex justify-between items-center">
        <span className={clsx(
          'text-sm font-bold',
          isFailed ? 'text-red-600' : 'text-foreground/80'
        )}>
          {isFailed ? (isZh ? '处理失败' : 'Processing Failed') : displayLabel}
        </span>
        <span className={clsx(
          'text-lg font-bold',
          isFailed ? 'text-red-600' : 'text-primary'
        )}>
          {overallProgress}%
        </span>
      </div>

      {/* Error message */}
      {errorMessage && (
        <div className="text-xs text-red-500 mt-1">
          {errorMessage}
        </div>
      )}
    </div>
  );
}

export type { ProgressIndicatorProps };