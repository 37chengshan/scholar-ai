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

    // Open mode dropdown (shows current mode label '自动')
    await user.click(screen.getByRole('button', { name: /自动/ }));
    // Select '快速问答' from the dropdown menu
    await user.click(screen.getByRole('button', { name: /快速问答/ }));
    expect(onModeChange).toHaveBeenCalledWith('rag');

    await user.type(screen.getByPlaceholderText('输入...'), 'A');
    expect(onInputChange).toHaveBeenCalled();

    // Send button is the button without accessible text (icon-only)
    const sendButton = screen.getAllByRole('button').filter(
      (btn) => !btn.textContent?.trim()
    );
    expect(sendButton).toHaveLength(1);
    await user.click(sendButton[0]);
    expect(onSend).toHaveBeenCalledTimes(1);
  });
});
