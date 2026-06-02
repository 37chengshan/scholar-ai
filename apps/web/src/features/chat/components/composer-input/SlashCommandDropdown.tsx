/**
 * SlashCommandDropdown - Keyboard-navigable slash command menu
 *
 * Uses Radix Popover for positioning and accessibility.
 * Supports keyboard navigation (ArrowUp/Down, Enter, Escape).
 */

import * as Popover from '@radix-ui/react-popover';
import { clsx } from 'clsx';
import type { SlashCommand } from './useComposerShortcuts';

interface SlashCommandDropdownProps {
  open: boolean;
  commands: SlashCommand[];
  selectedIndex: number;
  isZh: boolean;
  onSelect: (command: SlashCommand) => void;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLTextAreaElement | null>;
}

export function SlashCommandDropdown({
  open,
  commands,
  selectedIndex,
  isZh,
  onSelect,
  onClose,
  anchorRef,
}: SlashCommandDropdownProps) {
  if (!open) {
    return null;
  }

  return (
    <div
      role="menu"
      aria-label={isZh ? '斜杠命令' : 'Slash commands'}
      className="absolute bottom-full left-0 z-50 mb-1 min-w-[220px] overflow-hidden rounded-xl border border-border bg-card py-1 shadow-md"
    >
      {commands.map((command, index) => (
        <button
          key={command.value}
          type="button"
          role="menuitem"
          aria-selected={index === selectedIndex}
          onClick={() => onSelect(command)}
          className={clsx(
            'w-full text-left px-3 py-2 text-xs transition-colors flex items-center gap-2',
            index === selectedIndex
              ? 'bg-primary/10 text-primary font-semibold'
              : 'hover:bg-muted text-foreground/80',
          )}
        >
          <span className="font-mono text-[11px] text-primary/70">{command.label}</span>
          <span className="text-[10px] text-muted-foreground ml-auto">
            {isZh
              ? command.value === '/rag' ? '快速问答' : command.value === '/agent' ? '深度分析' : '多论文对比'
              : command.description
            }
          </span>
        </button>
      ))}
    </div>
  );
}
