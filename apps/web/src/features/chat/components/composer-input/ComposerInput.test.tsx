import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ComposerInput } from './ComposerInput';

describe('ComposerInput', () => {
  it('switches mode and sends message', async () => {
    const user = userEvent.setup();
    const onModeChange = vi.fn();
    const onInputChange = vi.fn();
    const onKeyDown = vi.fn();
    const onSend = vi.fn();

    render(
      <ComposerInput
        scopeType={'full_kb'}
        isZh={true}
        mode={'auto'}
        input={'hello'}
        disabled={false}
        placeholder={'输入...'}
        labels={{ mode: '模式', verify: '请验证输出结果。', sendKeyHint: '↵ 发送' }}
        onModeChange={onModeChange}
        onInputChange={onInputChange}
        onKeyDown={onKeyDown}
        onSend={onSend}
      />
    );

    await user.click(screen.getByRole('button', { name: '快速问答' }));
    expect(onModeChange).toHaveBeenCalledWith('rag');

    await user.type(screen.getByPlaceholderText('输入...'), 'A');
    expect(onInputChange).toHaveBeenCalled();

    const buttons = screen.getAllByRole('button');
    await user.click(buttons[buttons.length - 1]);
    expect(onSend).toHaveBeenCalledTimes(1);
  });
});
