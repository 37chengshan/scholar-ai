import { describe, expect, it, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAnnotationManager } from '@/features/read/hooks/useAnnotationManager';

vi.mock('@/services/annotationsApi', () => ({
  list: vi.fn().mockResolvedValue([
    {
      id: 'ann-1',
      paperId: 'paper-1',
      userId: 'user-1',
      type: 'highlight',
      pageNumber: 1,
      position: { x: 10, y: 20, width: 30, height: 5 },
      content: 'test highlight',
      color: '#FFEB3B',
      createdAt: '2024-01-01',
      updatedAt: '2024-01-01',
    },
  ]),
}));

describe('useAnnotationManager', () => {
  it('initializes with empty annotations', () => {
    const { result } = renderHook(() => useAnnotationManager('paper-1'));
    expect(result.current.annotations).toEqual([]);
  });

  it('initializes with empty selectedText', () => {
    const { result } = renderHook(() => useAnnotationManager('paper-1'));
    expect(result.current.selectedText).toBe('');
  });

  it('setSelectedText updates selectedText', () => {
    const { result } = renderHook(() => useAnnotationManager('paper-1'));

    act(() => {
      result.current.setSelectedText('hello world');
    });

    expect(result.current.selectedText).toBe('hello world');
  });

  it('setSelectionPosition updates selectionPosition', () => {
    const { result } = renderHook(() => useAnnotationManager('paper-1'));
    const pos = { x: 10, y: 20, width: 50, height: 5 };

    act(() => {
      result.current.setSelectionPosition(pos);
    });

    expect(result.current.selectionPosition).toEqual(pos);
  });

  it('handleAnnotationCreated refreshes annotations and clears selection', async () => {
    const { result } = renderHook(() => useAnnotationManager('paper-1'));

    act(() => {
      result.current.setSelectedText('some text');
      result.current.setSelectionPosition({ x: 1, y: 2, width: 3, height: 4 });
    });

    await act(async () => {
      await result.current.handleAnnotationCreated();
    });

    expect(result.current.annotations).toHaveLength(1);
    expect(result.current.selectedText).toBe('');
    expect(result.current.selectionPosition).toBeNull();
  });

  it('handleAnnotationCreated does nothing when paperId is undefined', async () => {
    const { result } = renderHook(() => useAnnotationManager(undefined));

    await act(async () => {
      await result.current.handleAnnotationCreated();
    });

    expect(result.current.annotations).toEqual([]);
  });
});
