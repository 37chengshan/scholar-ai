/**
 * Auth Context - Authentication State Management
 *
 * React Context wrapper for authentication:
 * - Provides useAuth() hook for components
 * - Integrates with authApi and authStore
 * - Handles session verification on mount
 * - Cookie-based auth (no localStorage)
 *
 * Usage:
 * 1. Wrap app with <AuthProvider>
 * 2. Use useAuth() in components to access auth state
 */

import { createContext, useContext, useEffect, ReactNode } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useUserStore } from '@/stores/userStore';
import * as authApi from '@/services/authApi';
import type { User } from '@/types';

/**
 * Auth context interface
 */
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

/**
 * Auth context
 *
 * Provides auth state to component tree.
 * Throws error if useAuth() is called outside AuthProvider.
 */
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Auth Provider Component
 *
 * Wraps app to provide auth state via context.
 * On mount, checks if session exists by calling /api/auth/me.
 *
 * @param children - Child components
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  // Get auth state and actions from store
  const { user, isAuthenticated, loading, setUser, setLoading, logout: clearAuth } = useAuthStore();

  // Get user store actions
  const { setProfile, setSettings, clearUser } = useUserStore();

  /**
   * Check authentication status
   *
   * Calls /api/auth/me to verify session.
   * Updates auth store with user data if session exists.
   */
  const checkAuth = async () => {
    try {
      setLoading(true);
      const userData = await authApi.me();
      setUser(userData);
      setProfile(userData);

      // Load user settings
      // Note: Will be implemented when settings API is integrated
      // const settings = await usersApi.getSettings();
      // setSettings(settings);
    } catch (error) {
      // Session invalid or not found
      setUser(null);
      clearUser();
    } finally {
      setLoading(false);
    }
  };

  /**
   * Login with email and password
   *
   * Calls /api/auth/login (backend sets cookies).
   * Updates auth store with user data.
   *
   * @param email - User email
   * @param password - User password
   */
  const login = async (email: string, password: string) => {
    const response = await authApi.login(email, password);

    // authApi.login returns response.data which is the AuthResponse:
    // { success: true, data: { user: {...}, meta: {...} } }
    if (response.success && response.data?.user) {
      setUser(response.data.user);
      setProfile(response.data.user);
    } else {
      throw new Error(response.error?.detail || 'Login failed');
    }
  };

  /**
   * Logout
   *
   * Calls /api/auth/logout (backend clears cookies).
   * Clears auth store state.
   */
  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      // Ignore logout errors - still clear local state
      console.error('Logout error:', error);
    } finally {
      // Clear auth state
      clearAuth();
      clearUser();
    }
  };

  // Check auth on mount (verify session)
  useEffect(() => {
    checkAuth();
  }, []); // Empty deps - only run on mount

  // Context value
  const value: AuthContextType = {
    user,
    isAuthenticated,
    loading,
    login,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * useAuth Hook
 *
 * Access auth context from components.
 * Throws error if used outside AuthProvider.
 *
 * @returns Auth context value
 */
export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }

  return context;
}