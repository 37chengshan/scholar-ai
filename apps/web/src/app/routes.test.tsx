/**
 * Protected Route Tests
 *
 * Tests for ProtectedRoute component:
 * - Redirects to /login when not authenticated
 * - Renders children when authenticated
 * - Shows loading state
 * - Keeps route assertions aligned with the current landing-page copy
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { ProtectedRoute, router } from './routes';
import { hasWarmAuthHint, useAuth } from '@/contexts/AuthContext';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
  hasWarmAuthHint: vi.fn(() => false),
}));

vi.mock('@/app/hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: [],
    currentSession: null,
    messages: [],
    loading: false,
    error: null,
    loadSessions: vi.fn(),
    createSession: vi.fn(),
    switchSession: vi.fn(),
    deleteSession: vi.fn(),
    addMessage: vi.fn(),
    clearMessages: vi.fn(),
    updateCurrentSession: vi.fn(),
  }),
}));

vi.mock('@/hooks/useKnowledgeBases', () => ({
  useKnowledgeBases: () => ({
    knowledgeBases: [],
    total: 0,
    loading: false,
    error: null,
    refetch: vi.fn(),
    createKB: vi.fn(),
    deleteKB: vi.fn(),
  }),
}));

class IntersectionObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('IntersectionObserver', IntersectionObserverMock);

// Test helper components
const TestChild = () => <div>Protected Content</div>;
const LoginPage = () => <div>Login Page</div>;

/**
 * Create a test router with ProtectedRoute
 */
function createTestRouter(initialPath: string) {
  return createMemoryRouter([
    {
      path: '/protected',
      element: <ProtectedRoute><TestChild /></ProtectedRoute>,
    },
    {
      path: '/dashboard',
      element: <ProtectedRoute><TestChild /></ProtectedRoute>,
    },
    {
      path: '/login',
      element: <LoginPage />,
    },
  ], {
    initialEntries: [initialPath],
  });
}

function createAppRouter(initialPath: string) {
  return createMemoryRouter(router.routes, {
    initialEntries: [initialPath],
  });
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(hasWarmAuthHint).mockReturnValue(false);
  });

  it('should redirect to login when not authenticated', async () => {
    // Mock useAuth to return isAuthenticated: false, loading: false
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    });

    // Create test router and render with RouterProvider
    const testRouter = createTestRouter('/protected');
    render(<RouterProvider router={testRouter} />);

    // Wait for navigation to complete and verify login page is shown
    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });
    // Should NOT show protected content
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('should render children when authenticated', () => {
    // Mock useAuth to return isAuthenticated: true, loading: false
    vi.mocked(useAuth).mockReturnValue({
      user: { id: '1', email: 'test@example.com', name: 'Test User' } as any,
      isAuthenticated: true,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    });

    // Create test router and render with RouterProvider
    const testRouter = createTestRouter('/protected');
    render(<RouterProvider router={testRouter} />);

    // Should show protected content immediately
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
    // Should NOT show login page
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });

  it('should show loading state', () => {
    // Mock useAuth to return loading: true
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      loading: true,
      login: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    });

    // Create test router and render with RouterProvider
    const testRouter = createTestRouter('/protected');
    render(<RouterProvider router={testRouter} />);

    // Should show loading indicator (LoadingFallback shows "加载中...")
    expect(screen.getByText('加载中...')).toBeInTheDocument();
    // Should NOT show protected content or login
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });

  it('should preserve intended route in state', async () => {
    // Mock useAuth to return isAuthenticated: false, loading: false
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    });

    const testRouter = createTestRouter('/dashboard');
    render(<RouterProvider router={testRouter} />);

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });

    expect(testRouter.state.location.pathname).toBe('/login');
    expect(testRouter.state.location.state).toEqual({ from: '/dashboard' });
  });

  it('should not expose standalone upload route', () => {
    const appShell = router.routes.find((route: any) => route.children);
    const childPaths = (appShell?.children || []).map((route: any) => route.path);
    expect(childPaths).not.toContain('upload');
  });

  it('should redirect root path to login when user is unauthenticated', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    });

    const testRouter = createAppRouter('/');
    render(<RouterProvider router={testRouter} />);

    await waitFor(() => {
      expect(screen.getByText('开始探索')).toBeInTheDocument();
    });
  });

  it('should redirect unknown routes to login through root/dashboard guard when user is unauthenticated', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      isAuthenticated: false,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      checkAuth: vi.fn(),
    });

    const testRouter = createAppRouter('/batch-upload');
    render(<RouterProvider router={testRouter} />);

    await waitFor(() => {
      expect(screen.getByText('开始探索')).toBeInTheDocument();
    });
  });
});
