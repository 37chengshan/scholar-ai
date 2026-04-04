/**
 * Test Setup File
 *
 * Global test configuration for Vitest:
 * - Import @testing-library/jest-dom matchers
 * - Mock localStorage for Cookie-based auth
 * - Mock fetch for API tests
 */

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock localStorage (not used in Cookie-based auth)
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};
global.localStorage = localStorageMock as any;

// Mock fetch for API tests
global.fetch = vi.fn();

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});