// TODO: Replace with real auth API
// Mock authentication service using localStorage

export interface MockUser {
  id: string;
  email: string;
  name: string;
  avatar?: string;
}

export interface MockAuthState {
  isAuthenticated: boolean;
  user: MockUser | null;
  token: string | null;
}

const AUTH_TOKEN_KEY = 'auth_token';
const AUTH_USER_KEY = 'auth_user';

// Mock user data
const MOCK_USER: MockUser = {
  id: 'user-001',
  email: 'researcher@scholar.ai',
  name: 'Dr. Zhang Wei',
  avatar: undefined,
};

// Get current auth state
export function getAuthState(): MockAuthState {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const userJson = localStorage.getItem(AUTH_USER_KEY);

  if (token && userJson) {
    try {
      const user = JSON.parse(userJson) as MockUser;
      return { isAuthenticated: true, user, token };
    } catch {
      return { isAuthenticated: false, user: null, token: null };
    }
  }

  return { isAuthenticated: false, user: null, token: null };
}

// Check if user is authenticated
export function isAuthenticated(): boolean {
  return localStorage.getItem(AUTH_TOKEN_KEY) !== null;
}

// Mock login function
export function mockLogin(email: string, password: string): Promise<{ success: boolean; user?: MockUser; error?: string }> {
  // Simulate async login
  return new Promise((resolve) => {
    setTimeout(() => {
      // For demo, accept any email/password
      if (email && password) {
        const token = 'mock_token_' + Date.now();
        localStorage.setItem(AUTH_TOKEN_KEY, token);
        localStorage.setItem(AUTH_USER_KEY, JSON.stringify(MOCK_USER));
        resolve({ success: true, user: MOCK_USER });
      } else {
        resolve({ success: false, error: 'Email and password required' });
      }
    }, 500);
  });
}

// Mock logout function
export function mockLogout(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

// Get current user
export function getCurrentUser(): MockUser | null {
  const userJson = localStorage.getItem(AUTH_USER_KEY);
  if (userJson) {
    try {
      return JSON.parse(userJson) as MockUser;
    } catch {
      return null;
    }
  }
  return null;
}