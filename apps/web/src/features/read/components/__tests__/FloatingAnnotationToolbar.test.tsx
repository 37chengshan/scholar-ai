import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FloatingAnnotationToolbar } from '@/features/read/components/FloatingAnnotationToolbar';

describe('FloatingAnnotationToolbar', () => {
  const mockRect = {
    top: 100,
    left: 200,
    width: 150,
    height: 20,
    bottom: 120,
    right: 350,
    x: 200,
    y: 100,
    toJSON: () => '',
  } as DOMRect;

  it('renders color buttons', () => {
    render(
      <FloatingAnnotationToolbar
        selectionRect={mockRect}
        onHighlight={vi.fn()}
        onDismiss={vi.fn()}
        isZh={false}
      />,
    );

    expect(screen.getByTestId('floating-annotation-toolbar')).toBeInTheDocument();
    expect(screen.getByTestId('floating-color-黄色')).toBeInTheDocument();
    expect(screen.getByTestId('floating-color-橙色')).toBeInTheDocument();
    expect(screen.getByTestId('floating-color-蓝色')).toBeInTheDocument();
    expect(screen.getByTestId('floating-color-绿色')).toBeInTheDocument();
  });

  it('calls onHighlight with color when color button clicked', () => {
    const onHighlight = vi.fn();
    render(
      <FloatingAnnotationToolbar
        selectionRect={mockRect}
        onHighlight={onHighlight}
        onDismiss={vi.fn()}
        isZh={false}
      />,
    );

    fireEvent.click(screen.getByTestId('floating-color-黄色'));
    expect(onHighlight).toHaveBeenCalledWith('#FFEB3B');
  });

  it('calls onDismiss when dismiss button clicked', () => {
    const onDismiss = vi.fn();
    render(
      <FloatingAnnotationToolbar
        selectionRect={mockRect}
        onHighlight={vi.fn()}
        onDismiss={onDismiss}
        isZh={false}
      />,
    );

    const dismissButton = screen.getByLabelText('Dismiss');
    fireEvent.click(dismissButton);
    expect(onDismiss).toHaveBeenCalled();
  });

  it('positions below selection when near viewport top', () => {
    const topRect = {
      top: 10,
      left: 200,
      width: 150,
      height: 20,
      bottom: 30,
      right: 350,
      x: 200,
      y: 10,
      toJSON: () => '',
    } as DOMRect;

    render(
      <FloatingAnnotationToolbar
        selectionRect={topRect}
        onHighlight={vi.fn()}
        onDismiss={vi.fn()}
        isZh={false}
      />,
    );

    const toolbar = screen.getByTestId('floating-annotation-toolbar');
    // When near top, toolbar should be positioned below selection (bottom + gap)
    const topValue = parseInt(toolbar.style.top, 10);
    expect(topValue).toBeGreaterThanOrEqual(topRect.bottom);
  });

  it('renders Chinese labels when isZh is true', () => {
    render(
      <FloatingAnnotationToolbar
        selectionRect={mockRect}
        onHighlight={vi.fn()}
        onDismiss={vi.fn()}
        isZh={true}
      />,
    );

    expect(screen.getByLabelText('关闭')).toBeInTheDocument();
  });
});
