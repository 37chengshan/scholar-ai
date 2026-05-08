import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LanguageProvider, useLanguage } from '@/app/contexts/LanguageContext';

function LanguageConsumer() {
  const { language, setLanguage } = useLanguage();

  return (
    <div>
      <span data-testid="language-value">{language}</span>
      <button type="button" onClick={() => setLanguage('en')}>
        switch-en
      </button>
    </div>
  );
}

describe('LanguageProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('hydrates language from localStorage when available', () => {
    vi.mocked(window.localStorage.getItem).mockReturnValue('en');

    render(
      <LanguageProvider>
        <LanguageConsumer />
      </LanguageProvider>,
    );

    expect(screen.getByTestId('language-value')).toHaveTextContent('en');
  });

  it('persists language changes to localStorage', () => {
    vi.mocked(window.localStorage.getItem).mockReturnValue(null);

    render(
      <LanguageProvider>
        <LanguageConsumer />
      </LanguageProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'switch-en' }));

    expect(screen.getByTestId('language-value')).toHaveTextContent('en');
    expect(window.localStorage.setItem).toHaveBeenLastCalledWith('scholarai-language', 'en');
  });
});
