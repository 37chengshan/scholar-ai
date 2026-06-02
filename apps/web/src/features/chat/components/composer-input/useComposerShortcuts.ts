/**
 * useComposerShortcuts - Keyboard shortcut handler for chat composer
 *
 * Shortcuts:
 * - Cmd/Ctrl+B: wrap selection with **bold**
 * - Cmd/Ctrl+I: wrap selection with *italic*
 * - Cmd/Ctrl+K: insert [text](url) link template
 * - Escape: clear input or cancel streaming
 * - "/" at line start: trigger slash commands dropdown
 */

import { useCallback, useState, useRef } from 'react';

export interface SlashCommand {
  value: string;
  label: string;
  description: string;
}

const DEFAULT_SLASH_COMMANDS: SlashCommand[] = [
  { value: '/rag', label: '/rag', description: 'Direct RAG retrieval' },
  { value: '/agent', label: '/agent', description: 'Multi-step agent reasoning' },
  { value: '/compare', label: '/compare', description: 'Compare multiple papers' },
];

interface UseComposerShortcutsOptions {
  input: string;
  onInputChange: (value: string) => void;
  onCancel?: () => void;
  slashCommands?: SlashCommand[];
}

interface UseComposerShortcutsResult {
  handleKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  slashMenuOpen: boolean;
  slashMenuIndex: number;
  slashCommands: SlashCommand[];
  selectSlashCommand: (command: SlashCommand) => void;
  closeSlashMenu: () => void;
}

export function useComposerShortcuts({
  input,
  onInputChange,
  onCancel,
  slashCommands = DEFAULT_SLASH_COMMANDS,
}: UseComposerShortcutsOptions): UseComposerShortcutsResult {
  const [slashMenuOpen, setSlashMenuOpen] = useState(false);
  const [slashMenuIndex, setSlashMenuIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const closeSlashMenu = useCallback(() => {
    setSlashMenuOpen(false);
    setSlashMenuIndex(0);
  }, []);

  const selectSlashCommand = useCallback((command: SlashCommand) => {
    // Replace the "/" trigger with the selected command
    onInputChange(command.value + ' ');
    closeSlashMenu();
  }, [onInputChange, closeSlashMenu]);

  const wrapSelection = useCallback((
    event: React.KeyboardEvent<HTMLTextAreaElement>,
    prefix: string,
    suffix: string,
  ) => {
    event.preventDefault();
    const textarea = event.currentTarget;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = input.substring(start, end);

    const before = input.substring(0, start);
    const after = input.substring(end);
    const newValue = `${before}${prefix}${selected}${suffix}${after}`;
    onInputChange(newValue);

    // Restore cursor position after React re-render
    requestAnimationFrame(() => {
      if (typeof textarea.setSelectionRange === 'function') {
        textarea.setSelectionRange(
          start + prefix.length,
          start + prefix.length + selected.length,
        );
      }
    });
  }, [input, onInputChange]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const isMod = event.metaKey || event.ctrlKey;

    // Cmd/Ctrl+B: bold
    if (isMod && event.key === 'b') {
      wrapSelection(event, '**', '**');
      return;
    }

    // Cmd/Ctrl+I: italic
    if (isMod && event.key === 'i') {
      wrapSelection(event, '*', '*');
      return;
    }

    // Cmd/Ctrl+K: link
    if (isMod && event.key === 'k') {
      event.preventDefault();
      const textarea = event.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const selected = input.substring(start, end) || 'text';
      const before = input.substring(0, start);
      const after = input.substring(end);
      const newValue = `${before}[${selected}](url)${after}`;
      onInputChange(newValue);
      return;
    }

    // Escape: close slash menu or cancel
    if (event.key === 'Escape') {
      if (slashMenuOpen) {
        event.preventDefault();
        closeSlashMenu();
        return;
      }
      if (onCancel) {
        event.preventDefault();
        onCancel();
        return;
      }
    }

    // Slash command trigger: "/" at line start
    if (event.key === '/' && (input === '' || input.endsWith('\n'))) {
      setSlashMenuOpen(true);
      setSlashMenuIndex(0);
      return;
    }

    // Arrow navigation within slash menu
    if (slashMenuOpen) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setSlashMenuIndex((prev) => (prev + 1) % slashCommands.length);
        return;
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setSlashMenuIndex((prev) => (prev - 1 + slashCommands.length) % slashCommands.length);
        return;
      }
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        selectSlashCommand(slashCommands[slashMenuIndex]);
        return;
      }
    }
  }, [
    input,
    onInputChange,
    onCancel,
    slashMenuOpen,
    slashMenuIndex,
    slashCommands,
    wrapSelection,
    closeSlashMenu,
    selectSlashCommand,
  ]);

  return {
    handleKeyDown,
    slashMenuOpen,
    slashMenuIndex,
    slashCommands,
    selectSlashCommand,
    closeSlashMenu,
  };
}
