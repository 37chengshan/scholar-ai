import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { ForgotPassword } from './ForgotPassword';
import { ResetPassword } from './ResetPassword';
import { Register } from './Register';
import { toast } from 'sonner';

const navigateMock = vi.fn();
const loginMock = vi.fn();

vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router');
  return {
    ...actual,
    useNavigate: () => navigateMock,
    useSearchParams: () => [new URLSearchParams('token=demo-token')],
  };
});

vi.mock('../contexts/LanguageContext', () => ({
  useLanguage: () => ({
    language: 'zh',
    setLanguage: vi.fn(),
  }),
}));

vi.mock('@/services/authApi', () => ({
  forgotPassword: vi.fn(),
  resetPassword: vi.fn(),
  register: vi.fn(),
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    login: loginMock,
  }),
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('auth pages', () => {
  it('adds email autocomplete on forgot password', () => {
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>
    );

    expect(screen.getByLabelText('邮箱地址')).toHaveAttribute('autocomplete', 'email');
  });

  it('shows custom invalid email feedback on forgot password submit', () => {
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText('邮箱地址'), { target: { value: 'invalid-email' } });
    fireEvent.click(screen.getByRole('button', { name: '发送重置链接' }));

    expect(toast.error).toHaveBeenCalledWith('邮箱格式不正确');
  });

  it('adds new-password autocomplete on reset password fields', () => {
    render(
      <MemoryRouter>
        <ResetPassword />
      </MemoryRouter>
    );

    expect(screen.getByLabelText('新密码')).toHaveAttribute('autocomplete', 'new-password');
    expect(screen.getByLabelText('确认密码')).toHaveAttribute('autocomplete', 'new-password');
    expect(screen.getByPlaceholderText('至少 8 个字符')).toBeInTheDocument();
  });

  it('renders register benefits without emoji glyphs', () => {
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    );

    expect(screen.getByText('管理个人论文库')).toBeInTheDocument();
    expect(screen.getByText('围绕论文继续追问')).toBeInTheDocument();
    expect(screen.queryByText('📚')).not.toBeInTheDocument();
    expect(screen.queryByText('🤖')).not.toBeInTheDocument();
  });
});
