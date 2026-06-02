/**
 * Tests for useComposerShortcuts hook
 *
 * Coverage:
 * - Cmd/Ctrl+B wraps selection with **bold**
 * - Cmd/Ctrl+I wraps selection with *italic*
 * - Cmd/Ctrl+K inserts link template
 * - Escape closes slash menu or cancels
 * - "/" at line start triggers slash menu
 * - Arrow keys navigate slash menu
 * - Enter selects slash command
 */
import { renderHook, act } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useComposerShortcuts } from './useComposerShortcuts';

function createKeyboardEvent(
  key: string,
  options: Partial<{ metaKey: boolean; ctrlKey: boolean; shiftKey: boolean }> = {},
): React.KeyboardEvent<HTMLTextAreaElement> {
  return {
    key,
    metaKey: options.metaKey ?? false,
    ctrlKey: options.ctrlKey ?? false,
    shiftKey: options.shiftKey ?? false,
    preventDefault: vi.fn(),
    currentTarget: {
      selectionStart: 0,
      selectionEnd: 0,
    },
  } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;
}

describe('useComposerShortcuts', () => {
  it('wraps selection with **bold** on Cmd+B', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: 'hello world',
        onInputChange,
      }),
    );

    // Simulate selection of "world" (positions 6-11)
    const event = {
      key: 'b',
      metaKey: true,
      ctrlKey: false,
      shiftKey: false,
      preventDefault: vi.fn(),
      currentTarget: {
        selectionStart: 6,
        selectionEnd: 11,
      },
    } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;

    act(() => {
      result.current.handleKeyDown(event);
    });

    expect(event.preventDefault).toHaveBeenCalled();
    expect(onInputChange).toHaveBeenCalledWith('hello **world**');
  });

  it('wraps selection with *italic* on Cmd+I', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: 'hello world',
        onInputChange,
      }),
    );

    const event = {
      key: 'i',
      metaKey: true,
      ctrlKey: false,
      shiftKey: false,
      preventDefault: vi.fn(),
      currentTarget: {
        selectionStart: 6,
        selectionEnd: 11,
      },
    } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;

    act(() => {
      result.current.handleKeyDown(event);
    });

    expect(event.preventDefault).toHaveBeenCalled();
    expect(onInputChange).toHaveBeenCalledWith('hello *world*');
  });

  it('inserts link template on Cmd+K', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: 'hello world',
        onInputChange,
      }),
    );

    const event = {
      key: 'k',
      metaKey: true,
      ctrlKey: false,
      shiftKey: false,
      preventDefault: vi.fn(),
      currentTarget: {
        selectionStart: 6,
        selectionEnd: 11,
      },
    } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;

    act(() => {
      result.current.handleKeyDown(event);
    });

    expect(event.preventDefault).toHaveBeenCalled();
    expect(onInputChange).toHaveBeenCalledWith('hello [world](url)');
  });

  it('inserts [text](url) when no selection on Cmd+K', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: 'hello ',
        onInputChange,
      }),
    );

    const event = {
      key: 'k',
      metaKey: true,
      ctrlKey: false,
      shiftKey: false,
      preventDefault: vi.fn(),
      currentTarget: {
        selectionStart: 6,
        selectionEnd: 6,
      },
    } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;

    act(() => {
      result.current.handleKeyDown(event);
    });

    expect(onInputChange).toHaveBeenCalledWith('hello [text](url)');
  });

  it('triggers slash menu on "/" at empty input', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: '',
        onInputChange,
      }),
    );

    const event = createKeyboardEvent('/');

    act(() => {
      result.current.handleKeyDown(event);
    });

    expect(result.current.slashMenuOpen).toBe(true);
  });

  it('triggers slash menu on "/" after newline', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: 'hello\n',
        onInputChange,
      }),
    );

    const event = createKeyboardEvent('/');

    act(() => {
      result.current.handleKeyDown(event);
    });

    expect(result.current.slashMenuOpen).toBe(true);
  });

  it('navigates slash menu with ArrowDown/ArrowUp', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: '',
        onInputChange,
      }),
    );

    // Open menu
    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('/'));
    });
    expect(result.current.slashMenuIndex).toBe(0);

    // ArrowDown
    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
    });
    expect(result.current.slashMenuIndex).toBe(1);

    // ArrowDown wraps
    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
    });
    expect(result.current.slashMenuIndex).toBe(2);

    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
    });
    expect(result.current.slashMenuIndex).toBe(0);

    // ArrowUp wraps
    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('ArrowUp'));
    });
    expect(result.current.slashMenuIndex).toBe(2);
  });

  it('selects slash command on Enter', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: '',
        onInputChange,
      }),
    );

    // Open menu
    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('/'));
    });

    // Select first command (Enter)
    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('Enter'));
    });

    expect(onInputChange).toHaveBeenCalledWith('/rag ');
    expect(result.current.slashMenuOpen).toBe(false);
  });

  it('closes slash menu on Escape', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: '',
        onInputChange,
      }),
    );

    // Open menu
    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('/'));
    });
    expect(result.current.slashMenuOpen).toBe(true);

    // Escape
    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('Escape'));
    });
    expect(result.current.slashMenuOpen).toBe(false);
  });

  it('calls onCancel on Escape when slash menu is closed', () => {
    const onCancel = vi.fn();
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: 'test',
        onInputChange,
        onCancel,
      }),
    );

    act(() => {
      result.current.handleKeyDown(createKeyboardEvent('Escape'));
    });

    expect(onCancel).toHaveBeenCalled();
  });

  it('works with Ctrl key (non-Mac)', () => {
    const onInputChange = vi.fn();
    const { result } = renderHook(() =>
      useComposerShortcuts({
        input: 'hello world',
        onInputChange,
      }),
    );

    const event = {
      key: 'b',
      metaKey: false,
      ctrlKey: true,
      shiftKey: false,
      preventDefault: vi.fn(),
      currentTarget: {
        selectionStart: 0,
        selectionEnd: 5,
      },
    } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;

    act(() => {
      result.current.handleKeyDown(event);
    });

    expect(onInputChange).toHaveBeenCalledWith('**hello** world');
  });
});
