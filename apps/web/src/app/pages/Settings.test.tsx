import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Settings } from '@/app/pages/Settings';

vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock('@/app/contexts/LanguageContext', () => ({
  useLanguage: () => ({
    language: 'en',
    setLanguage: vi.fn(),
  }),
}));

vi.mock('@/stores/settingsStore', () => ({
  useSettingsStore: () => ({
    fontSize: 'medium',
    setFontSize: vi.fn(),
  }),
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'u1', name: 'Test User', avatar: '' },
    logout: vi.fn(),
  }),
}));

describe('Settings page', () => {
  it('switches active section when sidebar button is clicked', () => {
    render(<Settings />);

    expect(screen.getByText('Profile Settings')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Localization/i }));

    expect(screen.getByText('Language Settings')).toBeInTheDocument();
  });
});
