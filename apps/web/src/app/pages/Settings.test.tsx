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
    language: 'zh',
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

    expect(screen.getByRole('heading', { level: 2, name: '个人资料' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '语言设置' }));

    expect(screen.getByRole('heading', { level: 2, name: '语言设置' })).toBeInTheDocument();
  });

  it('renders display section copy in the active language', () => {
    render(<Settings />);

    fireEvent.click(screen.getByRole('button', { name: '显示设置' }));

    expect(screen.getByRole('heading', { level: 3, name: '显示设置' })).toBeInTheDocument();
    expect(screen.getByText('自定义阅读与界面尺寸')).toBeInTheDocument();
  });
});
