import { describe, expect, it } from 'vitest';
import { resolveApiErrorMessage, isTransportLevelApiFailure } from './resolveApiErrorMessage';

describe('resolveApiErrorMessage', () => {
  it('falls back for transport-level failures', () => {
    expect(resolveApiErrorMessage(new Error('Network Error'), '本地化兜底文案')).toBe('本地化兜底文案');
    expect(isTransportLevelApiFailure(new Error('Network Error'))).toBe(true);
  });

  it('prefers backend detail when available', () => {
    const error = {
      message: 'Request failed with status code 400',
      response: {
        status: 400,
        data: {
          error: {
            detail: '后端返回的明确错误',
          },
        },
      },
    };

    expect(resolveApiErrorMessage(error, '本地化兜底文案')).toBe('后端返回的明确错误');
    expect(isTransportLevelApiFailure(error)).toBe(false);
  });

  it('falls back for generic 5xx failures without detail', () => {
    const error = {
      message: 'Request failed with status code 500',
      response: {
        status: 500,
        data: {},
      },
    };

    expect(resolveApiErrorMessage(error, '本地化兜底文案')).toBe('本地化兜底文案');
  });
});