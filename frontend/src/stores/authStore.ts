/**
 * Auth Store - Zustand State Management
 *
 * Manages authentication state globally:
 * - user: Current authenticated user (null if not logged in)
 * - isAuthenticated: Boolean flag for auth status
 * - loading: Loading state during auth checks
 *
 * Note: This store is used by AuthContext, not directly by components.
 * Components should use useAuth() hook from AuthContext.
 */

import { create } from 'zustand';
import type { User } from '@/types';

/**
 * Auth state interface
 */
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;

  // Actions
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

/**
 * Auth store
 *
 * Provides global auth state management with Zustand.
 * Persists in memory only (no localStorage - Cookie-based auth).
 */
export const useAuthStore = create<AuthState>((set) => ({
  // Initial state
  user: null,
  isAuthenticated: false,
  loading: true, // Start with loading=true to prevent flash

  // Set user (updates isAuthenticated automatically)
  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user,
    }),

  // Set loading state
  setLoading: (loading) => set({ loading }),

  // Logout (clear user and auth flag)
  logout: () =>
    set({
      user: null,
      isAuthenticated: false,
    }),
}));