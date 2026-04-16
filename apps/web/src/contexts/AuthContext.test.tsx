/**
 * AuthContext Tests
 *
 * Tests for AuthContext provider:
 * - Provides auth state to components
 * - Login flow integration
 * - Logout flow
 * - Session verification on mount
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';
import { ReactNode } from 'react';
import * as authApi from '@/services/authApi';

// Mock user data
const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  name: 'Test User',
  emailVerified: true,
  roles: ['user'],
};

// Create mutable state for mock store
let mockAuthState = {
  user: null as typeof mockUser | null,
  isAuthenticated: false,
  loading: true,
};

// Mock authApi
vi.mock('@/services/authApi', () => ({
  me: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

// Mock stores with mutable state
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    ...mockAuthState,
    setUser: vi.fn((user) => {
      mockAuthState.user = user;
      mockAuthState.isAuthenticated = !!user;
    }),
    setLoading: vi.fn((loading) => {
      mockAuthState.loading = loading;
    }),
    logout: vi.fn(() => {
      mockAuthState.user = null;
      mockAuthState.isAuthenticated = false;
    }),
  })),
}));

vi.mock('@/stores/userStore', () => ({
  useUserStore: vi.fn(() => ({
    setProfile: vi.fn(),
    setSettings: vi.fn(),
    clearUser: vi.fn(),
  })),
}));

// Test component that uses auth
function TestComponent() {
  const { user, isAuthenticated, loading, login, logout, checkAuth } = useAuth();
  return (
    <div>
      <span data-testid="loading">{loading.toString()}</span>
      <span data-testid="authenticated">{isAuthenticated.toString()}</span>
      <span data-testid="user">{user?.email || 'null'}</span>
      <button data-testid="login-btn" onClick={() => login('test@example.com', 'password')}>
        Login
      </button>
      <button data-testid="logout-btn" onClick={() => logout()}>
        Logout
      </button>
      <button data-testid="checkauth-btn" onClick={() => checkAuth()}>
        Check Auth
      </button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock state
    mockAuthState = {
      user: null,
      isAuthenticated: false,
      loading: true,
    };
  });

  it('should provide auth state', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
  });

  it('should login successfully', async () => {
    // Setup mock login response
    vi.mocked(authApi.login).mockResolvedValueOnce({
      user: mockUser,
    });

    // Reset loading state for this test
    mockAuthState.loading = false;

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Trigger login
    await act(async () => {
      screen.getByTestId('login-btn').click();
    });

    // Verify login API was called
    expect(authApi.login).toHaveBeenCalledWith('test@example.com', 'password');
  });

  it('should logout successfully', async () => {
    // Setup initial authenticated state
    mockAuthState = {
      user: mockUser,
      isAuthenticated: true,
      loading: false,
    };

    vi.mocked(authApi.logout).mockResolvedValueOnce(undefined);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Trigger logout
    await act(async () => {
      screen.getByTestId('logout-btn').click();
    });

    // Verify logout API was called
    expect(authApi.logout).toHaveBeenCalled();
  });

  it('should check auth on mount', async () => {
    // Setup mock me response
    vi.mocked(authApi.me).mockResolvedValueOnce(mockUser);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Verify me API was called on mount
    await waitFor(() => {
      expect(authApi.me).toHaveBeenCalled();
    });
  });

  it('should throw error if useAuth called outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAuth must be used within AuthProvider');

    consoleSpy.mockRestore();
  });

  it('should handle checkAuth explicitly', async () => {
    vi.mocked(authApi.me).mockResolvedValueOnce(mockUser);
    mockAuthState.loading = false;

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Trigger explicit checkAuth
    await act(async () => {
      screen.getByTestId('checkauth-btn').click();
    });

    // Verify me API was called
    expect(authApi.me).toHaveBeenCalled();
  });
});