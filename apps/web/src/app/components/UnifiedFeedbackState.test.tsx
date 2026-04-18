import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { UnifiedEmptyState, UnifiedErrorState, UnifiedLoadingState } from './UnifiedFeedbackState';

describe('UnifiedFeedbackState', () => {
  it('renders loading state label', () => {
    render(<UnifiedLoadingState label="正在加载" />);
    expect(screen.getByText('正在加载')).toBeInTheDocument();
  });

  it('renders empty state action', async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(<UnifiedEmptyState title="暂无数据" actionLabel="重试" onAction={onAction} />);
    await user.click(screen.getByRole('button', { name: '重试' }));
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it('renders error state retry action', async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<UnifiedErrorState title="加载失败" retryLabel="再试一次" onRetry={onRetry} />);
    await user.click(screen.getByRole('button', { name: '再试一次' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
