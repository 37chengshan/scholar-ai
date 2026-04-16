/**
 * User Store - Zustand State Management
 *
 * Manages user profile and settings state:
 * - profile: User profile data
 * - settings: User preferences (language, theme, defaultModel)
 *
 * Note: Separate from authStore to allow profile/settings updates
 * without affecting auth state.
 */

import { create } from 'zustand';
import type { User, UserSettings } from '@/types';

/**
 * User state interface
 */
interface UserState {
  profile: User | null;
  settings: UserSettings | null;

  // Actions
  setProfile: (profile: User) => void;
  setSettings: (settings: UserSettings) => void;
  clearUser: () => void;
}

/**
 * User store
 *
 * Manages user profile and settings separate from auth state.
 * Allows updating profile without affecting authentication.
 */
export const useUserStore = create<UserState>((set) => ({
  // Initial state
  profile: null,
  settings: null,

  // Set profile
  setProfile: (profile) => set({ profile }),

  // Set settings
  setSettings: (settings) => set({ settings }),

  // Clear all user data (on logout)
  clearUser: () =>
    set({
      profile: null,
      settings: null,
    }),
}));