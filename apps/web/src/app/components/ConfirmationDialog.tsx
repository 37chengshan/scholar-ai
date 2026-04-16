/**
 * ConfirmationDialog Component
 *
 * Modal dialog for tool call confirmation (ask_user_confirmation tool).
 * Per UI-SPEC: non-dismissable, shows tool info, params preview, approve/reject.
 *
 * Features:
 * - shadcn Dialog with no close button / escape / backdrop click
 * - Tool name with icon from TOOL_DISPLAY_CONFIG
 * - Parameters JSON preview (collapsible)
 * - Approve (primary orange) / Reject (outline destructive) buttons
 * - Bilingual labels via useLanguage()
 */

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { TOOL_DISPLAY_CONFIG } from '../../types/chat';

interface ConfirmationDialogProps {
  tool: string;
  params: Record<string, unknown>;
  onApprove: () => void;
  onReject: () => void;
  isOpen: boolean;
}

export function ConfirmationDialog({
  tool,
  params,
  onApprove,
  onReject,
  isOpen,
}: ConfirmationDialogProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const [showParams, setShowParams] = useState(false);

  const config = TOOL_DISPLAY_CONFIG[tool] || {
    icon: 'ShieldCheck',
    displayName: tool,
    description: isZh ? 'Agent需要您的确认' : 'Agent requests your confirmation',
  };

  const formatParams = () => {
    try {
      return JSON.stringify(params, null, 2);
    } catch {
      return String(params);
    }
  };

  return (
    <Dialog open={isOpen} modal>
      <DialogContent
        className="sm:max-w-md"
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className="text-lg">🛡️</span>
            {isZh ? 'Agent 请求确认' : 'Agent requests confirmation'}
          </DialogTitle>
          <DialogDescription>
            <div className="flex items-center gap-2 mt-1">
              <span className="font-medium text-foreground">
                {config.displayName}
              </span>
              <span className="text-muted-foreground">— {config.description}</span>
            </div>
          </DialogDescription>
        </DialogHeader>

        {/* Parameters preview */}
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => setShowParams(!showParams)}
            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {showParams ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
            {isZh ? '查看参数' : 'View parameters'}
          </button>

          {showParams && (
            <pre className="max-h-40 overflow-auto rounded-lg bg-muted p-3 text-xs font-mono">
              {formatParams()}
            </pre>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={onReject}
            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            {isZh ? '拒绝' : 'Reject'}
          </Button>
          <Button onClick={onApprove} className="bg-primary hover:bg-primary/90">
            {isZh ? '批准' : 'Approve'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
