/** @type {import('jest').Config} */

// 在 Jest 启动时立即设置测试环境变量
process.env.OSS_ENDPOINT = 'local'; // 必须在任何模块加载前设置
process.env.LOCAL_STORAGE_PATH = '/Users/cc/sc/scholar-ai/backend-node/uploads'; // 必须在任何模块加载前设置
require('dotenv').config({ path: '.env.test' });
process.env.NODE_ENV = 'test';

module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: ['**/*.test.ts', '**/*.spec.ts'],
  testPathIgnorePatterns: ['/node_modules/', '/dist/'],
  transform: {
    '^.+\\.ts$': ['ts-jest', {
      useESM: false,
      isolatedModules: true,
    }],
  },
  transformIgnorePatterns: [
    'node_modules/(?!(node-fetch|data-uri-to-buffer|fetch-blob|formdata-polyfill|@aws-sdk)/)',
  ],
  moduleNameMapper: {
    '^node-fetch$': '<rootDir>/node_modules/node-fetch/lib/index.js',
  },
  moduleFileExtensions: ['ts', 'js', 'json'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/*.test.ts',
    '!src/index.ts',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  setupFiles: ['<rootDir>/tests/setup-env.js'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  verbose: true,
  clearMocks: true,
  restoreMocks: true,
};
