/// <reference types="jest" />

import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { HttpClient } from '../../src/utils/httpClient';
import { v4 as uuidv4 } from 'uuid';

// Mock uuidv4 to avoid importing in test
jest.mock('uuid', () => ({
  v4: jest.fn(() => 'test-request-id'),
}));

describe('HttpClient Retry Mechanism', () => {
  let mock: MockAdapter;
  let httpClient: HttpClient;

  beforeEach(() => {
    // Create mock adapter for the axios instance
    mock = new MockAdapter(axios);
    
    // Create HttpClient with test config
    httpClient = new HttpClient({
      baseURL: 'http://test-service',
      timeout: 30000,
    });
  });

  afterEach(() => {
    mock.restore();
  });

  describe('Retry Behavior', () => {
    it('Test 1: Should retry on 429 status code', async () => {
      const endpoint = '/test';
      let callCount = 0;
      
      mock.onPost(endpoint).reply(() => {
        callCount++;
        if (callCount <= 2) {
          return [429, { error: 'Rate limited' }];
        }
        return [200, { success: true }];
      });

      const result = await httpClient.post(endpoint, { data: 'test' });

      expect(result).toEqual({ success: true });
      expect(callCount).toBe(3);
    });

    it('Test 2: Should retry on 500-599 status codes', async () => {
      const endpoint = '/test';
      let callCount = 0;
      
      mock.onPost(endpoint).reply(() => {
        callCount++;
        if (callCount === 1) {
          return [500, { error: 'Internal server error' }];
        }
        if (callCount === 2) {
          return [503, { error: 'Service unavailable' }];
        }
        return [200, { success: true }];
      });

      const result = await httpClient.post(endpoint, { data: 'test' });

      expect(result).toEqual({ success: true });
      expect(callCount).toBe(3);
    });

    it('Test 3: Should retry on network errors (5xx response)', async () => {
      const endpoint = '/test';
      let callCount = 0;
      
      mock.onPost(endpoint).reply(() => {
        callCount++;
        if (callCount === 1) {
          // Simulate server error which triggers retry
          return [502, { error: 'Bad Gateway' }];
        }
        return [200, { success: true }];
      });

      const result = await httpClient.post(endpoint, { data: 'test' });

      expect(result).toEqual({ success: true });
      expect(callCount).toBe(2);
    });
  });

  describe('Exponential Backoff', () => {
    it('Test 5: Retry delay should follow exponential backoff (1s, 2s, 4s)', async () => {
      const endpoint = '/test';
      let callCount = 0;

      // Mock to fail 3 times, then succeed
      mock.onPost(endpoint).reply(() => {
        callCount++;
        if (callCount <= 3) {
          return [429, { error: 'Rate limited' }];
        }
        return [200, { success: true }];
      });

      const startTime = Date.now();

      await httpClient.post(endpoint, { data: 'test' });

      const totalTime = Date.now() - startTime;

      // Total time should be approximately 1s + 2s + 4s = 7s
      // Allow some margin (±500ms) for test execution
      expect(totalTime).toBeGreaterThanOrEqual(6500);
      expect(totalTime).toBeLessThanOrEqual(8000);
      expect(callCount).toBe(4);
    });
  });

  describe('Max Retry Limit', () => {
    it('Test 6: Should stop after max 3 retries', async () => {
      const endpoint = '/test';
      let callCount = 0;

      // Mock to fail indefinitely (more than max retries)
      mock.onPost(endpoint).reply(() => {
        callCount++;
        return [429, { error: 'Rate limited' }];
      });

      await expect(httpClient.post(endpoint, { data: 'test' }))
        .rejects.toThrow();

      // Should have attempted 4 times: 1 initial + 3 retries
      expect(callCount).toBe(4);
    });
  });

  describe('No Retry Conditions', () => {
    it('Test 7: Should NOT retry on 4xx client errors (except 429)', async () => {
      const endpoint = '/test';
      let callCount = 0;
      
      mock.onPost(endpoint).reply(() => {
        callCount++;
        return [400, { error: 'Bad request' }];
      });

      await expect(httpClient.post(endpoint, { data: 'test' }))
        .rejects.toThrow();

      // Should only attempt once
      expect(callCount).toBe(1);
    });

    it('Test 8: Should NOT retry on 401 unauthorized', async () => {
      const endpoint = '/test';
      let callCount = 0;
      
      mock.onPost(endpoint).reply(() => {
        callCount++;
        return [401, { error: 'Unauthorized' }];
      });

      await expect(httpClient.post(endpoint, { data: 'test' }))
        .rejects.toThrow();

      expect(callCount).toBe(1);
    });

    it('Test 9: Should NOT retry on 404 not found', async () => {
      const endpoint = '/test';
      let callCount = 0;
      
      mock.onPost(endpoint).reply(() => {
        callCount++;
        return [404, { error: 'Not found' }];
      });

      await expect(httpClient.post(endpoint, { data: 'test' }))
        .rejects.toThrow();

      expect(callCount).toBe(1);
    });
  });
});